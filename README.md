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
mkdir -p ~/mcs_bead_project/data
```

Please store all your input data inside `~/mcs_bead_project/data` with proper format. Of course, you can choose a different data folder of your preference. However, you have to modify the commands accordingly in that case.

#### Run Docker Container
```
docker run -d --rm --name mcs_bead_proj -p 8050:8050 -v ~/mcs_bead_project:/mcs_bead_project mpgagebioinformatics/mcs_bead_proj:stable
```
This will fetch target data to a CSV file (in `~/mcs_bead_project/extracted/records.csv`, additionaly an excel file in the same location), generate base html figures (in `~/mcs_bead_project/extracted/`) and web application accessible through: http://localhost:8050/

If you prefer a different data directory rather than `~/mcs_bead_project/data`, please modify `~/mcs_bead_project` in the command.
You can change `stable` tag to `latest`, or a tag of your preference (image repo: https://hub.docker.com/r/mpgagebioinformatics/mcs_bead_proj).
Also, can remove the `-d` flag to get the state/logs of the running container.

#### Update/Add Data

After adding or updating data in `~/mcs_bead_project/data` directory run the following to get the latest ouputs:
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

Mounting the scripts would enable to run the app in the development mode:
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

### Support
For any query and support, please do not hesitate to get in touch through: bioinformatics@age.mpg.de





