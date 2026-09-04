import torch, os
d = r"D:\data\piano-v6\tensors"
bad = 0
good = 0
for f in sorted(os.listdir(d)):
    if f.endswith(".pt"):
        t = torch.load(os.path.join(d, f), weights_only=False)
        if "encoder_hidden_states" in t:
            good += 1
        else:
            bad += 1
            print(f"BAD: {f} keys={list(t.keys())}")
print(f"\nGood: {good}, Bad: {bad}")
