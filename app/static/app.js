import {
  extractCamHigh,
  fetchAnnotations,
  fetchEpisodes,
  saveEpisodeAnnotations,
} from "./api.js";
import { stepFrame, toggleFrameIndex } from "./player-controller.js";

const state = {
  episodes: [],
  annotations: {},
  currentEpisodeIndex: 0,
  currentFrameIndex: 0,
  playbackRate: 1,
  isPlaying: false,
  animationHandle: null,
};
const DEFAULT_FPS = 15;

function currentEpisode() {
  return state.episodes[state.currentEpisodeIndex];
}

function currentSavedFrames() {
  const episode = currentEpisode();
  if (!episode) {
    return [];
  }

  return state.annotations[episode.episodeId] ?? [];
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
    const status = episode.valid
      ? `${labelCount} labels`
      : `invalid: ${invalidReason(episode)}`;
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
  document.getElementById("current-frame-label").textContent = String(
    state.currentFrameIndex,
  );
  document.getElementById("jump-to-frame").value = String(state.currentFrameIndex);
  document.getElementById("saved-frame-list").textContent = JSON.stringify(
    currentSavedFrames(),
  );
}

function frameSrc(episode, camera) {
  return `${episode.frameBasePath}/${camera}/${state.currentFrameIndex}.png`;
}

function syncFramesToCurrentFrame() {
  const episode = currentEpisode();
  if (!episode) {
    return;
  }

  document.querySelectorAll(".viewer-card").forEach((card) => {
    const camera = card.dataset.camera;
    const frameLabel = card.querySelector('[data-role="frame-label"]');
    const markedLabel = card.querySelector('[data-role="marked-label"]');
    const image = card.querySelector("img");

    if (!frameLabel || !markedLabel || !image) {
      return;
    }

    frameLabel.textContent = `frame ${state.currentFrameIndex}`;
    markedLabel.textContent = currentSavedFrames().includes(state.currentFrameIndex)
      ? "marked"
      : "unmarked";
    image.src = frameSrc(episode, camera);
    image.alt = `${camera} frame ${state.currentFrameIndex}`;
  });
}

function loadEpisodeFrames() {
  const episode = currentEpisode();
  if (!episode || !episode.valid) {
    document.getElementById("status-message").textContent =
      "Select a valid episode to annotate.";
    return;
  }

  document.querySelectorAll(".viewer-card").forEach((card) => {
    const camera = card.dataset.camera;
    card.innerHTML = `
      <header class="viewer-card__header">
        <strong>${camera}</strong>
        <span data-role="frame-label">frame ${state.currentFrameIndex}</span>
        <span data-role="marked-label">unmarked</span>
      </header>
      <img src="${frameSrc(episode, camera)}" alt="${camera} frame ${state.currentFrameIndex}" />
    `;
  });

  document.getElementById("status-message").textContent = "";
  syncFramesToCurrentFrame();
  renderCurrentState();
}

function moveToAdjacentValidEpisode(direction) {
  let nextIndex = state.currentEpisodeIndex + direction;
  while (nextIndex >= 0 && nextIndex < state.episodes.length) {
    if (state.episodes[nextIndex].valid) {
      state.currentEpisodeIndex = nextIndex;
      state.currentFrameIndex = 0;
      loadEpisodeFrames();
      return;
    }
    nextIndex += direction;
  }
}

function tickPlayback() {
  if (!state.isPlaying) {
    return;
  }

  const episode = currentEpisode();
  if (!episode) {
    state.isPlaying = false;
    return;
  }

  state.currentFrameIndex = stepFrame(
    state.currentFrameIndex,
    1,
    episode.frameCount,
  );
  syncFramesToCurrentFrame();
  renderCurrentState();
  if (state.currentFrameIndex >= episode.frameCount - 1) {
    state.isPlaying = false;
    return;
  }
  state.animationHandle = window.setTimeout(
    tickPlayback,
    1000 / ((episode.fps || DEFAULT_FPS) * state.playbackRate),
  );
}

function bindControls() {
  document.getElementById("play-pause").addEventListener("click", () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    state.isPlaying = !state.isPlaying;
    if (state.isPlaying) {
      tickPlayback();
    } else {
      window.clearTimeout(state.animationHandle);
      syncFramesToCurrentFrame();
    }
  });

  document.getElementById("step-backward").addEventListener("click", () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    state.currentFrameIndex = stepFrame(
      state.currentFrameIndex,
      -1,
      episode.frameCount,
    );
    loadEpisodeFrames();
  });

  document.getElementById("step-forward").addEventListener("click", () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    state.currentFrameIndex = stepFrame(
      state.currentFrameIndex,
      1,
      episode.frameCount,
    );
    loadEpisodeFrames();
  });

  document.getElementById("jump-to-frame").addEventListener("change", (event) => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    state.currentFrameIndex = stepFrame(
      0,
      Number(event.target.value),
      episode.frameCount,
    );
    loadEpisodeFrames();
  });

  document.getElementById("mark-frame").addEventListener("click", async () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    const next = toggleFrameIndex(currentSavedFrames(), state.currentFrameIndex);
    state.annotations = await saveEpisodeAnnotations(episode.episodeId, next);
    renderEpisodeList();
    loadEpisodeFrames();
  });

  document
    .getElementById("extract-cam-high")
    .addEventListener("click", async () => {
      const episode = currentEpisode();
      if (!episode || !episode.valid) {
        return;
      }

      const result = await extractCamHigh(episode.episodeId);
      document.getElementById("status-message").textContent =
        `Exported ${result.exportedFrames} frame(s) to ${result.outputDir}`;
    });

  document.querySelectorAll("[data-rate]").forEach((button) => {
    button.addEventListener("click", () => {
      state.playbackRate = Number(button.dataset.rate);
      syncFramesToCurrentFrame();
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
    loadEpisodeFrames();
    return;
  }

  renderCurrentState();
  document.getElementById("status-message").textContent =
    "Select a valid episode to annotate.";
}

void start();
