#!/bin/bash
# Liszt Player 설치 스크립트 (macOS)
# Usage: bash install_liszt_player.sh

set -e

echo "=== Liszt Player 설치 ==="

# 1. Homebrew 확인
if ! command -v brew &>/dev/null; then
    echo "Homebrew 필요합니다. 설치 중..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. FluidSynth 설치
echo "[1/3] FluidSynth 설치..."
brew install fluid-synth 2>/dev/null || echo "FluidSynth 이미 설치됨"

# 3. Python 패키지 설치
echo "[2/3] Python 패키지 설치..."
pip3 install PyQt6 pyfluidsynth pretty_midi numpy

# 4. 확인
echo "[3/3] 설치 확인..."
python3 -c "import PyQt6; import fluidsynth; import pretty_midi; print('All OK!')"

echo ""
echo "=== 설치 완료! ==="
echo "실행: python3 liszt_player.py [midi파일/폴더]"
echo ""
echo "SoundFont(.sf2) 파일은 soundfonts/ 폴더에 넣으세요."
echo "없으면 Browse 버튼으로 직접 선택할 수 있습니다."
