import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم التربوي الشامل", layout="wide")

# تهيئة ذاكرة المحادثة إذا لم تكن موجودة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

st.markdown("""
    <div style="background-color:#ffffff;padding:20px;border-radius:15px;border-right:10px solid #2ecc71;box-shadow: 2px 2px 15px rgba(0,0,0,0.1)">
        <h1 style="margin:0;color:#2c3e50">🛡️ المقوم الذكي (نظام التحليل والنقاش)</h1>
        <p style="margin:0;color:#7f8c8d">حلل اختبارك ثم ناقش الخبير الذكي في النتائج</p>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    api_key = st.text_input("أدخل مفتاح API:", type="password")
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.chat_history = []
        st.rerun()

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        # قسم رفع الملفات
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: policy_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: book_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if test_file and st.button("🔍 بدء التحليل"):
            with st.spinner("جاري التحليل..."):
                def get_text(file):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    return "".join([page.get_text() for page in doc])

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "معايير عامة"
                b_text = get_text(book_file) if book_file else "محتوى عام"

                prompt = f"حلل هذا الاختبار بناءً على المراجع المرفقة وأعطني جدولاً مختصراً ونسبة مطابقة وتوصية.\nالوثيقة: {p_text}\nالكتاب: {b_text}\nالاختبار: {t_text}"
                
                response = model.generate_content(prompt)
                st.session_state.last_report = response.text
                st.session_state.context = f"المراجع: {p_text} {b_text}. الاختبار: {t_text}"

        # عرض التقرير إذا وجد
        if st.session_state.last_report:
            st.markdown("---")
            st.subheader("📊 تقرير التدقيق الفني")
            st.markdown(st.session_state.last_report)
            
            # --- إطار المحادثة أسفل التقرير ---
            st.markdown("---")
            st.subheader("💬 ناقش الخبير حول التقرير")
            
            # عرض رسائل الدردشة السابقة
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # مدخل الدردشة
            if user_input := st.chat_input("اسأل الخبير (مثلاً: اقترح سؤالاً بديلاً للمفردة 3)"):
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    chat_prompt = f"بناءً على التقرير التالي: {st.session_state.last_report}\nوعلى الأسئلة والمراجع الأصلية، أجب على سؤال المستخدم: {user_input}"
                    chat_response = model.generate_content(chat_prompt)
                    st.markdown(chat_response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": chat_response.text})

    except Exception as e:
        st.error(f"تنبيه: {e}")
else:
    st.info("يرجى إدخال مفتاح API للبدء.")
