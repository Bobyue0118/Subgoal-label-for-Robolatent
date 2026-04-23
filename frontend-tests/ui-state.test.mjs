import test from "node:test";
import assert from "node:assert/strict";

import {
  episodeButtonClassName,
  playPauseLabel,
  playbackRateButtonClassName,
} from "../app/static/ui-state.js";

test("playPauseLabel toggles between play and pause", () => {
  assert.equal(playPauseLabel(false), "Play");
  assert.equal(playPauseLabel(true), "Pause");
});

test("playbackRateButtonClassName marks the selected playback rate", () => {
  assert.equal(playbackRateButtonClassName(1, 1), "is-selected");
  assert.equal(playbackRateButtonClassName(1, 0.5), "");
});

test("episodeButtonClassName marks the selected episode", () => {
  assert.equal(episodeButtonClassName(2, 2), "is-selected");
  assert.equal(episodeButtonClassName(1, 2), "");
});
