import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# 1. إعداد الصفحة
st.set_page_config(page_title="المدقق التربوي العماني", layout="wide")

# 2. تنسيق الواجهة لليمين (RTL)
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    .report-box { border: 2px solid #007bff; padding: 20px; border-radius: 10px; background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

# 3. القائمة الجانبية (الإعدادات)
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API (Google):", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    grade = st.selectbox("الصف:", ["11", "12"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "نهائي"])
    pages = st.text_input("أرقام الصفحات (مثلاً 10-20):", value="10-20")

# 4. العنوان الرئيسي
st.title(f"🔍 نظام تدقيق اختبارات {subject}")
st.info("النظام يعمل وفق وثيقة تقويم تعلم الطلبة بوزارة التربية والتعليم - سلطنة عمان")

# 5. منطقة رفع الملفات
col1, col2, col3 = st.columns(3)
with col1: 
    file_test = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: 
    file_policy = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: 
    file_book = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

# 6. زر التشغيل والمنطق البرمجي
if st.button("🚀 بدء التحليل الشامل") and api_key and file_test:
    try:
        # إعداد Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        with st.spinner("جاري قراءة الملفات وتحليل البيانات..."):
            # دالة استخراج النص
            def extract_pdf(uploaded_file):
                if uploaded_file is None: return "غير متوفر"
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                return text

            # استخراج النصوص
            txt_test = extract_pdf(file_test)
            txt_book = extract_pdf(file_book)
            txt_policy = extract_pdf(file_policy)

            # البرومبت (التعليمات)
            prompt = f"""
            أنت خبير مناهج عماني. قم بمراجعة هذا الاختبار بناءً على البيانات التالية:
            - المادة: {subject}
            - الصف: {grade}
            
            المطلوب إنشاء تقرير دقيق يحتوي على:
            1. **جدول تحليل المفردات**: (رقم السؤال، الهدف التعليمي، المستوى المعرفي، الدرجة).
            2. **مدى المطابقة**: هل الأسئلة موجودة في الصفحات {pages} من الكتاب؟
            3. **الملاحظات الفنية**: (الرسومات، الصياغة اللغوية، الوضوح).

            نص الاختبار: {txt_test[:10000]}
            نص الكتاب: {txt_book[:10000]}
            نص الوثيقة: {txt_policy[:5000]}
            """

            # إرسال الطلب
            response = model.generate_content(prompt)
            
            # عرض النتيجة
            st.markdown("---")
            st.subheader("📋 التقرير النهائي:")
            st.markdown(f'<div class="report-box">{response.text}</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
        st.warning("تأكد من مفتاح API ومن أن الملفات صالحة.")
