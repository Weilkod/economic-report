#!/usr/bin/env bash
# run_report.sh — 한 번에 설치 + 실행

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  경제 지표 PDF 리포트 자동화"
echo "================================================"

# 패키지 설치 (최초 1회)
if ! python3 -c "import yfinance" 2>/dev/null; then
    echo "[설치] 필요 패키지를 설치합니다..."
    pip3 install -r requirements.txt --quiet
fi

# 리포트 생성
echo "[실행] 리포트 생성 시작..."
python3 main.py "$@"
