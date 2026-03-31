"""
fetch_data.py
- Yahoo Finance: 주가지수·환율 시계열 수집
- 키즈맘 뉴스 크롤링: 금·은 살때/팔때 실제 가격 수집
  URL: https://www.kizmom.com/news/articleView.html?idxno=숫자
  매일 오전 금시세 기사 발행 (금시세닷컴 or 한국금거래소 기준)
  기사 번호는 검색으로 오늘 날짜 기사를 찾음
- 크롤링 실패 시: KRX 공식(×배율)으로 자동 폴백
"""

import re
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ── Yahoo Finance 수집 대상 ──────────────────────────────────────
TICKERS = {
    "S&P 500":      "^GSPC",
    "NASDAQ":       "^IXIC",
    "다우존스":     "^DJI",
    "KOSPI":        "^KS11",
    "KOSDAQ":       "^KQ11",
    "원/달러 환율": "KRW=X",
    "비트코인":     "BTC-KRW",
    "금 (국제)":    "GC=F",
    "은 (국제)":    "SI=F",
}
PERIOD_DAYS = 90

# ── KRX 폴백 계수 ────────────────────────────────────────────────
GOLD_BUY_MULT  = 1.165
GOLD_SELL_MULT = 0.974
SILV_BUY_MULT  = 1.175
SILV_SELL_MULT = 0.808
TROY_OZ_PER_G  = 31.1035
DON_G          = 3.75
KG_G           = 1000.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ── 키즈맘 금시세 기사 크롤링 ────────────────────────────────────
def _parse_kizmom_article(idxno: int) -> dict:
    """
    키즈맘 기사에서 '한국금거래소' 기준 금·은 살때/팔때만 파싱합니다.
    기사 구조 예시:
      한국금거래소에 따르면 27일 오전 9시 50분 기준
      순금 한 돈(3.75g) 가격은 살 때 934,000원으로 ...
      팔 때 가격은 786,000원으로 ...
      은 시세는 살 때 14,740원, 팔 때 11,520원이다.
    """
    url = f"https://www.kizmom.com/news/articleView.html?idxno={idxno}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return {}
        soup = BeautifulSoup(res.text, "html.parser")

        # 금시세 기사 확인
        title = soup.find("h1") or soup.find("h2")
        if title and "금시세" not in title.get_text():
            return {}

        text = soup.get_text(" ", strip=True)

        # ── 한국금거래소 기준 섹션만 추출 ────────────────────────
        # "한국금거래소에 따르면" 이후 텍스트만 사용
        if "한국금거래소에 따르면" not in text:
            print(f"  ✗ idxno={idxno}: 한국금거래소 기준 없음")
            return {}

        # 한국금거래소 섹션 시작점 이후만 파싱
        krx_section = text[text.index("한국금거래소에 따르면"):]

        result = {}

        # 금 살때: "살 때 934,000원"
        m = re.search(r"살 때\s*([\d,]+)원", krx_section)
        if m:
            result["금_살때_1돈"] = int(m.group(1).replace(",", ""))

        # 금 팔때: "팔 때 가격은 786,000원" 또는 "팔 때 786,000원"
        m = re.search(r"팔 때 가격은\s*([\d,]+)원", krx_section)
        if not m:
            m = re.search(r"팔 때\s*([\d,]+)원", krx_section)
        if m:
            result["금_팔때_1돈"] = int(m.group(1).replace(",", ""))

        # 은: "은 시세는 살 때 14,740원, 팔 때 11,520원"
        m = re.search(r"은 시세는 살 때\s*([\d,]+)원[^팔]*팔 때\s*([\d,]+)원", krx_section)
        if m:
            result["은_살때_1돈"] = int(m.group(1).replace(",", ""))
            result["은_팔때_1돈"] = int(m.group(2).replace(",", ""))

        # 날짜 추출
        m = re.search(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", text)
        if m:
            result["기준일"] = (f"{m.group(1)}-"
                               f"{int(m.group(2)):02d}-"
                               f"{int(m.group(3)):02d}")

        result["출처"] = "키즈맘 (한국금거래소 기준)"
        return result

    except Exception as e:
        print(f"  ✗ 파싱 오류 (idxno={idxno}): {e}")
        return {}


def _find_latest_kizmom_idxno() -> int:
    """
    키즈맘 경제 섹션에서 오늘 금시세 기사의 idxno를 찾습니다.
    최근 기사 목록을 스캔해서 '금시세' 제목 기사를 반환합니다.
    """
    try:
        # 경제 섹션 목록 페이지
        url = ("https://www.kizmom.com/news/articleList.html"
               "?sc_section_code=S1N1&view_type=sm")
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if "금시세" in text and "idxno=" in href:
                m = re.search(r"idxno=(\d+)", href)
                if m:
                    idxno = int(m.group(1))
                    print(f"  ✓ 키즈맘 금시세 기사 발견: idxno={idxno} ({text[:20]})")
                    return idxno

    except Exception as e:
        print(f"  ✗ 목록 스캔 실패: {e}")

    return None


def _fetch_kizmom_gold() -> dict:
    """
    키즈맘에서 금·은 살때/팔때 가격을 크롤링합니다.
    오늘 기사 → 어제 기사 순으로 최대 7일 탐색합니다.
    """
    print("[키즈맘 금시세 크롤링]")

    # 1. 섹션 목록에서 최신 idxno 탐색
    idxno = _find_latest_kizmom_idxno()

    if idxno:
        # 최신 기사 + 전후 ±3개 범위 시도
        for candidate in range(idxno, idxno - 5, -1):
            result = _parse_kizmom_article(candidate)
            if result.get("금_살때_1돈") and result.get("금_팔때_1돈"):
                print(f"  ✓ 금 살때: {result['금_살때_1돈']:,}원  "
                      f"팔때: {result['금_팔때_1돈']:,}원")
                if result.get("은_살때_1돈"):
                    print(f"  ✓ 은 살때: {result['은_살때_1돈']:,}원  "
                          f"팔때: {result['은_팔때_1돈']:,}원")
                return result

    print("  ⚠ 키즈맘 크롤링 실패 — KRX 공식으로 폴백합니다.")
    return {}


# ── KRX 공식 폴백 ────────────────────────────────────────────────
def _calc_from_krx(raw: dict) -> dict:
    """Yahoo Finance 국제 시세 × 환율로 살때/팔때 근사 계산"""
    try:
        krw = float(raw["원/달러 환율"]["close"].iloc[-1])
        gold_usd = float(raw["금 (국제)"]["close"].iloc[-1])
        silv_usd = float(raw["은 (국제)"]["close"].iloc[-1])

        gold_don = gold_usd * krw / TROY_OZ_PER_G * DON_G
        silv_don = silv_usd * krw / TROY_OZ_PER_G * DON_G

        return {
            "금_살때_1돈": round(gold_don * GOLD_BUY_MULT),
            "금_팔때_1돈": round(gold_don * GOLD_SELL_MULT),
            "은_살때_1돈": round(silv_don * SILV_BUY_MULT),
            "은_팔때_1돈": round(silv_don * SILV_SELL_MULT),
            "기준일":      datetime.today().strftime("%Y-%m-%d"),
            "출처":        "KRX 공식 근사",
        }
    except Exception as e:
        print(f"  ✗ KRX 폴백 계산 실패: {e}")
        return {}


# ── Yahoo Finance 수집 ───────────────────────────────────────────
def fetch_yahoo(period_days: int = PERIOD_DAYS) -> dict:
    end   = datetime.today()
    start = end - timedelta(days=period_days)
    print(f"[Yahoo Finance] {start.date()} ~ {end.date()}")
    raw = {}
    for name, ticker in TICKERS.items():
        try:
            df = yf.download(
                ticker,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                auto_adjust=True,
                progress=False,
            )
            if df.empty:
                print(f"  ✗ {name}: 데이터 없음")
                continue
            close = df[["Close"]].copy()
            close.columns = ["close"]
            close.index = pd.to_datetime(close.index)
            raw[name] = close
            print(f"  ✓ {name}: {len(close)}행")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
    return raw


# ── 전체 수집 ────────────────────────────────────────────────────
def fetch_all(period_days: int = PERIOD_DAYS) -> tuple:
    """
    반환: (data, precious)
      data     : {지표명: DataFrame}  — 차트용 (금·은 국제 제외)
      precious : {항목명: 값}         — 금·은 살때/팔때
    """
    raw = fetch_yahoo(period_days)

    # 금·은 살때/팔때: 키즈맘 크롤링 우선, 실패 시 KRX 폴백
    print()
    precious = _fetch_kizmom_gold()
    if not precious.get("금_살때_1돈"):
        precious = _calc_from_krx(raw)

    # 차트용 데이터 — 금·은 국제시세도 포함 (차트에 표시)
    # 단, 요약 표에는 나타나지 않도록 fetch_data 단계에서는 그대로 둠
    data = {k: v for k, v in raw.items()}

    return data, precious


# ── 요약 DataFrame ───────────────────────────────────────────────
def latest_summary(data: dict, precious: dict) -> pd.DataFrame:
    """
    발행일(한국시간 기준) 데이터 선택 기준:
      - 미국 지수 (S&P500, NASDAQ, 다우존스)  → 발행일 전날 종가 (미국장 마감)
      - 금·은 국제시세 (GC=F, SI=F)          → 발행일 전날 종가
      - KOSPI, KOSDAQ                         → 발행일 당일 최신값
      - USD/KRW 환율                          → 발행일 당일 최신값
      - 금·은 국내 살때/팔때                  → 키즈맘 기사 발행일 기준
    """
    rows = []
    today = datetime.today().strftime("%Y-%m-%d")

    # 전날 종가를 써야 하는 미국 지표
    US_TICKERS = {"S&P 500", "NASDAQ", "다우존스", "금 (국제)", "은 (국제)"}
    # 당일 최신값을 쓰는 한국 지표
    KR_TICKERS = {"KOSPI", "KOSDAQ", "원/달러 환율", "비트코인"}

    unit_map = {
        "원/달러 환율": "원",
        "S&P 500":      "pt",  "NASDAQ":    "pt",
        "다우존스":     "pt",  "KOSPI":     "pt",  "KOSDAQ":    "pt",
        "금 (국제)":    "$/oz","은 (국제)": "$/oz",
        "비트코인":     "원",
    }

    for name, df in data.items():
        if len(df) < 2:
            continue

        if name in US_TICKERS:
            # 전날 종가 = iloc[-1] (야후파이낸스는 오늘 포함 안 하므로 그대로)
            latest = float(df["close"].iloc[-1])
            prev   = float(df["close"].iloc[-2])
            ref_date = df.index[-1].strftime("%Y-%m-%d")
        else:
            # 당일 최신값
            latest = float(df["close"].iloc[-1])
            prev   = float(df["close"].iloc[-2])
            ref_date = df.index[-1].strftime("%Y-%m-%d")

        chg = latest - prev
        pct = chg / prev * 100

        rows.append({
            "지표":      name,
            "최신값":    round(latest, 2),
            "전일대비":  round(chg, 2),
            "등락률(%)": round(pct, 2),
            "단위":      unit_map.get(name, ""),
            "기준일":    ref_date,
        })

    # 금·은 국내 살때/팔때 — 키즈맘 기사 발행일 기준
    base_dt = precious.get("기준일", today)
    DON_G   = 3.75
    KG_G    = 1000.0

    gold_buy_10  = precious.get("금_살때_1돈", 0) * 10
    gold_sell_10 = precious.get("금_팔때_1돈", 0) * 10
    silv_buy_kg  = round(precious.get("은_살때_1돈", 0) / DON_G * KG_G)
    silv_sell_kg = round(precious.get("은_팔때_1돈", 0) / DON_G * KG_G)

    if gold_buy_10:
        rows.append({"지표": "금 살때 (10돈)", "최신값": gold_buy_10,
                     "전일대비": "-", "등락률(%)": "-",
                     "단위": "원/10돈", "기준일": base_dt})
    if gold_sell_10:
        rows.append({"지표": "금 팔때 (10돈)", "최신값": gold_sell_10,
                     "전일대비": "-", "등락률(%)": "-",
                     "단위": "원/10돈", "기준일": base_dt})
    if silv_buy_kg:
        rows.append({"지표": "은 살때 (1kg)", "최신값": silv_buy_kg,
                     "전일대비": "-", "등락률(%)": "-",
                     "단위": "원/kg", "기준일": base_dt})
    if silv_sell_kg:
        rows.append({"지표": "은 팔때 (1kg)", "최신값": silv_sell_kg,
                     "전일대비": "-", "등락률(%)": "-",
                     "단위": "원/kg", "기준일": base_dt})

    return pd.DataFrame(rows)


if __name__ == "__main__":
    data, precious = fetch_all()
    summary = latest_summary(data, precious)
    print("\n=== 요약 ===")
    print(summary.to_string(index=False))
