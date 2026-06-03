# Use Python 3.12-slim image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy current directory
COPY . /app/

# Install dependencies
RUN pip install -r /app/requirements.txt

# Expose the default Dash port
EXPOSE 8050

# Command to run the app.
# Use ';' before app.py so the web app always starts even if HTML generation
# fails entirely (app.py only needs records.csv, not figures.html).
CMD ["sh", "-c", "python3 process_data.py -d /mcs_bead_project && python3 generate_html.py ; python3 app.py"]