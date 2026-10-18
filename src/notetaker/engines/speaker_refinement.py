"""Global, duration-filtered speaker clustering. No fixed speaker count.

Short or overlapping observations cannot create identities. Ambiguous speech
remains unattributed; proximity alone is never proof of an identity.
"""
import time
import numpy as np


def unit_vectors(vectors):
    vectors = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or (norms < 1e-8).any():
        raise ValueError("INVALID_SPEAKER_EMBEDDING")
    return vectors / norms[:, None], norms


def cluster_vectors(vectors, threshold=0.5, linkage="average"):
    if not len(vectors):
        return np.array([], dtype=int)
    vectors, _ = unit_vectors(vectors)
    n = len(vectors)
    if not n:
        return np.array([], dtype=int)
    if linkage not in {"average", "complete"} or not 0 < threshold < 2:
        raise ValueError("INVALID_CLUSTER_PARAMETERS")
    distances = np.clip(1 - vectors @ vectors.T, 0, 2)
    np.fill_diagonal(distances, np.inf)
    groups = {i: [i] for i in range(n)}
    sizes = np.ones(n)
    while len(groups) > 1:
        i, j = np.unravel_index(np.argmin(distances), distances.shape)
        if distances[i, j] > threshold:
            break
        if linkage == "average":
            merged = (distances[i] * sizes[i] + distances[j] * sizes[j]) / (sizes[i] + sizes[j])
        else:
            merged = np.maximum(distances[i], distances[j])
        distances[i] = merged
        distances[:, i] = merged
        distances[j] = distances[:, j] = np.inf
        distances[i, i] = np.inf
        groups[i] += groups.pop(j)
        sizes[i] += sizes[j]
    labels = np.empty(n, dtype=int)
    for label, members in enumerate(sorted(groups.values(), key=min)):
        labels[members] = label
    return labels


def clean_intervals(start, end, overlaps):
    spans = [(start, end)]
    for o in overlaps:
        spans = [(x, y) for a, b in spans for x, y in ((a, min(b, o["start"])), (max(a, o["end"]), b)) if y > x]
    return spans


def extract_observations(samples, turns, embedding_model, overlaps=(), progress=lambda message: None):
    import sherpa_onnx as s
    extractor = s.SpeakerEmbeddingExtractor(s.SpeakerEmbeddingExtractorConfig(model=str(embedding_model), num_threads=4, provider="cpu"))
    observations, vectors = [], []
    for turn in sorted(turns, key=lambda t: (t["start"], t["end"])):
        start, end = max(0, turn["start"]), min(len(samples) / 16000, turn["end"])
        for offset in np.arange(start, end, 4.0):
            stop = min(end, offset + 4)
            clean = clean_intervals(float(offset), stop, overlaps)
            clean = [(a, b) for a, b in clean if b - a >= 0.25]
            duration = sum(b - a for a, b in clean)
            observation = {"start": float(offset), "end": stop, "clean_seconds": duration, "vector_index": None}
            if duration >= 0.6:
                data = np.concatenate([samples[round(a * 16000):round(b * 16000)] for a, b in clean])
                stream = extractor.create_stream()
                stream.accept_waveform(16000, data)
                stream.input_finished()
                if extractor.is_ready(stream):
                    vector = np.asarray(extractor.compute(stream))
                    if np.isfinite(vector).all() and np.linalg.norm(vector) > 1e-8:
                        observation["vector_index"] = len(vectors)
                        vectors.append(vector)
            observations.append(observation)
            if len(observations) % 100 == 0:
                progress(f"Embeddings propres : {len(observations)} fenêtres examinées")
    return observations, np.asarray(vectors, dtype=np.float32).reshape(-1, extractor.dim)


def assign_observations(observations, vectors, threshold=0.5, linkage="average", minimum_anchor_seconds=2.0):
    started = time.perf_counter()
    vectors, norms = unit_vectors(vectors) if len(vectors) else (vectors, np.array([]))
    anchors = [i for i, o in enumerate(observations) if o["clean_seconds"] >= minimum_anchor_seconds and o["vector_index"] is not None]
    if not anchors:
        return {"turns": [{"start": o["start"], "end": o["end"], "speaker": None, "uncertain": True} for o in observations],
                "diagnostics": {"speakers": 0, "reason": "NO_RELIABLE_ANCHOR", "observations": len(observations)}}
    labels = cluster_vectors([vectors[observations[i]["vector_index"]] for i in anchors], threshold, linkage)
    centroids, radii = [], []
    for label in range(int(labels.max()) + 1):
        ids = [observations[anchors[j]]["vector_index"] for j in np.flatnonzero(labels == label)]
        vector = vectors[ids].mean(axis=0)
        centroid = vector / max(np.linalg.norm(vector), 1e-8)
        centroids.append(centroid)
        radii.append(min(0.35, max(0.08, float(np.quantile(1 - vectors[ids] @ centroid, 0.95)) + 0.05)))
    centroids = np.asarray(centroids)
    separation = np.clip(1 - centroids @ centroids.T, 0, 2)
    np.fill_diagonal(separation, np.inf)
    # Margins scale with the observed prototype separation, rather than using
    # a cosine margin tuned for a different embedding family.
    margins = np.clip(separation.min(axis=1) * 0.1, 0.02, 0.08)
    anchor_labels = dict(zip(anchors, labels.tolist()))
    turns, durations, uncertain, short = [], {}, 0, 0
    for i, observation in enumerate(observations):
        vid = observation["vector_index"]
        scores = centroids @ vectors[vid] if vid is not None else np.array([])
        rank = np.argsort(scores)[::-1]
        best = int(rank[0]) if len(rank) else None
        margin = float(scores[rank[0]] - scores[rank[1]]) if len(rank) > 1 else (float(scores[0]) if len(rank) else 0)
        is_short = i not in anchor_labels
        short += is_short
        label = anchor_labels.get(i)
        if is_short and best is not None and 1 - scores[best] <= min(0.4, radii[best] + 0.12) and margin >= margins[best]:
            label = best
        ambiguous = label is None or label != best or margin < margins[label] or (len(scores) > 0 and 1 - scores[label] > radii[label])
        uncertain += int(ambiguous)
        speaker = f"speaker_{label}" if label is not None else None
        durations[speaker or "unattributed"] = durations.get(speaker or "unattributed", 0) + observation["end"] - observation["start"]
        turns.append({"start": observation["start"], "end": observation["end"], "speaker": speaker,
                      "uncertain": bool(ambiguous), "confidence_margin": round(margin, 5), "short_observation": is_short})
    diagnostics = {"speakers": len(centroids), "observations": len(observations), "reliable_anchors": len(anchors),
                   "short_or_contaminated_observations": short, "uncertain_observations": uncertain,
                   "speaker_seconds": durations, "embedding_norms": {"min": float(norms.min()), "median": float(np.median(norms)), "max": float(norms.max())},
                   "linkage": linkage, "cosine_distance_threshold": threshold, "minimum_anchor_seconds": minimum_anchor_seconds,
                   "clustering_seconds": round(time.perf_counter() - started, 3), "quality_against_human_reference": "not-measured"}
    diagnostics["cluster_cosine_radii"] = radii
    diagnostics["prototype_margin_thresholds"] = margins.tolist()
    return {"turns": turns, "diagnostics": diagnostics, "device": "cpu", "clustering": "global-clean-anchors"}
