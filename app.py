import streamlit as st
import fitz
import google.generativeai as genai
import os
import ssl

# إجبار النظام على تجاهل أخطاء الشهادات في كل مكان
os.environ['PYTHONHTTPSVERIFY'] = '0'
if not environ.get('PYTHONHTTPSVERIFY', '') == '0':
    ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="المقوم الذكي - فيزياء 12", layout="wide")
st.title("🛡️ نظام التدقيق الآلي للاختبارات (فيزياء 12)")

with st.sidebar:
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        uploaded_file = st.file_uploader("ارفع ملف الاختبار القصير (PDF)", type="pdf")
        
        if uploaded_file:
            with st.spinner("جاري استخراج النص والتحليل..."):
                # قراءة الملف
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = "".join([page.get_text() for page in doc])
                
                if text:
                    st.info("تم قراءة نص الاختبار بنجاح، جاري الاتصال بالمحرك...")
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"بصفتك خبير تربوي عماني، حلل هذا الاختبار وفق وثيقة التقويم (10 درجات) وكتاب الفيزياء: {text[:2000]}"
                    
                    response = model.generate_content(prompt)
                    st.success("✅ اكتمل التحليل!")
                    st.markdown(response.text)
                else:
                    st.error("لم نتمكن من قراءة نص من الملف، تأكد أنه ملف PDF أصلي.")
                    
    except Exception as e:
        st.warning(f"وصلنا للملف ولكن هناك مشكلة في الاتصال: {e}")
        st.info("نصيحة: جرب تشغيل VPN بسيط أو التأكد من أن وقت وجهاز الكمبيوتر مضبوط بدقة.")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")