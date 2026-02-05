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
st.set_page_config(page_title="المحلل التربوي العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    table { width: 100%; border-collapse: collapse; direction: rtl; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
    th { background-color: #f0f2f6; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. دوال المعالجة
# ==========================================

def get_pdf_text(file):
    if not file: return ""
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join([page.get_text() for page in doc])
    except: return ""

def create_docx(data, subject, grade):
    doc = Document()
    
    # الترويسة
    title = doc.add_heading(f'تقرير فني: اختبار {subject}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f'الصف: {grade} | (تم التحليل بناءً على محتوى الملف المرفق)')
    doc.add_paragraph('-' * 70)

    def draw_table(headers, rows):
        if not rows: return
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            table.rows[0].cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for row_data in rows:
            row_cells = table.add_row().cells
            for i, val in enumerate(row_data):
                row_cells[i].text = str(val)
                row_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        doc.add_paragraph('\n')

    # الجداول
    doc.add_heading('1. جدول تحليل المفردات', level=1)
    if "vocab" in data:
        h = ["م", "الهدف", "المستوى", "الدرجة", "الملاحظة", "التعديل"]
        r = [[x.get("q"), x.get("obj"), x.get("level"), x.get("mark"), x.get("note"), x.get("fix")] for x in data.get("vocab", [])]
        draw_table(h, r)

    doc.add_heading('2. الجدول العامل', level=1)
    if "specs" in data:
        h = ["البند", "النتيجة", "التقييم"]
        s = data["specs"]
        r = [
            ["عدد الأسئلة", s.get("q_count", {}).get("val"), s.get("q_count", {}).get("status")],
            ["التغطية", s.get("lessons", {}).get("val"), s.get("lessons", {}).get("status")],
            ["مجموع AO1", s.get("ao1", {}).get("val"), s.get("ao1", {}).get("status")],
            ["مجموع AO2", s.get("ao2", {}).get("val"), s.get("ao2", {}).get("status")],
            ["المشتتات", s.get("mcq", {}).get("val"), s.get("mcq", {}).get("status")],
            ["الوضوح", s.get("clarity", {}).get("val"), s.get("clarity", {}).get("status")]
        ]
        draw_table(h, r)

    doc.add_heading('3. التقدير العام', level=1)
    p = doc.add_paragraph(data.get("summary", ""))
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. الواجهة (حسب طلبك بالضبط)
# ==========================================

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # فقط القوائم التي سمحت بها
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    grade = st.selectbox("الصف:", ["11", "12"])
    
    # لا يوجد فصل دراسي ولا نوع اختبار هنا
    pages_range = st.text_input("نطاق صفحات الكتاب:", "مثال: 10-30")

# ==========================================
# 4. التشغيل
# ==========================================

st.title(f"🔍 مدقق اختبارات {subject} (الصف {grade})")
st.info("سيتم استنتاج الفصل الدراسي ونوع الاختبار تلقائياً من الملف.")

col1, col2, col3 = st.columns(3)
with col1: f_test = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: f_policy = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: f_book = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

if st.button("🚀 تحليل") and api_key and f_test:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.spinner("جاري التحليل..."):
        txt_test = get_pdf_text(f_test)
        txt_book = get_pdf_text(f_book)
        txt_policy = get_pdf_text(f_policy)
        
        # نطلب من الذكاء الاصطناعي تحديد الفصل ونوع الاختبار بنفسه
        prompt = f"""
        أنت خبير مناهج في سلطنة عمان.
        المادة: {subject} - الصف: {grade}.
        
        التعليمات:
        1. اقرأ ملف الاختبار وحدد (الفصل الدراسي) و (نوع الاختبار) تلقائياً.
        2. قارن الأسئلة بصفحات الكتاب ({pages_range}) والوثيقة.
        3. استخرج JSON فقط:
        {{
            "vocab": [ {{"q": "1", "obj": "...", "level": "AO1", "mark": "1", "note": "...", "fix": "..."}} ],
            "specs": {{
                "q_count": {{"val": "...", "status": "..."}},
                "lessons": {{"val": "...", "status": "..."}},
                "ao1": {{"val": "...", "status": "..."}},
                "ao2": {{"val": "...", "status": "..."}},
                "mcq": {{"val": "...", "status": "..."}},
                "clarity": {{"val": "...", "status": "..."}}
            }},
            "summary": "ذكر الفصل الدراسي ونوع الاختبار الذي تم اكتشافه هنا، ثم التقرير."
        }}

        البيانات:
        الاختبار: {txt_test[:15000]}
        الكتاب: {txt_book[:15000]}
        الوثيقة: {txt_policy[:5000]}
        """
        
        try:
            res = model.generate_content(prompt)
            clean_json = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in clean_json: clean_json = clean_json[clean_json.find("{"):clean_json.rfind("}")+1]
            data = json.loads(clean_json)
            
            st.success("تم!")
            
            st.subheader("1. المفردات")
            rows = ""
            for i in data.get("vocab", []):
                rows += f"<tr><td>{i['q']}</td><td>{i['obj']}</td><td>{i['level']}</td><td>{i['mark']}</td><td>{i['note']}</td><td>{i['fix']}</td></tr>"
            st.markdown(f"<table><tr><th>م</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>{rows}</table>", unsafe_allow_html=True)
            
            st.subheader("2. الجدول العامل")
            rows2 = ""
            labels = {"q_count":"العدد", "lessons":"الدروس", "ao1":"AO1", "ao2":"AO2", "mcq":"المشتتات", "clarity":"الوضوح"}
            for k,v in labels.items():
                val = data.get("specs", {}).get(k, {})
                rows2 += f"<tr><td>{v}</td><td>{val.get('val')}</td><td>{val.get('status')}</td></tr>"
            st.markdown(f"<table><tr><th>البند</th><th>القيمة</th><th>التقييم</th></tr>{rows2}</table>", unsafe_allow_html=True)
            
            st.subheader("3. التقدير العام")
            st.info(data.get("summary"))
            
            st.download_button("📥 تحميل Word", create_docx(data, subject, grade), "Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
        except Exception as e:
            st.error("خطأ في التحليل.")
