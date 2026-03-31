"""
app.py
Streamlit 웹앱 — 경제 지표 PDF/JPG 리포트 생성기
"""

import streamlit as st
import os
import io
import zipfile
import tempfile
from datetime import datetime

st.set_page_config(
    page_title="경제 지표 리포트",
    page_icon="📊",
    layout="centered",
)

st.markdown("## 📊 경제 지표 리포트")
st.markdown("미국·한국 | 주가지수·환율·금·은 | 실시간 데이터")
st.divider()

# ── 설정 (기본값 먼저 지정) ─────────────────────────────────────
days     = 90
save_pdf = True
save_jpg = False
dpi      = 200
quality  = 92
use_ai   = True
api_key  = ""

with st.expander("⚙️ 설정", expanded=False):
    days     = st.slider("데이터 기간 (일)", 30, 365, 90, 30)
    col_fmt1, col_fmt2 = st.columns(2)
    with col_fmt1:
        save_pdf = st.checkbox("PDF 다운로드", value=True)
    with col_fmt2:
        save_jpg = st.checkbox("JPG 다운로드", value=False)
    if save_jpg:
        dpi     = st.select_slider("JPG 해상도 (DPI)", [100, 150, 200, 300], value=200)
        quality = st.slider("JPG 품질", 60, 100, 92)
    use_ai  = st.toggle("AI 변동 요약 사용", value=True)
    if use_ai:
        api_key = st.text_input(
            "Anthropic API Key", type="password",
            help="ANTHROPIC_API_KEY 환경변수로도 설정 가능"
        )

# ── 지표 미리보기 ────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.markdown("**📈 주가지수**")
    for idx in ["S&P 500", "NASDAQ", "다우존스", "KOSPI", "KOSDAQ"]:
        st.write(f"• {idx}")
with col2:
    st.markdown("**💱 환율·귀금속**")
    st.write("• USD/KRW")
    st.write("• 금 살때/팔때 (키즈맘)")
    st.write("• 은 살때/팔때 (키즈맘)")
    st.write(f"📅 최근 **{days}일** 기준")

st.markdown("")
generate = st.button("📄 리포트 생성", type="primary", use_container_width=True)

if generate:
    if not save_pdf and not save_jpg:
        st.warning("PDF 또는 JPG 중 하나 이상 선택해 주세요.")
        st.stop()

    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    # 1. 데이터 수집
    with st.spinner("📡 데이터 수집 중..."):
        try:
            from fetch_data import fetch_all, latest_summary
            data, precious = fetch_all(period_days=days)
            if not data:
                st.error("❌ 데이터를 가져오지 못했습니다.")
                st.stop()
            summary = latest_summary(data, precious)
        except Exception as e:
            st.error(f"❌ 데이터 수집 오류: {e}")
            st.stop()

    # 2. AI 요약
    ai_summaries = {}
    if use_ai and (api_key or os.environ.get("ANTHROPIC_API_KEY")):
        with st.spinner("🤖 AI 변동 요약 생성 중..."):
            try:
                from ai_summary import get_market_summaries
                ai_summaries = get_market_summaries(summary)
            except Exception as e:
                st.warning(f"AI 요약 실패 (건너뜀): {e}")

    # 3. 차트 + PDF + JPG
    with st.spinner("📊 리포트 생성 중..."):
        try:
            from make_charts import make_all_charts
            from generate_report import build_pdf, pdf_to_jpg

            with tempfile.TemporaryDirectory() as tmpdir:
                chart_paths = make_all_charts(
                    data, output_dir=tmpdir, summary_df=summary
                )
                today_str = datetime.today().strftime("%Y%m%d")
                pdf_name  = f"economic_report_{today_str}.pdf"
                pdf_path  = os.path.join(tmpdir, pdf_name)

                build_pdf(summary, chart_paths,
                          ai_summaries=ai_summaries,
                          output_path=pdf_path)

                # PDF 바이트
                pdf_bytes = None
                if save_pdf:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()

                # JPG 바이트
                jpg_data = {}
                if save_jpg:
                    jpg_dir   = os.path.join(tmpdir, "jpg")
                    jpg_paths = pdf_to_jpg(pdf_path, output_dir=jpg_dir,
                                           dpi=dpi, quality=quality)
                    for jp in jpg_paths:
                        with open(jp, "rb") as f:
                            jpg_data[os.path.basename(jp)] = f.read()

        except Exception as e:
            st.error(f"❌ 리포트 생성 오류: {e}")
            st.stop()

    # ── 결과 표시 ────────────────────────────────────────────────
    st.success("✅ 리포트 생성 완료!")

    # 요약 표
    st.markdown("### 📋 지표 요약")

    def fmt_pct(x):
        try:
            v = float(x)
            return f"▲ {v:.2f}%" if v >= 0 else f"▼ {abs(v):.2f}%"
        except Exception:
            return "-"

    def fmt_chg(x):
        try:
            v = float(x)
            return f"{v:+.2f}"
        except Exception:
            return "-"

    def fmt_val(x):
        try:
            v = float(x)
            return f"{v:,.0f}" if v > 999 else f"{v:,.2f}"
        except Exception:
            return str(x)

    df_disp = summary[~summary["지표"].str.contains("살때|팔때", na=False)].copy()
    df_disp["최신값"]    = df_disp["최신값"].apply(fmt_val)
    df_disp["전일대비"]  = df_disp["전일대비"].apply(fmt_chg)
    df_disp["등락률(%)"] = df_disp["등락률(%)"].apply(fmt_pct)
    st.dataframe(df_disp[["지표","최신값","단위","전일대비","등락률(%)","기준일"]],
                 use_container_width=True, hide_index=True)

    # 다운로드 버튼
    st.markdown("### ⬇️ 다운로드")
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        if save_pdf and pdf_bytes:
            st.download_button(
                label="📄 PDF 다운로드",
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

    with dl_col2:
        if save_jpg and jpg_data:
            if len(jpg_data) == 1:
                fname, fbytes = next(iter(jpg_data.items()))
                st.download_button(
                    label="🖼️ JPG 다운로드",
                    data=fbytes,
                    file_name=fname,
                    mime="image/jpeg",
                    use_container_width=True,
                )
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, fbytes in jpg_data.items():
                        zf.writestr(fname, fbytes)
                zip_buf.seek(0)
                zip_name = f"economic_report_{today_str}_jpg.zip"
                st.download_button(
                    label=f"🖼️ JPG 다운로드 ({len(jpg_data)}장 ZIP)",
                    data=zip_buf.getvalue(),
                    file_name=zip_name,
                    mime="application/zip",
                    use_container_width=True,
                )

st.divider()
st.caption("데이터 출처: Yahoo Finance · 키즈맘(금시세) | 투자 조언이 아닙니다.")
