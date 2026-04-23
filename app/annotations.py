import json
from pathlib import Path


class AnnotationFileError(RuntimeError):
    pass


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
        raw = json.loads(annotations_file.read_text())
    except json.JSONDecodeError as exc:
        raise AnnotationFileError(
            f"Malformed annotations file: {annotations_file}"
        ) from exc
    return _normalize_annotations(raw, annotations_file)


def save_episode_annotations(
    annotations_file: Path,
    episode_id: str,
    frame_indices: list[int],
) -> dict[str, list[int]]:
    annotations = load_annotations(annotations_file)
    annotations[episode_id] = _normalize_frame_indices(
        frame_indices,
        annotations_file,
        episode_id,
    )
    annotations_file.write_text(json.dumps(annotations, indent=2, sort_keys=True) + "\n")
    return annotations
