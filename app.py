import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة
st.set_page_config(page_title="نظام التقويم العماني الذكي", layout="wide")

# تنسيق الواجهة لتطابق الصور المطلوبة
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .main-header { background-color: #f1f8ff; padding: 20px; border-radius: 10px; border-right: 8px solid #007bff; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# استعادة كافة خيارات التدقيق في الجهة اليمنى (Sidebar)
with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    grade_level = st.selectbox("المرحلة الصفية:", ["الحادي عشر", "الثاني عشر"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "استقصائي"])
    pg_range = st.text_input("نطاق الصفحات (مثلاً 77-97):", value="97-77")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # استخدام النسخة الأكثر استقراراً لتجنب خطأ 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        st.markdown(f'<div class="main-header"><h2>تحليل {exam_type} - مادة {subject} - الصف {grade_level}</h2></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 1. ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 2. وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 3. كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 إصدار التقرير الرسمي"):
            with st.spinner("جاري تطبيق المعايير العمانية الرسمية..."):
                def get_text(file, r=None):
                    if not file: return ""
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r and '-' in r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(max(0, s-1), min(e, len(doc)))])
                        except: pass
                    return "".join([p.get_text() for p in doc])

                # تعريف المتغيرات بأسماء واضحة لتجنب أخطاء التعريف
                content_test = get_text(t_file)
                content_policy = get_text(p_file) if p_file else "المعايير العامة"
                content_book = get_text(b_file, pg_range) if b_file else "نص الكتاب"

                # البرومبت المعتمد كلياً على ملف الوورد المرفق
                prompt = f"""
                بصفتك خبير تربوي عماني، أنتج تقريراً يطابق العناصر التالية:
                
                ### جدول تحليل المفردات الامتحانية
                (أعمدة: المفردة، الهدف التعليمي، هدف التقويم A01/A02، الدرجة، نوع الملاحظة، الملاحظة، التعديل)

                ### الجدول العامل للاختبار القصير
                (أعمدة: البند، العدد/الدرجات، مطابق/غير مطابق)
                - احسب عدد المفردات.
                - حدد عدد الدروس بمطابقة الأسئلة مع صفحات الكتاب: {pg_range}.
                - اجمع درجات أهداف التقويم (A01, A02) بشكل منفصل.
                - قيم جودة الرسوم والصياغة.

                ### التقدير العام للاختبار القصير
                (اكتب تقييماً مختصراً وشاملاً مع نسبة المطابقة)

                البيانات المستخرجة:
                الاختبار: {content_test}
                الكتاب: {content_book[:6000]}
                """
                
                response = model.generate_content(prompt)
                st.session_state.final_report = response.text

        if "final_report" in st.session_state:
            st.markdown(st.session_state.final_report)
            st.download_button("📥 تحميل التقرير الرسمي", st.session_state.final_report, "Report.txt")

    except Exception as e:
        st.error(f"خطأ تقني: {e}")
