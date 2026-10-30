"""Shared source/output configuration, with the original DATA_ROOT layout as fallback."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    source_dir: str
    output_root: str

    @property
    def extracted_dir(self):
        return os.path.join(self.output_root, "extracted")

    @property
    def backup_dir(self):
        return os.path.join(self.output_root, "backup")

    def validate(self):
        source = Path(self.source_dir).resolve()
        for directory in (self.extracted_dir, self.backup_dir):
            output = Path(directory).resolve()
            if output.is_relative_to(source) or source.is_relative_to(output):
                raise ValueError("Source data must be separate from the extracted and backup directories.")
        return self


def get_data_paths(legacy_root=None, source_dir=None, output_root=None):
    root = legacy_root if legacy_root is not None else os.environ.get("DATA_ROOT", "/mcs_bead_project")
    return DataPaths(
        source_dir=source_dir or os.environ.get("SOURCE_DATA_DIR") or os.path.join(root, "data"),
        output_root=output_root or os.environ.get("OUTPUT_ROOT") or root,
    ).validate()
