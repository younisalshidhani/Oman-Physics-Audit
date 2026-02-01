import streamlit as st
import fitz 
import google.generativeai as genai
import os

st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام التدقيق الآلي للاختبارات (فيزياء 12)")

with st.sidebar:
    st.header("الإعدادات")
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        uploaded_file = st.file_uploader("ارفع ملف الاختبار (PDF)", type="pdf")
        
        if uploaded_file:
            with st.spinner("جاري التحليل والمطابقة مع معايير الوزارة..."):
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = "".join([page.get_text() for page in doc])
                
                # التعديل الجوهري هنا لضمان عمل الموديل
                model = genai.GenerativeModel('gemini-1.5-flash-001') 
                
                prompt = f"بصفتك خبير تربوي عماني، حلل هذا الاختبار بناءً على وثيقة التقويم (10 درجات) وكتاب الفيزياء ص 32: {text}"
                
                response = model.generate_content(prompt)
                st.success("✅ اكتمل التحليل بنجاح!")
                st.markdown("### 📋 تقرير التدقيق الفني:")
                st.write(response.text)
    except Exception as e:
        # إذا استمر الخطأ، سيقترح عليك البرنامج الحل آلياً
        st.error(f"خطأ في الاتصال: {e}")
        st.info("نصيحة: تأكد أن مفتاح API مفعل وأنك تستخدم إصداراً حديثاً من الموديل.")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")

