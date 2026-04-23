export function loadImageSource(image, src) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      image.removeEventListener("load", onLoad);
      image.removeEventListener("error", onError);
    };

    const onLoad = () => {
      cleanup();
      resolve();
    };

    const onError = () => {
      cleanup();
      reject(new Error(`Failed to load frame: ${src}`));
    };

    image.addEventListener("load", onLoad);
    image.addEventListener("error", onError);
    image.src = src;

    if (image.complete && image.naturalWidth > 0) {
      cleanup();
      resolve();
    }
  });
}

export async function loadFrameImages(imagesByCamera, sourcesByCamera) {
  await Promise.all(
    Object.entries(imagesByCamera).map(([camera, image]) =>
      loadImageSource(image, sourcesByCamera[camera]),
    ),
  );
}
