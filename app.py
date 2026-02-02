import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة والواجهة العربية
st.set_page_config(page_title="المحلل التربوي العماني الذكي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .official-header { background-color: #f1f8ff; padding: 20px; border-radius: 10px; border-right: 8px solid #007bff; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    grade_level = st.selectbox("المرحلة الصفية:", ["الحادي عشر", "الثاني عشر"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "استقصائي"])
    pg_range = st.text_input("نطاق الصفحات (مثلاً 77-97):")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        st.markdown(f'<div class="official-header"><h2>تحليل {exam_type} - مادة {subject}</h2></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 1. ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 2. وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 3. كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 إصدار التقرير الرسمي"):
            with st.spinner("جاري التحليل وتطبيق النموذج الرسمي..."):
                def get_text(file, r=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(s-1, min(e, len(doc)))])
                        except: return "".join([p.get_text() for p in doc])
                    return "".join([p.get_text() for p in doc])

                test_txt = get_text(t_file)
                policy_txt = get_text(p_file) if p_file else "المعايير الرسمية"
                book_txt = get_text(b_file, pg_range) if b_file else "محتوى الكتاب"

                prompt = f"""
                أنت خبير تقويم تربوي. حلل الاختبار المرفق لمادة {subject} بناءً على النموذج الرسمي التالي حرفياً:

                ### جدول تحليل المفردات الامتحانية
                | المفردة | الهدف التعليمي | هدف التقويم (AO1,AO2) | الدرجة | نوع الملاحظة (صياغة، علمية، فنية تشمل الرسم) | الملاحظة | التعديل |
                |---|---|---|---|---|---|---|

                ### الجدول العامل للاختبار القصير
                | البند | العدد / الدرجات – نعم / لا | مطابق / غير مطابق |
                |---|---|---|
                | عدد المفردات | | |
                | عدد الدروس | (استنتجه بمطابقة الأسئلة مع مواضيع الكتاب المرفق) | - |
                | درجات أهداف التقويم (AO1,AO2) | (اجمع درجات AO1 و AO2 بشكل منفصل) | |
                | هل توجد مفردة طويلة الإجابة؟ | | |
                | هل توجد مفردتان اختيار من متعدد؟ | (اذكر العدد الفعلي) | |
                | هل مفردات الاختيار من متعدد تحتوي على (إجابات خاطئة) مشتتات منطقية؟ | | |
                | هل صياغة المفردات وحجم ونوع الخط واضح للقراءة؟ | | |
                | هل الأشكال والرسومات واضحة؟ | | |

                ### التقدير العام للاختبار القصير
                (اكتب هنا مستوى الاختبار بشكل عام ومختصر ويقدره إذا مناسب مع إعطاء نسبة مدى مطابقته للمعايير بدون إطاله)

                البيانات:
                - الاختبار: {test_txt}
                - الكتاب (صفحات {pg_range}): {book_txt[:8000]}
                - الوثيقة: {policy_txt[:2000]}
                """
                
                response = model.generate_content(prompt)
                st.session_state.report = response.text

        if "report" in st.session_state:
            st.markdown(st.session_state.report)
            st.download_button("📥 تحميل التقرير (Text)", st.session_state.report, "Official_Report.txt")

    except Exception as e:
        st.error(f"تنبيه تقني: {e}")
