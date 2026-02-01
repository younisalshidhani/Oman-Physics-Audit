import streamlit as st
import fitz  # سيتم التعرف عليها لأنك وضعت pymupdf في requirements
import google.generativeai as genai
import os

# إعداد واجهة التطبيق
st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام التدقيق الآلي للاختبارات (فيزياء 12)")
st.subheader("مطابق لوثيقة التقويم 2024/2025 وكتاب الفيزياء")

with st.sidebar:
    st.header("الإعدادات")
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        uploaded_file = st.file_uploader("ارفع ملف الاختبار (PDF)", type="pdf")
        
        if uploaded_file:
            with st.spinner("جاري التحليل والمطابقة..."):
                # قراءة الملف المستند إلى مكتبة pymupdf
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = "".join([page.get_text() for page in doc])
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"""
                بصفتك خبير تربوي في سلطنة عمان، حلل هذا الاختبار بناءً على:
                1. وثيقة تقويم العلوم (الاختبار القصير الثاني من 10 درجات).
                2. كتاب الفيزياء 12 (دروس الموجات وتأثير دوبلر ص 32).
                3. جودة البدائل (4 بدائل لكل سؤال موضوعي).
                
                نص الاختبار:
                {text}
                """
                
                response = model.generate_content(prompt)
                st.success("✅ تم التحليل بنجاح!")
                st.markdown("### 📋 تقرير التدقيق الفني:")
                st.write(response.text)
    except Exception as e:
        st.error(f"حدث خطأ أثناء الاتصال: {e}")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
