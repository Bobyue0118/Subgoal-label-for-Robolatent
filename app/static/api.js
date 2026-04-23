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
