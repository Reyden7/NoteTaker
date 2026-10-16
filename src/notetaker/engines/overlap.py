"""Possible-overlap mask from the MIT segmentation powerset model, CPU only.

This flags uncertainty, never identities or confirmed overlap. Natural speech
quality is unqualified until the field corpus has actually been evaluated.
"""
def possible_overlaps(samples, model):
    import numpy as np
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    metadata = session.get_modelmeta().custom_metadata_map
    if (metadata.get("num_classes"), metadata.get("powerset_max_classes")) != ("7", "2"):
        raise ValueError("UNSUPPORTED_OVERLAP_MODEL")
    intervals = []
    for offset in range(0, len(samples), 80000):
        data = np.zeros((1, 1, 160000), dtype=np.float32)
        part = samples[offset:offset + 160000]
        data[0, 0, :len(part)] = part
        logits = session.run(None, {"x": data})[0][0]
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        mask = probs[:, 4:].sum(axis=1) >= 0.6
        start = None
        for i, flagged in enumerate([*mask, False]):
            if flagged and start is None:
                start = i
            elif not flagged and start is not None:
                a = (offset + 495.5 + start * 270) / 16000
                b = min((offset + 495.5 + i * 270) / 16000, len(samples) / 16000)
                if b - a >= 0.2:
                    intervals.append({"start": a, "end": b})
                start = None
    merged = []
    for interval in sorted(intervals, key=lambda x: x["start"]):
        if merged and interval["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], interval["end"])
        else:
            merged.append(interval)
    return merged
