"""
ai_summary.py
Claude Haiku API를 사용해 각 지표의 변동 이유를 한두 줄로 요약합니다.
API 키: 환경변수 ANTHROPIC_API_KEY 에 설정
"""

import os
import json
import requests
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def get_market_summaries(summary_df) -> dict:
    """
    지표별 변동 이유를 AI로 요약합니다.
    반환: {"S&P 500": "요약 내용", ...}
    """
    if not ANTHROPIC_API_KEY:
        print("  ⚠ ANTHROPIC_API_KEY 미설정 — AI 요약 건너뜁니다.")
        return {}

    # 살때/팔때 행은 제외, 국제 금·은 시세는 포함
    targets = summary_df[
        ~summary_df["지표"].str.contains("살때|팔때", na=False)
    ].copy()

    if targets.empty:
        return {}

    data_lines = []
    for _, row in targets.iterrows():
        pct = row["등락률(%)"]
        if str(pct) == "-":
            continue
        try:
            pct_f = float(pct)
        except Exception:
            continue
        direction = "상승" if pct_f >= 0 else "하락"
        data_lines.append(
            f"- {row['지표']}: {row['최신값']:,.2f} ({direction} {abs(pct_f):.2f}%)"
        )

    if not data_lines:
        return {}

    # 요약 대상 지표 목록 동적 생성
    target_names = [row["지표"] for _, row in targets.iterrows()
                    if str(row["등락률(%)"]) != "-"]
    json_template = "\n".join([f'  "{n}": "요약 내용",' for n in target_names])
    json_template = "{\n" + json_template.rstrip(",") + "\n}"

    prompt = f"""오늘({datetime.today().strftime('%Y년 %m월 %d일')}) 주요 경제 지표 현황입니다:

{chr(10).join(data_lines)}

위 각 지표에 대해 변동 이유를 **한두 문장**으로 간결하게 요약해 주세요.
- 주가지수·환율은 최근 경제 뉴스, 금리, 지정학적 요인 등을 고려해 주세요.
- 금·은 국제시세(금 (국제), 은 (국제))는 달러 흐름, 안전자산 수요, 지정학 리스크 등을 고려해 주세요.
- 확실하지 않은 내용은 "~가능성" 또는 "~영향으로 추정" 등으로 표현해 주세요.

아래 JSON 형식으로만 답변해 주세요 (다른 텍스트 없이):
{json_template}"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )

        content = response.json()["content"][0]["text"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        summaries = json.loads(content.strip())
        print(f"  ✓ AI 요약 완료 ({len(summaries)}개 지표)")
        return summaries

    except Exception as e:
        print(f"  ✗ AI 요약 실패: {e}")
        return {}
