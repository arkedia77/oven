#!/usr/bin/env python3
"""
RAG Query Utility for Liszt
=============================
Search the phrase embedding index with a seed MIDI or cluster ID.

Usage:
    # Search by MIDI file (find similar phrases)
    python query_rag.py --index embeddings/ --query seed.mid --top-k 10

    # Search by cluster ID
    python query_rag.py --index embeddings/ --cluster 7 --top-k 5

    # Get cluster info
    python query_rag.py --index embeddings/ --info
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


def load_index(emb_dir):
    """Load FAISS index and metadata."""
    index_path = os.path.join(emb_dir, "index.faiss")
    meta_path = os.path.join(emb_dir, "metadata.jsonl")
    emb_path = os.path.join(emb_dir, "embeddings.npy")

    metadata = []
    with open(meta_path, encoding="utf-8") as f:
        for line in f:
            metadata.append(json.loads(line))

    if faiss is not None and os.path.exists(index_path):
        index = faiss.read_index(index_path)
        print(f"Loaded FAISS index: {index.ntotal} vectors")
    else:
        embeddings = np.load(emb_path)
        index = None
        print(f"Loaded raw embeddings: {embeddings.shape}")

    return index, metadata


def search_by_midi(index, metadata, query_midi, embedder, top_k=10):
    """Find phrases similar to a query MIDI file."""
    from embed_phrases import segment_midi, phrase_to_midi_dict

    phrases = segment_midi(query_midi)
    if not phrases:
        print("No phrases found in query MIDI")
        return []

    print(f"Query MIDI: {len(phrases)} phrases detected")

    all_results = []
    for pi, (start_t, end_t, pnotes) in enumerate(phrases):
        midi_dict = phrase_to_midi_dict(pnotes, query_midi)
        query_emb = embedder.embed(midi_dict).reshape(1, -1).astype(np.float32)

        scores, indices = index.search(query_emb, top_k)

        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            m = metadata[idx].copy()
            m["similarity"] = round(float(score), 4)
            m["rank"] = rank
            results.append(m)

        all_results.append({
            "query_phrase": pi,
            "query_start": round(start_t, 3),
            "query_end": round(end_t, 3),
            "query_notes": len(pnotes),
            "results": results,
        })

    return all_results


def search_by_cluster(emb_dir, metadata, cluster_id, top_k=10):
    """Get phrases from a specific cluster."""
    labels = np.load(os.path.join(emb_dir, "cluster_labels.npy"))
    mask = labels == cluster_id
    cluster_meta = [(i, metadata[i]) for i in range(len(metadata)) if mask[i]]

    print(f"Cluster {cluster_id}: {len(cluster_meta)} phrases")

    # Return random sample
    import random
    sample = random.sample(cluster_meta, min(top_k, len(cluster_meta)))
    return [m for _, m in sample]


def show_info(emb_dir):
    """Show index and clustering info."""
    meta_path = os.path.join(emb_dir, "metadata.jsonl")
    n_phrases = sum(1 for _ in open(meta_path))

    emb = np.load(os.path.join(emb_dir, "embeddings.npy"))
    print(f"Embeddings: {emb.shape[0]} phrases, {emb.shape[1]}-dim")

    profiles_path = os.path.join(emb_dir, "cluster_profiles.json")
    if os.path.exists(profiles_path):
        with open(profiles_path) as f:
            profiles = json.load(f)
        print(f"Clusters: {len(profiles)}")
        sorted_p = sorted(profiles.values(), key=lambda x: x["size"], reverse=True)
        for p in sorted_p[:15]:
            print(f"  #{p['cluster_id']:3d} ({p['size']:5d}, {p['pct']:5.1f}%) "
                  f"{p['style_label']}")
    else:
        print("No cluster profiles found. Run cluster_styles.py first.")

    labels_path = os.path.join(emb_dir, "cluster_labels.npy")
    if os.path.exists(labels_path):
        labels = np.load(labels_path)
        from collections import Counter
        sizes = Counter(labels)
        print(f"\nCluster stats: {len(sizes)} clusters, "
              f"min={min(sizes.values())}, max={max(sizes.values())}, "
              f"median={np.median(list(sizes.values())):.0f}")


def main():
    parser = argparse.ArgumentParser(description="RAG Query Utility")
    parser.add_argument("--index", required=True, help="Embeddings directory")
    parser.add_argument("--query", help="Query MIDI file")
    parser.add_argument("--cluster", type=int, help="Cluster ID to sample from")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--info", action="store_true", help="Show index info")
    parser.add_argument("--model-dir", default=r"C:\Users\leo\liszt\aria-medium-embedding")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    if args.info:
        show_info(args.index)
        return

    if args.query:
        index, metadata = load_index(args.index)
        from embed_phrases import AriaEmbedder
        embedder = AriaEmbedder(args.model_dir, device=args.device)
        results = search_by_midi(index, metadata, args.query, embedder, args.top_k)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.cluster is not None:
        _, metadata = load_index(args.index)
        results = search_by_cluster(args.index, metadata, args.cluster, args.top_k)
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
