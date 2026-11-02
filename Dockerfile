# Use Python 3.12-slim image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies separately; never copy the whole build checkout.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r /app/requirements.txt

# Only runtime code/assets belong in a public image.
COPY app.py admin.py auth.py data_paths.py downloads.py generate_html.py helpers.py log_config.py process_data.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Expose the default Dash port
EXPOSE 8050

# Account storage must be explicitly initialized in a host-mounted folder.
# Validate it before extraction; never silently create a fresh user database.
ENV APP_STATE_DIR=/app-state
ENV DATA_ROOT=/mcs_bead_project
# SOURCE_DATA_DIR and OUTPUT_ROOT optionally split read-only inputs from outputs.
# Leave them unset here so existing DATA_ROOT mounts remain compatible.
# HTML exports are optional; the dashboard only needs extracted records.
# Keep one worker process so update/export locks are shared across requests.
CMD ["sh", "-c", "python3 auth.py check && { python3 process_data.py -d \"$DATA_ROOT\"; exec gunicorn --bind 0.0.0.0:8050 --workers 1 --threads 4 app:server; }"]
