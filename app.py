import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

# ==========================================
# 1. إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(page_title="المحلل التربوي العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    .header-box { background: #f0f8ff; padding: 20px; border-radius: 10px; border-right: 8px solid #007bff; margin-bottom: 20px; }
    table { width: 100%; direction: rtl; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
    th { background-color: #f2f2f2; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. دوال المعالجة (PDF و Word)
# ==========================================

def extract_text_from_pdf(uploaded_file):
    if not uploaded_file: return ""
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = "".join([page.get_text() for page in doc])
        return text
    except Exception as e:
        return ""

def create_word_docx(report_data, subject, grade, semester, exam_type):
    doc = Document()
    
    # عنوان التقرير
    title = doc.add_heading(f'تقرير تحليل {exam_type} - مادة {subject}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph(f'الصف: {grade} | الفصل الدراسي: {semester}')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('--------------------------------------------------------')

    # دالة مساعدة لرسم الجداول في الوورد
    def add_table_to_doc(headers, rows):
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # ترويسة الجدول
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        # البيانات
        for row_data in rows:
            row_cells = table.add_row().cells
            for i, item in enumerate(row_data):
                row_cells[i].text = str(item)
                row_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        doc.add_paragraph('')

    # 1. جدول المفردات
    doc.add_heading('1. جدول تحليل المفردات الامتحانية', level=1)
    vocab_headers = ["رقم السؤال", "الهدف", "المستوى (AO1/AO2)", "الدرجة", "الملاحظة", "التعديل"]
    vocab_rows = []
    if "vocab_table" in report_data:
        for item in report_data["vocab_table"]:
            vocab_rows.append([
                item.get("q_num", ""),
                item.get("objective", ""),
                item.get("level", ""),
                item.get("marks", ""),
                item.get("note", ""),
                item.get("fix", "")
            ])
        add_table_to_doc(vocab_headers, vocab_rows)

    # 2. الجدول العامل
    doc.add_heading('2. الجدول العامل (المواصفات الفنية)', level=1)
    working_headers = ["البند", "القيمة / العدد", "التقييم"]
    working_rows = []
    if "working_table" in report_data:
        wt = report_data["working_table"]
        # ترتيب العناصر
        keys_order = ["total_questions", "lessons_count", "ao1_marks", "ao2_marks", "mcq_distractors", "clarity"]
        labels = {
            "total_questions": "عدد المفردات", "lessons_count": "عدد الدروس", 
            "ao1_marks": "درجات المعرفة (AO1)", "ao2_marks": "درجات التطبيق (AO2)",
            "mcq_distractors": "المشتتات (MCQ)", "clarity": "جودة الرسوم والخط"
        }
        for k in keys_order:
            val = wt.get(k, {})
            working_rows.append([labels.get(k, k), val.get("value", "-"), val.get("status", "-")])
        add_table_to_doc(working_headers, working_rows)

    # 3. التقدير العام
    doc.add_heading('3. التقدير العام', level=1)
    if "summary" in report_data:
        p = doc.add_paragraph(report_data["summary"])
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. الواجهة الجانبية (Sidebar) - معدلة حسب طلبك
# ==========================================

with st.sidebar:
    st.header("⚙️ إعدادات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # 1. المواد المحددة فقط
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    
    # 2. الصفوف المحددة فقط
    grade = st.selectbox("المرحلة الصفية:", ["11", "12"])
    
    # 3. استعادة الفصل ونوع الاختبار (ضروري للدقة)
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "تجريبي/نهائي"])
    
    pages = st.text_input("نطاق الصفحات للكتاب:", "مثلاً: 20-45")

# ==========================================
# 4. الجسم الرئيسي للتطبيق
# ==========================================

st.markdown(f'<div class="header-box"><h2>🇴🇲 نظام تحليل اختبارات {subject} (الصف {grade})</h2><p>مطابقة المعايير + تصدير ملف Word</p></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: t_file = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: p_file = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: b_file = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

if st.button("🚀 بدء التحليل الرسمي") and api_key and t_file:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner("جاري قراءة الملفات وتحليل المفردات..."):
            # استخراج النصوص
            txt_test = extract_text_from_pdf(t_file)
            txt_book = extract_text_from_pdf(b_file)
            txt_policy = extract_text_from_pdf(p_file)
            
            # التعليمات للذكاء الاصطناعي (Prompt)
            prompt = f"""
            أنت خبير تقويم تربوي في سلطنة عمان. حلل اختبار مادة {subject} للصف {grade} الفصل {semester}.
            
            المطلوب: استخراج البيانات بصيغة JSON حصراً لملء الجداول التالية.

            هيكل JSON المطلوب:
            {{
                "vocab_table": [
                    {{ "q_num": "1", "objective": "الهدف", "level": "AO1", "marks": "1", "note": "ملاحظة", "fix": "تعديل" }}
                ],
                "working_table": {{
                    "total_questions": {{ "value": "العدد", "status": "مناسب/غير مناسب" }},
                    "lessons_count": {{ "value": "العدد التقريبي", "status": "-" }},
                    "ao1_marks": {{ "value": "المجموع", "status": "-" }},
                    "ao2_marks": {{ "value": "المجموع", "status": "-" }},
                    "mcq_distractors": {{ "value": "وصف المشتتات", "status": "جيد/ضعيف" }},
                    "clarity": {{ "value": "وصف الخط والرسوم", "status": "واضح/غير واضح" }}
                }},
                "summary": "نص التقدير العام ونسبة المطابقة."
            }}

            البيانات:
            الاختبار: {txt_test[:15000]}
            الكتاب (نطاق {pages}): {txt_book[:15000]}
            الوثيقة: {txt_policy[:5000]}
            """

            response = model.generate_content(prompt)
            
            # تنظيف رد الذكاء الاصطناعي لاستخراج JSON
            text_resp = response.text
            json_str = text_resp.replace("```json", "").replace("```", "").strip()
            # محاولة إصلاح سريعة إذا كان هناك نص قبل القوس
            if "{" in json_str:
                json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]

            try:
                data = json.loads(json_str)
                
                # عرض الجداول في الموقع
                st.success("تم التحليل بنجاح! النتائج بالأسفل 👇")
                
                # 1. عرض جدول المفردات
                st.subheader("1. جدول تحليل المفردات")
                v_rows = ""
                for r in data.get("vocab_table", []):
                    v_rows += f"<tr><td>{r.get('q_num')}</td><td>{r.get('objective')}</td><td>{r.get('level')}</td><td>{r.get('marks')}</td><td>{r.get('note')}</td><td>{r.get('fix')}</td></tr>"
                st.markdown(f"<table><tr><th>س</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>{v_rows}</table>", unsafe_allow_html=True)

                # 2. عرض الجدول العامل
                st.subheader("2. الجدول العامل")
                w_rows = ""
                wt = data.get("working_table", {})
                labels = {"total_questions": "عدد الأسئلة", "lessons_count": "عدد الدروس", "ao1_marks": "مجموع AO1", "ao2_marks": "مجموع AO2", "mcq_distractors": "المشتتات", "clarity": "الوضوح"}
                for k, v in labels.items():
                    item = wt.get(k, {})
                    w_rows += f"<tr><td>{v}</td><td>{item.get('value')}</td><td>{item.get('status')}</td></tr>"
                st.markdown(f"<table><tr><th>البند</th><th>القيمة</th><th>الحالة</th></tr>{w_rows}</table>", unsafe_allow_html=True)

                # 3. عرض الملخص
                st.subheader("3. التقدير العام")
                st.info(data.get("summary"))

                # 4. زر التحميل (Word)
                docx = create_word_docx(data, subject, grade, semester, exam_type)
                st.download_button("📥 تحميل التقرير (Word)", docx, "Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            except Exception as e:
                st.warning("حدث خطأ في تنسيق الجدول، لكن إليك النص الكامل للتحليل:")
                st.markdown(response.text)

    except Exception as e:
        st.error(f"خطأ غير متوقع: {e}")
