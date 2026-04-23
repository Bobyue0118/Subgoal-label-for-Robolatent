from pathlib import Path

import h5py
from PIL import Image


CAM_HIGH_DATASET = "/observations/images/cam_high"


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
