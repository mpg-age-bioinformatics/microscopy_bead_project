import os
import csv
import glob
import re
import shutil
import hashlib
import logging
import argparse
from datetime import datetime

from log_config import configure_logging

# Functions for differnet operations
def get_meta_values(input_str):
    """Get meta values from a path string"""
    try:
        date = input_str[:8] if input_str[:8].isdigit() else "NA"
        microscope = input_str.split('_M')[-1].split('_')[0] if '_M' in input_str else "NA"
        objective = input_str.split('_O')[-1].split('_')[0] if '_O' in input_str else "NA"
        test = input_str.split('_T')[-1].split('_')[0] if '_T' in input_str else "NA"
        bead_size = input_str.split('_S')[-1].split('_')[0] if '_S' in input_str else "NA"
        bead_number = input_str.split('_B')[-1].split('_')[0] if '_B' in input_str else "NA"

        return [date, microscope, objective, test, bead_size, bead_number]
    except Exception as e:
        logging.getLogger("process_data").debug("get_meta_values failed for %r: %s", input_str, e)
        return None

def extract_values_psfo(file_path):
    """Get property values from type psfo"""
    try:
        if not os.path.exists(file_path):
            return None

        # Handle two types of patterns and fetch the values 
        values_line = None
        values_lines = []
        capture = False
        with open(file_path, 'r') as file:
            for line in file:
                if capture:
                    values_lines.append(line.strip())
                    if len(values_lines) == 3:
                        break
                if "Measured FWHM" in line:
                    values_line = line.strip()
                    if values_line.startswith('Measured FWHM'):
                        break
                    else:
                        capture = True
                        continue

        if values_line is None:
            return None

        if not values_lines:
            values = (values_line.split('\t'))[1:] 
            values = [float(value) for value in values]
        else:
            values = [
                float(re.search(r'(X|Y|Z)\t([\d.]+)', line).group(2))
                for line in values_lines
                if re.search(r'(X|Y|Z)\t([\d.]+)', line)
            ]
        
        return values

    except Exception as e:
        logging.getLogger("process_data").debug("extract_values_psfo failed for %s: %s", file_path, e)
        return None

def extract_values_chrom(file_path):
    """Get property values from the types of chrom"""
    try:
        if not os.path.exists(file_path):
            return None

        target_line = None
        target_section = None
        with open(file_path, 'r') as file:
            for line in file:
                # Check if we are in the "Calibrated distances" section
                if ("calibrated distances" in line.lower() and "uncalibrated distances" not in line.lower()):
                    target_section = True
                    continue
                    
                if target_section and line.startswith("Channel 1"):
                    target_line = line.strip()  # Remove any leading/trailing whitespace
                    break

        if target_line is None:
            return None
                    
        values = re.findall(r"\b\d+\.\d+\b(?=\s*\()", target_line)
        if not values:
            values = re.findall(r"\b\d+\.\d+\b", target_line)
        values = [float(value) for value in values]
        return values
    except Exception as e:
        logging.getLogger("process_data").debug("extract_values_chrom failed for %s: %s", file_path, e)
        return None


# Setup arguments for the python file
# Use: python3 process_data.py -d </path/to/dir> -b <backup_limit>
parser = argparse.ArgumentParser(description="Process a directory path.")
parser.add_argument('-d', '--directory', type=str, default=".", help="Path to the directory (optional).")
parser.add_argument('-b', '--backup', type=int, default=100, help="Backup number (optional, default: 100).")
parser.add_argument('-e', '--excel-max-rows', type=int, default=100000,
                    help="Max record rows to still generate records.xlsx; above this it is skipped (optional, default: 100000). Set 0 to disable Excel.")
args = parser.parse_args()
root_dir = args.directory
backup_limit = args.backup
excel_max_rows = args.excel_max_rows

# Setup required paths
data_dir = f"{root_dir}/data"
fetch_dir = f"{root_dir}/extracted"
backup_dir = f"{root_dir}/backup"
html_dir = f"{fetch_dir}/html"
csv_file = f"{fetch_dir}/records.csv"
excel_file = f"{fetch_dir}/records.xlsx"
unprocessed_file = f"{fetch_dir}/unprocessed.txt"
dataless_file = f"{fetch_dir}/dataless.txt"

# Create required directories
os.makedirs(fetch_dir, exist_ok=True)
os.makedirs(backup_dir, exist_ok=True)
os.makedirs(html_dir, exist_ok=True)

# Configure logging (stdout, captured per-container by `docker logs`)
configure_logging()
logger = logging.getLogger("process_data")
logger.info("Starting data processing (directory=%s, backup_limit=%s)", root_dir, backup_limit)

# Back up the PREVIOUS run's records before records.csv is overwritten below.
#
# Only records.csv is irreplaceable; figures.html, the html/ tree and
# records.xlsx are all regenerable from it, so we don't copy them -- this is a
# big disk + time saving on the shared network volume (one small file instead of
# walking a large many-file tree over SMB). The two tiny .txt reports are bundled
# along. We also skip making a snapshot when records.csv is unchanged since the
# last backup, so plain restarts don't pile up duplicate backups.

def file_hash(path):
    """Content hash of a file, or None if it can't be read."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# Existing backups, oldest first
b_dir = [d for d in glob.glob(f"{backup_dir}/*") if os.path.isdir(d)]
b_dir.sort(key=os.path.getctime)

# Snapshot only if the current (previous-run) records.csv differs from the latest backup
current_hash = file_hash(csv_file) if os.path.exists(csv_file) else None
latest_backup_hash = file_hash(f"{b_dir[-1]}/records.csv") if b_dir else None

if current_hash is None:
    logger.info("No existing records.csv to back up; skipping backup.")
elif current_hash == latest_backup_hash:
    logger.info("records.csv unchanged since last backup; skipping backup.")
else:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ctime = datetime.now().timestamp()
    current_b_dir = f"{backup_dir}/{timestamp}"
    os.makedirs(current_b_dir, exist_ok=True)
    try:
        for src in (csv_file, unprocessed_file, dataless_file):
            if os.path.exists(src):
                shutil.copy2(src, current_b_dir)
        os.utime(current_b_dir, (ctime, ctime))
        b_dir.append(current_b_dir)  # newest -> keep at end for correct pruning
        logger.info("Backed up records.csv to %s", current_b_dir)
    except Exception as e:
        logger.warning("Could not back up records to %s: %s", current_b_dir, e)

# Prune oldest backups beyond the limit
if len(b_dir) > backup_limit:
    for dir_to_delete in b_dir[:-backup_limit]:
        try:
            shutil.rmtree(dir_to_delete)
        except Exception as e:
            logger.warning("Could not remove old backup %s: %s", dir_to_delete, e)

# CSV header
csv_header = ["date","microscope","objective","test","bead_size","bead_number","far_red","red","uv","dual","x","y","z","file_path"]

# Get xls files for processing
xls_files = glob.glob(f"{data_dir}/**/*.xls", recursive=True)
pattern = r".*\d{8}_M.*_O.*_T.*_S.*_B.*"
valid_files = [f for f in xls_files if re.match(pattern, f)]
untracked_files = [f for f in xls_files if not re.match(pattern, f)]
logger.info(
    "Found %d .xls files: %d match the naming scheme, %d untracked (see unprocessed.txt).",
    len(xls_files), len(valid_files), len(untracked_files)
)

# Write the list of untracked files
with open(unprocessed_file, "w") as f:
    f.writelines(p + '\n' for p in untracked_files)

# Extract values from valid files and store to records.csv
data_pattern = r"\d{8}_M[^_]*_O[^_]*_T[^_]*_S[^_]*_B\d+"

extracted_count = 0
dataless_count = 0

# Open records.csv and dataless.txt once for the whole loop instead of
# reopening them per row. On a network share each open/close is a round-trip,
# so per-row reopening dominated the cost as the dataset grew.
with open(csv_file, 'w', newline='') as csv_fh, open(dataless_file, 'w') as dataless_fh:
    writer = csv.writer(csv_fh)
    writer.writerow(csv_header)

    for path in valid_files:
        matches = re.findall(data_pattern, path)
        row = []
        if matches:
            value = matches[-1]
            meta_values = get_meta_values(value)
            if isinstance(meta_values, list) and len(meta_values) == 6:
                row.extend(meta_values)
                if meta_values[3] == "PSFo":
                    properties = extract_values_psfo(path)
                    if isinstance(properties, list) and len(properties) == 3:
                        row.extend(["NA", "NA", "NA", "NA"] + properties + [rf"{path}"])
                elif meta_values[3] == "ChromDual":
                    properties = extract_values_chrom(path)
                    if isinstance(properties, list) and len(properties) == 1:
                        row.extend(["NA", "NA", "NA"] + properties + ["NA", "NA", "NA"] + [rf"{path}"])
                else:
                    properties = extract_values_chrom(path)
                    if isinstance(properties, list) and len(properties) == 3:
                        row.extend(properties + ["NA", "NA", "NA", "NA", rf"{path}"])

        if isinstance(row, list) and len(row) == 14:
            writer.writerow(row)
            extracted_count += 1
        else:
            dataless_fh.write(f"{path}\n")
            dataless_count += 1

logger.info(
    "Extraction complete: %d records written to records.csv, %d files had no target data (see dataless.txt).",
    extracted_count, dataless_count
)
if extracted_count == 0:
    logger.warning(
        "No records were extracted. The app will start but show no data. "
        "Check that file contents/format match the expected parser (see dataless.txt/unprocessed.txt)."
    )

# Generate an Excel copy of records.csv. This is a convenience duplicate only
# (the app and HTML stages read records.csv, never the xlsx), so it must never
# break the run -- any problem just logs and continues.
#
#   * If the dataset is larger than the configured limit, skip Excel entirely:
#     building it would be slow and Excel itself caps at ~1.05M rows anyway.
#   * Otherwise build it by streaming row-by-row with openpyxl's write_only mode
#     so we never hold the whole workbook in memory (the old df.to_excel path
#     materialised every cell as an object -> multi-GB spikes / OOM).
if excel_max_rows <= 0:
    logger.info("Skipping records.xlsx (Excel generation disabled). Use records.csv.")
elif extracted_count > excel_max_rows:
    logger.info(
        "Skipping records.xlsx: %d rows exceeds the limit of %d. Use records.csv for the full data.",
        extracted_count, excel_max_rows
    )
else:
    try:
        from openpyxl import Workbook

        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        with open(csv_file, newline='') as f:
            for row in csv.reader(f):
                ws.append(row)
        wb.save(excel_file)
        logger.info("Wrote %s (%d data rows).", excel_file, extracted_count)
    except Exception as e:
        logger.warning("Could not write Excel file %s (skipping, not required): %s", excel_file, e)

logger.info("Finished data processing")