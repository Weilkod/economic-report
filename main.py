"""
main.py
경제 지표 PDF/JPG 리포트 생성 메인 진입점

실행 예시:
    python main.py                  # PDF만 생성
    python main.py --jpg            # PDF + JPG 함께
    python main.py --jpg-only       # JPG만 생성
    python main.py --no-ai          # AI 요약 없이
    python main.py --jpg --dpi 300  # 고해상도 JPG
"""

import argparse
import os
from datetime import datetime

from fetch_data      import fetch_all, latest_summary
from make_charts     import make_all_charts
from ai_summary      import get_market_summaries
from generate_report import build_pdf, pdf_to_jpg


def main():
    parser = argparse.ArgumentParser(description="경제 지표 PDF/JPG 리포트 생성기")
    parser.add_argument("--days",       type=int,  default=90)
    parser.add_argument("--out",        type=str,  default="")
    parser.add_argument("--no-ai",      action="store_true")
    parser.add_argument("--charts-dir", type=str,  default="charts")
    parser.add_argument("--jpg",        action="store_true")
    parser.add_argument("--jpg-only",   action="store_true")
    parser.add_argument("--dpi",        type=int,  default=200)
    parser.add_argument("--quality",    type=int,  default=92)
    args = parser.parse_args()

    today_str = datetime.today().strftime('%Y%m%d')
    out_path  = args.out or f"economic_report_{today_str}.pdf"

    print("=" * 50)
    print("  경제 지표 리포트 생성기")
    print("=" * 50)

    print("\n[1/4] 데이터 수집 중...")
    data, precious = fetch_all(period_days=args.days)
    if not data:
        print("ERROR: 데이터를 가져오지 못했습니다.")
        return
    summary = latest_summary(data, precious)

    ai_summaries = {}
    if not args.no_ai:
        print("\n[2/4] AI 변동 요약 생성 중...")
        ai_summaries = get_market_summaries(summary)
    else:
        print("\n[2/4] AI 요약 건너뜀")

    print("\n[3/4] 차트 생성 중...")
    # summary 전달 → 차트 헤더에 현재가·등락률 표시
    chart_paths = make_all_charts(data, output_dir=args.charts_dir,
                                  summary_df=summary)

    print("\n[4/4] PDF 생성 중...")
    build_pdf(summary, chart_paths,
              ai_summaries=ai_summaries,
              output_path=out_path)

    if args.jpg or args.jpg_only:
        print("\n[+] JPG 변환 중...")
        jpg_dir   = os.path.splitext(out_path)[0] + "_jpg"
        jpg_paths = pdf_to_jpg(out_path, output_dir=jpg_dir,
                               dpi=args.dpi, quality=args.quality)
        print(f"  총 {len(jpg_paths)}장 → {jpg_dir}/")
        if args.jpg_only:
            os.remove(out_path)

    print(f"\n✅ 완료!")


if __name__ == "__main__":
    main()
