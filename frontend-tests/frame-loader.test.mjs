import test from "node:test";
import assert from "node:assert/strict";

import { loadImageSource } from "../app/static/frame-loader.js";

class FakeImage {
  constructor() {
    this.listeners = new Map();
    this.complete = false;
    this.naturalWidth = 0;
    this._src = "";
  }

  addEventListener(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type).add(callback);
  }

  removeEventListener(type, callback) {
    this.listeners.get(type)?.delete(callback);
  }

  dispatch(type) {
    for (const callback of this.listeners.get(type) ?? []) {
      callback();
    }
  }

  set src(value) {
    this._src = value;
  }

  get src() {
    return this._src;
  }
}

test("loadImageSource resolves only after the image loads", async () => {
  const image = new FakeImage();
  let settled = false;
  const pending = loadImageSource(image, "/frame/1.png").then(() => {
    settled = true;
  });

  await Promise.resolve();
  assert.equal(image.src, "/frame/1.png");
  assert.equal(settled, false);

  image.complete = true;
  image.naturalWidth = 2;
  image.dispatch("load");
  await pending;

  assert.equal(settled, true);
});

test("loadImageSource rejects when the image fails to load", async () => {
  const image = new FakeImage();
  const pending = loadImageSource(image, "/frame/404.png");

  image.dispatch("error");

  await assert.rejects(
    pending,
    /Failed to load frame: \/frame\/404\.png/,
  );
});
