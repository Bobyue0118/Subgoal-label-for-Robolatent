import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetPaths:
    dataset_dir: Path
    annotations_file: Path
    extracted_frames_dir: Path


def resolve_dataset_dir(repo_root: Path) -> Path:
    configured = os.environ.get("DATASET_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root.resolve().parent


def dataset_paths(repo_root: Path) -> DatasetPaths:
    dataset_dir = resolve_dataset_dir(repo_root)
    return DatasetPaths(
        dataset_dir=dataset_dir,
        annotations_file=dataset_dir / "annotations.json",
        extracted_frames_dir=dataset_dir / "extracted_frames",
    )
