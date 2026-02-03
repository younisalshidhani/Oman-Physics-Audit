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
    .report-box { border: 2px solid #007bff; padding: 16px; border-radius: 10px; background-color: #f9f9f9; }
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

# ✅ تم إرجاع أحياء + كيمياء
subject = st.sidebar.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"], index=0)

semester = st.sidebar.selectbox("الفصل الدراسي:", ["الأول", "الثاني"], index=1)

# ✅ فقط الصفين 11 و 12
grade = st.sidebar.selectbox("الصف:", ["11", "12"], index=1)

# ✅ فقط قصير واستقصائي
exam_type = st.sidebar.selectbox("نوع الاختبار:", ["قصير", "استقصائي"], index=0)

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
    return (text or "")[:max_chars]

def strip_control_chars(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)

def pick_model(preferred="gemini-2.5-flash"):
    models = [
        m for m in genai.list_models()
        if "generateContent" in getattr(m, "supported_generation_methods", [])
    ]
    names = [m.name for m in models]  # models/...

    pref = preferred if preferred.startswith("models/") else f"models/{preferred}"
    if pref in names:
        return genai.GenerativeModel(pref), pref

    for n in names:
        if "flash" in n and "preview" not in n:
            return genai.GenerativeModel(n), n

    return genai.GenerativeModel(names[0]), names[0]

def repair_json_text(s: str) -> str:
    """
    إصلاحات شائعة: فواصل عربية، اقتباسات ذكية، مفقودات فواصل بين الأسطر.
    """
    s = strip_control_chars(s).strip()

    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]

    # اقتباسات ذكية → "
    s = s.replace("“", '"').replace("”", '"').replace("„", '"').replace("’", "'").replace("‘", "'")

    # الفاصلة العربية → الإنجليزية
    s = s.replace("،", ",")

    # إزالة فاصلة زائدة قبل إغلاق } أو ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # إدخال فاصلة مفقودة بين سطر ينتهي بقيمة وسطر يبدأ بمفتاح جديد
    s = re.sub(r'(")\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(\d)\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(})\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(])\s*\n\s*(")', r'\1,\n\2', s)

    return s

def parse_json_robust(raw: str) -> dict:
    """
    يحاول parse مباشر، ثم إصلاح، ثم parse.
    """
    if not raw:
        raise ValueError("رد فارغ من النموذج")

    raw = strip_control_chars(raw)

    # محاولة مباشرة
    try:
        return json.loads(raw)
    except Exception:
        pass

    fixed = repair_json_text(raw)
    return json.loads(fixed)

def _rtl_paragraph(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

def _rtl_cell(cell):
    for p in cell.paragraphs:
        _rtl_paragraph(p)

def exam_label_ar(exam_type_value: str) -> str:
    return "القصيرة" if exam_type_value == "قصير" else "الاستقصائية"

def build_report_docx(data: dict, exam_label: str) -> bytes:
    doc = Document()

    title = f"نموذج تقرير تطبيق الذكاء الاصطناعي لتحليل الاختبارات {exam_label}"
    p = doc.add_paragraph(title)
    _rtl_paragraph(p)
    doc.add_paragraph("")

    # جدول تحليل المفردات الامتحانية
    p = doc.add_paragraph("جدول تحليل المفردات الامتحانية")
    _rtl_paragraph(p)

    headers = [
        "المفردة",
        "الهدف التعليمي",
        "هدف التقويم (A01,A02)",
        "الدرجة",
        "نوع الملاحظة (صياغة، علمية، فنية تشمل الرسم)",
        "الملاحظة",
        "التعديل",
    ]

    items = data.get("items", []) or []
    rows_needed = max(1, len(items)) + 1

    t1 = doc.add_table(rows=rows_needed, cols=len(headers))
    t1.style = "Table Grid"
    t1.alignment = WD_TABLE_ALIGNMENT.RIGHT

    for j, h in enumerate(headers):
        t1.cell(0, j).text = h
        _rtl_cell(t1.cell(0, j))

    for i, item in enumerate(items, start=1):
        t1.cell(i, 0).text = str(item.get("mufrada", "-")).strip()
        t1.cell(i, 1).text = str(item.get("learning_objective", "-")).strip()
        t1.cell(i, 2).text = str(item.get("assessment_objective", "-")).strip()
        t1.cell(i, 3).text = str(item.get("marks", "-")).strip()
        t1.cell(i, 4).text = str(item.get("note_type", "-")).strip()
        t1.cell(i, 5).text = str(item.get("note", "-")).strip()
        t1.cell(i, 6).text = str(item.get("edit", "-")).strip()
        for j in range(len(headers)):
            _rtl_cell(t1.cell(i, j))

    doc.add_paragraph("")

    # الجدول العامل
    p = doc.add_paragraph(f"الجدول العامل للاختبار {exam_label}")
    _rtl_paragraph(p)

    wt = data.get("working_table", {}) or {}

    rows_order = [
        "عدد المفردات",
        "عدد الدروس",
        "درجات أهداف التقويم (A01,A02)",
        "هل توجد مفردة طويلة الإجابة؟",
        "هل توجد مفردتان اختيار من متعدد؟",
        "هل مفردات الاختيار من متعدد تحتوي على (إجابات خاطئة) مشتتات منطقية؟",
        "هل صياغة المفردات وحجم ونوع الخط واضح للقراءة؟",
        "هل الأشكال والرسومات واضحة؟",
    ]

    t2 = doc.add_table(rows=1 + len(rows_order), cols=3)
    t2.style = "Table Grid"
    t2.alignment = WD_TABLE_ALIGNMENT.RIGHT

    t2.cell(0, 0).text = "البند"
    t2.cell(0, 1).text = "العدد / الدرجات – نعم / لا"
    t2.cell(0, 2).text = "مطابق / غير مطابق"
    for j in range(3):
        _rtl_cell(t2.cell(0, j))

    for i, row_label in enumerate(rows_order, start=1):
        t2.cell(i, 0).text = row_label
        entry = wt.get(row_label, {}) or {}
        t2.cell(i, 1).text = str(entry.get("value", "-")).strip()
        t2.cell(i, 2).text = str(entry.get("status", "-")).strip()
        for j in range(3):
            _rtl_cell(t2.cell(i, j))

    # التقدير العام
    p = doc.add_paragraph(f"التقدير العام للاختبار {exam_label}")
    _rtl_paragraph(p)

    overall = data.get("overall", {}) or {}
    summary = str(overall.get("summary", "-")).strip()
    percent = overall.get("percent_match", "")

    text = summary
    if percent != "" and percent is not None:
        text = f"{summary}\nنسبة المطابقة للمعايير: {percent}%"
    p = doc.add_paragraph(text.strip())
    _rtl_paragraph(p)

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def generate_json(model, prompt: str, tries: int = 3):
    """
    محاولة إخراج JSON صالح مع إعادة تصحيح تلقائية عند الفشل.
    """
    last_raw = ""
    last_err = ""

    base_cfg = {
        "temperature": 0.0,
        "top_p": 1.0,
        "max_output_tokens": 8192,
    }

    for attempt in range(1, tries + 1):
        cfg = dict(base_cfg)
        if attempt == 1:
            cfg["response_mime_type"] = "application/json"

        try:
            resp = model.generate_content(prompt, generation_config=cfg)
        except TypeError:
            cfg.pop("response_mime_type", None)
            resp = model.generate_content(prompt, generation_config=cfg)

        last_raw = getattr(resp, "text", "") or ""

        try:
            return parse_json_robust(last_raw), last_raw
        except Exception as e:
            last_err = str(e)
            snippet = safe_clip(last_raw, 20000)
            prompt = f"""
أصلح JSON التالي ليصبح JSON صالح 100% (ولا تكتب أي شيء غير JSON).
تعليمات صارمة:
- لا تستخدم أي علامة اقتباس مزدوجة داخل القيم. إذا ظهرت " داخل قيمة استبدلها بـ '
- لا تستخدم أسطر جديدة داخل القيم
- استخدم الفاصلة الإنجليزية , فقط
- لا تستخدم الفاصلة العربية ،
- نفس المفاتيح تمامًا دون تغيير

JSON غير صالح:
{snippet}
"""

    raise ValueError(f"فشل توليد JSON صالح. آخر خطأ: {last_err}")


# =========================
# التنفيذ
# =========================
run = st.button("🚀 بدء التحليل الشامل")

if run:
    if not api_key:
        st.error("الرجاء إدخال مفتاح API أولًا.")
        st.stop()

    if not file_test or not file_policy or not file_book:
        st.error("الرجاء رفع الملفات الثلاثة: الاختبار + وثيقة التقويم + كتاب الطالب.")
        st.stop()

    try:
        genai.configure(api_key=api_key)
        model, model_name = pick_model()
        st.sidebar.success(f"✅ النموذج المختار: {model_name}")

        pr = _parse_page_range(pages_range)
        exam_label = exam_label_ar(exam_type)

        with st.spinner("جاري قراءة الملفات وتحليل الاختبار..."):
            # تقليل القص لتقليل احتمالية التقطيع/الـ truncation في الرد
            txt_test = safe_clip(extract_text_from_pdf(file_test.getvalue(), pr), 50000)
            txt_policy = safe_clip(extract_text_from_pdf(file_policy.getvalue(), pr), 60000)
            txt_book = safe_clip(extract_text_from_pdf(file_book.getvalue(), pr), 30000)

            prompt = f"""
أنت خبير تقويم وتحليل اختبارات وفق معايير سلطنة عمان.
المطلوب: إخراج JSON فقط دون أي نص إضافي.

قيود صارمة جدًا:
- JSON واحد فقط يبدأ بـ {{ وينتهي بـ }}
- استخدم علامات اقتباس مزدوجة " للمفاتيح فقط.
- لا تضع " داخل القيم إطلاقًا. استبدلها بـ ' عند الحاجة.
- لا تضع أسطر جديدة داخل القيم.
- القيم قصيرة (بحد أقصى 120 حرفًا لكل حقل نصي).
- المطابقة واحد لواحد: لكل مفردة اختر بند/هدف واحد فقط من وثيقة التقويم.
- percent_match رقم صحيح من 0 إلى 100.

صيغة JSON المطلوبة:
{{
  "items": [
    {{
      "mufrada": "نص المفردة/السؤال",
      "learning_objective": "البند/المعيار الأقرب من وثيقة التقويم",
      "assessment_objective": "A01 أو A02 أو A01/A02",
      "marks": "درجة المفردة",
      "note_type": "صياغة أو علمية أو فنية تشمل الرسم أو لا توجد",
      "note": "الملاحظة المختصرة",
      "edit": "التعديل المقترح المختصر"
    }}
  ],
  "working_table": {{
    "عدد المفردات": {{"value": "...", "status": "مطابق/غير مطابق"}},
    "عدد الدروس": {{"value": "...", "status": "مطابق/غير مطابق"}},
    "درجات أهداف التقويم (A01,A02)": {{"value": "...", "status": "مطابق/غير مطابق"}},
    "هل توجد مفردة طويلة الإجابة؟": {{"value": "نعم/لا + رقم السؤال إن وجد", "status": "مطابق/غير مطابق"}},
    "هل توجد مفردتان اختيار من متعدد؟": {{"value": "نعم/لا + رقم السؤال إن وجد", "status": "مطابق/غير مطابق"}},
    "هل مفردات الاختيار من متعدد تحتوي على (إجابات خاطئة) مشتتات منطقية؟": {{"value": "نعم/لا + ملاحظة", "status": "مطابق/غير مطابق"}},
    "هل صياغة المفردات وحجم ونوع الخط واضح للقراءة؟": {{"value": "نعم/لا + ملاحظة", "status": "مطابق/غير مطابق"}},
    "هل الأشكال والرسومات واضحة؟": {{"value": "نعم/لا + ملاحظة", "status": "مطابق/غير مطابق"}}
  }},
  "overall": {{
    "summary": "تقدير عام مختصر 3-5 أسطر",
    "percent_match": 0
  }}
}}

البيانات:
- المادة: {subject}
- الصف: {grade}
- الفصل: {semester}
- نوع الاختبار: {exam_type}

نص الاختبار:
{txt_test}

نص وثيقة التقويم:
{txt_policy}

نص كتاب الطالب:
{txt_book}
"""

            data, raw = generate_json(model, prompt, tries=3)
            docx_bytes = build_report_docx(data, exam_label)

        st.markdown("---")
        st.subheader("📋 ملخص التقدير العام:")
        overall = (data.get("overall", {}) or {})
        st.markdown(f'<div class="report-box">{overall.get("summary","-")}</div>', unsafe_allow_html=True)

        st.download_button(
            "📥 تحميل التقرير (Word)",
            data=docx_bytes,
            file_name="Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with st.expander("عرض الناتج الخام من Gemini (للتشخيص عند الحاجة)"):
            st.text(raw)

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
        st.info("إذا استمرت المشكلة: قلّل نطاق الصفحات (مثلاً 5-10 صفحات) لأن الرد قد يتقطع ويكسر JSON.")
