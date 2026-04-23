from io import BytesIO
from pathlib import Path

import h5py
import numpy as np
from PIL import Image

from app.episodes import CAMERAS
from app.main import create_app


def write_episode_hdf5(path: Path, frame_count: int = 2) -> None:
    with h5py.File(path, "w") as handle:
        for camera_index, camera in enumerate(CAMERAS):
            data = np.full((frame_count, 2, 2, 3), camera_index * 30, dtype=np.uint8)
            if camera == "cam_high":
                data[1, 0, 0] = [255, 0, 0]
            handle.create_dataset(f"/observations/images/{camera}", data=data)


def test_episode_and_annotation_routes_return_expected_payloads(tmp_path):
    write_episode_hdf5(tmp_path / "episode_49.hdf5", frame_count=2)

    app = create_app(dataset_dir=tmp_path)
    client = app.test_client()

    episodes_response = client.get("/api/episodes")
    annotations_response = client.get("/api/annotations")
    save_response = client.put(
        "/api/annotations/episode_49",
        json={"frameIndices": [241, 183]},
    )

    assert episodes_response.status_code == 200
    assert annotations_response.status_code == 200
    assert save_response.status_code == 200
    assert episodes_response.get_json()[0]["episodeId"] == "episode_49"
    assert episodes_response.get_json()[0]["frameCount"] == 2
    assert episodes_response.get_json()[0]["frameBasePath"] == "/api/episodes/episode_49/frames"
    assert episodes_response.get_json()[0]["valid"] is True
    assert annotations_response.get_json() == {}
    assert save_response.get_json()["episode_49"] == [183, 241]


def test_episode_frame_route_returns_png_from_hdf5(tmp_path):
    write_episode_hdf5(tmp_path / "episode_49.hdf5", frame_count=2)

    app = create_app(dataset_dir=tmp_path)
    client = app.test_client()

    response = client.get("/api/episodes/episode_49/frames/cam_high/1.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    image = Image.open(BytesIO(response.data))
    assert image.size == (2, 2)
    assert image.getpixel((0, 0)) == (255, 0, 0)


def test_root_page_contains_annotation_controls(tmp_path):
    app = create_app(dataset_dir=tmp_path)
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="episode-list"' in html
    assert 'id="viewer-grid"' in html
    assert 'id="mark-frame"' in html
    assert 'id="extract-cam-high"' in html


def test_root_page_loads_frontend_modules(tmp_path):
    app = create_app(dataset_dir=tmp_path)
    client = app.test_client()

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "fetchEpisodes" in response.get_data(as_text=True)
