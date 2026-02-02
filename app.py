import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة والواجهة
st.set_page_config(page_title="المقوم التربوي العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .official-card { background-color: #f8fbff; padding: 25px; border-radius: 15px; border-right: 10px solid #007bff; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# استعادة القائمة الجانبية بكامل خياراتها الأصلية
with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    semester = st.selectbox("الفصل الدراسي:", ["الأول", "الثاني"])
    grade_level = st.selectbox("المرحلة الصفية:", ["الحادي عشر", "الثاني عشر"])
    exam_type = st.selectbox("نوع الاختبار:", ["قصير", "استقصائي"])
    pg_range = st.text_input("نطاق الصفحات (مثلاً 10-15):", value="77-97")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        st.markdown(f'<div class="official-card"><h2>نظام تحليل {exam_type} - مادة {subject}</h2><p>وفق وثيقة تقويم تعلم الطلبة ومعايير سلطنة عمان</p></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 1. ملف الاختبار (PDF)", type="pdf")
        with col2: p_file = st.file_uploader("📜 2. وثيقة التقويم (PDF)", type="pdf")
        with col3: b_file = st.file_uploader("📚 3. كتاب الطالب (PDF)", type="pdf")
        
        if t_file and st.button("🚀 بدء المطابقة والتحليل الشامل"):
            with st.spinner("جاري استخراج البيانات وتطبيق النموذج الرسمي..."):
                def extract_text(file, pages=None):
                    if not file: return ""
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if pages and '-' in pages:
                        try:
                            start, end = map(int, pages.split('-'))
                            return "".join([doc[i].get_text() for i in range(max(0, start-1), min(end, len(doc)))])
                        except: pass
                    return "".join([page.get_text() for page in doc])

                # استخراج النصوص بأسماء متغيرات صحيحة
                test_data = extract_text(t_file)
                book_data = extract_text(b_file, pg_range)
                policy_data = extract_text(p_file)

                # بناء البرومبت بناءً على نموذج الوورد الرسمي المرفق
                prompt = f"""
                أنت خبير تقويم تربوي عماني. حلل الاختبار بناءً على النموذج الرسمي التالي:

                ### جدول تحليل المفردات الامتحانية
                | المفردة | الهدف التعليمي | هدف التقويم (A01,A02) | الدرجة | نوع الملاحظة | الملاحظة | التعديل |
                |---|---|---|---|---|---|---|

                ### الجدول العامل للاختبار القصير
                | البند | العدد / الدرجات – نعم / لا | مطابق / غير مطابق |
                |---|---|---|
                | عدد المفردات | | |
                | عدد الدروس | (استنتجه من مطابقة الاختبار بكتاب الطالب صفحات {pg_range}) | |
                | درجات أهداف التقويم (A01,A02) | | |
                | هل توجد مفردة طويلة الإجابة؟ | | |
                | هل صياغة المفردات والرسوم واضحة؟ | | |

                ### التقدير العام للاختبار القصير
                (اكتب هنا مستوى الاختبار بشكل عام ونسبة مطابقته للمعايير بدون إطالة).

                البيانات:
                الاختبار: {test_data}
                الكتاب: {book_data[:6000]}
                """
                
                res = model.generate_content(prompt)
                st.session_state.report = res.text

        if "report" in st.session_state:
            st.markdown(st.session_state.report)
            st.download_button("📥 تحميل التقرير الرسمي", st.session_state.report, "Official_Oman_Report.txt")

    except Exception as e:
        st.error(f"خطأ في الاتصال: تأكد من مفتاح API ومن تحديث المكتبات. التفاصيل: {e}")
