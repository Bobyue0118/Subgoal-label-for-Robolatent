from app.config import dataset_paths, resolve_dataset_dir


def test_resolve_dataset_dir_prefers_env_override(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "episodes"
    dataset_dir.mkdir()
    monkeypatch.setenv("DATASET_DIR", str(dataset_dir))

    assert resolve_dataset_dir(tmp_path / "repo") == dataset_dir


def test_dataset_paths_default_to_repo_parent(tmp_path, monkeypatch):
    monkeypatch.delenv("DATASET_DIR", raising=False)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    paths = dataset_paths(repo_root)

    assert paths.dataset_dir == tmp_path
    assert paths.annotations_file == tmp_path / "annotations.json"
    assert paths.extracted_frames_dir == tmp_path / "extracted_frames"


def test_dataset_paths_use_env_override(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "episodes"
    dataset_dir.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("DATASET_DIR", str(dataset_dir))

    paths = dataset_paths(repo_root)

    assert paths.dataset_dir == dataset_dir
    assert paths.annotations_file == dataset_dir / "annotations.json"
    assert paths.extracted_frames_dir == dataset_dir / "extracted_frames"
