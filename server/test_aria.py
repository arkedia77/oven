"""
Aria 생성 모델 빠른 테스트
- 체크포인트 로드 → 짧은 피아노 MIDI 생성
- GPU 메모리 / 속도 확인
"""
import sys
import os
import time

# aria 패키지 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aria"))

def check_environment():
    """GPU 및 환경 확인"""
    import torch
    print("=" * 50)
    print("환경 확인")
    print("=" * 50)
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_mem / 1e9
        print(f"GPU: {gpu}")
        print(f"VRAM: {vram:.1f} GB")
    else:
        print("WARNING: CUDA 사용 불가 — CPU로 테스트")
    print()
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def test_generation(device):
    """Aria 모델 로드 + 생성 테스트"""
    try:
        from aria.model import TransformerLM
        from aria.config import load_model_config
        from aria.tokenizer import AbsTokenizer
    except ImportError:
        print("ERROR: aria 패키지를 찾을 수 없습니다.")
        print("  → pip install -e ./aria 실행 필요")
        return False

    print("=" * 50)
    print("Aria 모델 로드 테스트")
    print("=" * 50)

    # 토크나이저
    tokenizer = AbsTokenizer()
    print(f"토크나이저 vocab size: {tokenizer.vocab_size}")

    # 모델 설정
    model_config = load_model_config("medium")
    print(f"모델 설정: {model_config}")

    # 모델 생성
    print("\n모델 로드 중...")
    t0 = time.time()
    model = TransformerLM(**model_config, vocab_size=tokenizer.vocab_size)

    # 체크포인트 로드
    ckpt_path = os.path.join("checkpoints", "aria-medium-gen", "model.safetensors")
    if os.path.exists(ckpt_path):
        from safetensors.torch import load_file
        state_dict = load_file(ckpt_path)
        model.load_state_dict(state_dict)
        print(f"체크포인트 로드 완료: {ckpt_path}")
    else:
        print(f"WARNING: 체크포인트 없음 ({ckpt_path}) — 랜덤 가중치로 테스트")

    model = model.to(device)
    model.eval()
    t1 = time.time()
    print(f"모델 로드 시간: {t1-t0:.1f}초")

    # 파라미터 수
    params = sum(p.numel() for p in model.parameters())
    print(f"파라미터: {params/1e6:.0f}M ({params/1e9:.2f}B)")

    # GPU 메모리
    if device.type == "cuda":
        import torch
        mem = torch.cuda.memory_allocated() / 1e9
        print(f"GPU 메모리 사용: {mem:.2f} GB")

    # 간단한 생성 테스트
    print("\n" + "=" * 50)
    print("생성 테스트 (16 토큰)")
    print("=" * 50)

    import torch
    # BOS 토큰으로 시작
    prompt = torch.tensor([[tokenizer.bos_tok]], dtype=torch.long, device=device)

    t0 = time.time()
    with torch.no_grad():
        generated = model.generate(
            prompt,
            max_new_tokens=16,
            temperature=0.95,
            top_p=0.95,
        )
    t1 = time.time()

    tokens = generated[0].tolist()
    print(f"생성된 토큰 수: {len(tokens)}")
    print(f"생성 시간: {t1-t0:.2f}초")
    print(f"토큰/초: {len(tokens)/(t1-t0):.1f}")

    # 토큰 디코드
    decoded = tokenizer.decode(tokens)
    print(f"\n디코드된 이벤트 (처음 10개):")
    for i, event in enumerate(decoded[:10]):
        print(f"  {i}: {event}")

    print("\n✅ 생성 테스트 완료!")
    return True


def test_full_generation(device, num_tokens=512):
    """더 긴 생성으로 실제 MIDI 출력"""
    try:
        from aria.model import TransformerLM
        from aria.config import load_model_config
        from aria.tokenizer import AbsTokenizer
        import torch
    except ImportError:
        return False

    print("\n" + "=" * 50)
    print(f"풀 생성 테스트 ({num_tokens} 토큰)")
    print("=" * 50)

    tokenizer = AbsTokenizer()
    model_config = load_model_config("medium")
    model = TransformerLM(**model_config, vocab_size=tokenizer.vocab_size)

    ckpt_path = os.path.join("checkpoints", "aria-medium-gen", "model.safetensors")
    if os.path.exists(ckpt_path):
        from safetensors.torch import load_file
        model.load_state_dict(load_file(ckpt_path))

    model = model.to(device)
    model.eval()

    prompt = torch.tensor([[tokenizer.bos_tok]], dtype=torch.long, device=device)

    t0 = time.time()
    with torch.no_grad():
        generated = model.generate(
            prompt,
            max_new_tokens=num_tokens,
            temperature=0.95,
            top_p=0.95,
        )
    t1 = time.time()

    tokens = generated[0].tolist()
    print(f"생성 토큰: {len(tokens)}")
    print(f"시간: {t1-t0:.1f}초 ({len(tokens)/(t1-t0):.1f} tok/s)")

    if device.type == "cuda":
        peak = torch.cuda.max_memory_allocated() / 1e9
        print(f"GPU 피크 메모리: {peak:.2f} GB")

    # MIDI 파일로 저장
    decoded = tokenizer.decode(tokens)
    output_path = "test_output.mid"
    try:
        mid = tokenizer.detokenize(decoded)
        mid.save(output_path)
        print(f"\n✅ MIDI 저장: {output_path}")
    except Exception as e:
        print(f"\nMIDI 저장 실패 (토큰 부족일 수 있음): {e}")

    return True


if __name__ == "__main__":
    device = check_environment()
    success = test_generation(device)
    if success:
        test_full_generation(device, num_tokens=512)
