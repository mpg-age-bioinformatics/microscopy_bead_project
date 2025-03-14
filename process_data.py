import os
import csv
import glob
import re
import shutil
import argparse
import pandas as pd
from datetime import datetime

print("Starts Data Processing")

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
    except:
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

    except:
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
    except:
        return None


# Setup arguments for the python file
# Use: python3 process_data.py -d </path/to/dir> -b <backup_limit>
parser = argparse.ArgumentParser(description="Process a directory path.")
parser.add_argument('-d', '--directory', type=str, default=".", help="Path to the directory (optional).")
parser.add_argument('-b', '--backup', type=int, default=100, help="Backup number (optional, default: 100).")
args = parser.parse_args()
root_dir = args.directory
backup_limit = args.backup

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

# Delete older backups if there are more than specific number of backups
b_dir = [d for d in glob.glob(f"{backup_dir}/*") if os.path.isdir(d)]
b_dir.sort(key=os.path.getctime)
if len(b_dir) > backup_limit:
    # Remove older directories
    for dir_to_delete in b_dir[:-backup_limit]:
        os.rmdir(dir_to_delete)

# Create a directory to store backup of existing files 
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ctime = datetime.now().timestamp()
current_b_dir = f"{backup_dir}/{timestamp}"
os.makedirs(current_b_dir, exist_ok=True)

# Copy extracted to a backup and fix creation time
try:
    shutil.copytree(fetch_dir, current_b_dir, dirs_exist_ok=True)
    os.utime(current_b_dir, (ctime, ctime))
except Exception as e:
    pass

# Setup CSV file with defined header
csv_header = ["date","microscope","objective","test","bead_size","bead_number","far_red","red","uv","dual","x","y","z","file_path"]
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(csv_header)

# Get xls files for processing
xls_files = glob.glob(f"{data_dir}/**/*.xls", recursive=True)
pattern = r".*\d{8}_M.*_O.*_T.*_S.*_B.*"
valid_files = [file for file in xls_files if re.match(pattern, file)]
untracked_files = [file for file in xls_files if not re.match(pattern, file)]

# Write to unprocessed_file and create dataless file
open(dataless_file, "w").close()
open(unprocessed_file, "w").writelines(file + '\n' for file in untracked_files)

# Extract values from valid files and store to records.csv
data_pattern = r"\d{8}_M[^_]*_O[^_]*_T[^_]*_S[^_]*_B\d+"

for file in valid_files:
    matches = re.findall(data_pattern, file)
    row = []
    if matches:
        value = matches[-1]
        meta_values = get_meta_values(value)
        if isinstance(meta_values, list) and len(meta_values) == 6:
            row.extend(meta_values)
            if meta_values[3] == "PSFo":
                properties = extract_values_psfo(file)
                if isinstance(properties, list) and len(properties) == 3:
                    row.extend(["NA", "NA", "NA", "NA"] + properties + [rf"{file}"])
            elif meta_values[3] == "ChromDual":
                properties = extract_values_chrom(file)
                if isinstance(properties, list) and len(properties) == 1:
                    row.extend(["NA", "NA", "NA"] + properties + ["NA", "NA", "NA"] + [rf"{file}"])
            else:
                properties = extract_values_chrom(file)
                if isinstance(properties, list) and len(properties) == 3:
                    row.extend(properties + ["NA", "NA", "NA", "NA", rf"{file}"])       
                
    if isinstance(row, list) and len(row) == 14:
        with open(csv_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(row)
    else:
        open(dataless_file, "a").write(f"{file}\n")

# Geneate exel file from the csv file
df = pd.read_csv(csv_file)
df.to_excel(excel_file, index=False)

print("Finished Data Processing")