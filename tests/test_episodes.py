from pathlib import Path

from app.episodes import VideoMetadata, discover_episodes


def write_empty(path: Path) -> None:
    path.write_bytes(b"")


def test_discover_episodes_returns_valid_and_invalid_records(tmp_path):
    for name in [
        "episode_1.hdf5",
        "episode_1_cam_high.mp4",
        "episode_1_cam_head.mp4",
        "episode_1_cam_left_wrist.mp4",
        "episode_1_cam_right_wrist.mp4",
        "episode_2.hdf5",
        "episode_2_cam_high.mp4",
    ]:
        write_empty(tmp_path / name)

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
