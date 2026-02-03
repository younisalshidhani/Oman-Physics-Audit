import re
import json
from io import BytesIO
from typing import List, Dict, Tuple

import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

try:
    from PIL import Image
except Exception:
    Image = None


# =========================
# واجهة
# =========================
st.set_page_config(page_title="نظام تدقيق الاختبارات - سلطنة عمان", layout="wide")

st.markdown(
    """
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }

    .report-box { border: 2px solid #007bff; padding: 14px; border-radius: 10px; background-color: #f9f9f9; }
    .tbl { width:100%; border-collapse:collapse; direction:rtl; }
    .tbl th, .tbl td { border:1px solid #ddd; padding:8px; vertical-align:top; text-align:right; }
    .tbl th { background:#f1f1f1; font-weight:700; }
    .muted { color:#666; font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🔎 نظام تدقيق الاختبارات (مطابقة البنود والمعايير)")
st.caption("يرفع: الاختبار + وثيقة التقويم + كتاب الطالب، ثم يعرض التقرير داخل الصفحة وفق نموذجك، مع خيار تنزيل Word.")


# =========================
# إعدادات جانبية
# =========================
st.sidebar.header("⚙️ إعدادات التدقيق")
api_key = st.sidebar.text_input("مفتاح API (Gemini):", type="password")

subject = st.sidebar.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"], index=0)
semester = st.sidebar.selectbox("الفصل الدراسي:", ["الأول", "الثاني"], index=1)
grade = st.sidebar.selectbox("الصف:", ["11", "12"], index=1)
exam_type = st.sidebar.selectbox("نوع الاختبار:", ["قصير", "استقصائي"], index=0)

# نطاق الصفحات خاص بكتاب الطالب فقط
pages_range = st.sidebar.text_input("نطاق صفحات كتاب الطالب (مثال 77-97):", value="")


# =========================
# تعريفات أهداف التقويم الرسمية
# =========================
A01_DEFINITION = """
هدف التقويم الأول (A01): المعرفة والفهم.
يقيس تذكر وفهم المفردات والمفاهيم والحقائق العلمية والإجراءات المرتبطة بها، وتفسيرها أو توضيحها بصورة مبسطة.
يمثل ذلك: المعطيات والحقائق والقوانين والتعريفات والمفاهيم والنظريات العلمية، الرموز والوحدات والصيغ والمصطلحات العلمية،
استخدام الأشكال التخطيطية/الرسومات الواضحة، الظواهر والأنماط والعلاقات، خواص المواد، استخدام الأجهزة العلمية، الكميات العلمية وقياسها.

ويتطلب بعض المهارات الحسابية مثل:
- إجراء عمليات حسابية ذات الخطوة الواحدة.
- إجراء تعويض بسيط للأرقام في صيغة يتم تذكرها أو تقديمها.
- إعادة ترتيب بسيطة/معالجة بسيطة للصيغ أو البيانات أو الأرقام المحددة.
"""

A02_DEFINITION = """
هدف التقويم الثاني (A02): التطبيق والتحليل والتقييم.
يعتمد على اختبار المعلومات غير المألوفة لدى الطلبة، بما يتطلب تطبيق المعرفة بطريقة منطقية واستنتاجية،
ويُتوقع أن يطلب تحليل البيانات وحل المشكلات أو تقييمها، وقد يصل لمستوى أعمق من التفكير النقدي.

يمثل ذلك: عرض/تفسير البيانات في شكل مرئي (جداول/رسومات/صور/مخططات/تمثيلات بيانية)،
جمع وتنظيم البيانات وتقديمها بصورة علمية، تحديد الأنماط والاتجاهات واستخلاص النتائج،
إجراء تحقيقات/تجارب ودعم الفرضيات وتقويم المعلومات، ربط المعرفة بسياقات غير مألوفة،
شرح الأحداث والظواهر والأنماط والعلاقات تفسيرًا سببيًا، استخدام المخططات/النماذج لإثبات المفهوم،
حساب ومعالجة البيانات العددية (خصوصًا متعددة الخطوات)، حل المشكلات.
"""


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
# أدوات PDF + نص + JSON
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
def extract_text_from_pdf_textonly(pdf_bytes: bytes, page_range_1idx=None) -> str:
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

def repair_json_text(s: str) -> str:
    s = strip_control_chars(s).strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]

    s = s.replace("“", '"').replace("”", '"').replace("„", '"').replace("’", "'").replace("‘", "'")
    s = s.replace("،", ",")
    s = re.sub(r",\s*([}\]])", r"\1", s)

    s = re.sub(r'(")\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(\d)\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(})\s*\n\s*(")', r'\1,\n\2', s)
    s = re.sub(r'(])\s*\n\s*(")', r'\1,\n\2', s)
    return s

def parse_json_robust(raw: str) -> dict:
    if not raw:
        raise ValueError("رد فارغ من النموذج")
    raw = strip_control_chars(raw)
    try:
        return json.loads(raw)
    except Exception:
        fixed = repair_json_text(raw)
        return json.loads(fixed)


# =========================
# اختيار موديل (لتفادي 404)
# =========================
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


# =========================
# OCR عبر Gemini (عند فشل استخراج النص أو كان النص غير مفيد)
# =========================
def _page_indices(doc, page_range_1idx):
    start0, end0 = 0, doc.page_count - 1
    if page_range_1idx:
        a, b = page_range_1idx
        start0 = max(0, a - 1)
        end0 = min(doc.page_count - 1, b - 1)
    return list(range(start0, end0 + 1))

def _is_text_meaningful(txt: str) -> bool:
    if not txt:
        return False
    t = strip_control_chars(txt)
    if len(t.strip()) < 300:
        return False

    ar = len(re.findall(r"[\u0600-\u06FF]", t))
    dg = len(re.findall(r"\d", t))

    if ar < 120 and dg < 30:
        return False

    has_qmark = "؟" in t or "?" in t
    has_numbering = bool(re.search(r"(^|\n)\s*\d+\s*[-.)]", t))
    has_keyword = bool(re.search(r"(سؤال|اختر|أجب|علل|فسر|احسب|اوجد)", t))
    return has_qmark or has_numbering or has_keyword or (ar > 300)

def ocr_pdf_with_gemini(model, pdf_bytes: bytes, page_range_1idx=None, max_pages: int = 25) -> str:
    if Image is None:
        raise RuntimeError("Pillow غير متوفر. أضف pillow إلى requirements.txt")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = _page_indices(doc, page_range_1idx)

    if len(pages) > max_pages:
        pages = pages[:max_pages]

    out_parts = []
    ocr_prompt = (
        "استخرج النص الظاهر في الصورة بدقة عالية (عربي/إنجليزي/أرقام/رموز). "
        "اكتب النص فقط كما هو دون إعادة صياغة. "
        "حافظ على ترتيب السطور. "
        "لا تضف أي كلمات غير موجودة."
    )

    for pno in pages:
        page = doc.load_page(pno)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        png_bytes = pix.tobytes("png")
        img = Image.open(BytesIO(png_bytes))

        resp = model.generate_content(
            [ocr_prompt, img],
            generation_config={"temperature": 0.0, "top_p": 1.0, "max_output_tokens": 2048},
        )
        txt = (getattr(resp, "text", "") or "").strip()
        if txt:
            out_parts.append(txt)

    doc.close()
    return "\n\n".join(out_parts).strip()

def extract_text_auto(model, pdf_bytes: bytes, page_range_1idx=None) -> Tuple[str, str]:
    txt = extract_text_from_pdf_textonly(pdf_bytes, page_range_1idx)
    if _is_text_meaningful(txt):
        return txt, "text"

    txt_ocr = ocr_pdf_with_gemini(model, pdf_bytes, page_range_1idx, max_pages=25)
    if txt_ocr.strip():
        return txt_ocr, "ocr"

    return txt, "text"


# =========================
# استرجاع سياق من وثيقة التقويم/الكتاب
# =========================
_ARABIC_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")

def norm_ar(s: str) -> str:
    s = s or ""
    s = _ARABIC_DIACRITICS.sub("", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 250) -> List[str]:
    text = text or ""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        j = min(len(text), i + chunk_size)
        chunks.append(text[i:j])
        i = max(j - overlap, i + 1)
    return chunks

def score_overlap(query: str, chunk: str) -> float:
    q = set(norm_ar(query).split())
    c = set(norm_ar(chunk).split())
    if not q or not c:
        return 0.0
    inter = len(q & c)
    return inter / (len(q) + 1e-9)

def top_k_chunks(query: str, text: str, k: int = 4) -> List[str]:
    chunks = chunk_text(text, chunk_size=1400, overlap=250)
    scored = sorted(((score_overlap(query, ch), ch) for ch in chunks), key=lambda x: x[0], reverse=True)
    best = [ch for sc, ch in scored[:k] if sc > 0]
    return best if best else (chunks[:k] if chunks else [])


# =========================
# مرشّح أولي A01/A02
# =========================
A02_TRIGGERS = [
    "استنتج", "حلل", "قارن", "علل", "فسر", "برر", "ناقش", "اثبت", "برهن",
    "من الرسم", "من الجدول", "ارسم", "مثل بيانيا", "منحنى", "رسم بياني", "مخطط", "بيانات",
    "تجربة", "تحقيق", "استقصاء", "صمم", "اقترح", "توقع", "استخلص", "فسر النتائج",
    "متعددة", "خطوات", "تقييم", "سياق غير مألوف"
]
A01_TRIGGERS = [
    "عرف", "اذكر", "عدد", "سم", "ما المقصود", "ما هو", "حدد", "صف", "وضح", "اكتب", "بين معنى",
    "قانون", "وحدة", "رمز", "مصطلح", "تعريف"
]

def heuristic_assessment_objective(item_text: str) -> str:
    t = norm_ar(item_text)

    for w in A02_TRIGGERS:
        if norm_ar(w) in t:
            return "A02"

    for w in A01_TRIGGERS:
        if norm_ar(w) in t:
            return "A01"

    if re.search(r"(من الرسم|من الجدول|بيانات|منحنى|مخطط)", item_text):
        return "A02"

    return "A01"


# =========================
# LLM: توليد JSON + تصحيح
# =========================
def generate_json(model, prompt: str, tries: int = 3) -> Tuple[dict, str]:
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
            snippet = safe_clip(last_raw, 25000)
            prompt = f"""
أصلح JSON التالي ليصبح JSON صالح 100% ولا تكتب أي شيء غير JSON.
قواعد صارمة:
- استخدم " للمفاتيح فقط
- لا تستخدم " داخل القيم (استبدلها بـ ')
- لا تضع أسطر جديدة داخل القيم
- استخدم الفاصلة الإنجليزية , فقط

JSON غير صالح:
{snippet}
"""

    raise ValueError(f"فشل توليد JSON صالح. آخر خطأ: {last_err}")


# =========================
# استخراج مفردات الاختبار
# =========================
def extract_items_via_llm(model, txt_test: str) -> List[Dict]:
    prompt = f"""
أنت مساعد تدقيق اختبارات.
مهمتك: استخراج "المفردات/الأسئلة" من نص الاختبار وإرجاع JSON فقط.

قواعد:
- JSON فقط.
- لكل مفردة: رقم المفردة (number) + نص المفردة (text) + الدرجة إن وُجدت (marks كنص).
- إذا لم يظهر رقم المفردة بوضوح: أنشئ ترقيمًا متسلسلًا 1..n.
- لا تضع " داخل القيم.

صيغة الإخراج:
{{
  "items":[
    {{"number":"1","text":"...","marks":"1"}}
  ]
}}

نص الاختبار:
{safe_clip(txt_test, 90000)}
"""
    data, _ = generate_json(model, prompt, tries=3)
    items = data.get("items", []) or []

    cleaned = []
    seq = 1
    for it in items:
        num = str(it.get("number", "")).strip() or str(seq)
        txt = str(it.get("text", "")).strip()
        marks = str(it.get("marks", "")).strip()
        if txt:
            cleaned.append({"number": num, "text": txt, "marks": marks})
            seq += 1
    return cleaned


# =========================
# تحليل مفردة واحدة
# =========================
def analyze_one_item(model, item: Dict, policy_text: str, book_text: str) -> Dict:
    item_no = str(item.get("number", "")).strip()
    item_text = str(item.get("text", "")).strip()
    item_marks = str(item.get("marks", "")).strip() or "-"

    policy_snips = top_k_chunks(item_text, policy_text, k=4)
    book_snips = top_k_chunks(item_text, book_text, k=3)

    ao_hint = heuristic_assessment_objective(item_text)

    prompt = f"""
أنت خبير تقويم وفق وثيقة التقويم.
حلّل مفردة واحدة فقط وأخرج JSON فقط.

التعريف الرسمي (التزم به حرفيًا عند اختيار هدف التقويم):
{A01_DEFINITION}

{A02_DEFINITION}

قاعدة قرار واضحة:
- إذا كان المطلوب: تطبيق/تحليل/استنتاج/تفسير سببي/مقارنة تحليلية/تحليل بيانات أو رسوم/نتائج/تجربة/استقصاء/حل مشكلة/عمليات متعددة الخطوات → A02
- إذا كان المطلوب: تذكر/تعريف/ذكر/تعداد/تحديد/تسمية/وصف/توضيح بسيط/قانون أو وحدة أو رمز/تعويض بسيط/عملية خطوة واحدة → A01
- إذا كان السؤال يجمع بين تذكر + تطبيق أو يطلب جزءًا بسيطًا ثم تطبيقًا → A01/A02

ملاحظة: مرشح أولي (ليس نهائيًا): {ao_hint}

قواعد إخراج صارمة:
- JSON فقط دون أي نص إضافي.
- لا تضع " داخل القيم (استبدلها بـ ' إن احتجت).
- اجعل القيم قصيرة وواضحة.
- learning_objective: اختر عبارة/بند من وثيقة التقويم "كما هو" قدر الإمكان من المقاطع المرفقة، ولا تختر من خارجها إلا عند الضرورة (وعندها ضع '-').

صيغة JSON المطلوبة:
{{
  "mufrada": "{item_no}",
  "learning_objective": "...",
  "assessment_objective": "A01 أو A02 أو A01/A02",
  "marks": "{item_marks}",
  "note_type": "صياغة أو علمية أو فنية تشمل الرسم أو لا توجد",
  "note": "...",
  "edit": "...",
  "ao_reason": "سبب دقيق ومختصر للاختيار (نوع مهارة/مطلوب)"
}}

المفردة رقم {item_no}:
{item_text}

مقاطع من وثيقة التقويم (الأكثر صلة):
{chr(10).join([f"- {s}" for s in policy_snips])}

مقاطع من كتاب الطالب (الأكثر صلة):
{chr(10).join([f"- {s}" for s in book_snips])}
"""
    out, raw = generate_json(model, prompt, tries=3)

    out["mufrada"] = item_no

    allowed = {"A01", "A02", "A01/A02"}
    ao = str(out.get("assessment_objective", "")).strip()
    if ao not in allowed:
        out["assessment_objective"] = ao_hint

    strong_a02 = bool(re.search(r"(من الرسم|من الجدول|بيانات|منحنى|مخطط|استنتج|حلل|علل|فسر النتائج|ارسم|مثل بيانيا)", item_text))
    if strong_a02 and str(out.get("assessment_objective", "")).strip() == "A01":
        fix_prompt = f"""
راجع تصنيف هدف التقويم فقط وفق التعريف الرسمي.
أخرج JSON فقط: {{"assessment_objective":"A01/A02","ao_reason":"..."}}

التعريف الرسمي:
{A01_DEFINITION}
{A02_DEFINITION}

المفردة:
{item_text}

التصنيف الحالي: A01
أعد التقييم بدقة شديدة.
"""
        try:
            fix, _ = generate_json(model, fix_prompt, tries=2)
            new_ao = str(fix.get("assessment_objective", "")).strip()
            if new_ao in allowed:
                out["assessment_objective"] = new_ao
            if fix.get("ao_reason"):
                out["ao_reason"] = fix["ao_reason"]
        except Exception:
            pass

    out["_item_text"] = item_text
    out["_raw"] = raw
    return out


# =========================
# الجدول العامل + نسبة المطابقة
# =========================
def compute_percent_match(items: List[Dict]) -> int:
    if not items:
        return 0
    ok = 0
    for it in items:
        lo = str(it.get("learning_objective", "")).strip()
        if lo and lo not in {"-", "غير محدد", "غير متوفر"}:
            ok += 1
    return int(round(100 * ok / len(items)))

def detect_mcq(item_text: str) -> bool:
    t = item_text or ""
    return bool(re.search(r"(أ\)|ب\)|ج\)|د\))|(\bA\b|\bB\b|\bC\b|\bD\b)", t))

def detect_long_answer(item_text: str) -> bool:
    t = norm_ar(item_text)
    return any(norm_ar(x) in t for x in ["ناقش", "برهن", "اثبت", "اكتب تقرير", "علل تعليلا", "فسر تفسيرا"])

def build_working_table(items: List[Dict]) -> Dict:
    n_items = len(items)
    mcq_count = sum(1 for it in items if detect_mcq(it.get("_item_text", "")))
    long_count = sum(1 for it in items if detect_long_answer(it.get("_item_text", "")))

    a01 = sum(1 for it in items if str(it.get("assessment_objective", "")).strip() == "A01")
    a02 = sum(1 for it in items if str(it.get("assessment_objective", "")).strip() == "A02")
    mix = sum(1 for it in items if str(it.get("assessment_objective", "")).strip() == "A01/A02")

    wt = {
        "عدد المفردات": {"value": str(n_items), "status": "مطابق"},
        "عدد الدروس": {"value": "-", "status": "مطابق"},
        "درجات أهداف التقويم (A01,A02)": {"value": f"A01={a01} | A02={a02} | A01/A02={mix}", "status": "مطابق"},
        "هل توجد مفردة طويلة الإجابة؟": {"value": "نعم" if long_count > 0 else "لا", "status": "مطابق"},
        "هل توجد مفردتان اختيار من متعدد؟": {"value": "نعم" if mcq_count >= 2 else "لا", "status": "مطابق"},
        "هل مفردات الاختيار من متعدد تحتوي على (إجابات خاطئة) مشتتات منطقية؟": {"value": "-", "status": "مطابق"},
        "هل صياغة المفردات وحجم ونوع الخط واضح للقراءة؟": {"value": "-", "status": "مطابق"},
        "هل الأشكال والرسومات واضحة؟": {"value": "-", "status": "مطابق"},
    }
    return wt


# =========================
# Word
# =========================
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


# =========================
# عرض HTML للجداول داخل الصفحة
# =========================
def render_table_html(headers: List[str], rows: List[List[str]]) -> str:
    th = "".join([f"<th>{h}</th>" for h in headers])
    trs = []
    for r in rows:
        tds = "".join([f"<td>{(c if c is not None and str(c).strip() else '-')}</td>" for c in r])
        trs.append(f"<tr>{tds}</tr>")
    return f'<table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


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

        # نطاق الصفحات لكتاب الطالب فقط
        pr_book = _parse_page_range(pages_range)

        exam_label = exam_label_ar(exam_type)

        with st.spinner("جاري قراءة الملفات (OCR تلقائيًا عند الحاجة)..."):
            # الاختبار: لا نطبق عليه نطاق صفحات (يُقرأ كاملًا)
            txt_test, mode_test = extract_text_auto(model, file_test.getvalue(), None)

            # وثيقة التقويم: تُقرأ كاملة
            txt_policy, mode_policy = extract_text_auto(model, file_policy.getvalue(), None)

            # كتاب الطالب: يطبق عليه نطاق الصفحات فقط
            txt_book, mode_book = extract_text_auto(model, file_book.getvalue(), pr_book)

            txt_test = safe_clip(txt_test, 110000)
            txt_policy = safe_clip(txt_policy, 150000)
            txt_book = safe_clip(txt_book, 120000)

        with st.spinner("جاري استخراج مفردات الاختبار..."):
            items_base = extract_items_via_llm(model, txt_test)

        if not items_base:
            with st.spinner("فشل استخراج المفردات من النص. سأجرب OCR مباشر للاختبار ثم أعيد الاستخراج..."):
                txt_test_ocr = ocr_pdf_with_gemini(model, file_test.getvalue(), None, max_pages=25)
                if txt_test_ocr.strip():
                    txt_test = safe_clip(txt_test_ocr, 110000)
                    items_base = extract_items_via_llm(model, txt_test)

        if not items_base:
            st.error("لم أستطع استخراج مفردات من ملف الاختبار حتى بعد OCR.")
            st.stop()

        analyzed_items = []
        prog = st.progress(0)
        total = len(items_base)

        for idx, it in enumerate(items_base, start=1):
            with st.spinner(f"تحليل المفردة {it.get('number')} ..."):
                analyzed_items.append(analyze_one_item(model, it, txt_policy, txt_book))
            prog.progress(int(100 * idx / total))

        percent_match = compute_percent_match(analyzed_items)
        working_table = build_working_table(analyzed_items)

        compact = [
            {
                "mufrada": x.get("mufrada"),
                "assessment_objective": x.get("assessment_objective"),
                "note_type": x.get("note_type"),
                "note": x.get("note"),
            }
            for x in analyzed_items
        ]

        overall_prompt = f"""
أنت خبير تقويم. اكتب تقديرًا عامًا مختصرًا (3-5 أسطر) عن الاختبار {exam_label}.
ركز على: توازن A01/A02 وفق التعريف الرسمي، جودة الصياغة والدقة العلمية، ومواطن التحسين.
لا تستخدم " داخل النص.

أخرج JSON فقط:
{{"summary":"..."}}

البيانات المختصرة:
{json.dumps(compact, ensure_ascii=False)}
"""
        overall_data, _ = generate_json(model, overall_prompt, tries=2)
        overall_summary = str(overall_data.get("summary", "")).strip() or "-"

        report_data = {
            "items": analyzed_items,
            "working_table": working_table,
            "overall": {"summary": overall_summary, "percent_match": percent_match},
        }

        st.markdown("---")
        st.subheader("جدول تحليل المفردات الامتحانية")

        headers1 = [
            "المفردة",
            "الهدف التعليمي",
            "هدف التقويم (A01,A02)",
            "الدرجة",
            "نوع الملاحظة (صياغة، علمية، فنية تشمل الرسم)",
            "الملاحظة",
            "التعديل",
        ]

        rows1 = []
        for it in analyzed_items:
            rows1.append([
                str(it.get("mufrada", "-")).strip(),
                str(it.get("learning_objective", "-")).strip(),
                str(it.get("assessment_objective", "-")).strip(),
                str(it.get("marks", "-")).strip(),
                str(it.get("note_type", "-")).strip(),
                str(it.get("note", "-")).strip(),
                str(it.get("edit", "-")).strip(),
            ])

        st.markdown(render_table_html(headers1, rows1), unsafe_allow_html=True)

        st.markdown("")
        st.subheader(f"الجدول العامل للاختبار {exam_label}")

        headers2 = ["البند", "العدد / الدرجات – نعم / لا", "مطابق / غير مطابق"]
        rows2 = []
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
        for k in rows_order:
            entry = working_table.get(k, {}) or {}
            rows2.append([k, str(entry.get("value", "-")), str(entry.get("status", "-"))])

        st.markdown(render_table_html(headers2, rows2), unsafe_allow_html=True)

        st.markdown("")
        st.subheader(f"التقدير العام للاختبار {exam_label}")
        st.markdown(
            f'<div class="report-box">{overall_summary}<br><br>نسبة المطابقة للمعايير: {percent_match}%</div>',
            unsafe_allow_html=True
        )

        with st.expander("عرض نص كل مفردة + سبب تصنيف A01/A02 (للمراجعة)"):
            for it in analyzed_items:
                st.markdown(f"**المفردة {it.get('mufrada')}**")
                st.write(it.get("_item_text", "-"))
                st.markdown(f"<div class='muted'>سبب التصنيف: {it.get('ao_reason','-')}</div>", unsafe_allow_html=True)
                st.markdown("---")

        docx_bytes = build_report_docx(report_data, exam_label)
        st.download_button(
            "📥 تنزيل التقرير (Word)",
            data=docx_bytes,
            file_name="Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
