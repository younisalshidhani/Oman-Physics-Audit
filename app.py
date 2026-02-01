import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام التدقيق الآلي للاختبارات (فيزياء 12)")

with st.sidebar:
    st.header("الإعدادات")
    # تأكد من وضع المفتاح الذي استخرجته من Google AI Studio هنا
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # التعديل الذهبي: نستخدم الموديل المتاح في قائمتك
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        uploaded_file = st.file_uploader("ارفع ملف الاختبار (PDF)", type="pdf")
        
        if uploaded_file:
            with st.spinner("جاري التحليل باستخدام ذكاء Gemini 2.5..."):
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = "".join([page.get_text() for page in doc])
                
                prompt = f"""
                أنت خبير تربوي في سلطنة عمان. حلل هذا الاختبار بناءً على:
                1. وثيقة التقويم (10 درجات للاختبار القصير).
                2. كتاب الفيزياء ص 32 (تأثير دوبلر).
                3. جودة الأسئلة (4 بدائل للمتعدد).
                
                نص الاختبار:
                {text}
                """
                
                response = model.generate_content(prompt)
                st.success("✅ تم التحليل بنجاح!")
                st.markdown("### 📋 تقرير التدقيق الفني:")
                st.write(response.text)
                
    except Exception as e:
        st.error(f"خطأ في الموديل: {e}")
        st.info("نصيحة: إذا استمر الخطأ، جرب تغيير 'gemini-2.5-flash' إلى 'gemini-2.5-pro' في الكود.")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
