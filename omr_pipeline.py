"""
OMR Pipeline: 악보 이미지 → kern → MIDI
SMT (Sheet Music Transformer) + music21 기반

Usage:
    python omr_pipeline.py image.png                    # 단일 이미지
    python omr_pipeline.py image.png -o output.mid      # 출력 경로 지정
    python omr_pipeline.py ./scores/ -o ./midi_out/     # 폴더 배치 처리
"""
import sys
import os
import argparse
from pathlib import Path

# SMT 리포 경로 추가
SMT_DIR = Path(__file__).parent / "smt"
sys.path.insert(0, str(SMT_DIR))

import torch
import cv2
from music21 import converter


def load_smt_model(model_name="PRAIG/smt-fp-grandstaff"):
    """SMT 모델 로드"""
    from data_augmentation.data_augmentation import convert_img_to_tensor
    from smt_model import SMTModelForCausalLM

    print(f"Loading SMT model: {model_name}")
    model = SMTModelForCausalLM.from_pretrained(model_name).to("cpu")
    print(f"Model loaded ({sum(p.numel() for p in model.parameters()):,} params)")
    return model, convert_img_to_tensor


def image_to_kern(model, convert_fn, image_path):
    """악보 이미지 → kern 문자열"""
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    tensor = convert_fn(image).unsqueeze(0).to("cpu")
    predictions, _ = model.predict(tensor, convert_to_str=True)

    raw = "".join(predictions)
    kern = raw.replace('<b>', '\n').replace('<s>', ' ').replace('<t>', '\t')
    return kern


def clean_kern_output(kern_str):
    """SMT 출력 정리 — ekern→kern 변환 + 반복/노이즈 제거 + 빔 마커 제거"""
    import re
    lines = kern_str.strip().split('\n')
    cleaned = []
    dot_streak = 0
    num_spines = None

    for line in lines:
        stripped = line.strip()

        # ekern 헤더 → 표준 kern 변환
        stripped = re.sub(r'\*\*ekern[_\d.]*', '**kern', stripped)

        # 빔 마커(L, J, Jk, k) 제거 — music21이 파싱 못하는 경우 있음
        if not stripped.startswith('*') and not stripped.startswith('!') and stripped != '=' and '=' not in stripped[:2]:
            parts = stripped.split('\t')
            clean_parts = []
            for p in parts:
                # 음표 토큰에서 L, J, Jk, k 제거 (단 pitch letter는 보존)
                tokens = p.split(' ')
                clean_tokens = []
                for t in tokens:
                    if t == '.':
                        clean_tokens.append(t)
                    else:
                        t = re.sub(r'[LJk]+$', '', t)  # 빔 마커 제거
                        if t:
                            clean_tokens.append(t)
                clean_parts.append(' '.join(clean_tokens))
            stripped = '\t'.join(clean_parts)

        # 스파인 수 결정 (첫 ** 라인 기준)
        if stripped.startswith('**') and num_spines is None:
            num_spines = stripped.count('\t') + 1

        # 순수 dot 라인 카운트
        if all(c in '.\t ' for c in stripped) and stripped:
            dot_streak += 1
            if dot_streak > 3:
                continue
        else:
            dot_streak = 0

        if stripped:
            cleaned.append(stripped)

    # 마지막에 종료 토큰 보장
    if cleaned and not cleaned[-1].strip().startswith('*-'):
        ns = num_spines or 2
        cleaned.append('\t'.join(['*-'] * ns))

    return '\n'.join(cleaned)


def kern_to_midi(kern_str, output_path):
    """kern 문자열 → MIDI 파일"""
    try:
        score = converter.parse(kern_str, format='humdrum')
        score.write('midi', fp=str(output_path))
        return True
    except Exception as e:
        print(f"  kern→MIDI 변환 실패: {e}")
        return False


def process_image(model, convert_fn, image_path, output_path, save_kern=False):
    """단일 이미지 전체 파이프라인"""
    image_path = Path(image_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/3] 이미지 로드: {image_path.name}")
    kern = image_to_kern(model, convert_fn, image_path)

    print(f"[2/3] kern 출력 정리")
    kern_clean = clean_kern_output(kern)

    if save_kern:
        kern_path = output_path.with_suffix('.krn')
        kern_path.write_text(kern_clean, encoding='utf-8')
        print(f"  kern 저장: {kern_path}")

    print(f"[3/3] MIDI 변환: {output_path.name}")
    success = kern_to_midi(kern_clean, output_path)

    if success:
        print(f"  ✅ 완료: {output_path}")
    else:
        # kern 파일은 디버깅용으로 항상 저장
        kern_path = output_path.with_suffix('.krn')
        kern_path.write_text(kern_clean, encoding='utf-8')
        print(f"  ❌ MIDI 실패, kern 저장: {kern_path}")

    return success


def main():
    parser = argparse.ArgumentParser(description='악보 이미지 → MIDI 변환')
    parser.add_argument('input', help='이미지 파일 또는 폴더')
    parser.add_argument('-o', '--output', help='출력 MIDI 파일/폴더')
    parser.add_argument('-m', '--model', default='PRAIG/smt-fp-grandstaff',
                        help='SMT 모델 (default: PRAIG/smt-fp-grandstaff)')
    parser.add_argument('--save-kern', action='store_true',
                        help='중간 kern 파일도 저장')
    args = parser.parse_args()

    model, convert_fn = load_smt_model(args.model)

    input_path = Path(args.input)

    if input_path.is_file():
        output = Path(args.output) if args.output else input_path.with_suffix('.mid')
        process_image(model, convert_fn, input_path, output, args.save_kern)

    elif input_path.is_dir():
        output_dir = Path(args.output) if args.output else input_path / 'midi_output'
        output_dir.mkdir(parents=True, exist_ok=True)

        images = sorted(
            p for p in input_path.iterdir()
            if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp')
        )
        print(f"Found {len(images)} images in {input_path}")

        success, fail = 0, 0
        for img in images:
            out = output_dir / img.with_suffix('.mid').name
            if process_image(model, convert_fn, img, out, args.save_kern):
                success += 1
            else:
                fail += 1

        print(f"\n=== 결과: {success} 성공, {fail} 실패 / {len(images)} 총 ===")
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)


if __name__ == '__main__':
    main()
