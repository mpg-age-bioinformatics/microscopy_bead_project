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

Please store all your input data inside `~/mcs_bead_project/data` with proper format.

#### Build Docker Image

Clone `microscope_bead_project` repo
```
git clone https://github.molgen.mpg.de/mpg-age-bioinformatics/microscopy_bead_project.git
```
or download the repo

Navigate to the repo directory (e.g. `cd microscope_bead_project`) and the run docker build:
```
docker build -t mcs_bead_proj .
```

#### Run Docker Container

```
docker run -d --rm --name mcs_bead_proj -p 8050:8050 -v ~/mcs_bead_project:/mcs_bead_project mcs_bead_proj
```
This will fetch target data to a CSV file (in `~/mcs_bead_project/extracted/records.csv`), generate base html figures (in `~/mcs_bead_project/extracted/`) and web application accessible through: http://localhost:8050/

To stop the running container:
```
docker stop mcs_bead_proj
```

#### Update/Add Data

After adding or updating data in `~/mcs_bead_project/data` directory run the following to get the latest ouputs:
```
docker restart mcs_bead_proj
```

#### Development

Mounting the scripts would enable to run the app in the development mode:
```
docker run -d --rm --name mcs_bead_proj -p 8050:8050 -v $(pwd):/app -v ~/mcs_bead_project:/mcs_bead_project mcs_bead_proj
```

Can remove the `-d` flag to get the state/logs of the running container.

### Components

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
- `dataless.txt`: contains directories where no target data was found
- `unprocessed.txt`: contains directories that could not be processed to fetch data
- `figures.html`: contains base figures in one html file
- `html`: directory contains html files of individual figures

#### Backup

Backups from previously extracted files are stored in `~/mcs_bead_project/backup`.
By default last 100 extracted backups would be stored. If something goes wrong, you can always get back to previous version of fetched data by copying them to `~/mcs_bead_project/extracted` directory.

### Support
For any query and support, please do not hesitate to get in touch through: bioinformatics@age.mpg.de





