import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


CAMERAS = ("cam_high", "cam_head", "cam_left_wrist", "cam_right_wrist")
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
        missing_cameras = [camera for camera in CAMERAS if camera not in item["videos"]]
        valid = item["hdf5"] is not None and not missing_cameras
        metadata = None
        if valid:
            try:
                metadata = probe_video(item["videos"]["cam_high"])
            except Exception:
                valid = False
        records.append(
            EpisodeRecord(
                episode_id=episode_id,
                hdf5_path=item["hdf5"],
                video_paths=item["videos"],
                frame_count=metadata.frame_count if metadata else None,
                fps=metadata.fps if metadata else None,
                valid=valid,
                missing_cameras=missing_cameras,
            )
        )
    return records
