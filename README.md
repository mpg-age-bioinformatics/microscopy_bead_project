# Microscopy Bead Project

Extract microscopy quality-control measurements from Excel files and explore them through an authenticated browser interface. Filter records, view interactive figures and deviations, inspect related images, and download reports.

## Deployment

Choose the guide for your environment:

- [Local deployment](deployment/LOCAL.md): run on your computer with Docker, including development, troubleshooting and account recovery.
- [Web deployment](deployment/README.md): serve the application over HTTPS with Docker Compose, Caddy and persistent storage.

## Features

- Extract measurements from `.xls` files into a shared CSV dataset.
- Filter by microscope, objective, test, bead size, bead number and date range.
- View interactive figures, underlying data, deviations and related images.
- Use local accounts with user and administrator roles; the entire interface requires sign-in.
- Run incremental updates or a full rebuild from the admin interface.
- Download CSV, Excel, processing reports, interactive HTML and extraction backups.
- Keep source data read-only, with extracted data and accounts in separate persistent storage.

## Data preparation

Place input `.xls` files and related images inside the configured source-data directory. Preserve the folder structure; the extractor searches the filename and its parent folders for measurement metadata.

For bead measurements, use this naming scheme:

```text
<date>_M<microscope>_O<objective>_T<test>_S<bead_size>_B<bead_number>
```

The date must use `YYYYMMDD`. Either of these paths can provide the required metadata:

```text
/Path/A/B/C/20250108_MAndorDragonfly_O100x1.45_TChromDual_S1.0_B0_other_text.xls
/Path/20250108_MAndorDragonfly_O100x1.45_TChromDual_S1.0_B0/A/B/file.xls
```

A simple approach is to rename the bead-level directory to match this pattern and leave its contents unchanged. For Centricity / Homogeneity (`TCenHom`) measurements, follow the dedicated [naming conventions](naming_cases.md).

To add a microscope, objective or test, add correctly named data files and ask an administrator to run **Add new data**. No code change is required. Empty folders alone do not appear in the filters.

## Using the interface

### Sign in

Open the URL localhost or web url and sign in. New accounts and accounts with reset passwords must change their temporary password before accessing data.

Use **Account / sign out** to change your own password or sign out. There is no self-registration or password-reset email service; contact someone with admin access if you cannot sign in.

### Dashboard

Choose filters in the sidebar, then click **Submit**:

| Filter | Purpose |
| --- | --- |
| Microscope, Objective, Test | Select the measurements to examine |
| Bead Size, Bead Number | Narrow the bead selection |
| Date Range | Restrict the measurement dates |
| Consider Previous Values for Line Deviation | Set how many previous values are considered for deviation calculations |
| Warning Percentage | Set the deviation warning threshold |

A loading animation appears in the results area while the output is prepared. The sidebar remains visible, and Submit is temporarily disabled.

| Output tab | Contents |
| --- | --- |
| Figure | Interactive Plotly chart |
| Data | Records used to generate the chart |
| Deviation | Calculated deviations |
| Image | Related bead images read from the source directory |

After a data update, filter options refresh within 15 seconds. Press **Submit** again to refresh an existing chart.

### Access levels

| Role | Permissions |
| --- | --- |
| User | View the dashboard, data, figures and images; change their password; sign out |
| Admin | All user permissions, plus download reports and backups, update data and manage accounts |

### Manage users

Administrators open **Users** at `/admin/users`.

- **Add a user:** enter a username, temporary password and access role, then click **Create user**. Usernames use 3–64 lowercase letters, numbers, dots, underscores or hyphens and start with a letter or number. Passwords must contain 8–256 characters. Share credentials privately; the user must change the temporary password at first sign-in.
- **Change a role:** select User or Admin and save. Leave the reset-password field empty to retain the password.
- **Disable or re-enable:** change **Account enabled** and save. Disabling blocks access while keeping the account record.
- **Reset a password:** enter a new temporary password and save. The user must change it before accessing data again.
- **Delete an account:** expand **Delete account**, confirm the username using the checkbox, and click **Delete account permanently**. Deletion preserves extracted data and update history. Use disabling for temporary access removal.

Saved account changes invalidate that user's existing sessions. You cannot delete your own account or delete, disable or demote the last active administrator. Recreating a deleted username does not reactivate its old sessions.

Passwords are stored as salted scrypt hashes. Sessions expire after eight hours. Five incorrect password attempts lock an account for five minutes, and sign-in requests are also throttled per connecting IP. State-changing requests require CSRF tokens.

### Update data

Administrators open **Updates** at `/admin`:

| Action | When to use it |
| --- | --- |
| Add new data | Process previously unseen source paths |
| Rebuild all data | Re-read everything after editing, deleting or renaming files, or retry previously unprocessed/dataless files |

A full rebuild requires confirmation. A schema change also triggers a full rebuild automatically. Incremental updates do not re-read files already tracked at the same path.

Only one update runs at a time. The page shows status, timestamps, the latest 200 log lines and the 10 most recent update-history entries. History records the initiating user, mode and result and persists with the accounts database. Detailed live logs clear on restart or the next update.

Extraction publishes the CSV atomically, keeping the previous dataset available until the replacement is ready. An unsuccessful backup aborts extraction. Updates do not automatically generate Excel or HTML exports.

### Downloads

Administrators open **Downloads** at `/download`. Regular users cannot access this page or its direct download routes.

| Download | Contents |
| --- | --- |
| `records.csv` | Latest published records |
| Excel | A fresh `records.xlsx` generated from the current CSV |
| `unprocessed.txt` | Paths that could not be recognized or processed |
| `dataless.txt` | Recognized paths with no usable target measurements |
| HTML report | A fresh combined report with interactive figures and deviation tables; opens offline |
| Backup `.tar.gz` | One selected extraction snapshot |

Unavailable files have disabled buttons. Empty processing reports are valid downloads. Excel, HTML and backup archives are generated temporarily and removed after the response closes; they are not saved as permanent exports. Only one generated export runs at a time. Large reports may take time.

Excel reads a complete CSV snapshot and preserves values as text, including values that resemble formulas. If Excel's size limits are exceeded, use CSV. Old saved Excel or HTML files are not served by these buttons.

HTML reports include Plotly once and identify combinations for which no figure could be produced. The optional `generate_html.py` script remains available for explicitly saving combined and individual reports; see the [local guide](deployment/LOCAL.md#optional-saved-exports).

### Extraction backups

The Downloads page lists completed snapshots newest first, with readable times, uncompressed sizes and **Download .tar.gz** buttons. Each archive contains a timestamped folder with `records.csv` and any saved `unprocessed.txt` and `dataless.txt` reports. Source files, account data, symbolic links and unrelated files are excluded.

Up to **20 snapshots** are retained by default; older snapshots are pruned during extraction. If a snapshot disappears before download, refresh the list. Unchanged records do not create another identical backup.

These are extraction snapshots, not complete application backups. The interface does not restore snapshots or back up user accounts. Account storage needs a separate backup as described in the deployment guides.

### Times and logs

Downloads, backup times, recent updates and processing logs use the server/container's local timezone, without timezone labels. Docker normally defaults to UTC; changing the browser timezone does not change these displays. Backup times use folder modification timestamps, so preserve timestamps when moving snapshots.

## Data storage

The source directory is read-only in the recommended deployments. Generated files go into a separate output directory, and `app.db` holds accounts, the session-signing secret and update history in local persistent storage.

| Output path | Purpose |
| --- | --- |
| `extracted/records.csv` | Primary extracted dataset used by the dashboard |
| `extracted/unprocessed.txt` | Processing report |
| `extracted/dataless.txt` | Report of inputs with no target data |
| `backup/` | Extraction snapshots |
| `extracted/records.xlsx` | Optional workbook, only saved when explicitly enabled by the extraction CLI |
| `extracted/figures.html`, `extracted/html/` | Optional reports saved by the standalone HTML script |

The dashboard caches extracted records and reloads them when the CSV changes. Related image previews are read from the source directory. Changing or removing a container does not delete host-mounted storage.

Keep one application container and one Gunicorn worker process per output directory so update/export locks are shared. Avoid running a separate extraction command during an interface update. Restarting interrupts active updates; the next startup marks unfinished update-history entries as failed.

## Support

For questions and support, contact bioinformatics@age.mpg.de.
