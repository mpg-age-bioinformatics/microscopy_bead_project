"""Password-protected maintenance routes and a single background update worker."""

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import logging
import os
import subprocess
import sys
import threading

from flask import g, jsonify, render_template, request
from auth import admin_required

logger = logging.getLogger(__name__)


class UpdateManager:
    """One update at a time in the application's single server process."""

    def __init__(self, paths, store):
        self.store = store
        self.job_id = None
        self.paths = paths
        self.script_dir = Path(__file__).resolve().parent
        self.lock = threading.Lock()
        self.logs = deque(maxlen=200)
        self.state = {"status": "idle", "mode": None, "started_at": None,
                      "finished_at": None, "started_by": None, "message": "No update has run yet."}
        with self.store.connect() as db:
            db.execute("UPDATE updates SET status='failed',finished_at=?,message=? WHERE status='running'",
                       (datetime.now(timezone.utc).isoformat(), "Server restarted before this update finished. Review the data and retry."))
            previous = db.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 1").fetchone()
            if previous:
                self.state = dict(previous)

    def snapshot(self):
        with self.lock:
            with self.store.connect() as db:
                history = [dict(row) for row in db.execute("SELECT * FROM updates ORDER BY id DESC LIMIT 10")]
            return {**self.state, "logs": list(self.logs), "history": history}

    def start(self, mode, username):
        if mode not in ("incremental", "full"):
            raise ValueError("Choose incremental or full.")
        with self.lock:
            if self.state["status"] == "running":
                return False
            state = {"status": "running", "mode": mode,
                          "started_at": datetime.now(timezone.utc).isoformat(),
                          "finished_at": None, "started_by": username, "message": "Extracting data…"}
            with self.store.connect() as db:
                cursor = db.execute("INSERT INTO updates (mode,status,started_by,started_at,message) VALUES (?,?,?,?,?)",
                                    (mode, 'running', username, state['started_at'], state['message']))
                self.job_id = cursor.lastrowid
            self.logs.clear()
            self.state = state
            try:
                threading.Thread(target=self._run, args=(mode,), daemon=True).start()
            except Exception:
                self.state.update(status="failed", message="Could not start the update worker.")
                with self.store.connect() as db:
                    db.execute("UPDATE updates SET status='failed',finished_at=?,message=? WHERE id=?",
                               (datetime.now(timezone.utc).isoformat(), self.state['message'], self.job_id))
                raise
        return True

    def _run(self, mode):
        try:
            self.paths.validate()
            if not Path(self.paths.source_dir).is_dir():
                raise RuntimeError("The input data directory is unavailable. Check the Docker mount.")
            env = os.environ.copy()
            # An explicitly requested incremental run must override startup flags.
            env.pop("COMPLETE", None)
            env.pop("REFETCH", None)
            env["SOURCE_DATA_DIR"] = self.paths.source_dir
            env["OUTPUT_ROOT"] = self.paths.output_root
            command = [sys.executable, "-u", str(self.script_dir / "process_data.py"),
                       "--source-dir", self.paths.source_dir, "--output-root", self.paths.output_root]
            if mode == "full":
                command.append("--complete")
            warnings = self._execute(command, env)
            self._finish("warning" if warnings else "succeeded",
                         "Update finished with warnings. Review the log below." if warnings
                         else "Update complete. The dashboard can now use the latest records.")
        except Exception as exc:
            logger.exception("Data update failed")
            self._finish("failed", f"Update failed: {exc}")

    def _execute(self, command, env):
        warnings = False
        with subprocess.Popen(command, cwd=self.script_dir, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors="replace") as process:
            for line in process.stdout:
                line = line.rstrip()
                logger.info("update: %s", line)
                warnings |= "[WARNING]" in line or "[ERROR]" in line
                with self.lock:
                    self.logs.append(line[-4000:])
            if process.wait() != 0:
                raise RuntimeError(f"{Path(command[2]).name} exited with code {process.returncode}. See the log.")
        return warnings

    def _finish(self, status, message):
        with self.lock:
            self.state.update(status=status, message=message,
                              finished_at=datetime.now(timezone.utc).isoformat())
            try:
                with self.store.connect() as db:
                    db.execute("UPDATE updates SET status=?,message=?,finished_at=? WHERE id=?",
                               (status, message, self.state['finished_at'], self.job_id))
            except Exception:
                logger.exception("Could not save update history")
                self.state.update(status="warning", message=message + " Could not save update history.")


def register_admin(server, paths, store):
    manager = UpdateManager(paths, store)

    @server.route("/admin", strict_slashes=False)
    @admin_required
    def admin_page():
        return render_template("admin.html")

    @server.route("/admin/api/status")
    @admin_required
    def admin_status():
        return jsonify(manager.snapshot())

    @server.route("/admin/api/update", methods=["POST"])
    @admin_required
    def admin_update():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("mode") not in ("incremental", "full"):
            return jsonify(error="Choose incremental or full."), 400
        if body["mode"] == "full" and body.get("confirm") is not True:
            return jsonify(error="Confirm the full refetch first."), 400
        if not manager.start(body["mode"], g.user["username"]):
            return jsonify(error="An update is already running."), 409
        return jsonify(manager.snapshot()), 202

    return manager
