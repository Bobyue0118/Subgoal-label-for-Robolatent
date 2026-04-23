from io import BytesIO
from pathlib import Path

import h5py
from PIL import Image


CAM_HIGH_DATASET = "/observations/images/cam_high"
CAMERA_DATASETS = {
    "cam_high": "/observations/images/cam_high",
    "cam_head": "/observations/images/cam_head",
    "cam_left_wrist": "/observations/images/cam_left_wrist",
    "cam_right_wrist": "/observations/images/cam_right_wrist",
}


def frame_png_bytes(hdf5_path: Path, camera: str, frame_index: int) -> bytes:
    if camera not in CAMERA_DATASETS:
        raise KeyError(camera)
    if frame_index < 0:
        raise IndexError(frame_index)

    with h5py.File(hdf5_path, "r") as handle:
        frames = handle[CAMERA_DATASETS[camera]]
        if frame_index >= int(frames.shape[0]):
            raise IndexError(frame_index)
        buffer = BytesIO()
        Image.fromarray(frames[frame_index]).save(buffer, format="PNG")
        return buffer.getvalue()


def extract_cam_high_frames(
    hdf5_path: Path,
    output_dir: Path,
    overwrite: bool = False,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(hdf5_path, "r") as handle:
        frames = handle[CAM_HIGH_DATASET]
        for frame_index, frame in enumerate(frames):
            target = output_dir / f"frame_{frame_index:06d}.png"
            if target.exists() and not overwrite:
                continue
            Image.fromarray(frame).save(target)
    return len(list(output_dir.glob("frame_*.png")))
