#!/usr/bin/env python3
"""Group visually similar consecutive segments within each video."""

import json
import os
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIMILARITY_THRESHOLD = 0.92  # cosine similarity threshold for grouping

def image_features(path):
    """Extract a compact feature vector from a thumbnail."""
    img = Image.open(path).resize((64, 18))  # small, preserves 32:9 ratio
    arr = np.array(img, dtype=np.float32).flatten()
    # Normalize
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr /= norm
    return arr

def cosine_sim(a, b):
    return float(np.dot(a, b))

def group_video_segments(video):
    """Group consecutive similar segments. Returns list of groups."""
    segments = video["segments"]
    if not segments:
        return []

    # Compute features for each segment
    features = []
    for seg in segments:
        thumb_path = os.path.join(BASE_DIR, seg["thumbnail"])
        if os.path.exists(thumb_path):
            features.append(image_features(thumb_path))
        else:
            features.append(None)

    # Group consecutive similar segments
    groups = []
    current_group = [0]
    for i in range(1, len(segments)):
        if features[i] is not None and features[current_group[0]] is not None:
            sim = cosine_sim(features[current_group[0]], features[i])
            if sim >= SIMILARITY_THRESHOLD:
                current_group.append(i)
                continue
        # Start new group
        groups.append(current_group)
        current_group = [i]
    groups.append(current_group)

    return groups

def main():
    manifest_path = os.path.join(BASE_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    total_groups = 0
    total_segments = 0

    for video in manifest:
        groups = group_video_segments(video)
        # Add group info to each segment
        for group_idx, group in enumerate(groups):
            for seg_pos, seg_i in enumerate(group):
                video["segments"][seg_i]["group"] = group_idx
                video["segments"][seg_i]["group_size"] = len(group)
                video["segments"][seg_i]["group_representative"] = (seg_pos == len(group) // 2)
        total_groups += len(groups)
        total_segments += len(video["segments"])
        print(f"{video['video_id']}: {len(video['segments'])} segments → {len(groups)} groups")

    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nTotal: {total_segments} segments → {total_groups} groups")

if __name__ == "__main__":
    main()
