import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام المطابقة والتدقيق الثلاثي (فيزياء 12)")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("أدخل مفتاح API:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro') 
        
        col1, col2 = st.columns(2)
        with col1:
            test_file = st.file_uploader("1. ارفع ملف الاختبار", type="pdf")
        with col2:
            ref_files = st.file_uploader("2. ارفع الوثيقة أو صفحة الكتاب (اختياري لدقة 100%)", type="pdf", accept_multiple_files=True)
        
        if test_file:
            with st.spinner("جاري فحص الملفات والمطابقة المباشرة..."):
                # قراءة الاختبار
                test_doc = fitz.open(stream=test_file.read(), filetype="pdf")
                test_text = "".join([page.get_text() for page in test_doc])
                
                # قراءة المراجع إذا وجدت
                ref_text = ""
                if ref_files:
                    for f in ref_files:
                        ref_doc = fitz.open(stream=f.read(), filetype="pdf")
                        ref_text += "".join([page.get_text() for page in ref_doc])

                prompt = f"""
                أنت خبير جودة. قارن "نص الاختبار" بـ "المراجع المرفقة".
                إذا لم تتوفر مراجع، اعتمد على وثيقة تقويم عمان 2024 وكتاب الفيزياء ص 32.
                
                المطلوب: جدول Markdown (رقم المفردة، الدرجة، الهدف، الملاحظة، التعديل).
                المراجع المرفقة: {ref_text if ref_text else 'اعتمد على ذاكرتك البرمجية للمنهج العماني'}
                نص الاختبار: {test_text}
                """
                
                response = model.generate_content(prompt)
                st.success("✅ تمت المطابقة المباشرة بنجاح!")
                st.markdown(response.text)
                
    except Exception as e:
        st.error(f"خطأ: {e}")
else:
    st.info("يرجى إدخال مفتاح API للبدء.")
