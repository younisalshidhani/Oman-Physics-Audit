import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة والواجهة العربية
st.set_page_config(page_title="المقوم التربوي العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .official-header { background-color: #f8f9fa; padding: 20px; border-bottom: 3px solid #007bff; text-align: center; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_html=True)

# القائمة الجانبية مع كافة الخيارات المطلوبة
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
        # استخدام النسخة v1beta لحل مشكلة 404 في بعض البيئات
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        st.markdown(f'<div class="official-header"><h3>تحليل {exam_type} - مادة {subject}</h3></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 1. ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 2. وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 3. كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 إصدار التقرير الرسمي"):
            with st.spinner("جاري التحليل..."):
                def get_pdf_text(file, r=None):
                    if not file: return ""
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r and '-' in r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(max(0, s-1), min(e, len(doc)))])
                        except: pass
                    return "".join([p.get_text() for p in doc])

                test_txt = get_pdf_text(t_file)
                book_txt = get_pdf_text(b_file, pg_range)
                policy_txt = get_pdf_text(p_file)

                prompt = f"""
                بصفتك خبير جودة، حلل الاختبار المرفق بناءً على النموذج الرسمي التالي حرفياً:

                ### جدول تحليل المفردات الامتحانية
                | المفردة | الهدف التعليمي | هدف التقويم (A01,A02) | الدرجة | نوع الملاحظة (صياغة، علمية، فنية تشمل الرسم) | الملاحظة | التعديل |
                |---|---|---|---|---|---|---|

                ### الجدول العامل للاختبار القصير
                | البند | العدد / الدرجات – نعم / لا | مطابق / غير مطابق |
                |---|---|---|
                | عدد المفردات | | |
                | عدد الدروس | (استنتجه من خلال مطابقة الاختبار بصفحات الكتاب: {pg_range}) | - |
                | درجات أهداف التقويم (A01,A02) | (اجمع درجات كل هدف بشكل منفصل) | |
                | هل توجد مفردة طويلة الإجابة؟ | | |
                | هل توجد مفردتان اختيار من متعدد؟ | | |
                | هل مفردات الاختيار من متعدد تحتوي على (إجابات خاطئة) مشتتات منطقية؟ | | |
                | هل صياغة المفردات وحجم ونوع الخط واضح للقراءة؟ | | |
                | هل الأشكال والرسومات واضحة؟ | | |

                ### التقدير العام للاختبار القصير
                (اكتب تقييماً مختصراً لمستوى الاختبار مع نسبة مطابقة المعايير).

                المعطيات:
                الاختبار: {test_txt}
                الكتاب: {book_txt[:7000]}
                """
                
                response = model.generate_content(prompt)
                st.session_state.final_rep = response.text

        if "final_rep" in st.session_state:
            st.markdown(st.session_state.final_rep)
            st.download_button("📥 تحميل التقرير", st.session_state.final_rep, "Official_Report.txt")

    except Exception as e:
        st.error(f"تنبيه تقني: {e}")
