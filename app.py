import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة والاتجاه العربي
st.set_page_config(page_title="المقوم التربوي العماني الذكي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .main-header { background-color: #ffffff; padding: 20px; border-radius: 12px; border-right: 10px solid #2ecc71; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    
    # العناصر الجديدة بالترتيب المطلوب
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    grade_level = st.selectbox("المرحلة الصفية:", ["الحادي عشر", "الثاني عشر"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "استقصائي"])
    
    # نطاق الصفحات
    pg_range = st.text_input("نطاق الصفحات (مثلاً 10-15):", help="سيتم التمعن في هذه الصفحات فقط")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # استخدام موديل مستقر لتجنب خطأ 404 (Gemini 1.5 Flash هو الأنسب حالياً)
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        st.write(f"### 📁 رفع ملفات مشروع ({subject} - الصف {grade_level})")
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 1. ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 2. وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 3. كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 بدء المطابقة والتحليل الشامل"):
            with st.spinner(f"جاري التمعن في مادة {subject}..."):
                def extract_text(file, r=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(s-1, min(e, len(doc)))])
                        except: return "".join([p.get_text() for p in doc])
                    return "".join([p.get_text() for p in doc])

                test_txt = extract_text(t_file)
                pol_txt = extract_text(p_file) if p_file else "معايير عمان العامة"
                book_txt = extract_text(b_file, pg_range) if b_file else "محتوى الكتاب"

                prompt = f"""
                بصفتك خبير جودة تربوي في سلطنة عمان لمادة {subject}.
                البيانات المحددة: [الصف: {grade_level} | الفصل: {semester} | نوع الاختبار: {exam_type}]
                
                المطلوب:
                1. جدول Markdown دقيق: (المفردة | الدرجة | الهدف | مطابقة الهدف | الملاحظة الفنية | التعديل | الحالة).
                2. استخدم الرموز (✅ مطابق، ⚠️ ملاحظة، 🚨 حرج) في عمود الحالة.
                3. التمعن: قارن الرسوم البيانية والمصطلحات العلمية في الاختبار مع صفحات الكتاب المحددة ({pg_range}).
                4. تجنب الحشو الإنشائي؛ ركز على الملاحظات التقنية فقط.
                
                المراجع المرفقة:
                - الكتاب: {book_txt[:6000]}
                - الوثيقة: {pol_txt[:2000]}
                - الاختبار: {test_txt}
                
                خاتمة التقرير:
                ضع "العبارة التقييمية النهائية" ونسبة المطابقة (%) بشكل بارز ومنظم.
                """
                
                res = model.generate_content(prompt)
                st.session_state.report = res.text

        if "report" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state.report)
            st.download_button("📥 تحميل التقرير كملف نصي", st.session_state.report, "Audit_Report.txt")

    except Exception as e:
        st.error(f"تنبيه تقني: {e}")
else:
    st.info("أدخل مفتاح API للبدء.")
