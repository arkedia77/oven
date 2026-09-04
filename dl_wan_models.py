"""
WAN 2.2 T2V + I2V sequential download
======================================
E:\models\ 에 다운로드, QoS 2.5Mbps 제한
T2V 완료 후 I2V 순차 실행
"""
import sys, time, subprocess, os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

LOG = r"D:\liszt\output\dl_wan.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def set_qos(name="HFDownloadLimit", bps=2500000):
    """Set QoS bandwidth limit for python.exe"""
    # Remove existing
    subprocess.run(
        ["powershell", "-Command",
         f"Remove-NetQosPolicy -Name '{name}' -Confirm:$false -EA SilentlyContinue"],
        capture_output=True)
    # Create new
    result = subprocess.run(
        ["powershell", "-Command",
         f"New-NetQosPolicy -Name '{name}' -AppPathNameMatchCondition 'python.exe' "
         f"-ThrottleRateActionBitsPerSecond {bps} -Confirm:$false"],
        capture_output=True, text=True)
    if result.returncode == 0:
        log(f"QoS set: {name} = {bps/1e6:.1f}Mbps")
    else:
        log(f"QoS warning: {result.stderr[:200]}")

def remove_qos(name="HFDownloadLimit"):
    subprocess.run(
        ["powershell", "-Command",
         f"Remove-NetQosPolicy -Name '{name}' -Confirm:$false -EA SilentlyContinue"],
        capture_output=True)
    log(f"QoS removed: {name}")

def download_model(repo_id, local_dir, label):
    from huggingface_hub import snapshot_download
    log(f"Starting download: {label} -> {local_dir}")
    t0 = time.time()
    try:
        snapshot_download(
            repo_id,
            local_dir=local_dir,
            token=True,
            resume_download=True,
        )
        elapsed = time.time() - t0
        # Check actual size
        total = 0
        for root, dirs, files in os.walk(local_dir):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        gb = total / (1024**3)
        log(f"DONE: {label} — {gb:.1f}GB in {elapsed/3600:.1f}h")
        return True
    except Exception as e:
        log(f"FAILED: {label} — {e}")
        return False

def main():
    log("=" * 60)
    log("WAN 2.2 T2V + I2V Sequential Download")
    log("=" * 60)

    # Set QoS (2.5Mbps = ~312KB/s, about half of 5Mbps line)
    set_qos(bps=2500000)

    # 1. T2V
    ok_t2v = download_model(
        "Wan-AI/Wan2.2-T2V-A14B",
        r"E:\models\Wan2.2-T2V-A14B",
        "Wan2.2-T2V-A14B"
    )

    # 2. I2V (after T2V)
    if ok_t2v:
        log("T2V complete, starting I2V...")
    else:
        log("T2V failed, attempting I2V anyway...")

    ok_i2v = download_model(
        "Wan-AI/Wan2.2-I2V-A14B",
        r"E:\models\Wan2.2-I2V-A14B",
        "Wan2.2-I2V-A14B"
    )

    # Cleanup QoS
    remove_qos()

    log("=" * 60)
    log(f"Download complete: T2V={'OK' if ok_t2v else 'FAIL'}, I2V={'OK' if ok_i2v else 'FAIL'}")
    log("=" * 60)

if __name__ == "__main__":
    main()
