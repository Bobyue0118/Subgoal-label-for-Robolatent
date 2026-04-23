export function playPauseLabel(isPlaying) {
  return isPlaying ? "Pause" : "Play";
}

export function playbackRateButtonClassName(currentRate, buttonRate) {
  return currentRate === buttonRate ? "is-selected" : "";
}

export function episodeButtonClassName(selectedEpisodeIndex, index) {
  return selectedEpisodeIndex === index ? "is-selected" : "";
}
