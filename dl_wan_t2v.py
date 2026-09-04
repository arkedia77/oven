"""Download Wan2.2-T2V-A14B to D:\models\ (run on 5090)"""
import sys, time, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG = r"D:\liszt\output\dl_wan_t2v.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

if __name__ == "__main__":
    from huggingface_hub import snapshot_download
    log("Starting Wan2.2-T2V-A14B download...")
    t0 = time.time()
    try:
        path = snapshot_download(
            "Wan-AI/Wan2.2-T2V-A14B",
            local_dir=r"D:\models\Wan2.2-T2V-A14B",
        )
        elapsed = time.time() - t0
        total = sum(os.path.getsize(os.path.join(r,f))
                    for r,d,fs in os.walk(path) for f in fs)
        log(f"DONE: {total/1e9:.1f}GB in {elapsed/60:.0f}min -> {path}")
    except Exception as e:
        log(f"FAILED: {e}")
        sys.exit(1)
