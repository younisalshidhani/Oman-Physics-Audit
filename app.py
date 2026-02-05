import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

# ==========================================
# 1. إعداد الصفحة
# ==========================================
st.set_page_config(page_title="المحلل التربوي العماني (Pro)", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    table { width: 100%; border-collapse: collapse; direction: rtl; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
    th { background-color: #f0f2f6; font-weight: bold; }
    .metric-box { background-color: #e8f4f8; padding: 15px; border-radius: 8px; border-right: 5px solid #007bff; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. الدوال المساعدة (Word + PDF)
# ==========================================

def get_pdf_text(file):
    """استخراج النص من ملف PDF"""
    if not file: return ""
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join([page.get_text() for page in doc])
    except: return ""

def create_docx(data, subject, grade, semester):
    """إنشاء ملف Word احترافي"""
    doc = Document()
    
    # الترويسة
    title = doc.add_heading(f'تقرير فني: اختبار {subject}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f'الصف: {grade} | الفصل: {semester} | حسب المعايير العمانية')
    doc.add_paragraph('-' * 70)

    # دالة رسم الجدول
    def draw_table(headers, rows):
        if not rows: return
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # تنسيق الرأس
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # البيانات
        for row_data in rows:
            row_cells = table.add_row().cells
            for i, val in enumerate(row_data):
                row_cells[i].text = str(val)
                row_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        doc.add_paragraph('\n')

    # 1. جدول المفردات
    doc.add_heading('أولاً: جدول تحليل المفردات', level=1)
    if "vocab" in data and data["vocab"]:
        headers = ["م", "الهدف التعليمي", "المستوى (AO1/AO2)", "الدرجة", "الملاحظة", "التعديل"]
        rows = [[x.get("q"), x.get("obj"), x.get("level"), x.get("mark"), x.get("note"), x.get("fix")] for x in data["vocab"]]
        draw_table(headers, rows)

    # 2. الجدول العامل
    doc.add_heading('ثانياً: الجدول العامل والمواصفات', level=1)
    if "specs" in data and data["specs"]:
        headers = ["البند", "النتيجة / العدد", "التقييم"]
        s = data["specs"]
        rows = [
            ["عدد المفردات", s.get("q_count", {}).get("val"), s.get("q_count", {}).get("status")],
            ["تغطية الدروس", s.get("lessons", {}).get("val"), s.get("lessons", {}).get("status")],
            ["درجات المعرفة (AO1)", s.get("ao1", {}).get("val"), s.get("ao1", {}).get("status")],
            ["درجات التطبيق (AO2)", s.get("ao2", {}).get("val"), s.get("ao2", {}).get("status")],
            ["جودة المشتتات (MCQ)", s.get("mcq", {}).get("val"), s.get("mcq", {}).get("status")],
            ["الوضوح الفني", s.get("clarity", {}).get("val"), s.get("clarity", {}).get("status")]
        ]
        draw_table(headers, rows)

    # 3. الملخص
    doc.add_heading('ثالثاً: التقدير العام', level=1)
    p = doc.add_paragraph(data.get("summary", "لا يوجد ملخص"))
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # الحفظ
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. الواجهة الجانبية (تم ضبطها بدقة)
# ==========================================

with st.sidebar:
    st.header("⚙️ إعدادات التحليل")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # القوائم كما طلبت بالضبط
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    grade = st.selectbox("الصف:", ["11", "12"])
    
    # إعادة الفصل ونوع الاختبار (ضروري جداً للدقة)
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "تجريبي/نهائي"])
    
    pages_range = st.text_input("نطاق صفحات الكتاب:", "مثال: 10-30")

# ==========================================
# 4. التطبيق الرئيسي
# ==========================================

st.title(f"🔍 مدقق الاختبارات العماني: {subject} ({grade})")
st.markdown(f'<div class="metric-box">يتم التحليل وفق: وثيقة تقويم تعلم الطلبة - الفصل {semester}</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: f_test = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: f_policy = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: f_book = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

if st.button("🚀 بدء التحليل الشامل") and api_key and f_test:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.spinner("جاري تحليل المفردات ومطابقة المعايير... (يرجى الانتظار)"):
        # قراءة الملفات
        txt_test = get_pdf_text(f_test)
        txt_book = get_pdf_text(f_book)
        txt_policy = get_pdf_text(f_policy)
        
        # البرومبت (الدماغ المحرك)
        prompt = f"""
        أنت خبير مناهج في سلطنة عمان. دورك هو تدقيق اختبار مادة {subject} للصف {grade} الفصل {semester}.
        نوع الاختبار: {exam_type}.

        المهمة: قارن الأسئلة بمحتوى الكتاب (الصفحات {pages_range}) ومعايير وثيقة التقويم.
        
        أخرج النتيجة بصيغة JSON فقط (بدون مقدمات) لملء الجداول التالية:
        1. "vocab": قائمة بالمفردات (رقم السؤال، الهدف، المستوى AO1/AO2، الدرجة، ملاحظة، تعديل).
        2. "specs": الجدول العامل (عدد المفردات، تغطية الدروس، مجموع درجات AO1 و AO2، جودة المشتتات، الوضوح).
        3. "summary": رأي خبير مختصر في جودة الاختبار.

        هيكل JSON المطلوب:
        {{
            "vocab": [
                {{"q": "1", "obj": "...", "level": "AO1", "mark": "1", "note": "...", "fix": "..."}}
            ],
            "specs": {{
                "q_count": {{"val": "...", "status": "..."}},
                "lessons": {{"val": "...", "status": "..."}},
                "ao1": {{"val": "...", "status": "..."}},
                "ao2": {{"val": "...", "status": "..."}},
                "mcq": {{"val": "...", "status": "..."}},
                "clarity": {{"val": "...", "status": "..."}}
            }},
            "summary": "..."
        }}

        البيانات:
        الاختبار: {txt_test[:15000]}
        الكتاب: {txt_book[:15000]}
        الوثيقة: {txt_policy[:5000]}
        """
        
        try:
            # إرسال الطلب
            response = model.generate_content(prompt)
            
            # تنظيف الرد (لضمان عمل الـ JSON)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            if "{" in clean_json:
                clean_json = clean_json[clean_json.find("{"):clean_json.rfind("}")+1]
            
            data = json.loads(clean_json)
            
            # عرض النتائج
            st.success("✅ تم التحليل بنجاح!")
            
            # 1. جدول المفردات
            st.subheader("1. جدول تحليل المفردات")
            rows_html = ""
            for item in data.get("vocab", []):
                rows_html += f"<tr><td>{item.get('q')}</td><td>{item.get('obj')}</td><td>{item.get('level')}</td><td>{item.get('mark')}</td><td>{item.get('note')}</td><td>{item.get('fix')}</td></tr>"
            st.markdown(f"<table><tr><th>م</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>{rows_html}</table>", unsafe_allow_html=True)
            
            # 2. الجدول العامل
            st.subheader("2. الجدول العامل (المطابقة)")
            specs = data.get("specs", {})
            labels = {
                "q_count": "عدد الأسئلة", "lessons": "تغطية الدروس", 
                "ao1": "مجموع المعرفة (AO1)", "ao2": "مجموع التطبيق (AO2)", 
                "mcq": "جودة المشتتات", "clarity": "الوضوح الفني"
            }
            rows_specs = ""
            for k, lbl in labels.items():
                val = specs.get(k, {})
                rows_specs += f"<tr><td>{lbl}</td><td>{val.get('val')}</td><td>{val.get('status')}</td></tr>"
            st.markdown(f"<table><tr><th>البند</th><th>القيمة / الوصف</th><th>التقييم</th></tr>{rows_specs}</table>", unsafe_allow_html=True)

            # 3. الملخص والتحميل
            st.subheader("3. التقدير العام")
            st.info(data.get("summary"))
            
            # زر Word
            docx_file = create_docx(data, subject, grade, semester)
            st.download_button("📥 تحميل التقرير (Word)", docx_file, f"Report_{subject}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
        except Exception as e:
            st.error("عذراً، حدث خطأ أثناء معالجة رد الذكاء الاصطناعي.")
            st.warning("حاول مرة أخرى، أو تأكد من وضوح ملف الاختبار.")
            with st.expander("تفاصيل الخطأ التقني (للمطور)"):
                st.write(e)
                st.write(response.text if 'response' in locals() else "No Response")
