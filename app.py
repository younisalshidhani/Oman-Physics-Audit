# app.py (مُعدّل) — نسخة مقترحة تعمل محلياً مع تحسينات لمعالجة الأخطاء والخصوصية
import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

st.set_page_config(page_title="نظام تدقيق الاختبارات العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    table { width: 100%; border-collapse: collapse; direction: rtl; margin-bottom: 20px; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
    th { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------
# دوال مساعدة
# ----------------------------
def extract_pdf_text(uploaded_file):
    """يقرأ ملف UploadedFile من Streamlit ويُرجع نص كل صفحاته"""
    if not uploaded_file:
        return ""
    data = uploaded_file.read()
    if not data:
        return ""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        texts = []
        for page in doc:
            texts.append(page.get_text())
        return "\n".join(texts)
    except Exception as e:
        # إن فشل PyMuPDF نرجع نص فارغ مع سجل الخطأ (حتى لا يكسر التطبيق)
        return f"[خطأ في استخراج النص من PDF: {e}]"

def generate_word(data, subject, grade, semester, exam_type):
    doc = Document()
    header = doc.add_heading(f'تقرير تحليل اختبار {subject}', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para = doc.add_paragraph(f'الصف: {grade} | الفصل: {semester} | النوع: {exam_type}')
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("-" * 50)

    # جدول 1 - تحليل المفردات
    doc.add_heading('1. تحليل المفردات', level=1)
    table1 = doc.add_table(rows=1, cols=6)
    table1.style = 'Table Grid'
    hdrs = ["م", "الهدف", "المستوى", "الدرجة", "الملاحظة", "التعديل"]
    for i, h in enumerate(hdrs):
        table1.rows[0].cells[i].text = h
    for item in data.get("vocab", []):
        row = table1.add_row().cells
        row[0].text = str(item.get("q", ""))
        row[1].text = item.get("obj", "")
        row[2].text = item.get("level", "")
        row[3].text = str(item.get("mark", ""))
        row[4].text = item.get("note", "")
        row[5].text = item.get("fix", "")

    # جدول 2 - المواصفات
    doc.add_heading('2. الجدول العامل', level=1)
    table2 = doc.add_table(rows=1, cols=3)
    table2.style = 'Table Grid'
    hdrs2 = ["البند", "البيان", "التقييم"]
    for i, h in enumerate(hdrs2):
        table2.rows[0].cells[i].text = h
    specs = data.get("specs", {})
    mapping = {"q_count":"عدد الأسئلة", "lessons":"تغطية الدروس", "ao1":"درجات AO1", "ao2":"درجات AO2", "clarity":"الوضوح"}
    for key, label in mapping.items():
        row = table2.add_row().cells
        item = specs.get(key, {})
        row[0].text = label
        row[1].text = str(item.get("val", "-"))
        row[2].text = item.get("status", "-")

    doc.add_heading('3. التقدير العام', level=1)
    doc.add_paragraph(data.get("summary", ""))

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ----------------------------
# واجهة جانبية
# ----------------------------
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API (لن يُخزن):", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    grade = st.selectbox("الصف:", ["11", "12"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "تجريبي/نهائي"])
    pages = st.text_input("نطاق الصفحات (مثلاً 1-5):", "1-50")

# ----------------------------
# الجسم الرئيسي
# ----------------------------
st.title(f"🔍 تدقيق اختبار {subject} - الصف {grade}")

c1, c2, c3 = st.columns(3)
with c1:
    f_test = st.file_uploader("ملف الاختبار (PDF)", type="pdf")
with c2:
    f_policy = st.file_uploader("وثيقة التقويم (PDF)", type="pdf")
with c3:
    f_book = st.file_uploader("كتاب الطالب (PDF)", type="pdf")

if st.button("🚀 تنفيذ التحليل"):
    if not api_key:
        st.error("يرجى إدخال مفتاح API في الإعدادات أولاً.")
    elif not f_test:
        st.error("يرجى رفع ملف الاختبار.")
    else:
        # اضبط مفتاح مكتبة Google Generative AI
        genai.configure(api_key=api_key)

        with st.spinner("جاري التحليل وفق المعايير..."):
            t_test = extract_pdf_text(f_test)
            t_policy = extract_pdf_text(f_policy) if f_policy else ""
            t_book = extract_pdf_text(f_book) if f_book else ""

            # لتجنب إرسال نصوص ضخمة جداً، نقتصر على الأحرف الأولى لكل مدخل (يمكن تعديل الطول حسب حاجة)
            max_chunk = 4000
            t_test_snip = t_test[:max_chunk]
            t_policy_snip = t_policy[:max_chunk]
            t_book_snip = t_book[:max_chunk]

            prompt = f"""
حلل اختبار {subject} للصف {grade} فصل {semester}.
قارن أسئلة الاختبار مع وثيقة التقويم (أدخل البنود المطابقة إن وُجدت) وبمحتوى كتاب الطالب.
- وثيقة التقويم (مقتطف): {t_policy_snip}
- كتاب الطالب (مقتطف): صفحات {pages} => {t_book_snip}
- نص الاختبار (مقتطف): {t_test_snip}

اطرح مخرجات JSON فقط بالهيكل التالي:
{{
  "vocab":[
    {{
      "q": "رقم السؤال",
      "obj": "الهدف/المؤشر المتطابق",
      "level": "AO1|AO2|AO3|...",
      "mark": 1,
      "note": "ملاحظات",
      "fix": "اقتراح تعديل"
    }}
  ],
  "specs": {{
    "q_count":{{"val": 0, "status": "OK|Missing"}},
    "lessons":{{"val":"قائمة","status":"Covered|Not covered"}},
    "ao1":{{"val":0,"status":"OK"}},
    "ao2":{{"val":0,"status":"OK"}},
    "clarity":{{"val":"High|Low","status":"OK|Needs revision"}}
  }},
  "summary":"ملخص تحليلي قصير"
}}
"""

            # ملاحظة: إذا استخدمت API أخرى أو صيغة مختلفة، عدّل الأسطر التالية وفقاً لذلك.
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(prompt)
                # قد تختلف الخ��صية التي تحتوي النص بحسب نسخة المكتبة؛ تحقّق من الوثائق إذا لم تعمل:
                raw_text = getattr(res, "text", None) or getattr(res, "content", None) or str(res)

                # تنظيف الكود إذا احتوى على أسوار ```json
                cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                # محاولة العثور على أول { وآخر }
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start == -1 or end == -1:
                    raise ValueError("لم يتم العثور على JSON صالح في ناتج النموذج.")
                js_str = cleaned[start:end+1]

                data = json.loads(js_str)

                st.success("اكتمل التحليل")

                # عرض تحليل المفردات (جدول HTML بسيط)
                st.subheader("تحليل المفردات")
                vocab = data.get("vocab", [])
                if vocab:
                    rows = "".join([f"<tr><td>{i.get('q','')}</td><td>{i.get('obj','')}</td><td>{i.get('level','')}</td><td>{i.get('mark','')}</td><td>{i.get('note','')}</td><td>{i.get('fix','')}</td></tr>" for i in vocab])
                    st.markdown(f"<table><tr><th>م</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>{rows}</table>", unsafe_allow_html=True)
                else:
                    st.info("لا توجد مفردات مُعالجة بالنتيجة.")

                # عرض الجدول العامل
                st.subheader("الجدول العامل")
                specs = data.get("specs", {})
                mapping = {"q_count":"العدد","lessons":"الدروس","ao1":"AO1","ao2":"AO2","clarity":"الوضوح"}
                s_rows = ""
                for k, lbl in mapping.items():
                    val = specs.get(k, {}).get("val", "-")
                    status = specs.get(k, {}).get("status", "-")
                    s_rows += f"<tr><td>{lbl}</td><td>{val}</td><td>{status}</td></tr>"
                st.markdown(f"<table><tr><th>البند</th><th>القيمة</th><th>الحالة</th></tr>{s_rows}</table>", unsafe_allow_html=True)

                st.info(data.get("summary", ""))

                st.download_button("📥 تحميل التقرير (Word)", generate_word(data, subject, grade, semester, exam_type), "Report.docx")

            except json.JSONDecodeError as je:
                st.error("فشل تحليل JSON من مخرجات النموذج.")
                st.code(raw_text if 'raw_text' in locals() else str(je))
            except Exception as e:
                st.error(f"فشل التحليل: {e}")
                # إن وُجد مخرجات خام نعرضها للمساعدة في التشخيص
                if 'raw_text' in locals():
                    st.subheader("مخرجات النموذج (خام)")
                    st.code(raw_text)
