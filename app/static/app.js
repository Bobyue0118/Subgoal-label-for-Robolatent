import {
  fetchAnnotations,
  fetchEpisodes,
  saveEpisodeAnnotations,
} from "./api.js";
import { loadFrameImages } from "./frame-loader.js";
import { stepFrame, toggleFrameIndex } from "./player-controller.js";
import {
  episodeButtonClassName,
  playPauseLabel,
  playbackRateButtonClassName,
} from "./ui-state.js";

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
    button.className = episodeButtonClassName(state.currentEpisodeIndex, index);
    button.disabled = !episode.valid;
    button.addEventListener("click", () => {
      state.currentEpisodeIndex = index;
      state.currentFrameIndex = 0;
      void loadEpisodeFrames();
      renderEpisodeList();
    });
    item.appendChild(button);
    list.appendChild(item);
  });
}

function renderControlState() {
  const playPauseButton = document.getElementById("play-pause");
  if (playPauseButton) {
    playPauseButton.textContent = playPauseLabel(state.isPlaying);
  }

  document.querySelectorAll("[data-rate]").forEach((button) => {
    const rate = Number(button.dataset.rate);
    button.className = playbackRateButtonClassName(state.playbackRate, rate);
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

async function syncFramesToCurrentFrame() {
  const episode = currentEpisode();
  if (!episode) {
    return false;
  }

  const imagesByCamera = {};
  const sourcesByCamera = {};

  document.querySelectorAll(".viewer-card").forEach((card) => {
    const camera = card.dataset.camera;
    const image = card.querySelector("img");

    if (!image) {
      return;
    }

    imagesByCamera[camera] = image;
    sourcesByCamera[camera] = frameSrc(episode, camera);
  });

  try {
    await loadFrameImages(imagesByCamera, sourcesByCamera);
  } catch (error) {
    document.getElementById("status-message").textContent =
      error instanceof Error ? error.message : "Failed to load frame.";
    return false;
  }

  document.querySelectorAll(".viewer-card").forEach((card) => {
    const frameLabel = card.querySelector('[data-role="frame-label"]');
    const markedLabel = card.querySelector('[data-role="marked-label"]');

    if (!frameLabel || !markedLabel) {
      return;
    }

    frameLabel.textContent = `frame ${state.currentFrameIndex}`;
    markedLabel.textContent = currentSavedFrames().includes(state.currentFrameIndex)
      ? "marked"
      : "unmarked";
  });

  renderCurrentState();
  return true;
}

async function loadEpisodeFrames() {
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
  await syncFramesToCurrentFrame();
  renderControlState();
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

  const nextFrameIndex = stepFrame(state.currentFrameIndex, 1, episode.frameCount);
  if (nextFrameIndex === state.currentFrameIndex) {
    state.isPlaying = false;
    renderControlState();
    return;
  }

  state.currentFrameIndex = nextFrameIndex;
  void syncFramesToCurrentFrame().then((didSync) => {
    if (!didSync || !state.isPlaying) {
      return;
    }

    state.animationHandle = window.setTimeout(
      tickPlayback,
      1000 / ((episode.fps || DEFAULT_FPS) * state.playbackRate),
    );
  });
}

function bindControls() {
  document.getElementById("play-pause").addEventListener("click", () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    state.isPlaying = !state.isPlaying;
    renderControlState();
    if (state.isPlaying) {
      tickPlayback();
    } else {
      window.clearTimeout(state.animationHandle);
      void syncFramesToCurrentFrame();
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
    void loadEpisodeFrames();
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
    void loadEpisodeFrames();
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
    void loadEpisodeFrames();
  });

  document.getElementById("mark-frame").addEventListener("click", async () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    const next = toggleFrameIndex(currentSavedFrames(), state.currentFrameIndex);
    state.annotations = await saveEpisodeAnnotations(episode.episodeId, next);
    renderEpisodeList();
    await loadEpisodeFrames();
  });

  document.querySelectorAll("[data-rate]").forEach((button) => {
    button.addEventListener("click", () => {
      state.playbackRate = Number(button.dataset.rate);
      renderControlState();
      void syncFramesToCurrentFrame();
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
  renderControlState();
  if (state.episodes.some((episode) => episode.valid)) {
    state.currentEpisodeIndex = state.episodes.findIndex((episode) => episode.valid);
    void loadEpisodeFrames();
    return;
  }

  renderCurrentState();
  document.getElementById("status-message").textContent =
    "Select a valid episode to annotate.";
}

void start();
