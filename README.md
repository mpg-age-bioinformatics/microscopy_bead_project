# microscopy_bead_project

### Features
- Parse data from all the input excel files and store required data in a CSV file
- Report files which are not parseable or with no target data
- Store/display target graphs as html with values and warning sign (parameters are flexible)
- Interactive interface (in browser) with option filters and outputs including figures, data, deviations and images

### Get Started

Prerequisite: Docker

#### Data Storage

Create a data folder where the input data should be stored
```
mkdir -p /Volumes/group_fi/group/Microscopy/Metrology/mcs_bead_project/data
```

Please store all your input data inside `data` directory with proper format ([check data preparation](https://github.com/mpg-age-bioinformatics/microscopy_bead_project/?tab=readme-ov-file#data-preparation)). For the Centricity / Homogeneity (`TCenHom`) test, follow the dedicated naming convention in [naming_cases.md](naming_cases.md). Of course, you can choose a different data folder of your preference. However, you have to modify the commands accordingly in that case.

#### Run Docker Container (using the latest stable image)
```
docker stop mcs_bead_proj
docker pull mpgagebioinformatics/mcs_bead_proj:stable
docker run -d --rm --name mcs_bead_proj -p 8050:8050 -v /Volumes/group_fi/group/Microscopy/Metrology/mcs_bead_project:/mcs_bead_project mpgagebioinformatics/mcs_bead_proj:stable
```
This will fetch target data to a CSV file (in `extracted/records.csv`), generate base html figures (in `extracted/`) and web application accessible through: http://localhost:8050/

You can change `stable` tag to `latest`, or a tag of your preference (image repo: https://hub.docker.com/r/mpgagebioinformatics/mcs_bead_proj).
Also, can remove the `-d` flag to get the state/logs of the running container.

If necessary, you can check the live logs with:
```
docker logs -f mcs_bead_proj
```

#### Update/Add Data

After adding or updating data in `/mcs_bead_project/data` directory you can re-run the earlier three docker commands or simply restart to get the latest ouputs:
```
docker restart mcs_bead_proj
```

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

Mounting the scripts would enable to run the app in the development mode (change `~/mcs_bead_project` to your preferred path):
```
docker run --rm --name mcs_bead_proj -p 8050:8050 -v $(pwd):/app -v ~/mcs_bead_project:/mcs_bead_project mcs_bead_proj
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

All important extracted files fetched from the input data will be stored in `~/mcs_bead_project/extracted`

`extracted` directory contains the following:
- `records.csv`: primary file that stores all the fetched records from the input directory
- `records.xlsx`: the same records in an excel file
- `dataless.txt`: contains directories where no target data was found
- `unprocessed.txt`: contains directories that could not be processed to fetch data
- `figures.html`: contains base figures in one html file
- `html`: directory contains html files of individual figures

#### Backup

Backups from previously extracted files are stored in `~/mcs_bead_project/backup`.
By default last 100 extracted backups would be stored. If something goes wrong, you can always get back to previous version of fetched data by copying them to `~/mcs_bead_project/extracted` directory.

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
- **Out of memory (exit 137):** increase Docker Desktop's memory limit (Settings → Resources). The tool already streams output and skips the optional `records.xlsx` above a row limit to keep memory low.

#### Adding a new microscope or new data

No code change or action from us is needed. Place the `.xls` files so the path contains the naming scheme with the new token (e.g. `_M<microscope>`; see [Data Preparation](#data-preparation)), then run `docker restart mcs_bead_proj` so the data is re-scanned. The new microscope/objective/test then appears in the filters automatically. **An empty folder alone will not appear** — it must contain the data files with the correct names.

### Support
For any query and support, please do not hesitate to get in touch through: bioinformatics@age.mpg.de

