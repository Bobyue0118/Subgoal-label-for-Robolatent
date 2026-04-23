import json
from pathlib import Path


class AnnotationFileError(RuntimeError):
    pass


def load_annotations(annotations_file: Path) -> dict[str, list[int]]:
    if not annotations_file.exists():
        return {}
    try:
        raw = json.loads(annotations_file.read_text())
    except json.JSONDecodeError as exc:
        raise AnnotationFileError(
            f"Malformed annotations file: {annotations_file}"
        ) from exc
    return {
        episode_id: sorted({int(frame_index) for frame_index in frame_indices})
        for episode_id, frame_indices in raw.items()
    }


def save_episode_annotations(
    annotations_file: Path,
    episode_id: str,
    frame_indices: list[int],
) -> dict[str, list[int]]:
    annotations = load_annotations(annotations_file)
    annotations[episode_id] = sorted({int(frame_index) for frame_index in frame_indices})
    annotations_file.write_text(json.dumps(annotations, indent=2, sort_keys=True) + "\n")
    return annotations
