import pandas as pd
# import plotly.express as px
import plotly.io as pio
# from datetime import datetime
import logging
from helpers import generate_fig_data
from log_config import configure_logging
import shutil
import os

extracted_dir = '/mcs_bead_project/extracted'
record_file = f"{extracted_dir}/records.csv"
html_dir = f"{extracted_dir}/html"
html_all_file = f"{extracted_dir}/figures.html"

configure_logging()
logger = logging.getLogger("generate_html")
logger.info("Starting HTML generation")

# Delete existing html files
try:
    shutil.rmtree(html_dir)
    os.makedirs(html_dir)
except Exception as e:
    pass

# Get dataframe
try:
    df = pd.read_csv(record_file)
    df = df.assign(date=lambda x: pd.to_datetime(x['date'], format='%Y%m%d', errors='coerce'))
except Exception:
    logger.exception("Could not read %s; writing empty figures and continuing.", record_file)
    df = pd.DataFrame(columns=["date", "microscope", "objective"])

# Generate html
microscope_list = df['microscope'].unique()

# All figures in one html
html_all = """
<!DOCTYPE html>
<html>
<head>
    <title>Microscopy Bead Project Figures</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <h1>Microscopy Bead Project</h1><br>
"""

# Loop over the perameters
processed = 0
skipped = 0
for microscope in microscope_list:
    m_df = df[df['microscope'] == microscope]
    objective_list = m_df['objective'].unique()
    for objective in objective_list:
        try:
            fig, considerd_df, change_df, fig_name, warning = generate_fig_data(df, microscope, objective)

            # Skip combinations that produced no usable figure/data instead of
            # crashing the whole stage (this was the cause of the container
            # exiting partway through generating HTML).
            if fig is None or change_df is None:
                logger.warning(
                    "No usable figure for microscope=%s objective=%s; skipping.",
                    microscope, objective
                )
                skipped += 1
                continue

            # Create an HTML table from the DataFrame
            table_html = change_df.to_html(index=False)

            # Get the Plotly figure HTML
            figure_html = pio.to_html(fig, full_html=False)

            # Combine the figure and table into a single HTML document
            html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Figure with Deviation Table</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div>{figure_html}</div>
            <h4>Deviation Table</h4>
            <div>{table_html}</div>
        </body>
        </html>
        """

            # Write the combined HTML to a file
            with open(f"{html_dir}/{fig_name}.html", "w") as f:
                f.write(html_content)

            # Add figure to html_all
            html_all += f"<div>{figure_html}</div>"
            html_all += "<h4>Deviation Table</h4>"
            html_all += f"<div>{table_html}</div>"
            processed += 1
        except Exception:
            logger.exception(
                "Failed to build figure for microscope=%s objective=%s; skipping.",
                microscope, objective
            )
            skipped += 1
            continue

logger.info("HTML generation: %d figures written, %d skipped.", processed, skipped)

# generate figures.html with html_all content
html_all += """
</body>
</html>
"""

try:
    with open(html_all_file, "w") as f:
        f.write(html_all)
except Exception:
    logger.exception("Could not write %s; continuing.", html_all_file)

logger.info("Finished generating HTML")