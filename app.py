import streamlit as st
import fitz 
import google.generativeai as genai

# 1. إعداد الصفحة والاتجاه من اليمين لليسار
st.set_page_config(page_title="المقوم التربوي الذكي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stExpander"] div[role="button"] p { font-size: 1.2rem; font-weight: bold; }
    .report-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-right: 5px solid #2ecc71; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# واجهة المستخدم
st.markdown('<div class="report-card"><h1>🛡️ المقوم التربوي الذكي (نسخة التدقيق المتقدمة)</h1><p>تحليل تخصصي شامل: المادة - الوثيقة - الكتاب</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: policy_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: book_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if test_file and st.button("🚀 تحليل ومطابقة البيانات"):
            with st.spinner("جاري التمعن في تفاصيل الكتاب والوثيقة..."):
                def get_text(file):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    return "".join([page.get_text() for page in doc])

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "معايير عامة"
                b_text = get_text(book_file) if book_file else "محتوى الكتاب"

                # البرومبت المطور بناءً على ملاحظاتك الأخيرة
                prompt = f"""
                بصفتك خبير جودة تربوي، حلل الاختبار بناءً على الكتاب والوثيقة المرفقين.
                
                شروط التحليل الفني:
                1. الجدول: (المفردة | الدرجة | الهدف | مطابقة الهدف للمفردة | الملاحظة | التعديل).
                2. الملاحظة: اختصرها جداً، وركز على (الصور، الرسوم البيانية، الأشكال) ومدى جودتها ومطابقتها للكتاب.
                3. مطابقة الهدف: وضح هل الهدف المقاس في الاختبار يطابق المخطط له في الوثيقة (نعم/لا مع السبب).
                4. التنظيم: اجعل الرد من اليمين لليسار.
                
                البيانات المرفقة:
                - الوثيقة: {p_text}
                - الكتاب: {b_text}
                - الاختبار: {t_text}
                
                بعد الجدول:
                - ملاحظات إضافية مرتبة في نقاط متباعدة.
                - عبارة تقييمية نهائية للاختبار ونسبة المطابقة الإجمالية (%).
                """
                
                response = model.generate_content(prompt)
                st.session_state.last_report = response.text

        if "last_report" in st.session_state and st.session_state.last_report:
            st.markdown("---")
            st.markdown(f'<div style="direction: rtl;">{st.session_state.last_report}</div>', unsafe_allow_html=True)
            
            # إطار المحادثة
            st.markdown("---")
            st.subheader("💬 ناقش الخبير حول التفاصيل")
            user_input = st.chat_input("اسأل عن الرسم البياني أو تفصيل في الكتاب...")
            if user_input:
                chat_response = model.generate_content(f"بناءً على التقرير السابق، أجب باختصار من اليمين لليسار: {user_input}")
                st.info(chat_response.text)

    except Exception as e:
        st.error(f"تنبيه تقني: {e}")
else:
    st.info("يرجى إدخال مفتاح API للبدء.")
