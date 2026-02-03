import re
import json
from io import BytesIO

import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


# =========================
# إعدادات الصفحة والواجهة
# =========================
st.set_page_config(page_title="نظام تدقيق الاختبارات - سلطنة عمان", layout="wide")

st.markdown(
    """
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    .report-box { border: 2px solid #007bff; padding: 20px; border-radius: 10px; background-color: #f9f9f9; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🔎 نظام تدقيق الاختبارات (مطابقة البنود والمعايير)")
st.caption("يرفع: الاختبار + وثيقة التقويم + كتاب الطالب، ثم ينتج تقرير Word وفق نموذجك.")


# =========================
# الشريط الجانبي
# =========================
st.sidebar.header("⚙️ إعدادات التدقيق")

api_key = st.sidebar.text_input("مفتاح API (Gemini):", type="password")

subject = st.sidebar.selectbox("المادة:", ["فيزياء", "علوم"], index=0)
semester = st.sidebar.selectbox("الفصل الدراسي:", ["الأول", "الثاني"], index=1)
grade = st.sidebar.selectbox("الصف:", ["5", "6", "7", "8", "9", "10", "11", "12"], index=7)
exam_type = st.sidebar.selectbox("نوع الاختبار:", ["قصير", "استقصائي", "نهائي"], index=0)
pages_range = st.sidebar.text_input("نطاق الصفحات (مثال 77-97):", value="")


# =========================
# رفع الملفات
# =========================
col1, col2, col3 = st.columns(3)
with col1:
    file_test = st.file_uploader("1) ملف الاختبار (PDF)", type="pdf")
with col2:
    file_policy = st.file_uploader("2) وثيقة التقويم (PDF)", type="pdf")
with col3:
    file_book = st.file_uploader("3) كتاب الطالب (PDF)", type="pdf")


# =========================
# أدوات مساعدة
# =========================
def _normalize_dash(s: str) -> str:
    return re.sub(r"[–—−]", "-", (s or "").strip())

def _parse_page_range(rng: str):
    """
    يقبل: "7-10" أو "7 – 10" أو "7 — 10"
    يرجع: (start, end) 1-indexed أو None
    """
    if not rng or not rng.strip():
        return None
    s = _normalize_dash(rng)
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", s)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    if a <= 0 or b <= 0:
        return None
    if a > b:
        a, b = b, a
    return (a, b)

@st.cache_data(show_spinner=False)
def extract_text_from_pdf(pdf_bytes: bytes, page_range_1idx=None) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    start0, end0 = 0, doc.page_count - 1

    if page_range_1idx:
        a, b = page_range_1idx
        start0 = max(0, a - 1)
        end0 = min(doc.page_count - 1, b - 1)

    parts = []
    for i in range(start0, end0 + 1):
        page = doc.load_page(i)
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts).strip()

def safe_clip(text: str, max_chars: int) -> str:
    text = text or ""
    return text[:max_chars]

def pick_model(preferred="gemini-2.5-flash"):
    """
    يختار نموذجًا متاحًا تلقائيًا يدعم generateContent لتفادي 404
    """
    try:
        models = [
            m for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]
        names = [m.name for m in models]  # غالبًا بصيغة models/...

        pref = preferred if preferred.startswith("models/") else f"models/{preferred}"
        if pref in names:
            return genai.GenerativeModel(pref), pref

        for n in names:
            if "flash" in n and "preview" not in n:
                return genai.GenerativeModel(n), n

        return genai.GenerativeModel(names[0]), names[0]
    except Exception:
        # fallback ثابت (قد يعمل حسب المفتاح)
        fallback = "models/gemini-2.5-flash"
        return genai.GenerativeModel(fallback), fallback

def _extract_json(text: str):
    """
    يحاول استخراج JSON حتى لو رجعه النموذج مع نص إضافي.
    """
    if not text:
        raise ValueError("رد فارغ من النموذج")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", ""*
