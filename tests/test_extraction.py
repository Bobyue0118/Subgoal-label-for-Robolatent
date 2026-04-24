import h5py
import numpy as np
from PIL import Image

from app.extraction import extract_cam_high_frames


def test_extract_cam_high_frames_writes_pngs_in_frame_order(tmp_path):
    hdf5_path = tmp_path / "episode_49.hdf5"
    with h5py.File(hdf5_path, "w") as handle:
        handle.create_dataset(
            "/observations/images/cam_high",
            data=np.array(
                [
                    [[[0, 0, 255], [0, 0, 0]], [[0, 0, 0], [0, 255, 0]]],
                    [[[255, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 255, 255]]],
                ],
                dtype=np.uint8,
            ),
        )

    output_dir = tmp_path / "frames"
    exported = extract_cam_high_frames(hdf5_path, output_dir)

    assert exported == 2
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "frame_000000.png",
        "frame_000001.png",
    ]
    image = Image.open(output_dir / "frame_000000.png")
    assert image.size == (2, 2)
    assert image.getpixel((0, 0)) == (255, 0, 0)
