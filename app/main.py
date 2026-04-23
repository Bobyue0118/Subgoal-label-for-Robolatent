from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from app.annotations import load_annotations, save_episode_annotations
from app.config import dataset_paths
from app.episodes import discover_episodes, probe_video_metadata
from app.extraction import extract_cam_high_frames


def create_app(dataset_dir: Path | None = None) -> Flask:
    repo_root = Path(__file__).resolve().parents[1]
    paths = dataset_paths(repo_root=repo_root, dataset_dir=dataset_dir)

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["DATASET_PATHS"] = paths
    app.config["PROBE_VIDEO"] = probe_video_metadata

    @app.get("/")
    def index():
        return send_file(Path(app.static_folder) / "index.html")

    @app.get("/dataset/<path:filename>")
    def dataset_file(filename: str):
        return send_from_directory(paths.dataset_dir, filename)

    @app.get("/api/episodes")
    def api_episodes():
        payload = []
        for record in discover_episodes(
            paths.dataset_dir,
            probe_video=app.config["PROBE_VIDEO"],
        ):
            item = record.to_dict()
            item["videos"] = {
                camera: f"/dataset/{path.name}"
                for camera, path in record.video_paths.items()
            }
            payload.append(item)
        return jsonify(payload)

    @app.get("/api/annotations")
    def api_annotations():
        return jsonify(load_annotations(paths.annotations_file))

    @app.put("/api/annotations/<episode_id>")
    def api_save_annotations(episode_id: str):
        body = request.get_json(force=True)
        saved = save_episode_annotations(
            paths.annotations_file,
            episode_id,
            body["frameIndices"],
        )
        return jsonify(saved)

    @app.post("/api/episodes/<episode_id>/extract-cam-high")
    def api_extract_cam_high(episode_id: str):
        records = {
            record.episode_id: record
            for record in discover_episodes(
                paths.dataset_dir,
                probe_video=app.config["PROBE_VIDEO"],
            )
        }
        record = records[episode_id]
        output_dir = paths.extracted_frames_dir / episode_id / "cam_high"
        exported = extract_cam_high_frames(record.hdf5_path, output_dir, overwrite=False)
        return jsonify(
            {
                "episodeId": episode_id,
                "exportedFrames": exported,
                "outputDir": str(output_dir),
            }
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
