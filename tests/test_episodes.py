from pathlib import Path

from app.episodes import VideoMetadata, discover_episodes


def write_empty(path: Path) -> None:
    path.write_bytes(b"")


def write_files(dataset_dir: Path, names: list[str]) -> None:
    for name in names:
        write_empty(dataset_dir / name)


def test_discover_episodes_returns_valid_and_invalid_records(tmp_path):
    write_files(
        tmp_path,
        [
            "episode_1.hdf5",
            "episode_1_cam_high.mp4",
            "episode_1_cam_head.mp4",
            "episode_1_cam_left_wrist.mp4",
            "episode_1_cam_right_wrist.mp4",
            "episode_2.hdf5",
            "episode_2_cam_high.mp4",
        ],
    )

    def fake_probe(_path: Path) -> VideoMetadata:
        return VideoMetadata(frame_count=422, fps=15.0)

    episodes = discover_episodes(tmp_path, probe_video=fake_probe)

    assert [episode.episode_id for episode in episodes] == ["episode_1", "episode_2"]
    assert episodes[0].valid is True
    assert episodes[0].frame_count == 422
    assert episodes[0].fps == 15.0
    assert episodes[1].valid is False
    assert episodes[1].missing_cameras == [
        "cam_head",
        "cam_left_wrist",
        "cam_right_wrist",
    ]


def test_discover_episodes_sorts_episode_ids_numerically(tmp_path):
    write_files(
        tmp_path,
        [
            "episode_10.hdf5",
            "episode_2.hdf5",
        ],
    )

    episodes = discover_episodes(tmp_path)

    assert [episode.episode_id for episode in episodes] == ["episode_2", "episode_10"]


def test_discover_episodes_probes_only_valid_complete_episodes(tmp_path):
    write_files(
        tmp_path,
        [
            "episode_1.hdf5",
            "episode_1_cam_high.mp4",
            "episode_1_cam_head.mp4",
            "episode_1_cam_left_wrist.mp4",
            "episode_1_cam_right_wrist.mp4",
            "episode_2.hdf5",
            "episode_2_cam_high.mp4",
            "episode_3_cam_high.mp4",
            "episode_3_cam_head.mp4",
            "episode_3_cam_left_wrist.mp4",
            "episode_3_cam_right_wrist.mp4",
        ],
    )
    probed_paths: list[Path] = []

    def fake_probe(path: Path) -> VideoMetadata:
        probed_paths.append(path)
        return VideoMetadata(frame_count=422, fps=15.0)

    discover_episodes(tmp_path, probe_video=fake_probe)

    assert probed_paths == [tmp_path / "episode_1_cam_high.mp4"]


def test_discover_episodes_marks_probe_failures_invalid_and_continues(tmp_path):
    write_files(
        tmp_path,
        [
            "episode_1.hdf5",
            "episode_1_cam_high.mp4",
            "episode_1_cam_head.mp4",
            "episode_1_cam_left_wrist.mp4",
            "episode_1_cam_right_wrist.mp4",
            "episode_2.hdf5",
            "episode_2_cam_high.mp4",
            "episode_2_cam_head.mp4",
            "episode_2_cam_left_wrist.mp4",
            "episode_2_cam_right_wrist.mp4",
        ],
    )
    probed_paths: list[Path] = []

    def fake_probe(path: Path) -> VideoMetadata:
        probed_paths.append(path)
        if path.name == "episode_1_cam_high.mp4":
            raise RuntimeError("probe failed")
        return VideoMetadata(frame_count=300, fps=24.0)

    episodes = discover_episodes(tmp_path, probe_video=fake_probe)

    assert probed_paths == [
        tmp_path / "episode_1_cam_high.mp4",
        tmp_path / "episode_2_cam_high.mp4",
    ]
    assert [episode.episode_id for episode in episodes] == ["episode_1", "episode_2"]
    assert episodes[0].valid is False
    assert episodes[0].frame_count is None
    assert episodes[0].fps is None
    assert episodes[0].missing_cameras == []
    assert episodes[1].valid is True
    assert episodes[1].frame_count == 300
    assert episodes[1].fps == 24.0
