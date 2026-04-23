import json
import os
from pathlib import Path
import threading
import time

import pytest

from app.annotations import AnnotationFileError, load_annotations, save_episode_annotations


def test_load_annotations_returns_empty_dict_for_missing_file(tmp_path):
    target = tmp_path / "annotations.json"

    assert load_annotations(target) == {}


def test_save_episode_annotations_sorts_and_deduplicates(tmp_path):
    target = tmp_path / "annotations.json"

    save_episode_annotations(target, "episode_49", [317, 183, 317, 241])

    assert json.loads(target.read_text()) == {"episode_49": [183, 241, 317]}


def test_save_episode_annotations_preserves_existing_episodes(tmp_path):
    target = tmp_path / "annotations.json"
    target.write_text(json.dumps({"episode_48": [8, 13]}))

    save_episode_annotations(target, "episode_49", [317, 183, 317, 241])

    assert json.loads(target.read_text()) == {
        "episode_48": [8, 13],
        "episode_49": [183, 241, 317],
    }


@pytest.mark.parametrize("existing_payload", ["{not-valid-json", json.dumps([])])
def test_save_episode_annotations_refuses_invalid_existing_file(
    tmp_path, existing_payload
):
    target = tmp_path / "annotations.json"
    target.write_text(existing_payload)

    with pytest.raises(AnnotationFileError):
        save_episode_annotations(target, "episode_49", [183, 241, 317])

    assert target.read_text() == existing_payload


def test_load_annotations_raises_for_malformed_json(tmp_path):
    target = tmp_path / "annotations.json"
    target.write_text("{not-valid-json")

    with pytest.raises(AnnotationFileError):
        load_annotations(target)


@pytest.mark.parametrize("payload", [[], {"episode_49": 317}])
def test_load_annotations_raises_for_invalid_schema(tmp_path, payload):
    target = tmp_path / "annotations.json"
    target.write_text(json.dumps(payload))

    with pytest.raises(AnnotationFileError):
        load_annotations(target)


@pytest.mark.parametrize(
    "payload",
    [
        {"episode_49": [-1, 241]},
        {"episode_49": [183, 241.5]},
        {"episode_49": [False, 241]},
        {"episode_49": ["317", 241]},
    ],
)
def test_load_annotations_raises_for_invalid_frame_indices(tmp_path, payload):
    target = tmp_path / "annotations.json"
    target.write_text(json.dumps(payload))

    with pytest.raises(AnnotationFileError):
        load_annotations(target)


@pytest.mark.parametrize(
    "frame_indices",
    [[-1, 241], [183, 241.5], [False, 241], ["317", 241]],
)
def test_save_episode_annotations_raises_for_invalid_frame_indices(
    tmp_path, frame_indices
):
    target = tmp_path / "annotations.json"

    with pytest.raises(AnnotationFileError):
        save_episode_annotations(target, "episode_49", frame_indices)


def test_save_episode_annotations_waits_for_lock_before_writing(tmp_path):
    target = tmp_path / "annotations.json"
    target.write_text(json.dumps({"episode_48": [8]}))
    lock_file = target.with_name(f"{target.name}.lock")
    lock_file.write_text("locked")

    started = threading.Event()
    finished = threading.Event()
    errors: list[Exception] = []

    def worker() -> None:
        started.set()
        try:
            save_episode_annotations(target, "episode_49", [241])
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=worker)
    thread.start()
    assert started.wait(timeout=1)
    time.sleep(0.05)

    assert finished.is_set() is False
    assert json.loads(target.read_text()) == {"episode_48": [8]}

    lock_file.unlink()
    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert errors == []
    assert json.loads(target.read_text()) == {
        "episode_48": [8],
        "episode_49": [241],
    }


def test_save_episode_annotations_uses_unique_sibling_temp_file(tmp_path, monkeypatch):
    target = tmp_path / "annotations.json"
    reserved_temp = target.with_name(f"{target.name}.tmp")
    reserved_temp.write_text("sentinel")
    replace_calls: list[tuple[Path, Path]] = []
    original_replace = os.replace

    def recording_replace(src, dst) -> None:
        replace_calls.append((Path(src), Path(dst)))
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", recording_replace)

    save_episode_annotations(target, "episode_49", [241])

    assert json.loads(target.read_text()) == {"episode_49": [241]}
    assert reserved_temp.read_text() == "sentinel"
    assert len(replace_calls) == 1
    source, destination = replace_calls[0]
    assert source.parent == target.parent
    assert destination == target
    assert source != target
    assert source.name != reserved_temp.name
