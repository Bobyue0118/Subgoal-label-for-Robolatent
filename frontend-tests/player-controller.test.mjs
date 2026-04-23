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
