import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم التربوي - نسخة المختبر", layout="wide")

# تهيئة الذاكرة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

# واجهة مستخدم نظيفة
st.markdown("""
    <div style="background-color:#ffffff;padding:15px;border-radius:10px;border-right:8px solid #2ecc71;box-shadow: 0 2px 10px rgba(0,0,0,0.05)">
        <h2 style="margin:0;color:#2c3e50">🛡️ نظام التدقيق التقني المركّز</h2>
        <p style="margin:0;color:#7f8c8d">تحليل مباشر | مطابقة صارمة | لغة تقنية</p>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    api_key = st.text_input("API Key:", type="password")
    if st.button("🗑️ مسح الجلسة"):
        st.session_state.chat_history = []
        st.session_state.last_report = ""
        st.rerun()

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("الاختبار (PDF)", type="pdf")
        with col2: policy_file = st.file_uploader("الوثيقة (PDF)", type="pdf")
        with col3: book_file = st.file_uploader("الكتاب (PDF)", type="pdf")
        
        if test_file and st.button("🔍 تحليل البيانات"):
            with st.spinner("جاري الاستخراج والمطابقة..."):
                def get_text(file):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    return "".join([page.get_text() for page in doc])

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "المعايير القياسية"
                b_text = get_text(book_file) if book_file else "المحتوى العلمي المرجعي"

                # البرومبت الجديد: التركيز على البيانات والابتعاد عن الإنشائيات
                prompt = f"""
                بصفتك محلل بيانات تربوي، استخرج الأخطاء والمطابقات بدقة تقنية عالية.
                
                المراجع: [وثيقة: {p_text} | كتاب: {b_text} | اختبار: {t_text}]
                
                قواعد الرد الصارمة:
                1. ممنوع المقدمات (أهلاً، بصفتي، إلخ).
                2. الجدول: (المفردة | الدرجة | الهدف | الملاحظة | التعديل).
                3. الملاحظة: يجب أن تكون تقنية مباشرة (مثال: "مخالف لصفحة 32"، "نقص بديل"، "هدف غير مطابق").
                4. النسبة: رقم مئوي بناءً على (صحة علمية + مطابقة مواصفات).
                5. التوصية: جملة واحدة تقنية فقط.
                """
                
                response = model.generate_content(prompt)
                st.session_state.last_report = response.text

        if st.session_state.last_report:
            st.markdown("---")
            st.markdown(st.session_state.last_report)
            
            # قسم الدردشة التقنية
            st.markdown("---")
            st.subheader("💬 نقاش تقني حول النتائج")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

            if user_input := st.chat_input("اسأل عن تفاصيل تقنية محددة..."):
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"): st.markdown(user_input)

                with st.chat_message("assistant"):
                    # توجيه الدردشة لتكون مختصرة أيضاً
                    chat_prompt = f"أجب باختصار شديد ودقة تقنية بناءً على هذا التقرير: {st.session_state.last_report}\nالسؤال: {user_input}"
                    chat_response = model.generate_content(chat_prompt)
                    st.markdown(chat_response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": chat_response.text})

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("أدخل مفتاح API للبدء.")
