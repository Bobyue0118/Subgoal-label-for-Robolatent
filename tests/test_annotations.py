import json

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


@pytest.mark.parametrize("frame_indices", [[183, 241.5], [False, 241], ["317", 241]])
def test_save_episode_annotations_raises_for_invalid_frame_indices(
    tmp_path, frame_indices
):
    target = tmp_path / "annotations.json"

    with pytest.raises(AnnotationFileError):
        save_episode_annotations(target, "episode_49", frame_indices)
