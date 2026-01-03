#!/usr/bin/env python3
import os
import subprocess
import numpy as np
import json
from PIL import Image
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from collections import defaultdict

def extract_frame_features(image_path):
    """Extract multiple features from a frame"""
    img = Image.open(image_path)
    img_array = np.array(img.resize((128, 128)))
    
    features = []
    
    # 1. Color distribution features
    for channel in range(3):
        channel_data = img_array[:,:,channel].flatten()
        features.extend([
            np.mean(channel_data),
            np.std(channel_data),
            np.percentile(channel_data, 10),
            np.percentile(channel_data, 90)
        ])
    
    # 2. Dominant colors (simplified k-means)
    pixels = img_array.reshape(-1, 3)
    if len(np.unique(pixels, axis=0)) > 3:
        kmeans = KMeans(n_clusters=3, n_init=3, random_state=42)
        kmeans.fit(pixels)
        for center in kmeans.cluster_centers_:
            features.extend(center)
    else:
        features.extend([0] * 9)
    
    # 3. Edge/texture features
    gray = np.array(img.convert('L').resize((64, 64)))
    
    # Sobel-like edge detection
    dx = np.abs(np.diff(gray, axis=1)).sum()
    dy = np.abs(np.diff(gray, axis=0)).sum()
    features.extend([dx, dy, dx + dy])
    
    # 4. Frequency domain features (for glitch detection)
    fft = np.fft.fft2(gray)
    fft_mag = np.abs(fft)
    
    # Low frequency energy
    low_freq = np.sum(fft_mag[:8, :8])
    # High frequency energy  
    high_freq = np.sum(fft_mag[32:, 32:])
    # Mid frequency energy
    mid_freq = np.sum(fft_mag[8:32, 8:32])
    
    features.extend([low_freq, mid_freq, high_freq])
    
    # 5. Noise/entropy features
    # Local variance (noise indicator)
    local_vars = []
    for i in range(0, 64, 16):
        for j in range(0, 64, 16):
            patch = gray[i:i+16, j:j+16]
            local_vars.append(np.var(patch))
    
    features.append(np.mean(local_vars))
    features.append(np.std(local_vars))
    
    # 6. Histogram entropy
    hist, _ = np.histogram(gray, bins=32)
    hist = hist + 1  # Avoid log(0)
    probs = hist / hist.sum()
    entropy = -np.sum(probs * np.log(probs))
    features.append(entropy)
    
    return np.array(features)

def segment_video_by_embeddings(video_path, sample_rate=2, method='transition'):
    """Segment video using frame embeddings"""
    
    print(f"Processing: {video_path}")
    print(f"Sampling frames every {sample_rate} seconds...")
    
    # Create temp directory
    temp_dir = "temp_frame_analysis"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Get video duration
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
           '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    duration = float(subprocess.check_output(cmd).decode().strip())
    
    # Extract frames
    print("Extracting frames...")
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/{sample_rate}',
        f'{temp_dir}/frame_%04d.jpg',
        '-hide_banner', '-loglevel', 'error'
    ]
    subprocess.run(cmd)
    
    # Get frame files and compute features
    frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
    print(f"Analyzing {len(frame_files)} frames...")
    
    features = []
    timestamps = []
    
    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(temp_dir, frame_file)
        feat = extract_frame_features(frame_path)
        features.append(feat)
        timestamps.append(i * sample_rate)
        
        if i % 10 == 0:
            print(f"  Processed {i}/{len(frame_files)} frames...")
    
    features = np.array(features)
    
    # Normalize features
    scaler = StandardScaler()
    features_norm = scaler.fit_transform(features)
    
    # Dimensionality reduction for visualization
    pca = PCA(n_components=2)
    features_2d = pca.fit_transform(features_norm)
    
    # Find segments based on method
    if method == 'transition':
        # Detect transitions by comparing consecutive frames
        distances = []
        for i in range(1, len(features_norm)):
            dist = np.linalg.norm(features_norm[i] - features_norm[i-1])
            distances.append(dist)
        
        # Find peaks in distance
        distances = np.array(distances)
        threshold = np.percentile(distances, 85)  # Top 15% changes
        
        transitions = []
        for i, dist in enumerate(distances):
            if dist > threshold:
                # Ensure minimum gap between transitions
                if not transitions or timestamps[i+1] - transitions[-1] > 10:
                    transitions.append(timestamps[i+1])
        
        print(f"\nFound {len(transitions)} major transitions")
        
    elif method == 'cluster':
        # Use clustering to find natural groupings
        # Determine optimal number of clusters
        if len(features_norm) < 10:
            n_clusters = 2
        else:
            # Try different k values
            inertias = []
            K = range(2, min(10, len(features_norm)))
            for k in K:
                kmeans = KMeans(n_clusters=k, n_init=3, random_state=42)
                kmeans.fit(features_norm)
                inertias.append(kmeans.inertia_)
            
            # Find elbow point
            diffs = np.diff(inertias)
            elbow = np.argmin(diffs) + 2
            n_clusters = min(elbow + 1, 8)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(features_norm)
        
        # Find transition points
        transitions = []
        for i in range(1, len(labels)):
            if labels[i] != labels[i-1]:
                transitions.append(timestamps[i])
        
        print(f"\nFound {n_clusters} clusters with {len(transitions)} transitions")
    
    # Create visualization
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Feature space
    plt.subplot(2, 1, 1)
    plt.scatter(features_2d[:, 0], features_2d[:, 1], c=range(len(features_2d)), 
                cmap='viridis', alpha=0.6)
    plt.colorbar(label='Time (frame index)')
    plt.title('Frame Features in 2D Space (PCA)')
    plt.xlabel('First Principal Component')
    plt.ylabel('Second Principal Component')
    
    # Mark transitions
    for t in transitions:
        idx = int(t / sample_rate)
        if idx < len(features_2d):
            plt.scatter(features_2d[idx, 0], features_2d[idx, 1], 
                       color='red', s=100, marker='x')
    
    # Plot 2: Distance over time
    if method == 'transition':
        plt.subplot(2, 1, 2)
        plt.plot(timestamps[1:], distances)
        plt.axhline(y=threshold, color='r', linestyle='--', label='Threshold')
        plt.scatter([t for t in transitions], 
                   [distances[int(t/sample_rate)-1] for t in transitions if int(t/sample_rate)-1 < len(distances)],
                   color='red', s=50, zorder=5)
        plt.title('Frame-to-Frame Distance')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Feature Distance')
        plt.legend()
    
    plt.tight_layout()
    plt.savefig('embedding_analysis.png', dpi=150)
    print("\nSaved visualization to: embedding_analysis.png")
    
    # Clean up temp files
    for f in frame_files:
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)
    
    return transitions, duration

# Main execution
if __name__ == "__main__":
    video_path = "/Volumes/Workspace/Downloads/charybdis_v2 (1080p).mp4"
    
    print("Advanced Frame Embedding Segmenter")
    print("Designed for glitch/noise/abstract video")
    print("=" * 50)
    
    # Run analysis
    transitions, duration = segment_video_by_embeddings(
        video_path, 
        sample_rate=3,  # Sample every 3 seconds
        method='transition'  # or 'cluster'
    )
    
    # Generate outputs
    from tools.generate_edl import create_edl, seconds_to_timecode
    
    video_name = os.path.basename(video_path).rsplit('.', 1)[0]
    
    # Create EDL
    edl_content = create_edl(video_name, duration, transitions)
    with open(f'{video_name}_embedding.edl', 'w') as f:
        f.write(edl_content)
    
    # Create segment info
    segments = []
    for i in range(len(transitions) + 1):
        if i == 0:
            start = 0
            end = transitions[0] if transitions else duration
        elif i == len(transitions):
            start = transitions[-1]
            end = duration
        else:
            start = transitions[i-1]
            end = transitions[i]
        
        segments.append({
            "index": i,
            "start": start,
            "end": end,
            "duration": end - start,
            "start_tc": seconds_to_timecode(start),
            "end_tc": seconds_to_timecode(end)
        })
    
    # Save analysis results
    results = {
        "video": video_name,
        "duration": duration,
        "method": "frame_embeddings",
        "transitions": transitions,
        "segments": segments,
        "features_used": [
            "color_statistics",
            "dominant_colors", 
            "edge_density",
            "frequency_spectrum",
            "local_noise",
            "entropy"
        ]
    }
    
    with open(f'{video_name}_embedding_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Analysis complete!")
    print(f"Found {len(transitions)} transitions creating {len(segments)} segments")
    print(f"\nOutputs:")
    print(f"- {video_name}_embedding.edl")
    print(f"- {video_name}_embedding_analysis.json")
    print(f"- embedding_analysis.png")
    
    # Show segment summary
    print(f"\nSegments:")
    for seg in segments[:5]:
        print(f"  {seg['index']+1}: {seg['start_tc']} - {seg['end_tc']} ({seg['duration']:.1f}s)")
    if len(segments) > 5:
        print(f"  ... and {len(segments)-5} more")