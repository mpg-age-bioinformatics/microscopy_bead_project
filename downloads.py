"""Authenticated downloads of extracted data, with Excel and HTML generated on request."""

import csv
import io
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import tempfile
import threading

from flask import abort, flash, redirect, render_template, send_file, url_for
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from generate_html import write_report


logger = logging.getLogger(__name__)

# Only these output files are downloadable. Never expose source paths or accounts.
FILES = {
    "records.csv": ("Records · CSV", "The latest extracted records, ready to download.", "text/csv"),
    "unprocessed.txt": ("Unprocessed files", "Input paths not recognized by the extractor.", "text/plain"),
    "dataless.txt": ("Files without data", "Recognized input paths with no usable target measurements.", "text/plain"),
}


def attachment(handle, filename, mimetype):
    """Send the opened snapshot; derive its size from the same file descriptor."""
    try:
        response = send_file(handle, as_attachment=True, download_name=filename,
                             mimetype=mimetype, conditional=False, etag=False)
        response.content_length = os.fstat(handle.fileno()).st_size
        response.call_on_close(handle.close)
        return response
    except Exception:
        handle.close()
        raise


def write_excel(source, destination):
    """Stream one CSV snapshot to a workbook without loading the dataset in memory."""
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Records")
    sheet.freeze_panes = "A2"
    try:
        for number, row in enumerate(csv.reader(source), start=1):
            if number > 1048576 or len(row) > 16384:
                raise ValueError("The records exceed Excel's sheet limits. Download the CSV instead.")
            cells = []
            for value in row:
                if len(value) > 32767:
                    raise ValueError("A value is too long for an Excel cell. Download the CSV instead.")
                cell = WriteOnlyCell(sheet, value=value)
                # CSV values are data, never executable spreadsheet formulas.
                cell.data_type = "s"
                if number == 1:
                    cell.font = Font(bold=True)
                cells.append(cell)
            sheet.append(cells)
    finally:
        # Finalize the write-only worksheet and clean its temporary XML even if
        # conversion failed. The caller discards any incomplete workbook.
        workbook.save(destination)


def write_html(source, destination):
    writer = io.TextIOWrapper(destination, encoding="utf-8", newline="")
    try:
        write_report(source, writer)
    finally:
        # Flush text without closing the binary file used by the download response.
        writer.detach()


def register_downloads(server, paths):
    directory = Path(paths.extracted_dir).resolve()
    export_lock = threading.Lock()

    def available_path(filename):
        path = (directory / filename).resolve()
        if path.is_relative_to(directory) and path.is_file():
            return path
        return None

    def metadata(filename):
        path = available_path(filename)
        try:
            stat = path.stat() if path else None
        except FileNotFoundError:
            stat = None
        return {
            "available": stat is not None,
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if stat else None,
        }

    @server.route("/download", strict_slashes=False)
    def download_page():
        files = [{"name": name, "title": title, "description": description, **metadata(name)}
                 for name, (title, description, _) in FILES.items()]
        return render_template("download.html", files=files, records=metadata("records.csv"))

    @server.route("/download/<path:filename>")
    def download_file(filename):
        if filename not in FILES:
            abort(404)
        path = available_path(filename)
        if path is None:
            flash("That file is not available yet. Ask an administrator to update the data.", "error")
            return redirect(url_for("download_page"))
        try:
            return attachment(path.open("rb"), filename, FILES[filename][2])
        except FileNotFoundError:
            flash("The file changed while preparing the download. Please try again.", "error")
            return redirect(url_for("download_page"))

    def generated_download(filename, writer, mimetype):
        # POST uses the existing session CSRF check; limit conversion to one job.
        if not export_lock.acquire(blocking=False):
            flash("Another export is being prepared. Please try again shortly.", "error")
            return redirect(url_for("download_page"), code=303)
        output = None
        try:
            path = available_path("records.csv")
            if path is None:
                raise FileNotFoundError
            output = tempfile.TemporaryFile(mode="w+b")
            # Keep this descriptor open: atomic replacement by an update cannot
            # mix old and new rows in a download already in progress.
            with path.open(newline="", encoding="utf-8-sig") as source:
                writer(source, output)
            output.seek(0)
            response = attachment(output, filename, mimetype)
            output = None  # The response owns the temporary file until it closes.
            return response
        except FileNotFoundError:
            flash("No records are available yet. Ask an administrator to update the data.", "error")
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception:
            logger.exception("%s download failed", filename)
            flash("Could not prepare the export. Please try the CSV download instead.", "error")
        finally:
            if output is not None:
                output.close()
            export_lock.release()
        return redirect(url_for("download_page"), code=303)

    @server.route("/download/records.xlsx", methods=["POST"])
    def download_excel():
        return generated_download("records.xlsx", write_excel,
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @server.route("/download/figures.html", methods=["POST"])
    def download_html():
        return generated_download("figures.html", write_html, "text/html")
