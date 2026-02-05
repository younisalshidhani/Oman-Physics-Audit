import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import json
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO

# ==========================================
# 1. إعداد الصفحة وتنسيق RTL
# ==========================================
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

# ==========================================
# 2. الدوال المساعدة
# ==========================================

def extract_pdf_text(file):
    if not file: return ""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "".join([page.get_text() for page in doc])

def generate_word(data, subject, grade, semester, exam_type):
    doc = Document()
    # العناوين
    header = doc.add_heading(f'تقرير تحليل اختبار {subject}', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f'الصف: {grade} | الفصل: {semester} | النوع: {exam_type}').alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("-" * 50)

    # جدول 1
    doc.add_heading('1. تحليل المفردات', level=1)
    table1 = doc.add_table(rows=1, cols=6)
    table1.style = 'Table Grid'
    hdrs = ["م", "الهدف", "المستوى", "الدرجة", "الملاحظة", "التعديل"]
    for i, h in enumerate(hdrs): table1.rows[0].cells[i].text = h
    for item in data.get("vocab", []):
        row = table1.add_row().cells
        row[0].text = str(item.get("q"))
        row[1].text = item.get("obj")
        row[2].text = item.get("level")
        row[3].text = str(item.get("mark"))
        row[4].text = item.get("note")
        row[5].text = item.get("fix")

    # جدول 2
    doc.add_heading('2. الجدول العامل', level=1)
    table2 = doc.add_table(rows=1, cols=3)
    table2.style = 'Table Grid'
    hdrs2 = ["البند", "البيان", "التقييم"]
    for i, h in enumerate(hdrs2): table2.rows[0].cells[i].text = h
    specs = data.get("specs", {})
    mapping = {"q_count":"عدد الأسئلة", "lessons":"تغطية الدروس", "ao1":"درجات AO1", "ao2":"درجات AO2", "mcq":"المشتتات", "clarity":"الوضوح"}
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

# ==========================================
# 3. الواجهة الجانبية (تم التعديل بدقة)
# ==========================================

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # المواد المطلوبة فقط
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    
    # الصفوف المطلوبة فقط
    grade = st.selectbox("الصف:", ["11", "12"])
    
    # الفصل والنوع (تم إبقاؤهما كما طلبت)
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "تجريبي/نهائي"])
    
    pages = st.text_input("نطاق الصفحات:", "1-50")

# ==========================================
# 4. الجسم الرئيسي
# ==========================================

st.title(f"🔍 تدقيق اختبار {subject} - الصف {grade}")

c1, c2, c3 = st.columns(3)
with c1: f_test = st.file_uploader("ملف الاختبار", type="pdf")
with c2: f_policy = st.file_uploader("وثيقة التقويم", type="pdf")
with c3: f_book = st.file_uploader("كتاب الطالب", type="pdf")

if st.button("🚀 تنفيذ التحليل") and api_key and f_test:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.spinner("جاري التحليل وفق المعايير..."):
        t1 = extract_pdf_text(f_test)
        t2 = extract_pdf_text(f_policy)
        t3 = extract_pdf_text(f_book)
        
        prompt = f"حلل اختبار {subject} صف {grade} فصل {semester}. قارن مع صفحات الكتاب {pages}. أخرج JSON حصراً: {{'vocab': [{{'q':'1','obj':'','level':'','mark':'','note':'','fix':''}}], 'specs': {{'q_count':{{'val':'','status':''}},'lessons':{{'val':'','status':''}},'ao1':{{'val':'','status':''}},'ao2':{{'val':'','status':''}},'mcq':{{'val':'','status':''}},'clarity':{{'val':'','status':''}}}}, 'summary': ''}}. البيانات: {t1[:10000]} {t2[:3000]} {t3[:5000]}"
        
        try:
            res = model.generate_content(prompt)
            js_str = res.text.replace("```json","").replace("```","").strip()
            data = json.loads(js_str[js_str.find("{"):js_str.rfind("}")+1])
            
            st.success("اكتمل التحليل")
            
            # عرض الجداول
            st.subheader("تحليل المفردات")
            rows = "".join([f"<tr><td>{i['q']}</td><td>{i['obj']}</td><td>{i['level']}</td><td>{i['mark']}</td><td>{i['note']}</td><td>{i['fix']}</td></tr>" for i in data['vocab']])
            st.markdown(f"<table><tr><th>م</th><th>الهدف</th><th>المستوى</th><th>الدرجة</th><th>الملاحظة</th><th>التعديل</th></tr>{rows}</table>", unsafe_allow_html=True)
            
            st.subheader("الجدول العامل")
            specs = data['specs']
            s_rows = "".join([f"<tr><td>{lbl}</td><td>{specs[k]['val']}</td><td>{specs[k]['status']}</td></tr>" for k, lbl in {"q_count":"العدد","lessons":"الدروس","ao1":"AO1","ao2":"AO2","mcq":"المشتتات","clarity":"الوضوح"}.items()])
            st.markdown(f"<table><tr><th>البند</th><th>القيمة</th><th>الحالة</th></tr>{s_rows}</table>", unsafe_allow_html=True)
            
            st.info(data['summary'])
            
            st.download_button("📥 تحميل التقرير (Word)", generate_word(data, subject, grade, semester, exam_type), "Report.docx")
            
        except Exception as e:
            st.error("فشل التحليل، يرجى المحاولة مرة أخرى.")
