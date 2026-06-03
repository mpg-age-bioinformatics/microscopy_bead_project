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

# All figures in one html.
# Stream figures straight to the file as they are generated rather than
# accumulating them in one big in-memory string: this file grows with the
# dataset, so holding it all in memory was an unbounded memory consumer.
html_header = """
<!DOCTYPE html>
<html>
<head>
    <title>Microscopy Bead Project Figures</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <h1>Microscopy Bead Project</h1><br>
"""

html_footer = """
</body>
</html>
"""

# Open the combined figures.html once for streaming writes. If it can't be
# opened we still generate the individual per-figure files below.
try:
    html_all_fh = open(html_all_file, "w")
    html_all_fh.write(html_header)
except Exception:
    logger.exception("Could not open %s for writing; continuing without combined HTML.", html_all_file)
    html_all_fh = None

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

            # Stream this figure into the combined HTML instead of holding the
            # whole document in memory. Both strings are already built above, so
            # we never write a partially-rendered figure.
            if html_all_fh is not None:
                html_all_fh.write(f"<div>{figure_html}</div>")
                html_all_fh.write("<h4>Deviation Table</h4>")
                html_all_fh.write(f"<div>{table_html}</div>")
            processed += 1
        except Exception:
            logger.exception(
                "Failed to build figure for microscope=%s objective=%s; skipping.",
                microscope, objective
            )
            skipped += 1
            continue

logger.info("HTML generation: %d figures written, %d skipped.", processed, skipped)

# Close out the combined figures.html (write footer, then close the handle).
if html_all_fh is not None:
    try:
        html_all_fh.write(html_footer)
    except Exception:
        logger.exception("Could not finish writing %s; continuing.", html_all_file)
    finally:
        html_all_fh.close()

logger.info("Finished generating HTML")