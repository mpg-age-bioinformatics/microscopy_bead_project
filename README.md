# microscopy_bead_project

For the local setup using `$HOME/microscopy-local/data`, `accounts` and `output`, follow [Deploy Locally and Manage User](procedure.md).

### Features
- Parse data from all the input excel files and store required data in a CSV file
- Report files which are not parseable or with no target data
- Download a combined interactive HTML report on request, or explicitly save exports using `generate_html.py`
- Interactive interface (in browser) with option filters and outputs including figures, data, deviations and images

### Get Started

Prerequisite: Docker

#### Data Storage

Create a data folder where the input data should be stored
```
mkdir -p /Volumes/group_fi/group/Microscopy/Metrology/mcs_bead_project/data
```

Please store all your input data inside `data` directory with proper format ([check data preparation](https://github.com/mpg-age-bioinformatics/microscopy_bead_project/?tab=readme-ov-file#data-preparation)). For the Centricity / Homogeneity (`TCenHom`) test, follow the dedicated naming convention in [naming_cases.md](naming_cases.md). Of course, you can choose a different data folder of your preference. However, you have to modify the commands accordingly in that case.

#### Build and initialize local accounts

Build the image from this checkout:

```bash
docker build -t mcs_bead_proj .
```

Choose a **local host folder** for account storage, separate from any network-mounted microscopy data. Create it once and initialize the first administrator:

```bash
export APP_STATE_HOST="$HOME/microscopy-app-state"
mkdir -p "$APP_STATE_HOST"
chmod 700 "$APP_STATE_HOST"
docker run --rm -it \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  mcs_bead_proj python3 auth.py init --username admin
```

The command prompts for a password of at least 12 characters. It creates `app.db` with password hashes, roles, a session-signing secret and update history. Initialization refuses to overwrite an existing database. The initial administrator must change their password at first sign-in. For unattended initialization, supply `INITIAL_ADMIN_PASSWORD` to this one-time command; normal startup does not read it or reset any credentials.

#### Run Docker Container

Use three separate host folders: read-only source data, writable extraction outputs, and local account storage. The source mount points at the folder that directly contains the input data (the previous `data/` folder).

```bash
export SOURCE_DATA_HOST="/Volumes/group_fi/group/Microscopy/Metrology/mcs_bead_project/data"
export OUTPUT_HOST="$HOME/microscopy-output"
mkdir -p "$OUTPUT_HOST"

docker run -d --rm --name mcs_bead_proj -p 127.0.0.1:8050:8050 \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  --mount "type=bind,source=$SOURCE_DATA_HOST,target=/mcs_bead_project/data,readonly" \
  --mount "type=bind,source=$OUTPUT_HOST,target=/output" \
  -e SOURCE_DATA_DIR=/mcs_bead_project/data -e OUTPUT_ROOT=/output \
  -e SESSION_COOKIE_SECURE=false \
  mcs_bead_proj
```

| Host folder | Container path | Access |
| --- | --- | --- |
| `$SOURCE_DATA_HOST` | `/mcs_bead_project/data` | Read-only inputs and images |
| `$OUTPUT_HOST` | `/output` | Writable `extracted/` and `backup/` |
| `$APP_STATE_HOST` | `/app-state` | Writable local SQLite accounts and update history |

The extractor never writes to the source directory. CSV, reports, staging files and extraction backups go under the output mount. Excel and HTML downloads are generated temporarily from CSV and sent to the browser; neither is saved in the output folder. The manual HTML script can still explicitly save exports there. Image previews are read directly from the source mount. Keep the account mount on local storage as described above.

Open [http://localhost:8050/](http://localhost:8050/). The dashboard, images and backend requests all require sign-in. The container extracts data before starting the web application; it does not generate HTML exports automatically. Check progress with `docker logs -f mcs_bead_proj`.

`SESSION_COOKIE_SECURE=false` is for local HTTP development only. For a hosted URL, use HTTPS and leave the default secure cookie setting enabled. Deploy with a production WSGI server configured for **one process with multiple request threads** behind your reverse proxy; the included `python3 app.py` command is a local development server. Keep the application's port private to that proxy. The app does not trust forwarded identity or IP headers; its per-peer login throttle is shared by users behind the same proxy, so configure appropriate login rate limits at the proxy for a larger deployment.

Reuse the same host folder when recreating or upgrading the container. Removing the container, including with `--rm`, does not delete that folder. `--mount` refuses a missing host source directory; the app also refuses a missing or uninitialized database. It never automatically creates a new administrator at startup.

#### Existing installations and path configuration

Old mounts remain supported: when the new variables are unset, `DATA_ROOT=/mcs_bead_project` still uses `data/` for input and `extracted/` plus `backup/` for output. The legacy extractor command `python3 process_data.py -d /path/to/project` also continues to work.

To migrate existing extracted records, stop the old container and copy its `extracted/` and `backup/` directories into `$OUTPUT_HOST` before starting with the separate mounts. Leave the originals intact until you verify the new setup. Continue mounting the same source files at `/mcs_bead_project/data`, as shown above: records contain source paths, so keeping this path stable preserves incremental processing and image links. If you change the **container-side source path**, run a full refetch to replace old paths; a plain incremental run would retain old rows and add duplicates at the new paths.

Configuration is shared by the dashboard, Docker startup, HTML generation and admin updates:

- `SOURCE_DATA_DIR`: the input directory itself, defaulting to `$DATA_ROOT/data`.
- `OUTPUT_ROOT`: the writable parent of `extracted/` and `backup/`, defaulting to `$DATA_ROOT`.
- `APP_STATE_DIR`: local account storage, defaulting to `/app-state`; independent of both data mounts.

For CLI extraction, `--source-dir` and `--output-root` override the corresponding environment variables. `-d` supplies the legacy fallback root. For example:

```bash
python3 process_data.py --source-dir /path/to/input-data --output-root /path/to/output
SOURCE_DATA_DIR=/path/to/input-data OUTPUT_ROOT=/path/to/output python3 generate_html.py
```

Source data must not overlap the generated `extracted/` or `backup/` directories; invalid configurations fail before processing.

#### Update/Add Data

With the admin interface enabled, open `/admin` to run either update mode without restarting the container (see below).

Use the **Updates** page at `/admin` after adding or changing input files. Restarting the container also runs incremental extraction:

```bash
docker restart mcs_bead_proj
```

Incremental extraction processes only previously unseen paths. Use a full refetch after editing, deleting or renaming existing files, or to retry files previously reported as unprocessed/dataless. A schema change also triggers a full rebuild automatically.

#### Admin interface and accounts

- **User:** can view data, charts and images, change their password and sign out.
- **Admin:** can also download extracted records and reports, run updates and manage accounts at `/admin/users`.
- Admins create users with a temporary password and either role. Users must change temporary passwords before accessing data. There is no self-registration or email service.
- Admins can change roles, disable accounts and reset passwords. Saving account changes invalidates that user's existing sessions. The last active administrator cannot be disabled or demoted.
- Passwords are stored as salted scrypt hashes. Sessions expire after eight hours. State-changing forms and update requests require CSRF tokens. Five incorrect password attempts lock an account for five minutes; sign-in requests are also throttled per connecting IP.

The Updates page provides **Add new data** and **Rebuild all data** (with confirmation). It shows status, timestamps and the latest 200 log lines. Only one update runs at a time. Update history records the initiating username, mode and outcome in SQLite and survives container replacement. Live logs remain in memory; process output is also available in `docker logs`.

Extraction publishes records atomically, leaving the previous CSV available until extraction finishes. Filters refresh within 15 seconds; press **Submit** to refresh an existing chart. Full refetches use the existing data-backup policy, and an unsuccessful backup aborts extraction. Updates finish after extraction; HTML exports are optional and are not regenerated automatically. Dashboard charts still use the latest records.

Keep one application process and one container writing to a given data folder. Do not run a separate CLI extraction during an admin update. Restarting the container interrupts any running update; the next startup marks that history entry as interrupted/failed.

#### Downloads

Sign in as an administrator and open `/download` (for the local setup, [http://localhost:8051/download](http://localhost:8051/download)). The page, direct file downloads and Excel/HTML generation routes are admin-only; regular users receive HTTP 403 even when using a direct URL. Available downloads:

- **records.csv**: the latest published records, downloaded directly.
- **Excel**: generated from the current CSV when requested; it never serves a previously saved `records.xlsx`.
- **unprocessed.txt** and **dataless.txt**: the latest published processing reports. Empty reports are valid downloads.
- **HTML report**: generated from the current CSV on request, with interactive figures and deviation tables for all microscopes and objectives. It includes Plotly once and opens offline in a browser.

Unavailable files have disabled buttons. Only these named exports are accessible; source files, backups and account storage are not exposed by this page.

Automatic Excel generation is disabled during startup and admin updates. The download uses streaming conversion to a temporary workbook. Excel and HTML share a lock: only one export is generated at a time per application process. It reads a complete CSV snapshot even if an update publishes new records during conversion. Cell values are preserved as text, including values that look like spreadsheet formulas. If Excel's row, column or cell limits are exceeded, download CSV instead.

Generated downloads use temporary files that are closed and removed after the response completes or fails; no permanent export is saved. HTML is written figure by figure rather than accumulating the entire report in memory. Plot generation still loads the CSV into memory, so large datasets can take time and memory to process. The report notes any combinations for which no figure could be produced. Older `records.xlsx` files in the output directory are left untouched and may be stale; the Downloads page does not use them. For a CLI workflow that explicitly needs a saved workbook, opt in with `python3 process_data.py ... --excel-max-rows 100000` (replace `...` with your source/output options).

#### Optional HTML exports

For a fresh report without storing an export on the server, use **Generate and download HTML** on `/download`.

The standalone `generate_html.py` script remains available when you explicitly want saved combined and individual exports. Run it after an update finishes:

```bash
docker exec mcs_bead_proj python3 generate_html.py
```

For the local procedure's container, use `mcs_bead_dev` instead. The script reads the extracted `records.csv` and writes `extracted/figures.html` and `extracted/html/` under the configured output mount. It does not re-read the source data. Existing saved exports remain unchanged during startup, data updates and downloads. The download button always uses the current CSV and never serves these older files.

#### Account recovery and backups

To reset an existing administrator from the host:

```bash
docker exec -it mcs_bead_proj python3 auth.py reset-admin --username admin
```

This prompts for a new temporary password and signs out that account's existing sessions. Host/Docker access is required. It does not create a new account.

Back up the account database separately from microscopy records. For the simplest consistent backup, stop the application before copying the state folder (the container uses `--rm`, so recreate it afterwards using the same mount):

```bash
docker stop mcs_bead_proj
cp -a "$APP_STATE_HOST" "${APP_STATE_HOST}-backup-$(date +%Y%m%d-%H%M%S)"
```

Store backups securely: they contain password hashes and the session-signing secret. To restore, stop the application, restore the saved state directory and start a container with that directory mounted at `/app-state`. For live backups, use SQLite's backup API instead of copying an active database file.

For local Python development, create a state directory outside the repository, run `APP_STATE_DIR=/local/state python3 auth.py init`, then start with `APP_STATE_DIR=/local/state SOURCE_DATA_DIR=/path/to/input-data OUTPUT_ROOT=/path/to/output SESSION_COOKIE_SECURE=false python3 app.py`.

#### Stop Docker Container

To stop the running container:
```
docker stop mcs_bead_proj
```

#### Development

Clone `microscope_bead_project` repo
```
git clone https://github.com/mpg-age-bioinformatics/microscopy_bead_project.git
```
or download the repo

Navigate to the repo directory (e.g. `cd microscope_bead_project`) and the run docker build:
```
docker build -t mcs_bead_proj .
```

Mounting the scripts enables local development. Reuse the initialized account folder and source/output variables from the setup above:
```
docker run --rm --name mcs_bead_proj -p 127.0.0.1:8050:8050 \
  --mount "type=bind,source=$APP_STATE_HOST,target=/app-state" \
  --mount "type=bind,source=$SOURCE_DATA_HOST,target=/mcs_bead_project/data,readonly" \
  --mount "type=bind,source=$OUTPUT_HOST,target=/output" \
  -e SOURCE_DATA_DIR=/mcs_bead_project/data -e OUTPUT_ROOT=/output \
  -e SESSION_COOKIE_SECURE=false -v "$(pwd):/app" mcs_bead_proj
```

### Components

#### Data Preparation

This program extracts the data from the excel (`.xls`) files, stored in the `data` folder.

The naming scheme, the extractor will look for is: `<date>_M<microscope>_O<objective>_T<test>_S<bead_size>_B<bead_number>`. Either the filename itself or any parent folders of the file should contain the naming scheme. For example, from both of the followings, data can be extracted:
```
/Path/A/B/C/20250108_MAndorDragonfly_O100x1.45_TChromDual_S1.0_B0_other_text.xls
/Path/20250108_MAndorDragonfly_O100x1.45_TChromDual_S1.0_B0/A/B/file.xls
```

The simplest way of preparing data possibly be to just modify the folder name in `Bead` level directory that complies with `<date>_M<microscope>_O<objective>_T<test>_S<bead_size>_B<bead_number>` format, and leave the rest as it is.
Also, please note, the <date> should contain the format of `YYYYMMDD`.

#### Microscopy Bead Project App

Web app can be accessed from your browser with: http://localhost:8050/

Filter Options: Microscope, Objective, Test, Bead Size, Bead Number, Date Range, Consider Previous Values for Line Deviation, Warning Percentage

Output Tabs:
- Figure (plotly output diagram)
- Data (data table from inputs that generates the diagram)
- Deviation (data table depicts the deviations in different lines)
- Image (related bead images)

#### Extracted

Extracted files are stored in `$OUTPUT_HOST/extracted` on the host (`/output/extracted` in the recommended container setup). With the legacy configuration, they remain in `$DATA_ROOT/extracted`.

`extracted` directory contains the following:
- `records.csv`: primary file that stores all the fetched records from the input directory
- `records.xlsx`: optional saved workbook, only created when extraction explicitly enables `--excel-max-rows`; normally download a freshly generated Excel file through `/download`
- `dataless.txt`: contains directories where no target data was found
- `unprocessed.txt`: contains directories that could not be processed to fetch data
- `figures.html`: optional combined figure export, created by manually running `generate_html.py`
- `html`: directory for optional individual figure exports

#### Backup

Extraction backups are stored in `$OUTPUT_HOST/backup` (`/output/backup` in the container), or `$DATA_ROOT/backup` with the legacy configuration. The latest 20 backups are kept by default; older ones are pruned on the next extraction run. The CLI `--backup` option can override this limit. Stop the application before restoring previous records into the corresponding `extracted/` directory. These data backups are separate from account-database backups.

### Troubleshooting

#### Preparing Docker on your laptop

- **Give Docker enough resources.** The data folder can be large and keeps growing, so allocate sufficient memory (and CPU/disk) to Docker under **Docker Desktop → Settings → Resources** — increasing the **Memory** limit (e.g. to 8 GB or more) is the most important and helps avoid out-of-memory crashes (exit code `137`). Apply & Restart after changing it.
- **Make sure the data path is accessible.** Before running, confirm the folder you pass to `-v` (e.g. `/Volumes/group_fi/.../mcs_bead_project`) actually **exists and is reachable from your machine**. If it lives on a network share, **mount/connect it first** (e.g. in Finder) — if Docker cannot reach the path you will get a `mount source path ... permission denied` or "no such file or directory" error.
- **Data on a network drive (macOS):** if your data folder lives on a mounted network share (e.g. `/Volumes/group_fi/...`), Docker may need explicit permission to see it:
  - Make sure the share is actually **mounted in Finder** before you run `docker`.
  - Add the path (if `/Volumes` is not already there) under **Docker Desktop → Settings → Resources → File Sharing** (e.g. `/Volumes/group_fi`), then **Apply & Restart**.
  - If it still fails, grant **Docker Desktop** *Full Disk Access* (System Settings → Privacy & Security), or use a **local** folder for the `-v` mount instead of the network drive.

#### "permission denied" errors

- `error while creating mount source path '...': ... permission denied` — Docker cannot access the **mounted folder** (commonly a network drive). See the File Sharing notes above; this is *not* an image or daemon problem.

#### Cannot open http://localhost:8050/

1. **Is the container running?** Run `docker ps` and look for `mcs_bead_proj`. If it is not listed, it has stopped.
2. **Give the first run time.** On startup the container scans all data and builds the records *before* the web app starts — this can take some time on large or network folders. The page is only available once that finishes.
3. **Check the logs:** `docker logs mcs_bead_proj` (add `-f` to follow live). Any error or crash is reported there.
4. **Crashed and disappeared?** The `docker run` command uses `--rm`, so a crashed container is removed automatically. Re-run **without** `-d` to watch the live output, or read the logs before it exits.
5. **Port already in use:** if something else uses port 8050, map a different one, e.g. `-p 8051:8050`, and open http://localhost:8051/ (or simply free up the 8050 port by stoping the other container/service).

#### General health checks

- `docker ps` / `docker ps -a` — see running vs. exited containers. Note the **exit code**: `137` means the container ran **out of memory**.
- `docker logs mcs_bead_proj` — application logs, including the data-processing summary, warnings, and errors.
- **Out of memory (exit 137):** increase Docker Desktop's memory limit (Settings → Resources). Extraction streams output and no longer generates Excel automatically. Excel is generated on demand through Downloads.

#### Adding a new microscope or new data

No code change or action from us is needed. Place the `.xls` files so the path contains the naming scheme with the new token (e.g. `_M<microscope>`; see [Data Preparation](#data-preparation)), then use **Add new data** on `/admin` or run `docker restart mcs_bead_proj` so the data is re-scanned. The new microscope/objective/test then appears in the filters automatically. **An empty folder alone will not appear** — it must contain the data files with the correct names.

### Support
For any query and support, please do not hesitate to get in touch through: bioinformatics@age.mpg.de
