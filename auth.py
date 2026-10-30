"""Local accounts and sessions, backed by an explicitly initialized SQLite file."""

from collections import OrderedDict
from contextlib import contextmanager
from datetime import timedelta
from functools import wraps
from pathlib import Path
import argparse
import hmac
import os
import re
import secrets
import sqlite3
import time
import threading

from flask import abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def validate_password(password):
    if not 12 <= len(password) <= 256:
        raise ValueError("Use a password between 12 and 256 characters.")


def validate_username(username):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", username):
        raise ValueError("Use 3–64 lowercase letters, numbers, dots, underscores or hyphens for the username.")


class AccountStore:
    def __init__(self):
        directory = Path(os.environ.get("APP_STATE_DIR", "/app-state"))
        if not directory.is_dir():
            raise RuntimeError("APP_STATE_DIR must be an existing local folder mounted from the host.")
        self.path = directory / "app.db"
        self.dummy_hash = generate_password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def connect(self):
        # mode=rw prevents a missing mount/database from silently resetting accounts.
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self, username, password):
        validate_username(username)
        validate_password(password)
        # Exclusive creation: initial credentials can never overwrite existing accounts.
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with self.connect() as db:
                db.executescript('''
                    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','admin')),
                        active INTEGER NOT NULL DEFAULT 1, must_change INTEGER NOT NULL DEFAULT 1,
                        version INTEGER NOT NULL DEFAULT 1,
                        failures INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0
                    );
                    CREATE TABLE updates (
                        id INTEGER PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL,
                        started_by TEXT NOT NULL, started_at TEXT NOT NULL,
                        finished_at TEXT, message TEXT NOT NULL
                    );
                ''')
                db.execute("INSERT INTO settings VALUES ('secret_key', ?)", (secrets.token_hex(32),))
                db.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,'admin')",
                           (username, generate_password_hash(password)))
        except Exception:
            self.path.unlink(missing_ok=True)
            raise

    def secret_key(self):
        with self.connect() as db:
            return db.execute("SELECT value FROM settings WHERE key='secret_key'").fetchone()[0]

    def user(self, user_id):
        with self.connect() as db:
            return db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    def users(self):
        with self.connect() as db:
            return db.execute("SELECT id,username,role,active,must_change FROM users ORDER BY username").fetchall()

    def authenticate(self, username, password):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if not user or not user['active'] or user['locked_until'] > time.time():
                check_password_hash(self.dummy_hash, password)
                return None
            if not check_password_hash(user['password_hash'], password):
                failures = user['failures'] + 1
                db.execute("UPDATE users SET failures=?,locked_until=? WHERE id=?",
                           (failures, time.time() + 300 if failures >= 5 else 0, user['id']))
                return None
            db.execute("UPDATE users SET failures=0,locked_until=0 WHERE id=?", (user['id'],))
            return user

    def add_user(self, username, password, role):
        validate_username(username)
        validate_password(password)
        if role not in ('user', 'admin'):
            raise ValueError("Choose a valid role.")
        with self.connect() as db:
            try:
                db.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                           (username, generate_password_hash(password), role))
            except sqlite3.IntegrityError as exc:
                raise ValueError("That username already exists.") from exc

    def edit_user(self, user_id, role, active, password):
        if role not in ('user', 'admin'):
            raise ValueError("Choose a valid role.")
        password_hash = None
        if password:
            validate_password(password)
            password_hash = generate_password_hash(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not user:
                raise ValueError("User not found.")
            count = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]
            if user['role'] == 'admin' and user['active'] and count == 1 and (role != 'admin' or not active):
                raise ValueError("Keep at least one active administrator.")
            db.execute("UPDATE users SET role=?,active=?,version=version+1 WHERE id=?", (role, active, user_id))
            if password_hash:
                db.execute("UPDATE users SET password_hash=?,must_change=1,failures=0,locked_until=0 WHERE id=?",
                           (password_hash, user_id))

    def change_password(self, user_id, current, password):
        validate_password(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not user or not check_password_hash(user['password_hash'], current):
                raise ValueError("Current password is incorrect.")
            if check_password_hash(user['password_hash'], password):
                raise ValueError("Choose a different password.")
            db.execute("UPDATE users SET password_hash=?,must_change=0,version=version+1 WHERE id=?",
                       (generate_password_hash(password), user_id))

    def recover_admin(self, username, password):
        validate_password(password)
        with self.connect() as db:
            result = db.execute("UPDATE users SET password_hash=?,active=1,must_change=1,version=version+1,"
                                "failures=0,locked_until=0 WHERE username=? AND role='admin'",
                                (generate_password_hash(password), username))
            if not result.rowcount:
                raise ValueError("No administrator with that username.")


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user['role'] != 'admin':
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def register_auth(server):
    store = AccountStore()
    server.config.update(
        SECRET_KEY=store.secret_key(),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() != 'false',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8), SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    server.jinja_env.globals['csrf_token'] = csrf_token
    login_attempts = OrderedDict()
    attempts_lock = threading.Lock()

    @server.before_request
    def restrict_access():
        g.user = None
        if session.get('user_id'):
            user = store.user(session['user_id'])
            if user and user['active'] and user['version'] == session.get('version'):
                g.user = user
            else:
                session.clear()
        if request.endpoint == 'static':
            return None  # Only application CSS/JS; never dataset files.
        is_api = request.path.startswith('/admin/api/') or request.path.startswith('/_dash-')
        if request.endpoint != 'login' and not g.user:
            if is_api:
                return jsonify(error="Please sign in again."), 401
            return redirect(url_for('login'))
        if g.user and g.user['must_change'] and request.endpoint not in ('account', 'logout'):
            if is_api:
                return jsonify(error="Change your temporary password on the Account page first."), 403
            return redirect(url_for('account'))
        # Dash POST callbacks only read data. All state-changing routes require CSRF.
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.path != '/_dash-update-component':
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            expected = session.get('csrf', '')
            if not expected or not hmac.compare_digest(token.encode(), expected.encode()):
                if is_api:
                    return jsonify(error="Session expired. Reload the page and try again."), 403
                abort(400, "Session expired. Reload the page and try again.")

    @server.after_request
    def security_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @server.route('/login', methods=['GET', 'POST'])
    def login():
        if g.user:
            return redirect('/account' if g.user['must_change'] else '/')
        if request.method == 'POST':
            # Bounded per-peer throttle; do not trust client-supplied forwarded IPs.
            with attempts_lock:
                now = time.monotonic()
                attempts = [t for t in login_attempts.pop(request.remote_addr, []) if now - t < 60]
                limited = len(attempts) >= 20
                if not limited:
                    attempts.append(now)
                login_attempts[request.remote_addr] = attempts
                if len(login_attempts) > 1024:
                    login_attempts.popitem(last=False)
            if limited:
                flash("Too many sign-in attempts. Please wait one minute.", 'error')
                return render_template('login.html'), 429, {'Retry-After': '60'}
            password = request.form.get('password', '')
            user = store.authenticate(request.form.get('username', '').strip().lower(), password) if len(password) <= 256 else None
            if user:
                session.clear()
                session.permanent = True
                session.update(user_id=user['id'], version=user['version'])
                return redirect('/account' if user['must_change'] else '/')
            flash("Sign-in failed. Check your credentials, or wait five minutes after repeated failures.", 'error')
        return render_template('login.html')

    @server.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @server.route('/account', methods=['GET', 'POST'])
    def account():
        if request.method == 'POST':
            try:
                if request.form.get('password') != request.form.get('confirm_password'):
                    raise ValueError("The new passwords do not match.")
                store.change_password(g.user['id'], request.form.get('current_password', ''), request.form.get('password', ''))
                session.clear()
                flash("Password changed. Sign in with your new password.", 'success')
                return redirect(url_for('login'))
            except ValueError as exc:
                flash(str(exc), 'error')
        return render_template('account.html')

    @server.route('/admin/users', methods=['GET', 'POST'])
    @admin_required
    def users():
        if request.method == 'POST':
            try:
                if request.form.get('action') == 'create':
                    store.add_user(request.form.get('username', '').strip().lower(), request.form.get('password', ''),
                                   request.form.get('role'))
                    flash("User created. Share the temporary password privately.", 'success')
                elif request.form.get('action') == 'edit':
                    store.edit_user(int(request.form.get('user_id', '0')), request.form.get('role'),
                                    request.form.get('active') == 'on', request.form.get('password', ''))
                    flash("User saved. Their existing sessions have been signed out.", 'success')
                else:
                    raise ValueError("Unknown action.")
            except ValueError as exc:
                flash(str(exc), 'error')
            return redirect(url_for('users'))
        return render_template('users.html', users=store.users())

    return store


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Initialize, check or recover local accounts in APP_STATE_DIR.")
    parser.add_argument('action', choices=['init', 'check', 'reset-admin'])
    parser.add_argument('--username', default='admin')
    args = parser.parse_args()
    try:
        store = AccountStore()
        if args.action == 'check':
            store.secret_key()
        else:
            from getpass import getpass
            password = os.environ.get('INITIAL_ADMIN_PASSWORD') or getpass('Admin password (at least 12 characters): ')
            if args.action == 'init':
                store.initialize(args.username, password)
            else:
                store.recover_admin(args.username, password)
        print('Account storage ready.' if args.action == 'check' else 'Account setup complete.')
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Account storage error: {exc}\nUse auth.py init once with the intended host folder mounted.\n')
