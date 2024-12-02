import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
from helpers import generate_fig_data
import shutil
import os

print("Starts Generating HTML")

extracted_dir = '/mbp/extracted'
record_file = f"{extracted_dir}/records.csv"
html_dir = f"{extracted_dir}/html"
html_all_file = f"{extracted_dir}/figures.html"

# Delete existing html files
try:
    shutil.rmtree(html_dir)
    os.makedirs(html_dir)
except Exception as e:
    pass

# Get dataframe
df = pd.read_csv(record_file)
df = df.assign(date=lambda x: pd.to_datetime(x['date'], format='%Y%m%d'))

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
for microscope in microscope_list:
    m_df = df[df['microscope'] == microscope]
    objective_list = m_df['objective'].unique()
    for objective in objective_list:
        fig, considerd_df, change_df, fig_name, warning = generate_fig_data(df, microscope, objective)
        
        # Create an HTML table from the DataFrame
        table_html = change_df.to_html(index=False)

        # Get the Plotly figure HTML
        figure_html = pio.to_html(fig, full_html=False)

        # Combine the figure and table into a single HTML document
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Figure with Change Table</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div>{figure_html}</div>
            <h4>Change Table</h4>
            <div>{table_html}</div>
        </body>
        </html>
        """

        # Write the combined HTML to a file
        with open(f"{html_dir}/{fig_name}.html", "w") as f:
            f.write(html_content)
        
        # Add figure to html_all
        html_all += f"<div>{figure_html}</div>"
        html_all += "<h4>Change Table</h4>"
        html_all += f"<div>{table_html}</div>"
        
# generate figures.html with html_all content
html_all += """
</body>
</html>
"""

with open(html_all_file, "w") as f:
    f.write(html_all)

print("Finished Generating HTML")