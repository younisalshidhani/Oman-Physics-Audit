import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

# ==========================================
# 1. إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(page_title="المحلل التربوي العماني (Pro)", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .header-box { background: #f0f8ff; padding: 20px; border-radius: 10px; border-right: 8px solid #007bff; margin-bottom: 20px; }
    .success-box { background: #d4edda; padding: 15px; border-radius: 5px; color: #155724; border: 1px solid #c3e6cb; }
    table { width: 100%; direction: rtl; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
    th { background-color: #f2f2f2; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. دوال مساعدة (Word + PDF)
# ==========================================

def extract_text_from_pdf(uploaded_file):
    if not uploaded_file: return ""
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = "".join([page.get_text() for page in doc])
        return text
    except Exception as e:
        return f"خطأ في قراءة الملف: {str(e)}"

def create_word_docx(report_data, subject, grade):
    doc = Document()
    
    # تنسيق العنوان
    title = doc.add_heading(f'تقرير تحليل اختبار مادة {subject} - الصف {grade}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f'تم التحليل وفق معايير وثيقة تقويم تعلم الطلبة - سلطنة عمان')
    doc.add_paragraph(f'--------------------------------------------------------')

    # دالة لإضافة جدول في الوورد
    def add_table_to_doc(headers, rows):
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            # محاولة ضبط الاتجاه (غالباً الوورد يحتاج إعدادات لغة، لكن هذا يفي بالغرض)
        
        for row_data in rows:
            row_cells = table.add_row().cells
            for i, item in enumerate(row_data):
                row_cells[i].text = str(item)
        doc.add_paragraph('') # مسافة

    # 1. جدول المفردات
    doc.add_heading('1. جدول تحليل المفردات الامتحانية', level=1)
    vocab_headers = ["رقم السؤال", "الهدف التعليمي", "المستوى (AO1/AO2)", "الدرجة", "الملاحظة الفنية", "التعديل المقترح"]
    vocab_rows = []
    if "vocab_table" in report_data:
        for item in report_data["vocab_table"]:
            vocab_rows.append([
                item.get("q_num", "-"),
                item.get("objective", "-"),
                item.get("level", "-"),
                item.get("marks", "-"),
                item.get("note", "-"),
                item.get("fix", "-")
            ])
        add_table_to_doc(vocab_headers, vocab_rows)

    # 2. الجدول العامل
    doc.add_heading('2. الجدول العامل (المواصفات الفنية)', level=1)
    working_headers = ["البند", "القيمة / العدد", "التقييم (مطابق/غير مطابق)"]
    working_rows = []
    if "working_table" in report_data:
        wt = report_data["working_table"]
        # تحويل القاموس إلى قائمة
        items_map = {
            "total_questions": "عدد المفردات",
            "lessons_count": "عدد الدروس المغطاة",
            "ao1_marks": "مجموع درجات AO1",
            "ao2_marks": "مجموع درجات AO2",
            "mcq_distractors": "جودة المشتتات (MCQ)",
            "clarity": "وضوح الرسومات والصياغة"
        }
        for key, label in items_map.items():
            val = wt.get(key, {})
            working_rows.append([label, val.get("value", "-"), val.get("status", "-")])
        add_table_to_doc(working_headers, working_rows)

    # 3. التقدير العام
    doc.add_heading('3. التقدير العام والتوصيات', level=1)
    if "summary" in report_data:
        p = doc.add_paragraph(report_data["summary"])
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # حفظ في الذاكرة
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. الواجهة الرئيسية
# ==========================================

with st.sidebar:
    st.header("⚙️ إعدادات التحليل")
    api_key = st.text_input("مفتاح API:", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم", "رياضيات"])
    grade = st.selectbox("الصف:", ["10", "11", "12"])
    pages = st.text_input("نطاق الصفحات (للمطابقة):", "مثلاً: 12-45")

st.markdown('<div class="header-box"><h2>🇴🇲 نظام تحليل الاختبارات - المعايير العمانية</h2><p>يدعم التصدير لملف Word + تحليل دقيق للمستويات المعرفية</p></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: t_file = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: p_file = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: b_file = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

if st.button("🚀 بدء التحليل وإنشاء التقرير") and api_key and t_file:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner("جاري قراءة الملفات وتحليل البيانات (قد يستغرق 30 ثانية)..."):
            # 1. استخراج النصوص
            txt_test = extract_text_from_pdf(t_file)
            txt_book = extract_text_from_pdf(b_file)
            txt_policy = extract_text_from_pdf(p_file)
            
            # 2. بناء البرومبت (محكم جداً ليخرج JSON)
            prompt = f"""
            أنت خبير تقويم تربوي في وزارة التربية والتعليم بسلطنة عمان.
            لديك اختبار لمادة {subject} للصف {grade}.
            
            قم بتحليل الاختبار ومقارنته بالمحتوى الدراسي (صفحات {pages}) وبوثيقة التقويم.
            
            المهمة: استخرج البيانات التالية بصيغة JSON فقط (بدون أي نصوص إضافية في البداية أو النهاية).
            
            هيكل JSON المطلوب:
            {{
                "vocab_table": [
                    {{ "q_num": "1", "objective": "وصف الهدف", "level": "AO1", "marks": "2", "note": "الملاحظة", "fix": "التعديل" }},
                    ... لكل الأسئلة
                ],
                "working_table": {{
                    "total_questions": {{ "value": "رقم", "status": "مطابق/غير مطابق" }},
                    "lessons_count": {{ "value": "تقديري", "status": "-" }},
                    "ao1_marks": {{ "value": "المجموع", "status": "-" }},
                    "ao2_marks": {{ "value": "المجموع", "status": "-" }},
                    "mcq_distractors": {{ "value": "تحليل المشتتات", "status": "جيد/ضعيف" }},
                    "clarity": {{ "value": "وصف الوضوح", "status": "-" }}
                }},
                "summary": "اكتب هنا التقرير الختامي ونسبة المطابقة."
            }}

            البيانات المدخلة:
            - الاختبار: {txt_test[:10000]}
            - الكتاب: {txt_book[:10000]} (للمساعدة في تحديد الدروس والمستويات)
            - الوثيقة: {txt_policy[:5000]} (للمعايير)
            """

            # 3. الاتصال بالموديل
            response = model.generate_content(prompt)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(clean_json)
                
                # --- عرض النتائج في الموقع ---
                
                # 1. جدول المفردات
                st.subheader("1. جدول تحليل المفردات")
                html_table = "<table><tr><th>السؤال</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>"
                for row in data.get("vocab_table", []):
                    html_table += f"<tr><td>{row.get('q_num')}</td><td>{row.get('objective')}</td><td>{row.get('level')}</td><td>{row.get('marks')}</td><td>{row.get('note')}</td><td>{row.get('fix')}</td></tr>"
                html_table += "</table>"
                st.markdown(html_table, unsafe_allow_html=True)

                # 2. الجدول العامل
                st.subheader("2. الجدول العامل للاختبار")
                wt = data.get("working_table", {})
                html_w_table = "<table><tr><th>البند</th><th>القيمة / الوصف</th><th>الحالة</th></tr>"
                labels = {
                    "total_questions": "عدد الأسئلة", "lessons_count": "عدد الدروس", 
                    "ao1_marks": "مجموع المعرفة (AO1)", "ao2_marks": "مجموع التطبيق/الاستدلال (AO2)",
                    "mcq_distractors": "مشتتات الاختيار من متعدد", "clarity": "جودة الرسوم والصياغة"
                }
                for k, label in labels.items():
                    item = wt.get(k, {})
                    html_w_table += f"<tr><td>{label}</td><td>{item.get('value')}</td><td>{item.get('status')}</td></tr>"
                html_w_table += "</table>"
                st.markdown(html_w_table, unsafe_allow_html=True)

                # 3. التقدير العام
                st.subheader("3. التقدير العام")
                st.info(data.get("summary", "لا يوجد ملخص"))

                # 4. زر التحميل (Word)
                docx_file = create_word_docx(data, subject, grade)
                st.download_button(
                    label="📥 تحميل التقرير بصيغة Word (.docx)",
                    data=docx_file,
                    file_name="Oman_Exam_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except json.JSONDecodeError:
                # في حال فشل الـ JSON، نعرض النص كما جاء (خطة بديلة)
                st.warning("تم التحليل، لكن حدث خطأ في تنسيق الجداول التلقائي. إليك النص الخام:")
                st.markdown(response.text)

    except Exception as e:
        st.error(f"حدث خطأ غير متوقع: {str(e)}")
        st.info("نصيحة: تأكد من أن الملفات المرفقة هي ملفات PDF صالحة وليست صوراً.")
