import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة لتكون واسعة ومنظمة
st.set_page_config(page_title="المقوم الذكي - سلطنة عمان", layout="wide")
st.title("🛡️ نظام التدقيق والمطابقة الثلاثية (فيزياء 12)")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ إعدادات الاتصال")
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")
    st.info("سيتم استخدام هذا المفتاح لتفعيل الذكاء الاصطناعي للمطابقة.")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro') 
        
        # إنشاء ثلاثة أجزاء (أعمدة) لرفع الملفات
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
                with st.spinner("جاري قراءة الملفات الثلاثة والمطابقة بينها..."):
                    # 1. قراءة نص الاختبار
                    test_doc = fitz.open(stream=test_file.read(), filetype="pdf")
                    test_text = "".join([page.get_text() for page in test_doc])
                    
                    # 2. قراءة نص الوثيقة (إن وجدت)
                    policy_text = ""
                    if policy_file:
                        p_doc = fitz.open(stream=policy_file.read(), filetype="pdf")
                        policy_text = "".join([page.get_text() for page in p_doc])
                    
                    # 3. قراءة نص الكتاب (إن وجد)
                    book_text = ""
                    if book_file:
                        b_doc = fitz.open(stream=book_file.read(), filetype="pdf")
                        book_text = "".join([page.get_text() for page in b_doc])

                    # صياغة الأمر الموجه للذكاء الاصطناعي
                    prompt = f"""
                    بصفتك خبير جودة تربوي في سلطنة عمان، قم بإجراء مطابقة ثلاثية دقيقة.
                    
                    المراجع المرفقة:
                    - محتوى وثيقة التقويم: {policy_text if policy_text else 'اعتمد على معايير الاختبار القصير (10 درجات)'}
                    - محتوى كتاب الطالب: {book_text if book_text else 'اعتمد على درس تأثير دوبلر ص 32'}
                    
                    المطلوب تحليل نص الاختبار التالي بناءً عليها:
                    {test_text}
                    
                    أخرج النتائج في جدول Markdown بالأعمدة:
                    (رقم المفردة | الدرجة | نوع هدف التقويم | نوع الملاحظة | الملاحظات | التعديل المقترح)
                    
                    ثم أضف:
                    1. التوصية النهائية المختصرة.
                    2. نسبة مطابقة الاختبار للمعايير (%).
                    """
                    
                    response = model.generate_content(prompt)
                    st.markdown("---")
                    st.success("✅ اكتمل التحليل بنجاح!")
                    st.markdown("### 📋 تقرير التدقيق والمطابقة الثلاثية:")
                    st.markdown(response.text)
                
    except Exception as e:
        st.error(f"حدث خطأ أثناء المعالجة: {e}")
else:
    st.info("يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
