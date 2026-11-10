"""Build a combined HTML report, optionally saving individual figures for CLI use."""

from html import escape
import logging
from pathlib import Path
import re
import shutil

import pandas as pd
import plotly.io as pio

from data_paths import get_data_paths
from helpers import generate_fig_data
from log_config import configure_logging


logger = logging.getLogger("generate_html")

HTML_HEADER = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Microscopy Bead Project Figures</title>
  <style>
    body { font: 16px/1.5 system-ui, sans-serif; margin: 24px; color: #182637; }
    section { margin: 32px 0; overflow-x: auto; }
    table { border-collapse: collapse; }
    th, td { padding: 8px; border: 1px solid #d5dee8; }
    .notice { background: #fff0ca; padding: 16px; }
  </style>
</head>
<body>
<h1>Microscopy Bead Project</h1>
"""
HTML_FOOTER = "\n</body>\n</html>\n"


def write_report(source, destination, individual_dir=None):
    """Read one CSV snapshot and write figures incrementally to a text stream.

    No output directories are created unless individual_dir is explicitly supplied.
    Plotly is embedded once in the combined report so it works offline.
    """
    df = pd.read_csv(source)
    if not {"date", "microscope", "objective"}.issubset(df.columns):
        raise ValueError("Records are missing required columns. Ask an administrator to update the data.")
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
    destination.write(HTML_HEADER)
    destination.write(f"<p>Report generated from {len(df):,} records. Includes all microscopes and objectives.</p>\n")
    processed = 0
    skipped = 0
    for microscope in df['microscope'].dropna().unique():
        objectives = df.loc[df['microscope'] == microscope, 'objective'].dropna().unique()
        for objective in objectives:
            label = f"{microscope} / {objective}"
            try:
                fig, _, change_df, fig_name, _ = generate_fig_data(df, microscope, objective)
                if fig is None or change_df is None:
                    raise ValueError("No usable figure or deviation table")
                table_html = change_df.to_html(index=False, escape=True)
                figure_html = pio.to_html(fig, full_html=False, include_plotlyjs=(processed == 0))
            except Exception:
                logger.exception("Could not generate figure for %s", label)
                destination.write(f'<p class="notice">Figure unavailable: {escape(label)}. '
                                  'Check that the records contain usable measurements.</p>\n')
                skipped += 1
                continue

            destination.write(f"<section><h2>{escape(label)}</h2>\n")
            destination.write(figure_html)
            destination.write("<h3>Deviation table</h3>\n")
            destination.write(table_html)
            destination.write("</section>\n")
            processed += 1

            if individual_dir is not None:
                # Keep source metadata from becoming a filesystem path.
                filename = re.sub(r"[^A-Za-z0-9_.-]", "_", fig_name) + ".html"
                try:
                    with (Path(individual_dir) / filename).open("w", encoding="utf-8") as output:
                        output.write(HTML_HEADER)
                        output.write(pio.to_html(fig, full_html=False, include_plotlyjs=True))
                        output.write("<h3>Deviation table</h3>\n" + table_html + HTML_FOOTER)
                except Exception:
                    logger.exception("Could not save individual figure %s", filename)

    destination.write(f"<p>{processed} figures generated; {skipped} combinations unavailable.</p>\n")
    if processed == 0:
        destination.write('<p class="notice">No figures could be generated from these records.</p>\n')
    destination.write(HTML_FOOTER)
    logger.info("HTML generation: %d figures written, %d unavailable.", processed, skipped)
    return processed, skipped


def main():
    """Retain the explicit CLI workflow that saves exports in extracted/."""
    configure_logging()
    directory = Path(get_data_paths().extracted_dir)
    html_dir = directory / "html"
    logger.info("Starting HTML generation")
    with (directory / "records.csv").open(newline="", encoding="utf-8-sig") as source:
        if html_dir.exists():
            shutil.rmtree(html_dir)
        html_dir.mkdir(parents=True)
        with (directory / "figures.html").open("w", encoding="utf-8") as destination:
            write_report(source, destination, individual_dir=html_dir)
    logger.info("Finished generating HTML")


if __name__ == '__main__':
    main()
