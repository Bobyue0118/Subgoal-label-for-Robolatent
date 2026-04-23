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
