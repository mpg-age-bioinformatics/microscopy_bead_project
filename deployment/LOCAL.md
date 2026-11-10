# Local deployment

Run the application on your computer with Docker. For HTTPS access from other computers, use the [web deployment guide](README.md). Data preparation and interface features are documented in the [main README](../README.md).

Docker must be installed and running. Use Bash for the commands below; local builds and development commands run from the repository root.

## 1. Prepare the folders

Set these variables in the terminal used for the remaining steps. Repeat them when opening a new terminal:

```bash
export SOURCE_DATA_HOST="$HOME/microscopy-local/data"
export APP_STATE_HOST="$HOME/microscopy-local/accounts"
export OUTPUT_HOST="$HOME/microscopy-local/output"
export IMAGE="mpgagebioinformatics/mcs_bead_proj:web"

mkdir -p "$SOURCE_DATA_HOST" "$APP_STATE_HOST" "$OUTPUT_HOST"
chmod 700 "$APP_STATE_HOST"
```

Place your source files and folders directly inside `SOURCE_DATA_HOST`, following [Data preparation](../README.md#data-preparation). Do not create another `data` folder inside it. For an existing source directory or mounted share, set `SOURCE_DATA_HOST` to that directory instead; confirm it exists and is mounted before starting Docker.

| Host directory | Container path | Access |
| --- | --- | --- |
| `$SOURCE_DATA_HOST` | `/mcs_bead_project/data` | Read-only source files and images |
| `$APP_STATE_HOST` | `/app-state` | Writable accounts and update history |
| `$OUTPUT_HOST` | `/output` | Writable `extracted/` and `backup/` |

Keep accounts on a local filesystem, separate from network-mounted source data. Source data must not overlap the generated output directories.

## 2. Pull or build the image

To use the published application:

```bash
docker pull "$IMAGE"
```

Alternatively, to build the current checkout, set a local image name and build from the repository root:

```bash
export IMAGE="mcs_bead_proj:dev"
docker build -t "$IMAGE" .
```

Use the same `IMAGE` value for initialization and startup.

## 3. Initialize accounts once

**Skip this step if `$APP_STATE_HOST/app.db` already exists.**

```bash
docker run --rm -it \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  "$IMAGE" python3 auth.py init --username admin
```

Enter a password of 8–256 characters. Initialization refuses to overwrite existing accounts. For unattended initialization, the command also accepts `INITIAL_ADMIN_PASSWORD` through its environment; normal startup does not use it to reset accounts.

## 4. Start the application

If a previous `mcs_bead_dev` container is running, wait for active updates/exports to finish and stop it first.

```bash
docker run -d --rm --name mcs_bead_dev \
  -p 127.0.0.1:8051:8050 \
  --mount "type=bind,source=$SOURCE_DATA_HOST,target=/mcs_bead_project/data,readonly" \
  --mount "type=bind,source=$OUTPUT_HOST,target=/output" \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  -e SOURCE_DATA_DIR=/mcs_bead_project/data \
  -e OUTPUT_ROOT=/output \
  -e SESSION_COOKIE_SECURE=false \
  "$IMAGE"
```

The URL is accessible only from this computer. `SESSION_COOKIE_SECURE=false` is for local HTTP; use HTTPS and secure cookies for web deployment. The image runs Gunicorn with one worker and four threads. Keep one application container per output directory.

Watch startup:

```bash
docker logs -f mcs_bead_dev
```

Extraction runs before Gunicorn starts. After processing finishes and the server is listening, open [http://localhost:8051](http://localhost:8051). Sign in as `admin`, change the initial password, and sign in again. Press **Ctrl+C** to leave the logs without stopping the application.

See the main README for [dashboard features](../README.md#dashboard), [managing users](../README.md#manage-users), [data updates](../README.md#update-data) and [downloads](../README.md#downloads).

To confirm mount permissions:

```bash
docker inspect mcs_bead_dev \
  --format '{{range .Mounts}}{{println .Destination "writable=" .RW}}{{end}}'
```

The source should show `writable=false`; accounts and output should show `writable=true`.

## Stop, restart or update

Wait for active updates and exports to finish, then stop:

```bash
docker stop mcs_bead_dev
```

Because startup uses `--rm`, stopping removes the container, but all three host directories remain. To start again, repeat step 4 with the same variables and paths. Do not initialize accounts again.

To deploy a newer published image, pull it again before recreating the container. For local code changes, rebuild it first. Pulling or rebuilding alone does not change a running container.

## Account recovery and backups

To reset an existing administrator while the container is running:

```bash
docker exec -it mcs_bead_dev python3 auth.py reset-admin --username admin
```

Replace `admin` if needed. Enter a temporary password, sign in, and change it when prompted. This does not create an account or erase other users.

Back up accounts separately from extraction snapshots. Stop the application for a consistent database copy. The helper container below can read database files owned by the application container's root user:

```bash
docker stop mcs_bead_dev
export ACCOUNT_BACKUP_HOST="${APP_STATE_HOST}-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$ACCOUNT_BACKUP_HOST"

docker run --rm \
  --mount "type=bind,source=$APP_STATE_HOST,target=/state,readonly" \
  --mount "type=bind,source=$ACCOUNT_BACKUP_HOST,target=/backup" \
  alpine:3.22 cp -a /state/. /backup/
```

Then recreate the application using step 4. Store backups securely: they contain password hashes and the session-signing secret. Back up output and source files separately. For live account backups, use SQLite's backup API instead of copying an active database.

To restore accounts, stop the application, restore the saved account directory with its permissions preserved, and recreate the container with that directory mounted at `/app-state`. Do not run initialization on the restored database.

## Optional saved exports

The Downloads page generates Excel and HTML on request without keeping permanent exports. To explicitly save combined and individual HTML reports, wait for any data update to finish, then run:

```bash
docker exec mcs_bead_dev python3 generate_html.py
```

This reads the extracted CSV and writes `extracted/figures.html` and `extracted/html/` under `OUTPUT_HOST`; it does not re-read the source files. These saved exports are not refreshed automatically during updates and are not used by the download buttons.

For a CLI workflow that needs a saved workbook, pass `--excel-max-rows 100000` to `process_data.py` with your source/output options. The default extraction skips Excel generation.

## Existing installations and path configuration

When the new path variables are unset, `DATA_ROOT=/mcs_bead_project` retains the legacy layout: `data/` for input and `extracted/` and `backup/` for output. `python3 process_data.py -d /path/to/project` remains supported.

To migrate existing output, stop the old container and copy its `extracted/` and `backup/` directories into `OUTPUT_HOST`, preserving permissions and timestamps. Reuse the existing account directory. Keep the original files until the new setup is verified.

Keep the container-side source path stable at `/mcs_bead_project/data`: records contain source paths. If that internal path changes, run a full rebuild; an incremental update would retain old paths and can add duplicate records. Moving host storage while keeping the container paths unchanged does not require rebuilding records.

| Variable | Purpose / default |
| --- | --- |
| `SOURCE_DATA_DIR` | Input directory; defaults to `$DATA_ROOT/data` |
| `OUTPUT_ROOT` | Parent of `extracted/` and `backup/`; defaults to `$DATA_ROOT` |
| `APP_STATE_DIR` | Local account storage; defaults to `/app-state` |

CLI `--source-dir` and `--output-root` override the corresponding environment variables. `-d` supplies the legacy fallback root. The `--backup` extraction option overrides the default retention of 20 snapshots.

## Development

Clone the repository if needed:

```bash
git clone https://github.com/mpg-age-bioinformatics/microscopy_bead_project.git
cd microscopy_bead_project
```

Follow the setup above, choosing the local image build. To use code directly from the checkout, add this mount to the step 4 `docker run` command before `"$IMAGE"`:

```bash
--mount "type=bind,source=$PWD,target=/app,readonly"
```

Restart the container after code changes; Gunicorn does not automatically reload them. Rebuild the image when dependencies change.

For direct Python development, install `requirements.txt` in a virtual environment. With the host path variables set as in step 1, initialize accounts once if needed:

```bash
APP_STATE_DIR="$APP_STATE_HOST" python3 auth.py init --username admin
```

Then start the development server:

```bash
APP_STATE_DIR="$APP_STATE_HOST" \
SOURCE_DATA_DIR="$SOURCE_DATA_HOST" \
OUTPUT_ROOT="$OUTPUT_HOST" \
SESSION_COOKIE_SECURE=false \
python3 app.py
```

Direct Python startup uses port 8050 and Flask's development server; it does not run startup extraction. Prepare records first, or use an admin update after sign-in. If accounts were created by Docker, ensure your local Python user has access to the state files. Use this mode only on a trusted development machine.

Standalone extraction and HTML commands are also available:

```bash
python3 process_data.py --source-dir "$SOURCE_DATA_HOST" --output-root "$OUTPUT_HOST"
SOURCE_DATA_DIR="$SOURCE_DATA_HOST" OUTPUT_ROOT="$OUTPUT_HOST" python3 generate_html.py
```

Do not run separate extraction commands during an interface update.

## Troubleshooting

- **Cannot open localhost:** run `docker ps` and `docker logs -f mcs_bead_dev`. Wait for extraction and Gunicorn startup. Use port **8051** for the Docker command above; 8050 is the internal container port.
- **Port already in use:** stop the conflicting service or change the host side of `127.0.0.1:8051:8050`, then use that port in the browser.
- **Container exits and disappears:** `--rm` removes stopped containers. Repeat the startup command without `-d` to see the error directly.
- **Mount missing or permission denied:** confirm the host directory exists and any network share is mounted. On macOS, check Docker Desktop's file-sharing permissions for the source path. Use a local source folder if share access remains unavailable.
- **Memory pressure:** check Docker Desktop's resource allocation and increase it if necessary. Exit code 137 indicates the process was killed and can result from an out-of-memory condition; it is not proof by itself. Extraction skips Excel generation by default.
- **Account storage not ready:** confirm `APP_STATE_HOST` points to the intended initialized database. Initialize only a new installation; do not replace an existing account directory.
- **No new microscope in filters:** check the [naming scheme](../README.md#data-preparation), add actual `.xls` files, and run an admin update. Empty folders are not enough.
