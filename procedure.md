# Local deployment and user management

This procedure uses the local setup below. Docker Desktop must be running. Run the shell commands in a terminal opened in the repository directory.

| Setting | Value |
| --- | --- |
| Application URL | [http://localhost:8051](http://localhost:8051) |
| Docker image | `mcs_bead_proj:dev` |
| Container name | `mcs_bead_dev` |
| Source data | `$HOME/microscopy-local/data` (read-only inside Docker) |
| Accounts and update history | `$HOME/microscopy-local/accounts` |
| Extracted records and backups | `$HOME/microscopy-local/output` |

## Deploy Locally

### 1. Prepare the folders

Run these commands in the same terminal you will use for the remaining steps. Re-run the three `export` commands whenever you open a new terminal.

```bash
export SOURCE_DATA_HOST="$HOME/microscopy-local/data"
export APP_STATE_HOST="$HOME/microscopy-local/accounts"
export OUTPUT_HOST="$HOME/microscopy-local/output"

mkdir -p "$SOURCE_DATA_HOST" "$APP_STATE_HOST" "$OUTPUT_HOST"
chmod 700 "$APP_STATE_HOST"
```

Manually place input files and their folders directly inside `$HOME/microscopy-local/data`. Preserve the required folder/file naming structure; do not create an extra `data` folder inside it. See [Data Preparation](README.md#data-preparation) and the [Centricity / Homogeneity naming conventions](naming_cases.md).

### 2. Build the Docker image

From the repository directory:

```bash
docker build -t mcs_bead_proj:dev .
```

### 3. Initialize the administrator once

**Skip this step if `$HOME/microscopy-local/accounts/app.db` already exists.** Rebuilding the image or recreating the container does not require another initialization.

```bash
docker run --rm -it \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  mcs_bead_proj:dev python3 auth.py init --username admin
```

Enter a password between 12 and 256 characters when prompted. This creates the initial `admin` account. Initialization refuses to overwrite an existing database.

### 4. Start the application

If `mcs_bead_dev` is already running, first stop it with `docker stop mcs_bead_dev`. Then run:

```bash
docker run -d --rm --name mcs_bead_dev \
  -p 127.0.0.1:8051:8050 \
  --mount "type=bind,source=$SOURCE_DATA_HOST,target=/mcs_bead_project/data,readonly" \
  --mount "type=bind,source=$OUTPUT_HOST,target=/output" \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  -e SOURCE_DATA_DIR=/mcs_bead_project/data \
  -e OUTPUT_ROOT=/output \
  -e SESSION_COOKIE_SECURE=false \
  mcs_bead_proj:dev
```

This binds the application to this machine's localhost interface. `SESSION_COOKIE_SECURE=false` is for local HTTP only. For deployment through a public URL, follow the HTTPS and production-server guidance in the [README](README.md#run-docker-container).

### 5. Open the application

Watch startup progress:

```bash
docker logs -f mcs_bead_dev
```

Initial extraction runs before the web application starts; HTML exports are not generated automatically. Once the server is running, open [http://localhost:8051](http://localhost:8051).

Sign in as `admin` with the password from step 3. You must choose a different password before accessing the dashboard, then sign in again with the new password.

Press **Ctrl+C** to leave the log viewer; this does not stop the container.

The resulting folders are:

```text
~/microscopy-local/
├── data/                 # Input files and images you provide
├── accounts/
│   └── app.db            # Accounts, roles and update history
└── output/
    ├── extracted/        # CSV, Excel, reports and optional HTML exports
    └── backup/           # Previous extracted records
```

### 6. Check access and update data

- In a private browser window, open the dashboard without signing in. It should redirect to the login page.
- As an admin, open [Updates](http://localhost:8051/admin). Use **Add new data** for newly added files, or **Rebuild all data** after editing, renaming or deleting existing files. A full rebuild asks for confirmation.
- The update page shows progress, logs and recent update history. Only one update can run at a time.
- After an update, filters refresh within 15 seconds. Press **Submit** on the dashboard to refresh a chart.

To check the mounts:

```bash
docker inspect mcs_bead_dev \
  --format '{{range .Mounts}}{{println .Destination "writable=" .RW}}{{end}}'
```

`/mcs_bead_project/data` should report `writable=false`; `/output` and `/app-state` should report `writable=true`.

Extraction keeps up to **20 backups** in `$HOME/microscopy-local/output/backup` by default. Older backups are pruned on the next extraction run. These contain previous records and reports; account-database backups are managed separately.

HTML generation is optional and does not run during startup or data updates. Dashboard charts continue to work directly from the extracted records. If you need HTML exports, wait for any data update to finish, then run:

```bash
docker exec mcs_bead_dev python3 generate_html.py
```

This reads `output/extracted/records.csv` and rebuilds the HTML exports in `output/extracted/`; it does not read the original input files. Existing HTML exports are left unchanged by data updates and may be out of date until you run this command. There is no HTML-generation button yet.

### 7. Stop, restart or apply code changes

To stop the application:

```bash
docker stop mcs_bead_dev
```

Because the container uses `--rm`, stopping it removes the container. The three host folders remain intact. To start again, repeat step 4 using the same paths; do not initialize the accounts again.

After code changes, rebuild the image with step 2, stop the old container, and repeat step 4. Rebuilding alone does not update a running container. Wait for any active data update to finish before stopping it.

To confirm persistence, create a user as described below, stop and recreate the container, then sign in with that user's current password. The account and update history should still be present. For backup and restore instructions, see [Account recovery and backups](README.md#account-recovery-and-backups).

## Manage User

Sign in as an administrator and open [Users](http://localhost:8051/admin/users), or select **Users** from the admin navigation.

| Access | Permissions |
| --- | --- |
| User | View the dashboard, data, charts and images; change their own password; sign out |
| Admin | All user permissions, plus run data updates and manage accounts |

### Add a user

1. Under **Add a user**, enter a username of 3–64 characters: lowercase letters, numbers, dots, underscores or hyphens. The first character must be a letter or number.
2. Enter a temporary password between 12 and 256 characters.
3. Select **User** or **Admin** under **Access**.
4. Click **Create user**.
5. Share the username and temporary password privately with the user.

The user must change the temporary password at first sign-in before accessing data. There is no self-registration or password-reset email service. For this localhost setup, test the new account in a private browser window on the same machine; the URL is not accessible from another computer.

### Change a user's role

1. Find the account under **Existing users**.
2. Change **Access** to **User** or **Admin**.
3. Leave **Reset password (optional)** empty to retain the current password.
4. Click **Save changes**.

Saving changes signs out that user's existing sessions. A regular user can view data but cannot access `/admin` or `/admin/users`.

### Disable or re-enable an account

1. Find the account under **Existing users**.
2. Clear **Account enabled** to disable it, or select it to re-enable it.
3. Click **Save changes**.

Disabling an account blocks login and invalidates existing sessions while retaining the user record. The last active administrator cannot be disabled or demoted.

### Reset a user's password

1. Find the account under **Existing users**.
2. Enter a new temporary password in **Reset password (optional)**.
3. Click **Save changes** and privately share the temporary password.

Existing sessions are signed out. The user must change the temporary password before accessing data again.

Users who know their current password can change it themselves through [Account](http://localhost:8051/account). Changing a password signs out all of that user's sessions.

### Recover administrator access

If the administrator cannot sign in, run this from the host while the container is running:

```bash
docker exec -it mcs_bead_dev python3 auth.py reset-admin --username admin
```

Replace `admin` if the administrator has a different username. Enter a new temporary password at the prompt, sign in, and change it when requested. This resets an existing administrator; it does not create a new account or erase other users.

After repeated incorrect passwords, an account is temporarily locked for five minutes. Wait before retrying, or have an administrator reset the password.
