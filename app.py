import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم الذكي", layout="wide")
st.title("🛡️ نظام التدقيق الذكي - سلطنة عمان")

with st.sidebar:
    api_key = st.text_input("أدخل مفتاح API:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("الاختبار", type="pdf")
        with col2: policy_file = st.file_uploader("الوثيقة", type="pdf")
        with col3: book_file = st.file_uploader("الكتاب", type="pdf")
        
        if test_file and st.button("🚀 تحليل فوري"):
            with st.spinner("جاري التلخيص والمطابقة..."):
                def get_text(file):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    return "".join([page.get_text() for page in doc])

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "10 درجات، فيزياء 12"
                b_text = get_text(book_file) if book_file else "تأثير دوبلر ص 32"

                # البرومبت الجديد يركز على الاختصار ومنع الكلام الإنشائي
                prompt = f"""
                حلل الاختبار بناءً على المراجع المرفقة (وثيقة: {p_text}, كتاب: {b_text}).
                نص الاختبار: {t_text}
                
                شروط العرض (هام جداً):
                1. الجدول: استخدم كلمات مختصرة جداً (مثلاً: "نقص بديل"، "خطأ علمي"، "مطابق").
                2. الأعمدة: (المفردة | الدرجة | الهدف | نوع الملاحظة | الملاحظة | التعديل).
                3. الخلاصة: اذكر النسبة والتوصية في سطر واحد فقط.
                4. ممنوع كتابة أي مقدمات ترحيبية أو فقرات طويلة.
                """
                
                response = model.generate_content(prompt)
                
                # عرض النتائج بشكل مرئي جذاب
                st.markdown("---")
                
                # عرض الجدول في حاوية واسعة
                st.subheader("📊 تقرير المطابقة المختصر")
                st.markdown(response.text)
                
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
else:
    st.info("يرجى إدخال مفتاح API للبدء.")
