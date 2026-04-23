import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


class AnnotationFileError(RuntimeError):
    pass


LOCK_POLL_INTERVAL_SECONDS = 0.01
LOCK_TIMEOUT_SECONDS = 5.0


def _normalize_frame_indices(
    frame_indices: object,
    annotations_file: Path,
    episode_id: str,
) -> list[int]:
    if not isinstance(frame_indices, list):
        raise AnnotationFileError(
            f"Invalid frame index list for {episode_id} in {annotations_file}"
        )

    normalized: set[int] = set()
    for frame_index in frame_indices:
        if isinstance(frame_index, bool) or not isinstance(frame_index, int):
            raise AnnotationFileError(
                f"Invalid frame index for {episode_id} in {annotations_file}"
            )
        if frame_index < 0:
            raise AnnotationFileError(
                f"Negative frame index for {episode_id} in {annotations_file}"
            )
        normalized.add(frame_index)
    return sorted(normalized)


def _normalize_annotations(raw: object, annotations_file: Path) -> dict[str, list[int]]:
    if not isinstance(raw, dict):
        raise AnnotationFileError(f"Invalid annotations file: {annotations_file}")

    return {
        episode_id: _normalize_frame_indices(frame_indices, annotations_file, episode_id)
        for episode_id, frame_indices in raw.items()
    }


def load_annotations(annotations_file: Path) -> dict[str, list[int]]:
    if not annotations_file.exists():
        return {}
    try:
        raw = json.loads(annotations_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AnnotationFileError(
            f"Malformed annotations file: {annotations_file}"
        ) from exc
    return _normalize_annotations(raw, annotations_file)


@contextmanager
def _locked_annotations_file(annotations_file: Path):
    lock_file = annotations_file.with_name(f"{annotations_file.name}.lock")
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS

    while True:
        try:
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise AnnotationFileError(
                    f"Timed out waiting for annotation lock: {annotations_file}"
                )
            time.sleep(LOCK_POLL_INTERVAL_SECONDS)

    try:
        yield
    finally:
        os.close(lock_fd)
        lock_file.unlink(missing_ok=True)


def _write_annotations_atomically(
    annotations_file: Path,
    annotations: dict[str, list[int]],
) -> None:
    payload = json.dumps(annotations, indent=2, sort_keys=True) + "\n"
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f"{annotations_file.name}.",
        suffix=".tmp",
        dir=annotations_file.parent,
        text=True,
    )
    temp_file = Path(temp_name)

    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temp_file, annotations_file)
    finally:
        temp_file.unlink(missing_ok=True)


def save_episode_annotations(
    annotations_file: Path,
    episode_id: str,
    frame_indices: list[int],
) -> dict[str, list[int]]:
    with _locked_annotations_file(annotations_file):
        annotations = load_annotations(annotations_file)
        annotations[episode_id] = _normalize_frame_indices(
            frame_indices,
            annotations_file,
            episode_id,
        )
        _write_annotations_atomically(annotations_file, annotations)
        return annotations
