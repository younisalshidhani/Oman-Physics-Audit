import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة وتنسيق الاتجاه العربي
st.set_page_config(page_title="المحلل التربوي العماني الذكي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .main-header { background-color: #f1f8ff; padding: 20px; border-radius: 10px; border-right: 8px solid #007bff; margin-bottom: 20px; }
    .report-card { background-color: #ffffff; padding: 25px; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# القائمة الجانبية (Sidebar)
with st.sidebar:
    st.header("⚙️ إعدادات التقويم")
    api_key = st.text_input("مفتاح API:", type="password")
    
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    grade_level = st.selectbox("المرحلة الصفية:", ["الحادي عشر", "الثاني عشر"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "استقصائي"])
    
    pg_range = st.text_input("نطاق الصفحات (مثلاً 77-97):", help="أرقام الصفحات من كتاب الطالب المرتبطة بالاختبار")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # تم ضبط الموديل على النسخة الأكثر استقراراً لتفادي خطأ 404
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        st.markdown(f'<div class="main-header"><h2>تحليل {exam_type} - مادة {subject} - الصف {grade_level}</h2></div>', unsafe_allow_True=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 ملف الاختبار (PDF)", type="pdf")
        with col2: p_file = st.file_uploader("📜 وثيقة التقويم (PDF)", type="pdf")
        with col3: b_file = st.file_uploader("📚 كتاب الطالب (PDF)", type="pdf")
        
        if t_file and st.button("🚀 إصدار التقرير الرسمي"):
            with st.spinner("جاري تطبيق المعايير الرسمية والتحليل الحسابي..."):
                
                def get_pdf_text(file, r=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            start, end = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(start-1, min(end, len(doc)))])
                        except: return "".join([p.get_text() for p in doc])
                    return "".join([p.get_text() for p in doc])

                test_txt = get_pdf_text(t_file)
                policy_txt = get_pdf_text(p_file) if p_file else "المعايير العامة"
                book_txt = get_pdf_text(b_file, pg_range) if b_file else "نص الكتاب"

                # البرومبت النهائي المعتمد على نموذج Word
                prompt = f"""
                أنت خبير تربوي عماني. حلل الاختبار المرفق لمادة {subject} بناءً على نموذج التقرير الرسمي.
                
                يجب أن يتضمن التقرير حصراً العناصر التالية وبنفس المسميات:

                1. **جدول تحليل المفردات الامتحانية**[cite: 2, 3]:
                استخرج المفردات بجدول يحتوي (المفردة | الهدف التعليمي | هدف التقويم AO1,AO2 | الدرجة | نوع الملاحظة | الملاحظة | التعديل).

                2. **الجدول العامل للاختبار القصير**[cite: 4, 5]:
                يجب أن يحتوي البنود التالية (مطابق/غير مطابق):
                - عدد المفردات.
                - عدد الدروس (استنتجه بمطابقة أسئلة الاختبار مع مواضيع الكتاب المرفق).
                - درجات أهداف التقويم (AO1, AO2) - اذكر المجموع الفعلي لكل هدف.
                - هل توجد مفردة طويلة الإجابة؟
                - هل توجد مفردتان اختيار من متعدد؟ (اذكر العدد الفعلي).
                - هل خيارات الاختيار من متعدد تحتوي مشتتات منطقية؟
                - جودة الخط والصياغة والأشكال والرسومات.

                3. **التقدير العام للاختبار القصير**[cite: 6]:
                (اكتب تقييماً مختصراً وشاملاً مع نسبة المطابقة) [cite: 7].

                المحتوى:
                - الاختبار: {test_txt}
                - صفحات الكتاب ({pg_range}): {book_txt[:8000]}
                - الوثيقة: {policy_txt[:2000]}
                """
                
                response = model.generate_content(prompt)
                st.session_state.final_out = response.text

        if "final_out" in st.session_state:
            st.markdown("---")
            st.markdown('<div class="report-card">', unsafe_allow_html=True)
            st.markdown(st.session_state.final_out)
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("📥 تحميل التقرير الرسمي", st.session_state.final_out, "Official_Report.txt")

    except Exception as e:
        st.error(f"تنبيه: تأكد من تحديث نسخة google-generativeai في ملف requirements.txt. الخطأ: {e}")
