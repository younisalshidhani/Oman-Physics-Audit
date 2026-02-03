import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# 1. إعداد الصفحة
st.set_page_config(page_title="نظام تدقيق الاختبارات - سلطنة عمان", layout="wide")

# 2. تنسيق الواجهة لليمين (RTL) بشكل إجباري
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { text-align: right; direction: rtl; }
    div[data-testid="stMarkdownContainer"] { text-align: right; direction: rtl; }
    .report-box { border: 2px solid #007bff; padding: 20px; border-radius: 10px; background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

# 3. القائمة الجانبية (تمت استعادة الفصل الدراسي)
with st.sidebar:
    st.header("⚙️ إعدادات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # القوائم المنسدلة المطلوبة
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "علوم"])
    semester = st.selectbox("الفصل الدراسي:", ["الاول", "الثاني"])  # تم إضافته كما طلبت
    grade = st.selectbox("المرحلة الصفية:", ["11", "12"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "نهائي/تجريبي"])
    pages = st.text_input("نطاق الصفحات (مثلاً 77-97):", value="77-97")

# 4. واجهة التطبيق الرئيسية
st.title(f"🔍 نظام تدقيق اختبارات {subject} ({semester})")
st.info("النظام يعمل وفق وثيقة تقويم تعلم الطلبة بوزارة التربية والتعليم - سلطنة عمان")

col1, col2, col3 = st.columns(3)
with col1: file_test = st.file_uploader("1. ملف الاختبار (PDF)", type="pdf")
with col2: file_policy = st.file_uploader("2. وثيقة التقويم (PDF)", type="pdf")
with col3: file_book = st.file_uploader("3. كتاب الطالب (PDF)", type="pdf")

# 5. منطق التحليل
if st.button("🚀 بدء التحليل الشامل") and api_key and file_test:
    try:
        genai.configure(api_key=api_key)
        # استخدام الموديل المتوافق مع المكتبة المحدثة
        model = genai.GenerativeModel('gemini-1.5-flash')

        with st.spinner("جاري قراءة الملفات ومطابقة المعايير..."):
            
            def get_text(uploaded_file):
                if not uploaded_file: return "لا يوجد ملف"
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                return "".join([page.get_text() for page in doc])

            # استخراج النصوص
            txt_test = get_text(file_test)
            txt_policy = get_text(file_policy)
            txt_book = get_text(file_book)

            # البرومبت المتقن
            prompt = f"""
            بصفتك خبير تربوي في مناهج سلطنة عمان، قم بتحليل اختبار مادة {subject} للصف {grade} الفصل {semester}.
            
            استخدم البيانات التالية:
            - نص الاختبار: {txt_test}
            - نص الكتاب (الصفحات {pages}): {txt_book[:15000]}
            
            المطلوب تقرير دقيق جداً يحتوي على الجداول التالية:
            
            1. **جدول تحليل المفردات**:
               (رقم السؤال | الهدف التعليمي | مستوى الهدف (A01/A02) | الدرجة | الملاحظات الفنية)
            
            2. **الجدول العامل (المطابقة)**:
               - هل الأسئلة مشتقة من الصفحات {pages}؟
               - عدد المفردات ونوعها.
               - توزيع الدرجات.
            
            3. **التقدير العام**:
               حكم نهائي على جودة الاختبار ومطابقته للوثيقة.
            """

            response = model.generate_content(prompt)
            
            st.markdown("---")
            st.subheader("📋 التقرير الرسمي:")
            st.markdown(f'<div class="report-box">{response.text}</div>', unsafe_allow_html=True)
            
            # زر التحميل
            st.download_button("📥 تحميل التقرير", response.text, file_name="Report.txt")

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
        st.warning("تنبيه: إذا ظهر خطأ 404، يرجى حذف التطبيق وإعادة نشره لتحديث المكتبات.")
