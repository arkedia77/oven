#!/usr/bin/env python3
"""
Style Clustering Pipeline for Liszt RAG System
================================================
Takes phrase embeddings → K-Means clustering → Style profile analysis

Usage (on 5090):
    python cluster_styles.py --embeddings embeddings/ --k 50
    python cluster_styles.py --embeddings embeddings/ --k 100 --analyze

Outputs:
    - cluster_labels.npy: cluster assignment for each phrase
    - cluster_centers.npy: K cluster centroids (K x 512)
    - cluster_profiles.json: human-readable style analysis per cluster
"""

import argparse
import json
import os
import sys

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from collections import Counter


def load_data(emb_dir):
    """Load embeddings and metadata."""
    embeddings = np.load(os.path.join(emb_dir, "embeddings.npy"))
    metadata = []
    meta_path = os.path.join(emb_dir, "metadata.jsonl")
    with open(meta_path, encoding="utf-8") as f:
        for line in f:
            metadata.append(json.loads(line))
    assert len(embeddings) == len(metadata), \
        f"Mismatch: {len(embeddings)} embeddings vs {len(metadata)} metadata"
    print(f"Loaded {len(embeddings)} embeddings, dim={embeddings.shape[1]}")
    return embeddings, metadata


def run_kmeans(embeddings, k, niter=50, seed=42):
    """Run K-Means clustering using FAISS (GPU if available)."""
    dim = embeddings.shape[1]
    n = embeddings.shape[0]

    if faiss is not None:
        kmeans = faiss.Kmeans(
            dim, k,
            niter=niter,
            verbose=True,
            seed=seed,
            gpu=True if faiss.get_num_gpus() > 0 else False,
        )
        kmeans.train(embeddings)
        _, labels = kmeans.index.search(embeddings, 1)
        labels = labels.squeeze()
        centers = kmeans.centroids
    else:
        # Fallback: scikit-learn
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=k, n_init=10, max_iter=niter, random_state=seed, verbose=1)
        labels = km.fit_predict(embeddings)
        centers = km.cluster_centers_

    return labels, centers


def analyze_clusters(labels, metadata, centers, k):
    """Generate human-readable style profiles for each cluster."""
    profiles = {}

    for ci in range(k):
        mask = labels == ci
        cluster_meta = [metadata[i] for i in range(len(metadata)) if mask[i]]

        if not cluster_meta:
            continue

        # Aggregate statistics
        avg_pitch = np.mean([m["avg_pitch"] for m in cluster_meta])
        avg_vel = np.mean([m["avg_velocity"] for m in cluster_meta])
        avg_dur = np.mean([m["duration"] for m in cluster_meta])
        avg_notes = np.mean([m["num_notes"] for m in cluster_meta])
        avg_density = avg_notes / max(avg_dur, 0.1)

        # Pitch range
        pitch_ranges = [m["pitch_range"] for m in cluster_meta]
        avg_span = np.mean([pr[1] - pr[0] for pr in pitch_ranges])

        # Source distribution
        sources = Counter()
        for m in cluster_meta:
            src = os.path.basename(os.path.dirname(m["source_file"]))
            sources[src] += 1
        top_sources = sources.most_common(5)

        # Register
        if avg_pitch < 48:
            register = "bass"
        elif avg_pitch < 60:
            register = "tenor"
        elif avg_pitch < 72:
            register = "alto"
        elif avg_pitch < 84:
            register = "soprano"
        else:
            register = "high soprano"

        # Dynamic
        if avg_vel < 40:
            dynamic = "pp"
        elif avg_vel < 55:
            dynamic = "p"
        elif avg_vel < 70:
            dynamic = "mp"
        elif avg_vel < 85:
            dynamic = "mf"
        elif avg_vel < 100:
            dynamic = "f"
        else:
            dynamic = "ff"

        # Texture
        if avg_density < 3:
            texture = "sparse/slow"
        elif avg_density < 6:
            texture = "moderate"
        elif avg_density < 12:
            texture = "dense"
        else:
            texture = "virtuosic"

        # Span
        if avg_span < 12:
            span_desc = "narrow (< octave)"
        elif avg_span < 24:
            span_desc = "moderate (1-2 octaves)"
        elif avg_span < 36:
            span_desc = "wide (2-3 octaves)"
        else:
            span_desc = "very wide (3+ octaves)"

        profile = {
            "cluster_id": ci,
            "size": int(mask.sum()),
            "pct": round(100 * mask.sum() / len(labels), 1),
            "style_label": f"cluster_{ci}_{register}_{dynamic}_{texture}",
            "register": register,
            "dynamic": dynamic,
            "texture": texture,
            "span": span_desc,
            "stats": {
                "avg_pitch": round(avg_pitch, 1),
                "avg_velocity": round(avg_vel, 1),
                "avg_duration_sec": round(avg_dur, 1),
                "avg_notes": round(avg_notes, 1),
                "avg_density_nps": round(avg_density, 1),
                "avg_pitch_span": round(avg_span, 1),
            },
            "top_sources": [{"source": s, "count": c} for s, c in top_sources],
        }
        profiles[ci] = profile

    return profiles


def find_optimal_k(embeddings, k_range=(20, 30, 50, 75, 100, 150)):
    """Test multiple K values and report inertia/silhouette."""
    from sklearn.metrics import silhouette_score

    results = []
    for k in k_range:
        print(f"\nTesting K={k}...")
        labels, centers = run_kmeans(embeddings, k, niter=20)

        # Inertia (sum of distances to nearest center)
        if faiss is not None:
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(centers.astype(np.float32))
            dists, _ = index.search(embeddings, 1)
            inertia = float(dists.sum())
        else:
            inertia = 0

        # Silhouette (subsample for speed)
        n_sample = min(10000, len(embeddings))
        idx = np.random.choice(len(embeddings), n_sample, replace=False)
        sil = silhouette_score(embeddings[idx], labels[idx])

        results.append({"k": k, "inertia": round(inertia, 1), "silhouette": round(sil, 4)})
        print(f"  K={k}: inertia={inertia:.1f}, silhouette={sil:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Style Clustering Pipeline")
    parser.add_argument("--embeddings", required=True, help="Embeddings directory")
    parser.add_argument("--k", type=int, default=50, help="Number of clusters")
    parser.add_argument("--output", help="Output directory (default: same as embeddings)")
    parser.add_argument("--analyze", action="store_true", help="Generate style profiles")
    parser.add_argument("--find-k", action="store_true", help="Test multiple K values")
    parser.add_argument("--niter", type=int, default=50, help="K-Means iterations")
    args = parser.parse_args()

    output_dir = args.output or args.embeddings
    os.makedirs(output_dir, exist_ok=True)

    embeddings, metadata = load_data(args.embeddings)

    if args.find_k:
        results = find_optimal_k(embeddings)
        with open(os.path.join(output_dir, "k_search_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        print("\nResults saved to k_search_results.json")
        return

    print(f"\nRunning K-Means with K={args.k}...")
    labels, centers = run_kmeans(embeddings, args.k, niter=args.niter)

    # Save
    np.save(os.path.join(output_dir, "cluster_labels.npy"), labels)
    np.save(os.path.join(output_dir, "cluster_centers.npy"), centers)
    print(f"Saved: cluster_labels.npy ({len(labels)}), cluster_centers.npy ({centers.shape})")

    # Cluster size distribution
    sizes = Counter(labels)
    print(f"\nCluster sizes: min={min(sizes.values())}, max={max(sizes.values())}, "
          f"median={np.median(list(sizes.values())):.0f}")

    if args.analyze:
        print("\nAnalyzing cluster profiles...")
        profiles = analyze_clusters(labels, metadata, centers, args.k)
        with open(os.path.join(output_dir, "cluster_profiles.json"), "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        print(f"Saved cluster_profiles.json ({len(profiles)} clusters)")

        # Print top 10 largest clusters
        sorted_clusters = sorted(profiles.values(), key=lambda x: x["size"], reverse=True)
        print("\nTop 10 clusters:")
        for p in sorted_clusters[:10]:
            print(f"  #{p['cluster_id']:3d} ({p['size']:5d} phrases, {p['pct']:5.1f}%) — "
                  f"{p['register']} {p['dynamic']} {p['texture']} {p['span']}")


if __name__ == "__main__":
    main()
