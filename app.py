import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المحلل التربوي العماني", layout="wide")

# إعداد الموديل
if st.sidebar.text_input("مفتاح API:", type="password", key="api_key"):
    genai.configure(api_key=st.session_state.api_key)
    # تحديث اسم الموديل لضمان التوافق
    model = genai.GenerativeModel('gemini-1.5-flash')

    st.header("📋 نظام تدقيق الاختبارات القصيرة")
    
    col1, col2, col3 = st.columns(3)
    with col1: t_file = st.file_uploader("1. ملف الاختبار", type="pdf")
    with col2: p_file = st.file_uploader("2. وثيقة التقويم", type="pdf")
    with col3: b_file = st.file_uploader("3. كتاب الطالب", type="pdf")

    pg_range = st.sidebar.text_input("نطاق الصفحات (مثلاً 77-97):")

    if t_file and st.button("🚀 بدء التحليل الرسمي"):
        def get_pdf_text(file, r=None):
            if not file: return ""
            doc = fitz.open(stream=file.read(), filetype="pdf")
            if r and '-' in r:
                try:
                    s, e = map(int, r.split('-'))
                    return "".join([doc[i].get_text() for i in range(max(0,s-1), min(e, len(doc)))])
                except: pass
            return "".join([page.get_text() for page in doc])

        # تصحيح أسماء المتغيرات لتفادي NameError
        test_txt = get_pdf_text(t_file)
        policy_txt = get_pdf_text(p_file)
        book_txt = get_pdf_text(b_file, pg_range)

        prompt = f"""
        حلل الاختبار بناءً على النموذج الرسمي التالي:
        1. جدول تحليل المفردات الامتحانية (المفردة، الهدف، AO1/AO2، الدرجة، الملاحظة، التعديل).
        2. الجدول العامل (عدد المفردات، عدد الدروس، مجموع درجات AO1 و AO2، المشتتات، جودة الرسوم).
        3. التقدير العام ونسبة المطابقة.

        بيانات الاختبار: {test_txt}
        بيانات الكتاب: {book_txt[:5000]}
        """
        
        response = model.generate_content(prompt)
        st.markdown(response.text)
