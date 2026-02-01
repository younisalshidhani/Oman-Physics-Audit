import streamlit as st
import fitz 
import google.generativeai as genai

# إعدادات الصفحة
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
                # قراءة الملف
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = "".join([page.get_text() for page in doc])
                
                # استخدام الموديل المستقر 1.5-flash
                model = genai.GenerativeModel('gemini-1.5-flash') 
                
                # توجيهات الذكاء الاصطناعي (Prompt)
                prompt = f"""
                أنت خبير تربوي في فيزياء كامبريدج سلطنة عمان. حلل الاختبار التالي بناءً على:
                1. وثيقة التقويم (الاختبار القصير الثاني 10 درجات).
                2. كتاب الفيزياء ص 32 (تأثير دوبلر).
                3. جودة الصياغة (4 بدائل للمتعدد).
                
                نص الاختبار:
                {text}
                """
                
                response = model.generate_content(prompt)
                st.success("✅ اكتمل التحليل بنجاح!")
                st.markdown("### 📋 تقرير التدقيق الفني:")
                st.write(response.text)
                
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
