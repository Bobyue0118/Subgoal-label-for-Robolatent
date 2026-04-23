from pathlib import Path

import h5py
import numpy as np

from app.episodes import CAMERAS, DEFAULT_FPS, VideoMetadata, discover_episodes


def write_empty(path: Path) -> None:
    path.write_bytes(b"")


def write_episode_hdf5(
    path: Path,
    cameras: tuple[str, ...] | list[str],
    frame_count: int = 2,
) -> None:
    with h5py.File(path, "w") as handle:
        for camera_index, camera in enumerate(cameras):
            handle.create_dataset(
                f"/observations/images/{camera}",
                data=np.full((frame_count, 2, 2, 3), camera_index, dtype=np.uint8),
            )


def test_discover_episodes_uses_hdf5_camera_datasets_for_validity(tmp_path):
    write_episode_hdf5(tmp_path / "episode_1.hdf5", CAMERAS, frame_count=2)
    write_episode_hdf5(tmp_path / "episode_2.hdf5", ("cam_high",), frame_count=3)

    episodes = discover_episodes(tmp_path)

    assert [episode.episode_id for episode in episodes] == ["episode_1", "episode_2"]
    assert episodes[0].valid is True
    assert episodes[0].frame_count == 2
    assert episodes[0].fps == DEFAULT_FPS
    assert episodes[1].valid is False
    assert episodes[1].missing_cameras == [
        "cam_head",
        "cam_left_wrist",
        "cam_right_wrist",
    ]


def test_discover_episodes_sorts_episode_ids_numerically(tmp_path):
    write_episode_hdf5(tmp_path / "episode_10.hdf5", CAMERAS)
    write_episode_hdf5(tmp_path / "episode_2.hdf5", CAMERAS)

    episodes = discover_episodes(tmp_path)

    assert [episode.episode_id for episode in episodes] == ["episode_2", "episode_10"]


def test_discover_episodes_uses_video_probe_for_fps_when_available(tmp_path):
    write_episode_hdf5(tmp_path / "episode_1.hdf5", CAMERAS, frame_count=4)
    write_empty(tmp_path / "episode_1_cam_high.mp4")
    probed_paths: list[Path] = []

    def fake_probe(path: Path) -> VideoMetadata:
        probed_paths.append(path)
        return VideoMetadata(frame_count=4, fps=12.0)

    episodes = discover_episodes(tmp_path, probe_video=fake_probe)

    assert probed_paths == [tmp_path / "episode_1_cam_high.mp4"]
    assert episodes[0].valid is True
    assert episodes[0].frame_count == 4
    assert episodes[0].fps == 12.0


def test_discover_episodes_keeps_valid_hdf5_episode_when_video_probe_fails(tmp_path):
    write_episode_hdf5(tmp_path / "episode_1.hdf5", CAMERAS, frame_count=5)
    write_empty(tmp_path / "episode_1_cam_high.mp4")

    def fake_probe(_path: Path) -> VideoMetadata:
        raise RuntimeError("probe failed")

    episodes = discover_episodes(tmp_path, probe_video=fake_probe)

    assert episodes[0].valid is True
    assert episodes[0].frame_count == 5
    assert episodes[0].fps == DEFAULT_FPS
