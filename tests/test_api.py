from pathlib import Path

from app.main import create_app


def write_empty(path: Path) -> None:
    path.write_bytes(b"")


def test_episode_and_annotation_routes_return_expected_payloads(tmp_path):
    for name in [
        "episode_49.hdf5",
        "episode_49_cam_high.mp4",
        "episode_49_cam_head.mp4",
        "episode_49_cam_left_wrist.mp4",
        "episode_49_cam_right_wrist.mp4",
    ]:
        write_empty(tmp_path / name)

    app = create_app(dataset_dir=tmp_path)

    def fake_probe(_path: Path):
        from app.episodes import VideoMetadata

        return VideoMetadata(frame_count=422, fps=15.0)

    app.config["PROBE_VIDEO"] = fake_probe
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
    assert (
        episodes_response.get_json()[0]["videos"]["cam_high"]
        == "/dataset/episode_49_cam_high.mp4"
    )
    assert annotations_response.get_json() == {}
    assert save_response.get_json()["episode_49"] == [183, 241]


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
