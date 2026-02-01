import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد واجهة التطبيق الاحترافية
st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام التدقيق والمطابقة الثلاثية (فيزياء 12)")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # استخدام الموديل المتوفر والمستقر في حسابك
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        st.subheader("📁 تحميل ملفات المشروع")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("1. ملف الاختبار")
            test_file = st.file_uploader("ارفع الاختبار (PDF)", type="pdf", key="test")
        with col2:
            st.success("2. وثيقة التقويم")
            policy_file = st.file_uploader("ارفع الوثيقة (PDF)", type="pdf", key="policy")
        with col3:
            st.warning("3. كتاب الطالب")
            book_file = st.file_uploader("ارفع صفحة الكتاب (PDF)", type="pdf", key="book")
        
        if test_file:
            if st.button("🚀 بدء المطابقة والتحليل الشامل"):
                with st.spinner("جاري معالجة البيانات وصياغة الجدول..."):
                    def get_text(file):
                        doc = fitz.open(stream=file.read(), filetype="pdf")
                        return "".join([page.get_text() for page in doc])

                    t_text = get_text(test_file)
                    p_text = get_text(policy_file) if policy_file else "معايير الاختبار القصير (10 درجات)"
                    b_text = get_text(book_file) if book_file else "درس تأثير دوبلر ص 32"

                    prompt = f"""
                    بصفتك خبير جودة تربوي، حلل الاختبار التالي بناءً على المراجع المرفقة.
                    يجب أن يكون الرد الأساسي عبارة عن جدول Markdown بالأعمدة:
                    (رقم المفردة | الدرجة | نوع هدف التقويم | نوع الملاحظة | الملاحظات | التعديل المقترح)
                    
                    المراجع:
                    - الوثيقة: {p_text}
                    - الكتاب: {b_text}
                    - الاختبار: {t_text}
                    
                    بعد الجدول، اذكر التوصية النهائية ونسبة مطابقة الاختبار (%).
                    """
                    
                    response = model.generate_content(prompt)
                    
                    st.markdown("---")
                    st.success("✅ اكتمل التحليل بنجاح!")
                    
                    # إنشاء التبويبات لتنظيم العرض ومنع التداخل
                    tab1, tab2 = st.tabs(["📊 جدول التحليل الفني", "📝 التوصيات النهائية"])
                    
                    with tab1:
                        st.markdown(response.text)
                    
                    with tab2:
                        st.info("راجع الخلاصة والنسبة المئوية في أسفل التقرير المولد.")
                        
    except Exception as e:
        st.error(f"حدث خطأ فني: {e}")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
