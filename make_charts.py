"""
make_charts.py
모바일·고령 가독성 개선:
  - 차트 높이 확대
  - 폰트 사이즈 업
  - 굵은 선, 강한 색상 대비
  - 헤더에 현재가·등락률 크게 표시
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

try:
    import matplotlib.font_manager as fm
    # Streamlit Cloud(리눅스) + 로컬 환경 모두 대응
    for fp in [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    ]:
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)

    korean_fonts = [f.name for f in fm.fontManager.ttflist
                    if any(k in f.name for k in
                           ["Nanum","Malgun","malgun","AppleGothic",
                            "NotoSansCJK","Noto Sans CJK","Gulim","Batang"])]
    plt.rcParams["font.family"] = korean_fonts[0] if korean_fonts else "DejaVu Sans"
except Exception:
    plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "S&P 500":   "#1D4ED8",
    "NASDAQ":    "#6D28D9",
    "다우존스":  "#0369A1",
    "KOSPI":     "#B91C1C",
    "KOSDAQ":    "#C2410C",
    "USD/KRW":   "#065F46",
    "금 (국제)": "#B45309",
    "은 (국제)": "#475569",
}
DEFAULT_COLOR = "#374151"


def plot_single(name: str, df: pd.DataFrame, output_dir: str,
                summary_row: dict = None) -> str:
    color = COLORS.get(name, DEFAULT_COLOR)

    # 높이를 넉넉하게
    fig, ax = plt.subplots(figsize=(8, 4.2))
    fig.patch.set_facecolor("white")

    # ── 헤더 영역 ─────────────────────────────────────────────────
    if summary_row:
        try:
            val = float(summary_row["최신값"])
            chg = float(summary_row["전일대비"])
            pct = float(summary_row["등락률(%)"])
            sign    = "▲" if pct >= 0 else "▼"
            chg_col = "#059669" if pct >= 0 else "#DC2626"
            val_str = f"{val:,.2f}" if val < 1000 else f"{val:,.0f}"
            pct_str = f"{sign} {abs(pct):.2f}%  ({'+' if chg>=0 else ''}{chg:,.2f})"

            # 지표명 — 크고 굵게
            ax.text(0.0, 1.20, name,
                    transform=ax.transAxes,
                    fontsize=14, fontweight="bold",
                    color="#1E3A5F", va="bottom", ha="left")
            # 현재가
            ax.text(0.0, 1.08, val_str,
                    transform=ax.transAxes,
                    fontsize=13, fontweight="bold",
                    color="#111827", va="bottom", ha="left")
            # 등락
            ax.text(0.38, 1.08, pct_str,
                    transform=ax.transAxes,
                    fontsize=11, fontweight="bold",
                    color=chg_col, va="bottom", ha="left")
        except Exception:
            ax.set_title(name, fontsize=14, fontweight="bold",
                         loc="left", color="#1E3A5F", pad=10)
    else:
        ax.set_title(name, fontsize=14, fontweight="bold",
                     loc="left", color="#1E3A5F", pad=10)

    # ── 라인 차트 ────────────────────────────────────────────────
    ax.plot(df.index, df["close"],
            color=color, linewidth=2.5, zorder=3)
    ax.fill_between(df.index, df["close"], df["close"].min(),
                    alpha=0.10, color=color)

    # 최근값 강조점
    ax.scatter(df.index[-1], df["close"].iloc[-1],
               color=color, s=70, zorder=5, linewidths=0)

    # 축 포맷 — 글씨 크게
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.tick_params(axis="both", labelsize=9)
    plt.xticks(rotation=30, ha="right")

    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#D1D5DB")
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#9CA3AF")
    ax.set_facecolor("#FAFAFA")

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    safe = name.replace("/","_").replace(" ","_")
    path = os.path.join(output_dir, f"{safe}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def make_all_charts(data: dict, output_dir: str = "charts",
                    summary_df=None) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for name, df in data.items():
        if len(df) < 2:
            continue
        row = None
        if summary_df is not None:
            m = summary_df[summary_df["지표"] == name]
            if not m.empty:
                row = m.iloc[0].to_dict()
        path = plot_single(name, df, output_dir, summary_row=row)
        paths[name] = path
        print(f"  차트 저장: {path}")
    return paths
