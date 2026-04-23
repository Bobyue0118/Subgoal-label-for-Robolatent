import json

import pytest

from app.annotations import AnnotationFileError, load_annotations, save_episode_annotations


def test_save_episode_annotations_sorts_and_deduplicates(tmp_path):
    target = tmp_path / "annotations.json"

    save_episode_annotations(target, "episode_49", [317, 183, 317, 241])

    assert json.loads(target.read_text()) == {"episode_49": [183, 241, 317]}


def test_load_annotations_raises_for_malformed_json(tmp_path):
    target = tmp_path / "annotations.json"
    target.write_text("{not-valid-json")

    with pytest.raises(AnnotationFileError):
        load_annotations(target)
