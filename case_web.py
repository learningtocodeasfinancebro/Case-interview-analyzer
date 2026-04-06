#!/usr/bin/env python3
"""
Case Interview Analyzer — Web App (Streamlit)
Run: python3 -m streamlit run ~/Documents/case_web.py
"""

import os
import sys
import json
import tempfile

import streamlit as st
import streamlit.components.v1 as components

# ── Import core logic from case_interview.py ────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from case_interview import (
    SYSTEM_PROMPT,
    analyze_case,
    generate_html,
    extract_pdf_text,
    extract_docx_text,
    PDF_SUPPORT,
    DOCX_SUPPORT,
)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Case Interview Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }

  /* Page background */
  .stApp { background: #f0f2f5; }

  /* Main container width */
  .block-container { max-width: 860px; padding-top: 2rem; }

  /* Header box */
  .app-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
  }
  .app-header h1 {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 6px 0;
  }
  .app-header p {
    font-size: 13px;
    opacity: 0.55;
    margin: 0;
  }

  /* Input card */
  .input-card {
    background: white;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }

  /* Analyze button */
  div.stButton > button {
    background: linear-gradient(135deg, #e94560 0%, #c62828 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 36px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
    width: 100%;
    cursor: pointer;
    margin-top: 8px;
  }
  div.stButton > button:hover {
    opacity: 0.9;
  }

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    font-size: 13px;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🎯 Case Interview Analyzer</h1>
  <p>BCG · Bain · McKinsey Korea &nbsp;·&nbsp; Based on Case in Point (11th Ed.) + 70+ real 기출 transcripts</p>
</div>
""", unsafe_allow_html=True)

# ── API Key ──────────────────────────────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not api_key:
    api_key = st.text_input(
        "🔑 Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get your key at console.anthropic.com",
    )
    if not api_key:
        st.info("API 키를 입력하면 분석을 시작할 수 있어요.")
        st.stop()

# ── Input section ────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📝 텍스트로 입력", "📄 파일 업로드 (PDF / Word)"])

question = ""
display_label = None

with tab1:
    question_text = st.text_area(
        "케이스 질문을 붙여넣어주세요",
        height=200,
        placeholder="예) 국내 편의점 체인이 수익성 악화를 겪고 있습니다. 원인과 개선 방안을 제시해주세요.",
    )
    if question_text.strip():
        question = question_text.strip()

with tab2:
    uploaded = st.file_uploader(
        "PDF 또는 Word 파일을 업로드하세요",
        type=["pdf", "docx"],
        help="pypdf / python-docx 패키지가 필요합니다",
    )
    if uploaded:
        suffix = "." + uploaded.name.split(".")[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        try:
            if suffix == ".docx":
                if not DOCX_SUPPORT:
                    st.error("pip install python-docx 를 먼저 실행해주세요.")
                else:
                    question = extract_docx_text(tmp_path)
                    display_label = f"📄 {uploaded.name}"
            else:
                if not PDF_SUPPORT:
                    st.error("pip install pypdf 를 먼저 실행해주세요.")
                else:
                    question = extract_pdf_text(tmp_path)
                    display_label = f"📄 {uploaded.name}"
            if question:
                st.success(f"파일 읽기 완료: {uploaded.name}")
                with st.expander("추출된 텍스트 미리보기"):
                    st.text(question[:800] + ("..." if len(question) > 800 else ""))
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")
        finally:
            os.unlink(tmp_path)

# ── Analyze button ───────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
analyze = st.button("⚡ 케이스 분석하기", disabled=not question)

# ── Analysis ─────────────────────────────────────────────────────────────────
if analyze and question:
    with st.spinner("Claude가 분석 중입니다... (보통 20~40초 소요)"):
        try:
            data = analyze_case(question, api_key)
        except SystemExit:
            st.error("Claude 응답을 JSON으로 파싱하지 못했습니다. 잠시 후 다시 시도해주세요.")
            st.stop()
        except Exception as e:
            st.error(f"오류 상세: {type(e).__name__}: {e}")
            st.stop()

    html = generate_html(question, data, display_label=display_label)

    st.success("분석 완료! 아래에서 결과를 확인하세요.")

    # Download button
    st.download_button(
        label="💾 HTML 리포트 다운로드",
        data=html.encode("utf-8"),
        file_name="case_analysis.html",
        mime="text/html",
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Render the report inline
    components.html(html, height=5000, scrolling=True)
