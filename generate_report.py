"""
generate_report.py
모바일·60대 가독성 개선판:
  - 표지 제거
  - 전체 폰트 사이즈 업 (최소 11pt 기준)
  - 줄간격·여백 넉넉하게
  - 색상 대비 강화 (밝은 배경 + 진한 글씨)
  - 표 행 높이 확대
  - 금·은 박스 더 크고 명확하게
  - AI 요약: 지표별 구분선 + 큰 글씨
  - 섹션마다 새 페이지
  - 정보량 유지
"""

import os, io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, PageBreak,
)
import pandas as pd

# ── 색상 ─────────────────────────────────────────────────────────
BLUE_DARK    = colors.HexColor("#1E3A5F")
BLUE_MID     = colors.HexColor("#2563EB")
BLUE_LIGHT   = colors.HexColor("#EFF6FF")
GOLD_BG      = colors.HexColor("#FFFBEB")
GOLD_BORDER  = colors.HexColor("#B45309")
SILV_BG      = colors.HexColor("#F1F5F9")
SILV_BORDER  = colors.HexColor("#475569")
GREEN        = colors.HexColor("#065F46")
RED          = colors.HexColor("#991B1B")
GRAY         = colors.HexColor("#6B7280")
DARK         = colors.HexColor("#111827")
WHITE        = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm   # 좌우 여백
# 표 전체 폭 = PAGE_W - 2*MARGIN (약 174mm) → 6등분
TBL_W  = PAGE_W - 2 * MARGIN


# ── 한글 폰트 ─────────────────────────────────────────────────────
def _find_korean_font():
    for p in [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "/Library/Fonts/AppleGothic.ttf",
    ]:
        if os.path.exists(p):
            return p
    return None

KOR_FONT = _find_korean_font()


# ── PIL 텍스트 → ReportLab Image ─────────────────────────────────
def _img(text: str, fontsize: int = 13, color: str = "#111827",
         max_width_mm: float = 174) -> RLImage:
    if not KOR_FONT:
        buf = io.BytesIO()
        Image.new("RGBA",(10,20),(255,255,255,0)).save(buf,"PNG")
        buf.seek(0)
        return RLImage(buf, width=1, height=fontsize*0.5*mm)

    px   = int(fontsize * 2.6)
    font = ImageFont.truetype(KOR_FONT, size=px)
    dummy = Image.new("RGBA",(1,1))
    bbox  = ImageDraw.Draw(dummy).textbbox((0,0), text, font=font)
    w = bbox[2]-bbox[0]+10
    h = bbox[3]-bbox[1]+10

    img  = Image.new("RGBA",(w,h),(255,255,255,0))
    draw = ImageDraw.Draw(img)
    r,g,b = int(color[1:3],16),int(color[3:5],16),int(color[5:7],16)
    draw.text((5, 5-bbox[1]), text, font=font, fill=(r,g,b,255))

    pt_per_px = 72.0/150.0
    out_w = w*pt_per_px
    out_h = h*pt_per_px
    max_w = max_width_mm*mm
    if out_w > max_w:
        s = max_w/out_w; out_w*=s; out_h*=s

    buf = io.BytesIO()
    img.save(buf,"PNG",dpi=(150,150))
    buf.seek(0)
    return RLImage(buf, width=out_w, height=out_h)


# ── 섹션 헤더 ─────────────────────────────────────────────────────
def _section(title: str) -> list:
    return [
        Spacer(1, 1*mm),
        _img(title, fontsize=14, color="#1E3A5F", max_width_mm=174),
        HRFlowable(width="100%", thickness=1.2, color=BLUE_MID,
                   spaceBefore=1, spaceAfter=3),
    ]


# ── 날짜 헤더 바 ─────────────────────────────────────────────────
def _date_bar(summary_df: pd.DataFrame = None) -> Table:
    today = datetime.today().strftime("%Y년 %m월 %d일")

    # 미국 지표 기준일 (전날)
    us_date = ""
    kr_date = today
    if summary_df is not None:
        us_rows = summary_df[summary_df["지표"].isin(["S&P 500","NASDAQ","다우존스"])]
        kr_rows = summary_df[summary_df["지표"].isin(["KOSPI","KOSDAQ"])]
        if not us_rows.empty:
            us_date = us_rows.iloc[0]["기준일"]
        if not kr_rows.empty:
            kr_date = kr_rows.iloc[0]["기준일"]

    left_txt  = f"경제 지표 리포트   {today}"
    right_txt = (f"미국·금은(국제) {us_date}  |  한국·환율·금은 {kr_date}"
                 if us_date and us_date != kr_date else today)

    row = [[
        _img(left_txt,  fontsize=12, color="#FFFFFF",  max_width_mm=120),
        _img(right_txt, fontsize=9,  color="#BFD7F7",  max_width_mm=65),
    ]]
    t = Table(row, colWidths=[TBL_W*0.62, TBL_W*0.38])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE_DARK),
        ("ALIGN",         (0,0),(0,-1),  "LEFT"),
        ("ALIGN",         (1,0),(1,-1),  "RIGHT"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
    ]))
    return t


# ── 1. 지표 요약 표 ───────────────────────────────────────────────
def _summary_table(summary_df: pd.DataFrame) -> Table:
    # 금·은 살때/팔때 제외
    df = summary_df[~summary_df["지표"].str.contains("살때|팔때", na=False)]

    col_w = [TBL_W*0.22, TBL_W*0.18, TBL_W*0.11,
             TBL_W*0.15, TBL_W*0.15, TBL_W*0.19]

    headers = ["지표", "최신값", "단위", "전일대비", "등락률(%)", "기준일"]
    header_row = [_img(t, fontsize=10, color="#FFFFFF", max_width_mm=col_w[i]/mm)
                  for i, t in enumerate(headers)]
    rows = [header_row]

    for _, row in df.iterrows():
        pct = row["등락률(%)"]
        if str(pct) == "-":
            pct_img = _img("-", fontsize=11, color="#6B7280")
            chg_img = _img("-", fontsize=11, color="#6B7280")
        else:
            v = float(pct)
            sign = "▲" if v >= 0 else "▼"
            col  = "#065F46" if v >= 0 else "#991B1B"
            pct_img = _img(f"{sign} {abs(v):.2f}%",
                           fontsize=11, color=col, max_width_mm=col_w[4]/mm)
            chg_img = _img(f"{float(row['전일대비']):+.2f}",
                           fontsize=11, color=col, max_width_mm=col_w[3]/mm)

        val = row["최신값"]
        try:
            val_str = (f"{float(val):,.0f}" if float(val) > 999
                       else f"{float(val):,.2f}")
        except Exception:
            val_str = str(val)

        rows.append([
            _img(row["지표"],   fontsize=11, color="#111827", max_width_mm=col_w[0]/mm),
            _img(val_str,       fontsize=11, color="#111827", max_width_mm=col_w[1]/mm),
            _img(row["단위"],   fontsize=10, color="#374151", max_width_mm=col_w[2]/mm),
            chg_img,
            pct_img,
            _img(row["기준일"], fontsize=10, color="#374151", max_width_mm=col_w[5]/mm),
        ])

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  BLUE_DARK),
        ("ALIGN",          (0,0),(-1,-1), "CENTER"),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [BLUE_LIGHT, WHITE]),
        ("GRID",           (0,0),(-1,-1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
    ]))
    return t


# ── 금·은 박스 ────────────────────────────────────────────────────
def _precious_box(summary_df: pd.DataFrame) -> list:
    elements = []

    def get(label):
        r = summary_df[summary_df["지표"] == label]
        return r.iloc[0]["최신값"] if not r.empty else None

    def fmt(v):
        try: return f"{int(float(v)):,}"
        except: return str(v)

    def make_box(title, buy_val, sell_val, unit, date, bg, border):
        rows = [
            # 제목 + 기준일 (오른쪽)
            [_img(title,           fontsize=13, color="#1E3A5F", max_width_mm=TBL_W*0.55/mm),
             _img(f"기준일  {date}", fontsize=10, color="#6B7280", max_width_mm=TBL_W*0.38/mm)],
            # 살때 / 팔때
            [_img(f"살  때     {fmt(buy_val)} 원",
                  fontsize=15, color="#065F46", max_width_mm=TBL_W*0.5/mm),
             _img(f"팔  때     {fmt(sell_val)} 원",
                  fontsize=15, color="#991B1B", max_width_mm=TBL_W*0.5/mm)],
            # 단위
            [_img(f"({unit})", fontsize=9, color="#9CA3AF"),
             Spacer(1,1)],
        ]
        t = Table(rows, colWidths=[TBL_W*0.5, TBL_W*0.5])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("BOX",           (0,0),(-1,-1), 1.5, border),
            ("ALIGN",         (0,0),(-1,-1), "LEFT"),
            ("ALIGN",         (1,0),(1,0),   "RIGHT"),   # 기준일 오른쪽 정렬
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("LINEBELOW",     (0,0),(-1,0),  0.8, border),
        ]))
        return t

    gb = get("금 살때 (10돈)"); gs = get("금 팔때 (10돈)")
    sb = get("은 살때 (1kg)");  ss = get("은 팔때 (1kg)")
    dt = summary_df[summary_df["지표"].str.contains("금 살때", na=False)]
    date = dt.iloc[0]["기준일"] if not dt.empty else "-"

    if gb and gs:
        elements.append(make_box("금  (순금 24K)", gb, gs,
                                 "10돈 기준, 살 때 VAT 포함, 한국금거래소 기준",
                                 date, GOLD_BG, GOLD_BORDER))
    if sb and ss:
        elements.append(Spacer(1, 2*mm))
        elements.append(make_box("은  (순은)", sb, ss,
                                 "1kg 기준, 살 때 VAT 포함, 한국금거래소 기준",
                                 date, SILV_BG, SILV_BORDER))

    elements.append(Spacer(1, 2*mm))
    return elements


# ── 2. AI 변동 요약 ───────────────────────────────────────────────
def _ai_summary_section(summaries: dict, summary_df: pd.DataFrame) -> list:
    elements = []
    elements += _section("2.  지표별 변동 요약")

    if not summaries:
        elements.append(_img(
            "AI 요약을 불러오지 못했습니다. ANTHROPIC_API_KEY를 확인해 주세요.",
            fontsize=12, color="#991B1B"
        ))
        elements.append(Spacer(1, 4*mm))
        return elements

    for i, (name, text) in enumerate(summaries.items()):
        if i > 0:
            elements.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#E2E8F0"),
                spaceBefore=4, spaceAfter=4
            ))

        # 등락 뱃지 + 현재값
        matched = summary_df[summary_df["지표"] == name]
        badge_color = "#374151"
        badge_text  = name
        if not matched.empty:
            try:
                row    = matched.iloc[0]
                pct_f  = float(row["등락률(%)"])
                val    = float(row["최신값"])
                unit   = row["단위"]
                sign   = "▲" if pct_f >= 0 else "▼"
                badge_color = "#065F46" if pct_f >= 0 else "#991B1B"

                # 현재값 포맷
                val_str = (f"{val:,.0f}" if val > 999 else f"{val:,.2f}")

                # "• S&P 500   6,508 pt   ▲ 1.27%"
                badge_text = (f"{name}     "
                              f"{val_str} {unit}     "
                              f"{sign} {abs(pct_f):.2f}%")
            except Exception:
                pass

        # 지표명 + 현재값 + 등락 한 줄
        elements.append(_img(f"• {badge_text}", fontsize=13,
                             color=badge_color, max_width_mm=174))
        # 요약 내용 (넉넉한 크기, 왼쪽 정렬)
        elements.append(Spacer(1, 1*mm))
        elements.append(_img(text, fontsize=12,
                             color="#1F2937", max_width_mm=168))
        elements.append(Spacer(1, 2*mm))

    elements.append(Spacer(1, 4*mm))
    return elements


# ── 3. 차트 그리드 ────────────────────────────────────────────────
def _chart_grid(chart_paths: dict) -> list:
    items = list(chart_paths.items())
    elements = []
    IMG_W = (TBL_W - 4*mm) / 2
    IMG_H = IMG_W * 0.52   # 비율 유지

    for i in range(0, len(items), 2):
        left  = items[i][1]
        right = items[i+1][1] if i+1 < len(items) else None
        cells = [[
            RLImage(left,  width=IMG_W, height=IMG_H),
            RLImage(right, width=IMG_W, height=IMG_H)
            if right else Spacer(IMG_W, IMG_H),
        ]]
        t = Table(cells, colWidths=[IMG_W+2*mm, IMG_W+2*mm])
        t.setStyle(TableStyle([
            ("ALIGN",       (0,0),(-1,-1),"CENTER"),
            ("VALIGN",      (0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0,0),(-1,-1), 1),
            ("RIGHTPADDING",(0,0),(-1,-1), 1),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 4*mm))
    return elements


# ── 페이지 헤더/푸터 ──────────────────────────────────────────────
class _PageDecorator:
    """
    한글 텍스트를 PIL로 이미지 렌더링 후 canvas에 삽입해서 깨짐 방지
    """

    def _draw_kor(self, canvas, text: str, x, y,
                  fontsize: int = 9, color: str = "#6B7280"):
        """PIL로 한글 텍스트를 고해상도로 그려 canvas에 삽입"""
        if not KOR_FONT:
            canvas.setFont("Helvetica", fontsize)
            r = int(color[1:3], 16) / 255
            g = int(color[3:5], 16) / 255
            b = int(color[5:7], 16) / 255
            canvas.setFillColorRGB(r, g, b)
            canvas.drawString(x, y, text)
            return

        RENDER_DPI = 300                        # 고해상도로 렌더링
        px   = int(fontsize * RENDER_DPI / 72)  # pt → px 변환
        font = ImageFont.truetype(KOR_FONT, size=px)
        dummy = Image.new("RGBA", (1, 1))
        bbox  = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0] + 8
        h = bbox[3] - bbox[1] + 8

        img  = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        cr = int(color[1:3], 16)
        cg = int(color[3:5], 16)
        cb = int(color[5:7], 16)
        draw.text((4, 4 - bbox[1]), text, font=font, fill=(cr, cg, cb, 255))

        buf = io.BytesIO()
        img.save(buf, "PNG", dpi=(RENDER_DPI, RENDER_DPI))
        buf.seek(0)

        from reportlab.lib.utils import ImageReader
        img_r = ImageReader(buf)
        # pt 단위 크기 = px * (72 / RENDER_DPI)
        out_w = w * (72.0 / RENDER_DPI)
        out_h = h * (72.0 / RENDER_DPI)
        canvas.drawImage(img_r, x, y - out_h * 0.72,
                         width=out_w, height=out_h,
                         mask="auto")

    def on_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BLUE_MID)
        canvas.setLineWidth(1)
        canvas.line(MARGIN, PAGE_H - 14*mm, PAGE_W - MARGIN, PAGE_H - 14*mm)

        # 한글 헤더 텍스트 — PIL 렌더링
        self._draw_kor(canvas, "경제 지표 리포트",
                       MARGIN, PAGE_H - 10*mm,
                       fontsize=9, color="#6B7280")

        # 날짜는 ASCII라 Helvetica 그대로
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 10.5*mm,
                               datetime.today().strftime("%Y.%m.%d"))

        canvas.line(MARGIN, 13*mm, PAGE_W - MARGIN, 13*mm)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 9*mm, f"- {doc.page} -")
        canvas.restoreState()


# ── 메인 ─────────────────────────────────────────────────────────
def build_pdf(summary_df: pd.DataFrame,
              chart_paths: dict,
              ai_summaries: dict = None,
              output_path: str = "economic_report.pdf"):

    if ai_summaries is None:
        ai_summaries = {}

    deco = _PageDecorator()
    doc  = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=20*mm,   bottomMargin=20*mm,
    )
    story = []

    # ── 날짜 헤더 바 ──────────────────────────────────────────────
    story.append(_date_bar(summary_df))
    story.append(Spacer(1, 2*mm))

    # ── 섹션 1: 지표 요약 ─────────────────────────────────────────
    story += _section("1.  지표 요약")

    us_rows = summary_df[summary_df["지표"].isin(["S&P 500","NASDAQ","다우존스"])]
    kr_rows = summary_df[summary_df["지표"].isin(["KOSPI","KOSDAQ"])]
    us_date = us_rows.iloc[0]["기준일"] if not us_rows.empty else "-"
    kr_date = kr_rows.iloc[0]["기준일"] if not kr_rows.empty else "-"

    if us_date != kr_date:
        date_note = f"미국·금은(국제): {us_date} 종가  |  한국·환율·금은: {kr_date} 기준"
    else:
        date_note = f"기준일: {us_date}"

    story.append(_img(
        f"주가지수·환율의 최신값과 전일 대비 변동입니다.  ({date_note})",
        fontsize=10, color="#374151"
    ))
    story.append(Spacer(1, 2*mm))
    story.append(_summary_table(summary_df))
    story.append(Spacer(1, 3*mm))
    story += _precious_box(summary_df)

    # ── 섹션 2: AI 변동 요약 — 내용 있을 때만 새 페이지 ────────────
    if ai_summaries:
        story.append(PageBreak())
        story += _ai_summary_section(ai_summaries, summary_df)

    # ── 섹션 3: 차트 ─────────────────────────────────────────────
    story.append(PageBreak())
    story += _section("3.  최근 90일 추이")
    story.append(_img(
        "각 지표의 최근 90일간 종가 추이입니다.",
        fontsize=11, color="#374151"
    ))
    story.append(Spacer(1, 5*mm))
    story.extend(_chart_grid(chart_paths))

    # ── 생성 시각 ─────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(_img(
        "생성 시각: " + datetime.now().strftime("%Y-%m-%d %H:%M"),
        fontsize=10, color="#9CA3AF"
    ))

    doc.build(story, onLaterPages=deco.on_page, onFirstPage=deco.on_page)
    print(f"\n[완료] PDF 저장: {output_path}")
    return output_path


# ── PDF → JPG ────────────────────────────────────────────────────
def pdf_to_jpg(pdf_path: str, output_dir: str = None,
               dpi: int = 200, quality: int = 92) -> list:
    from pdf2image import convert_from_path
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    base  = os.path.splitext(os.path.basename(pdf_path))[0]
    imgs  = convert_from_path(pdf_path, dpi=dpi)
    paths = []
    for i, img in enumerate(imgs, 1):
        suffix = "" if len(imgs)==1 else f"_p{i:02d}"
        p = os.path.join(output_dir, f"{base}{suffix}.jpg")
        img.convert("RGB").save(p, "JPEG", quality=quality, optimize=True)
        paths.append(p)
        print(f"  JPG 저장: {p}")
    return paths
