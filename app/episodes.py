import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import h5py


CAMERAS = ("cam_high", "cam_head", "cam_left_wrist", "cam_right_wrist")
CAMERA_DATASETS = {
    camera: f"/observations/images/{camera}"
    for camera in CAMERAS
}
DEFAULT_FPS = 15.0
HDF5_RE = re.compile(r"^(episode_\d+)\.hdf5$")
VIDEO_RE = re.compile(r"^(episode_\d+)_(cam_[a-z_]+)\.mp4$")


@dataclass(frozen=True)
class VideoMetadata:
    frame_count: int
    fps: float


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    hdf5_path: Path | None
    video_paths: dict[str, Path]
    frame_count: int | None
    fps: float | None
    valid: bool
    missing_cameras: list[str]

    def to_dict(self) -> dict:
        return {
            "episodeId": self.episode_id,
            "hdf5Path": str(self.hdf5_path) if self.hdf5_path else None,
            "videos": {camera: str(path) for camera, path in self.video_paths.items()},
            "frameCount": self.frame_count,
            "fps": self.fps,
            "valid": self.valid,
            "missingCameras": self.missing_cameras,
        }


def probe_video_metadata(video_path: Path) -> VideoMetadata:
    import json

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_frames,r_frame_rate",
            "-of",
            "json",
            str(video_path),
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    numerator, denominator = stream["r_frame_rate"].split("/")
    return VideoMetadata(
        frame_count=int(stream["nb_frames"]),
        fps=int(numerator) / int(denominator),
    )


def inspect_episode_hdf5(hdf5_path: Path) -> tuple[int | None, list[str]]:
    missing_cameras: list[str] = []
    frame_count: int | None = None

    with h5py.File(hdf5_path, "r") as handle:
        for camera, dataset_path in CAMERA_DATASETS.items():
            if dataset_path not in handle:
                missing_cameras.append(camera)
                continue

            dataset = handle[dataset_path]
            camera_frame_count = int(dataset.shape[0])
            if frame_count is None:
                frame_count = camera_frame_count
            elif camera_frame_count != frame_count:
                raise ValueError("camera frame counts do not match")

    return frame_count, missing_cameras


def discover_episodes(
    dataset_dir: Path,
    probe_video=probe_video_metadata,
) -> list[EpisodeRecord]:
    grouped: dict[str, dict] = {}
    for path in sorted(dataset_dir.iterdir()):
        hdf5_match = HDF5_RE.match(path.name)
        if hdf5_match:
            grouped.setdefault(hdf5_match.group(1), {"hdf5": None, "videos": {}})[
                "hdf5"
            ] = path
            continue
        video_match = VIDEO_RE.match(path.name)
        if video_match:
            episode = grouped.setdefault(
                video_match.group(1),
                {"hdf5": None, "videos": {}},
            )
            episode["videos"][video_match.group(2)] = path

    records: list[EpisodeRecord] = []
    for episode_id in sorted(grouped, key=lambda value: int(value.split("_")[1])):
        item = grouped[episode_id]
        frame_count = None
        fps = DEFAULT_FPS
        missing_cameras = list(CAMERAS)
        valid = False

        if item["hdf5"] is not None:
            try:
                frame_count, missing_cameras = inspect_episode_hdf5(item["hdf5"])
                valid = frame_count is not None and not missing_cameras
            except Exception:
                frame_count = None
                missing_cameras = []

        if valid and "cam_high" in item["videos"]:
            try:
                fps = probe_video(item["videos"]["cam_high"]).fps
            except Exception:
                fps = DEFAULT_FPS

        records.append(
            EpisodeRecord(
                episode_id=episode_id,
                hdf5_path=item["hdf5"],
                video_paths=item["videos"],
                frame_count=frame_count,
                fps=fps,
                valid=valid,
                missing_cameras=missing_cameras,
            )
        )
    return records
