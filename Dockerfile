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

# Account storage must be explicitly initialized in a host-mounted folder.
# Validate it before extraction; never silently create a fresh user database.
ENV APP_STATE_DIR=/app-state
ENV DATA_ROOT=/mcs_bead_project
# SOURCE_DATA_DIR and OUTPUT_ROOT optionally split read-only inputs from outputs.
# Leave them unset here so existing DATA_ROOT mounts remain compatible.
# HTML exports are optional; the dashboard only needs extracted records.
CMD ["sh", "-c", "python3 auth.py check && { python3 process_data.py -d \"$DATA_ROOT\"; exec python3 app.py; }"]
