import {
  extractCamHigh,
  fetchAnnotations,
  fetchEpisodes,
  saveEpisodeAnnotations,
} from "./api.js";
import {
  frameToSeconds,
  stepFrame,
  toggleFrameIndex,
} from "./player-controller.js";

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

function syncVideosToCurrentFrame() {
  const episode = currentEpisode();
  if (!episode) {
    return;
  }

  const currentSeconds = frameToSeconds(state.currentFrameIndex, episode.fps);
  document.querySelectorAll(".viewer-card video").forEach((video) => {
    video.pause();
    video.currentTime = currentSeconds;
  });
}

function loadEpisodeVideos() {
  const episode = currentEpisode();
  if (!episode || !episode.valid) {
    document.getElementById("status-message").textContent =
      "Select a valid episode to annotate.";
    return;
  }

  document.querySelectorAll(".viewer-card").forEach((card) => {
    const camera = card.dataset.camera;
    const marked = currentSavedFrames().includes(state.currentFrameIndex)
      ? "marked"
      : "unmarked";
    card.innerHTML = `
      <header class="viewer-card__header">
        <strong>${camera}</strong>
        <span>frame ${state.currentFrameIndex}</span>
        <span>${marked}</span>
      </header>
      <video muted playsinline preload="metadata" src="${episode.videos[camera]}"></video>
    `;
  });

  document.getElementById("status-message").textContent = "";
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
  syncVideosToCurrentFrame();
  renderCurrentState();
  if (state.currentFrameIndex >= episode.frameCount - 1) {
    state.isPlaying = false;
    return;
  }
  state.animationHandle = window.setTimeout(
    tickPlayback,
    1000 / (episode.fps * state.playbackRate),
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
      syncVideosToCurrentFrame();
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
    loadEpisodeVideos();
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
    loadEpisodeVideos();
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
    loadEpisodeVideos();
  });

  document.getElementById("mark-frame").addEventListener("click", async () => {
    const episode = currentEpisode();
    if (!episode || !episode.valid) {
      return;
    }

    const next = toggleFrameIndex(currentSavedFrames(), state.currentFrameIndex);
    state.annotations = await saveEpisodeAnnotations(episode.episodeId, next);
    renderEpisodeList();
    loadEpisodeVideos();
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
    return;
  }

  renderCurrentState();
  document.getElementById("status-message").textContent =
    "Select a valid episode to annotate.";
}

void start();
