# Episode Frame Annotation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local browser app that lets a user annotate multiple zero-based `frame_index` labels per episode while reviewing 4 synchronized camera videos and exporting `cam_high` frames from each episode `.hdf5`.

**Architecture:** Use a small Flask backend to discover episodes, validate the expected file set, persist `annotations.json`, serve the local MP4 files, and extract `cam_high` PNGs from `.hdf5`. Use a plain HTML/CSS/ES-module frontend with one authoritative frame controller that drives all four video panes from the same `currentFrameIndex`.

**Tech Stack:** Python 3.11, Flask, h5py, Pillow, pytest, vanilla HTML/CSS/JavaScript, Node built-in test runner, `ffprobe`

---

## Assumptions

- The repository lives inside the dataset directory, so the default dataset root is the repo parent directory.
- `DATASET_DIR` may override the default dataset root for other setups.
- `annotations.json` and `extracted_frames/` live under the dataset root, not inside the repo.
- `frame_index` is zero-based and must stay within `0..frame_count-1`.

## Planned File Structure

- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/episodes.py`
- Create: `app/annotations.py`
- Create: `app/extraction.py`
- Create: `app/main.py`
- Create: `app/static/index.html`
- Create: `app/static/app.css`
- Create: `app/static/api.js`
- Create: `app/static/player-controller.js`
- Create: `app/static/app.js`
- Create: `tests/test_config.py`
- Create: `tests/test_episodes.py`
- Create: `tests/test_annotations.py`
- Create: `tests/test_extraction.py`
- Create: `tests/test_api.py`
- Create: `frontend-tests/player-controller.test.mjs`

### File Responsibilities

- `.gitignore`: ignore local Python artifacts and `.DS_Store`
- `pyproject.toml`: Python project metadata and dependencies
- `app/config.py`: dataset-root resolution and canonical data paths
- `app/episodes.py`: file discovery, metadata probing, and episode validation
- `app/annotations.py`: load, sanitize, sort, and save shared JSON annotations
- `app/extraction.py`: export `/observations/images/cam_high` to ordered PNGs
- `app/main.py`: Flask app factory, API routes, static shell, and dataset file serving
- `app/static/index.html`: sidebar, 2x2 viewer, and controls shell
- `app/static/app.css`: layout and visual states
- `app/static/api.js`: `fetch` wrappers for episodes, annotations, and extraction
- `app/static/player-controller.js`: pure frame math and mark/unmark helpers
- `app/static/app.js`: DOM wiring, playback sync loop, and UI rendering
- `tests/*.py`: backend unit and API coverage
- `frontend-tests/player-controller.test.mjs`: frontend frame-controller unit coverage

### Task 1: Bootstrap The Project Skeleton

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Test: `tests/test_config.py`

Before Step 3, pause and get approval for the new Python dependencies in `pyproject.toml`: `Flask`, `h5py`, `Pillow`, and `pytest`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path

from app.config import dataset_paths, resolve_dataset_dir


def test_resolve_dataset_dir_prefers_env_override(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "episodes"
    dataset_dir.mkdir()
    monkeypatch.setenv("DATASET_DIR", str(dataset_dir))

    assert resolve_dataset_dir(tmp_path / "repo") == dataset_dir


def test_dataset_paths_default_to_repo_parent(tmp_path, monkeypatch):
    monkeypatch.delenv("DATASET_DIR", raising=False)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    paths = dataset_paths(repo_root)

    assert paths.dataset_dir == tmp_path
    assert paths.annotations_file == tmp_path / "annotations.json"
    assert paths.extracted_frames_dir == tmp_path / "extracted_frames"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write minimal implementation**

```gitignore
# .gitignore
.DS_Store
.pytest_cache/
__pycache__/
*.pyc
.venv/
```

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "subgoal-label-for-robolatent"
version = "0.1.0"
description = "Local episode frame annotation tool"
requires-python = ">=3.11"
dependencies = [
  "Flask>=3.0,<4.0",
  "h5py>=3.11,<4.0",
  "Pillow>=10.3,<11.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# app/__init__.py
"""Application package for the local annotation tool."""
```

```python
# app/config.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class DatasetPaths:
    dataset_dir: Path
    annotations_file: Path
    extracted_frames_dir: Path


def resolve_dataset_dir(repo_root: Path) -> Path:
    configured = os.environ.get("DATASET_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root.resolve().parent


def dataset_paths(repo_root: Path) -> DatasetPaths:
    dataset_dir = resolve_dataset_dir(repo_root)
    return DatasetPaths(
        dataset_dir=dataset_dir,
        annotations_file=dataset_dir / "annotations.json",
        extracted_frames_dir=dataset_dir / "extracted_frames",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -q`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml app/__init__.py app/config.py tests/test_config.py
git commit -m "chore: bootstrap annotation tool skeleton"
```

### Task 2: Implement Episode Discovery And Validation

**Files:**
- Create: `app/episodes.py`
- Test: `tests/test_episodes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_episodes.py
from pathlib import Path

from app.episodes import discover_episodes, VideoMetadata


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
    assert episodes[1].missing_cameras == ["cam_head", "cam_left_wrist", "cam_right_wrist"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_episodes.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `discover_episodes`

- [ ] **Step 3: Write minimal implementation**

```python
# app/episodes.py
from dataclasses import dataclass
from pathlib import Path
import json
import re
import subprocess


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
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    numerator, denominator = stream["r_frame_rate"].split("/")
    return VideoMetadata(
        frame_count=int(stream["nb_frames"]),
        fps=int(numerator) / int(denominator),
    )


def discover_episodes(dataset_dir: Path, probe_video=probe_video_metadata) -> list[EpisodeRecord]:
    grouped: dict[str, dict] = {}
    for path in sorted(dataset_dir.iterdir()):
        hdf5_match = HDF5_RE.match(path.name)
        if hdf5_match:
            grouped.setdefault(hdf5_match.group(1), {"hdf5": None, "videos": {}})["hdf5"] = path
            continue
        video_match = VIDEO_RE.match(path.name)
        if video_match:
            episode = grouped.setdefault(video_match.group(1), {"hdf5": None, "videos": {}})
            episode["videos"][video_match.group(2)] = path

    records: list[EpisodeRecord] = []
    for episode_id in sorted(grouped, key=lambda value: int(value.split("_")[1])):
        item = grouped[episode_id]
        missing_cameras = [camera for camera in CAMERAS if camera not in item["videos"]]
        valid = item["hdf5"] is not None and not missing_cameras
        metadata = probe_video(item["videos"]["cam_high"]) if valid else None
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_episodes.py -q`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/episodes.py tests/test_episodes.py
git commit -m "feat: add episode discovery and validation"
```

### Task 3: Implement Shared Annotation Storage

**Files:**
- Create: `app/annotations.py`
- Test: `tests/test_annotations.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_annotations.py
import json

import pytest

from app.annotations import AnnotationFileError, load_annotations, save_episode_annotations


def test_save_episode_annotations_sorts_and_deduplicates(tmp_path):
    target = tmp_path / "annotations.json"

    save_episode_annotations(target, "episode_49", [317, 183, 317, 241])

    assert json.loads(target.read_text()) == {"episode_49": [183, 241, 317]}


def test_load_annotations_raises_for_malformed_json(tmp_path):
    target = tmp_path / "annotations.json"
    target.write_text("{not-valid-json")

    with pytest.raises(AnnotationFileError):
        load_annotations(target)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_annotations.py -q`

Expected: FAIL with missing `app.annotations`

- [ ] **Step 3: Write minimal implementation**

```python
# app/annotations.py
import json
from pathlib import Path


class AnnotationFileError(RuntimeError):
    pass


def load_annotations(annotations_file: Path) -> dict[str, list[int]]:
    if not annotations_file.exists():
        return {}
    try:
        raw = json.loads(annotations_file.read_text())
    except json.JSONDecodeError as exc:
        raise AnnotationFileError(f"Malformed annotations file: {annotations_file}") from exc
    return {
        episode_id: sorted({int(frame_index) for frame_index in frame_indices})
        for episode_id, frame_indices in raw.items()
    }


def save_episode_annotations(
    annotations_file: Path,
    episode_id: str,
    frame_indices: list[int],
) -> dict[str, list[int]]:
    annotations = load_annotations(annotations_file)
    annotations[episode_id] = sorted({int(frame_index) for frame_index in frame_indices})
    annotations_file.write_text(json.dumps(annotations, indent=2, sort_keys=True) + "\n")
    return annotations
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_annotations.py -q`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add app/annotations.py tests/test_annotations.py
git commit -m "feat: add shared annotation storage"
```

### Task 4: Implement `cam_high` Frame Extraction

**Files:**
- Create: `app/extraction.py`
- Test: `tests/test_extraction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extraction.py
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
                    [[[255, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 255, 0]]],
                    [[[0, 0, 255], [0, 0, 0]], [[0, 0, 0], [255, 255, 0]]],
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
    assert Image.open(output_dir / "frame_000001.png").size == (2, 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_extraction.py -q`

Expected: FAIL with missing `app.extraction`

- [ ] **Step 3: Write minimal implementation**

```python
# app/extraction.py
from pathlib import Path

import h5py
from PIL import Image


CAM_HIGH_DATASET = "/observations/images/cam_high"


def extract_cam_high_frames(hdf5_path: Path, output_dir: Path, overwrite: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(hdf5_path, "r") as handle:
        frames = handle[CAM_HIGH_DATASET]
        for frame_index, frame in enumerate(frames):
            target = output_dir / f"frame_{frame_index:06d}.png"
            if target.exists() and not overwrite:
                continue
            Image.fromarray(frame).save(target)
    return len(list(output_dir.glob("frame_*.png")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_extraction.py -q`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/extraction.py tests/test_extraction.py
git commit -m "feat: add cam_high extraction support"
```

### Task 5: Expose API Routes And Dataset File Serving

**Files:**
- Create: `app/main.py`
- Modify: `app/config.py`
- Modify: `app/episodes.py`
- Modify: `app/annotations.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
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
    save_response = client.put("/api/annotations/episode_49", json={"frameIndices": [241, 183]})

    assert episodes_response.status_code == 200
    assert episodes_response.get_json()[0]["episodeId"] == "episode_49"
    assert episodes_response.get_json()[0]["videos"]["cam_high"] == "/dataset/episode_49_cam_high.mp4"
    assert annotations_response.get_json() == {}
    assert save_response.get_json()["episode_49"] == [183, 241]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py -q`

Expected: FAIL with missing `create_app`

- [ ] **Step 3: Write minimal implementation**

```python
# app/config.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class DatasetPaths:
    dataset_dir: Path
    annotations_file: Path
    extracted_frames_dir: Path


def resolve_dataset_dir(repo_root: Path) -> Path:
    configured = os.environ.get("DATASET_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root.resolve().parent


def dataset_paths(repo_root: Path | None = None, dataset_dir: Path | None = None) -> DatasetPaths:
    if dataset_dir is not None:
        resolved_dataset_dir = Path(dataset_dir).expanduser().resolve()
    else:
        if repo_root is None:
            raise ValueError("repo_root is required when dataset_dir is not supplied")
        resolved_dataset_dir = resolve_dataset_dir(repo_root)
    return DatasetPaths(
        dataset_dir=resolved_dataset_dir,
        annotations_file=resolved_dataset_dir / "annotations.json",
        extracted_frames_dir=resolved_dataset_dir / "extracted_frames",
    )
```

```python
# app/main.py
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
        records = discover_episodes(paths.dataset_dir, probe_video=app.config["PROBE_VIDEO"])
        payload = []
        for record in records:
            item = record.to_dict()
            item["videos"] = {
                camera: f"/dataset/{Path(path).name}" for camera, path in record.video_paths.items()
            }
            payload.append(item)
        return jsonify(payload)

    @app.get("/api/annotations")
    def api_annotations():
        return jsonify(load_annotations(paths.annotations_file))

    @app.put("/api/annotations/<episode_id>")
    def api_save_annotations(episode_id: str):
        body = request.get_json(force=True)
        saved = save_episode_annotations(paths.annotations_file, episode_id, body["frameIndices"])
        return jsonify(saved)

    @app.post("/api/episodes/<episode_id>/extract-cam-high")
    def api_extract_cam_high(episode_id: str):
        records = {
            record.episode_id: record
            for record in discover_episodes(paths.dataset_dir, probe_video=app.config["PROBE_VIDEO"])
        }
        record = records[episode_id]
        output_dir = paths.extracted_frames_dir / episode_id / "cam_high"
        exported = extract_cam_high_frames(record.hdf5_path, output_dir, overwrite=False)
        return jsonify({"episodeId": episode_id, "exportedFrames": exported, "outputDir": str(output_dir)})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -q`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/config.py app/main.py tests/test_api.py
git commit -m "feat: add api routes for episodes and annotations"
```

### Task 6: Add Pure Frontend Frame Controller Logic

**Files:**
- Create: `app/static/player-controller.js`
- Test: `frontend-tests/player-controller.test.mjs`

- [ ] **Step 1: Write the failing test**

```javascript
// frontend-tests/player-controller.test.mjs
import test from "node:test";
import assert from "node:assert/strict";

import {
  clampFrameIndex,
  frameToSeconds,
  stepFrame,
  toggleFrameIndex,
} from "../app/static/player-controller.js";

test("toggleFrameIndex sorts unique frame indices", () => {
  assert.deepEqual(toggleFrameIndex([317, 183], 241), [183, 241, 317]);
  assert.deepEqual(toggleFrameIndex([183, 241, 317], 241), [183, 317]);
});

test("stepFrame respects lower and upper bounds", () => {
  assert.equal(stepFrame(0, -1, 422), 0);
  assert.equal(stepFrame(420, 1, 422), 421);
});

test("frameToSeconds converts the current frame index to seek time", () => {
  assert.equal(frameToSeconds(15, 15), 1);
  assert.equal(clampFrameIndex(999, 422), 421);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend-tests/player-controller.test.mjs`

Expected: FAIL with `Cannot find module '../app/static/player-controller.js'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// app/static/player-controller.js
export function clampFrameIndex(frameIndex, frameCount) {
  if (frameCount <= 0) {
    return 0;
  }
  return Math.min(Math.max(frameIndex, 0), frameCount - 1);
}

export function stepFrame(currentFrameIndex, delta, frameCount) {
  return clampFrameIndex(currentFrameIndex + delta, frameCount);
}

export function frameToSeconds(frameIndex, fps) {
  return frameIndex / fps;
}

export function toggleFrameIndex(existingFrameIndices, frameIndex) {
  const next = new Set(existingFrameIndices);
  if (next.has(frameIndex)) {
    next.delete(frameIndex);
  } else {
    next.add(frameIndex);
  }
  return [...next].sort((left, right) => left - right);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test frontend-tests/player-controller.test.mjs`

Expected: PASS with `3 tests`

- [ ] **Step 5: Commit**

```bash
git add app/static/player-controller.js frontend-tests/player-controller.test.mjs
git commit -m "feat: add frontend frame controller helpers"
```

### Task 7: Build The Static Annotation Shell

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/app.css`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_api.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py -q`

Expected: FAIL because `index.html` does not exist or does not contain the required controls

- [ ] **Step 3: Write minimal implementation**

```html
<!-- app/static/index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Episode Frame Annotator</title>
    <link rel="stylesheet" href="/static/app.css" />
  </head>
  <body>
    <div class="app-shell">
      <aside class="sidebar">
        <h1>Episodes</h1>
        <div class="sidebar-actions">
          <button id="previous-episode" type="button">Previous</button>
          <button id="next-episode" type="button">Next</button>
        </div>
        <ul id="episode-list"></ul>
      </aside>

      <main class="workspace">
        <section id="viewer-grid" class="viewer-grid">
          <article class="viewer-card" data-camera="cam_high"></article>
          <article class="viewer-card" data-camera="cam_head"></article>
          <article class="viewer-card" data-camera="cam_left_wrist"></article>
          <article class="viewer-card" data-camera="cam_right_wrist"></article>
        </section>

        <section class="controls">
          <button id="play-pause" type="button">Play</button>
          <button data-rate="1" type="button">1x</button>
          <button data-rate="0.5" type="button">0.5x</button>
          <button data-rate="0.25" type="button">0.25x</button>
          <button data-rate="0.1" type="button">0.1x</button>
          <button id="step-backward" type="button">Prev Frame</button>
          <button id="step-forward" type="button">Next Frame</button>
          <input id="jump-to-frame" type="number" min="0" />
          <button id="mark-frame" type="button">Mark / Unmark</button>
          <button id="extract-cam-high" type="button">Extract cam_high</button>
        </section>

        <section class="current-state">
          <p>Current frame: <strong id="current-frame-label">0</strong></p>
          <p>Saved frames: <span id="saved-frame-list">[]</span></p>
          <p id="status-message"></p>
        </section>
      </main>
    </div>

    <script type="module" src="/static/app.js"></script>
  </body>
</html>
```

```css
/* app/static/app.css */
:root {
  --bg: #f5f0e8;
  --panel: #fffaf2;
  --ink: #1b1a17;
  --accent: #b4512f;
  --border: #d5c6b2;
}

body {
  margin: 0;
  font-family: "Avenir Next", "Helvetica Neue", sans-serif;
  background: radial-gradient(circle at top, #fff7ea, var(--bg));
  color: var(--ink);
}

.app-shell {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}

.sidebar,
.workspace {
  padding: 20px;
}

.sidebar {
  border-right: 1px solid var(--border);
  background: rgba(255, 250, 242, 0.92);
}

.viewer-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.viewer-card {
  min-height: 260px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 12px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

#episode-list {
  list-style: none;
  padding: 0;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -q`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add app/static/index.html app/static/app.css tests/test_api.py
git commit -m "feat: add annotation app shell"
```

### Task 8: Wire The Frontend To The Backend And Sync The Videos

**Files:**
- Create: `app/static/api.js`
- Create: `app/static/app.js`
- Modify: `app/static/app.css`
- Modify: `app/static/index.html`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_api.py
def test_root_page_loads_frontend_modules(tmp_path):
    app = create_app(dataset_dir=tmp_path)
    client = app.test_client()

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "fetchEpisodes" in response.get_data(as_text=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py -q`

Expected: FAIL because `/static/app.js` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```javascript
// app/static/api.js
export async function fetchEpisodes() {
  const response = await fetch("/api/episodes");
  return response.json();
}

export async function fetchAnnotations() {
  const response = await fetch("/api/annotations");
  return response.json();
}

export async function saveEpisodeAnnotations(episodeId, frameIndices) {
  const response = await fetch(`/api/annotations/${episodeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frameIndices }),
  });
  return response.json();
}

export async function extractCamHigh(episodeId) {
  const response = await fetch(`/api/episodes/${episodeId}/extract-cam-high`, {
    method: "POST",
  });
  return response.json();
}
```

```javascript
// app/static/app.js
import { fetchAnnotations, fetchEpisodes, saveEpisodeAnnotations, extractCamHigh } from "./api.js";
import { frameToSeconds, stepFrame, toggleFrameIndex } from "./player-controller.js";

const cameras = ["cam_high", "cam_head", "cam_left_wrist", "cam_right_wrist"];

const state = {
  episodes: [],
  annotations: {},
  currentEpisodeIndex: 0,
  currentFrameIndex: 0,
  playbackRate: 1,
  isPlaying: false,
  animationHandle: null,
};

function currentEpisode() {
  return state.episodes[state.currentEpisodeIndex];
}

function currentSavedFrames() {
  return state.annotations[currentEpisode().episodeId] ?? [];
}

function invalidReason(episode) {
  const missingParts = [...episode.missingCameras];
  if (!episode.hdf5Path) {
    missingParts.unshift("hdf5");
  }
  return missingParts.join(", ");
}

function renderEpisodeList() {
  const list = document.getElementById("episode-list");
  list.innerHTML = "";
  state.episodes.forEach((episode, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const labelCount = (state.annotations[episode.episodeId] ?? []).length;
    const status = episode.valid ? `${labelCount} labels` : `invalid: ${invalidReason(episode)}`;
    button.textContent = `${episode.episodeId} (${status})`;
    button.disabled = !episode.valid;
    button.addEventListener("click", () => {
      state.currentEpisodeIndex = index;
      state.currentFrameIndex = 0;
      loadEpisodeVideos();
    });
    item.appendChild(button);
    list.appendChild(item);
  });
}

function renderCurrentState() {
  document.getElementById("current-frame-label").textContent = String(state.currentFrameIndex);
  document.getElementById("saved-frame-list").textContent = JSON.stringify(currentSavedFrames());
}

function loadEpisodeVideos() {
  const episode = currentEpisode();
  if (!episode || !episode.valid) {
    document.getElementById("status-message").textContent = "Select a valid episode to annotate.";
    return;
  }
  document.querySelectorAll(".viewer-card").forEach((card) => {
    const camera = card.dataset.camera;
    const marked = currentSavedFrames().includes(state.currentFrameIndex) ? "marked" : "unmarked";
    card.innerHTML = `
      <header class="viewer-card__header">
        <strong>${camera}</strong>
        <span>frame ${state.currentFrameIndex}</span>
        <span>${marked}</span>
      </header>
      <video muted playsinline preload="metadata" src="${episode.videos[camera]}"></video>
    `;
  });
  syncVideosToCurrentFrame();
  renderCurrentState();
}

function moveToAdjacentValidEpisode(direction) {
  let nextIndex = state.currentEpisodeIndex + direction;
  while (nextIndex >= 0 && nextIndex < state.episodes.length) {
    if (state.episodes[nextIndex].valid) {
      state.currentEpisodeIndex = nextIndex;
      state.currentFrameIndex = 0;
      loadEpisodeVideos();
      return;
    }
    nextIndex += direction;
  }
}

function syncVideosToCurrentFrame() {
  const episode = currentEpisode();
  const currentSeconds = frameToSeconds(state.currentFrameIndex, episode.fps);
  document.querySelectorAll(".viewer-card video").forEach((video) => {
    video.pause();
    video.currentTime = currentSeconds;
  });
}

function tickPlayback() {
  if (!state.isPlaying) {
    return;
  }
  const episode = currentEpisode();
  state.currentFrameIndex = stepFrame(state.currentFrameIndex, 1, episode.frameCount);
  syncVideosToCurrentFrame();
  renderCurrentState();
  if (state.currentFrameIndex >= episode.frameCount - 1) {
    state.isPlaying = false;
    return;
  }
  state.animationHandle = window.setTimeout(tickPlayback, 1000 / (episode.fps * state.playbackRate));
}

function bindControls() {
  document.getElementById("play-pause").addEventListener("click", () => {
    state.isPlaying = !state.isPlaying;
    if (state.isPlaying) {
      tickPlayback();
    } else {
      window.clearTimeout(state.animationHandle);
      syncVideosToCurrentFrame();
    }
  });

  document.getElementById("step-backward").addEventListener("click", () => {
    state.currentFrameIndex = stepFrame(state.currentFrameIndex, -1, currentEpisode().frameCount);
    loadEpisodeVideos();
  });

  document.getElementById("step-forward").addEventListener("click", () => {
    state.currentFrameIndex = stepFrame(state.currentFrameIndex, 1, currentEpisode().frameCount);
    loadEpisodeVideos();
  });

  document.getElementById("jump-to-frame").addEventListener("change", (event) => {
    state.currentFrameIndex = stepFrame(0, Number(event.target.value), currentEpisode().frameCount);
    loadEpisodeVideos();
  });

  document.getElementById("mark-frame").addEventListener("click", async () => {
    const next = toggleFrameIndex(currentSavedFrames(), state.currentFrameIndex);
    state.annotations = await saveEpisodeAnnotations(currentEpisode().episodeId, next);
    loadEpisodeVideos();
  });

  document.getElementById("extract-cam-high").addEventListener("click", async () => {
    const result = await extractCamHigh(currentEpisode().episodeId);
    document.getElementById("status-message").textContent =
      `Exported ${result.exportedFrames} frame(s) to ${result.outputDir}`;
  });

  document.querySelectorAll("[data-rate]").forEach((button) => {
    button.addEventListener("click", () => {
      state.playbackRate = Number(button.dataset.rate);
      syncVideosToCurrentFrame();
    });
  });

  document.getElementById("previous-episode").addEventListener("click", () => {
    moveToAdjacentValidEpisode(-1);
  });

  document.getElementById("next-episode").addEventListener("click", () => {
    moveToAdjacentValidEpisode(1);
  });
}

async function start() {
  state.episodes = await fetchEpisodes();
  state.annotations = await fetchAnnotations();
  bindControls();
  renderEpisodeList();
  if (state.episodes.some((episode) => episode.valid)) {
    state.currentEpisodeIndex = state.episodes.findIndex((episode) => episode.valid);
    loadEpisodeVideos();
  }
}

void start();
```

```css
/* append to app/static/app.css */
.viewer-card__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.viewer-card video {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  background: #000;
}

.sidebar button,
.controls button {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: white;
  padding: 8px 12px;
  cursor: pointer;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -q`

Expected: PASS with `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/static/api.js app/static/app.js app/static/app.css app/static/index.html tests/test_api.py
git commit -m "feat: wire frontend annotation workflow"
```

### Task 9: Run Full Verification And Document Local Usage

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

```bash
python - <<'PY'
from pathlib import Path

readme = Path("README.md").read_text()

assert "DATASET_DIR" in readme
assert "python -m app.main" in readme
assert "node --test frontend-tests/player-controller.test.mjs" in readme
PY
```

- [ ] **Step 2: Run test to verify it fails**

Run the same command from Step 1.

Expected: FAIL because the placeholder README does not document setup, run, or verification yet

- [ ] **Step 3: Write minimal implementation**

````markdown
# README.md
# Subgoal-label-for-Robolatent

Local browser app for annotating zero-based subgoal-complete frame indices across four synchronized camera views.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

The app defaults `DATASET_DIR` to the parent directory of the repo checkout. Override it if your episode files live elsewhere.

```bash
export DATASET_DIR=/absolute/path/to/episode/files
python -m app.main
```

Open `http://127.0.0.1:5000` in a browser.

## Verify

```bash
python -m pytest -q
node --test frontend-tests/player-controller.test.mjs
```
````

- [ ] **Step 4: Run test to verify it passes**

Run:

- `python -m pytest -q`
- `node --test frontend-tests/player-controller.test.mjs`
- Re-run the README check from Step 1

Expected: backend tests PASS, frontend controller tests PASS

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add local setup and verification instructions"
```

## Self-Review Checklist

- Spec coverage:
  - synced 4-camera viewer: Tasks 7-8
  - slow playback, frame step, jump-to-frame: Tasks 6 and 8
  - shared `annotations.json`: Tasks 3 and 5
  - one-episode-at-a-time navigation with sidebar: Tasks 7-8
  - invalid or incomplete episodes shown clearly: Tasks 2, 7, and 8
  - `cam_high` extraction: Tasks 4 and 5
- Placeholder scan:
  - No placeholder markers or undefined file references remain
- Type consistency:
  - API uses `episodeId`, `frameCount`, `frameIndices`, and zero-based `currentFrameIndex` consistently
