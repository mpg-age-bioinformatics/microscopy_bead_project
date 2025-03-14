# Use Python 3.10.8 image as the base
FROM python:3.10.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy current directory
COPY . /app/

# Install dependencies
RUN pip install -r /app/requirements.txt

# Expose the default Dash port
EXPOSE 8050

# Command to run the app
CMD ["sh", "-c", "python3 process_data.py -d /mcs_bead_project && python3 generate_html.py && python3 app.py"]