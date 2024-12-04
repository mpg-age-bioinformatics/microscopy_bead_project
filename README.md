# microscopy_bead_project

### Features
- Parse data from all the input excel files and store required data in a CSV file
- Report files which are not parseable or with no target data
- Store/display target graphs as html with values and warning sign (parameters are flexible)
- Interactive interface (in browser) with option filters and outputs including figures, data, deviations and images

### Get Started

Prequisite: Docker

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
docker run -d --rm --name mcs_bead_proj -p 8050:8050 -v ~/mcs_bead_project:/mbp mcs_bead_proj
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

