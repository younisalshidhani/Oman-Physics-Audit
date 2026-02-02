import streamlit as st
import fitz 
import google.generativeai as genai

# إعداد الصفحة وتفادي أخطاء التنسيق القديمة
st.set_page_config(page_title="المقوم التربوي العماني", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .header-box { background-color: #f0f7ff; padding: 20px; border-radius: 10px; border-right: 10px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    subject = st.selectbox("المادة:", ["فيزياء", "كيمياء", "أحياء", "العلوم البيئية"])
    pg_range = st.text_input("نطاق الصفحات (مثلاً 77-97):")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # استخدام النسخة الأحدث لتجنب خطأ 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        st.markdown('<div class="header-box"><h2>نظام تحليل الاختبارات القصيرة (النموذج الرسمي)</h2></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 إصدار التقرير النهائي"):
            with st.spinner("جاري استخراج البيانات وتحليل المفردات..."):
                def get_txt(file, r=None):
                    if not file: return ""
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(max(0, s-1), min(e, len(doc)))])
                        except: pass
                    return "".join([p.get_text() for p in doc])

                # تعريف المتغيرات بأسماء صحيحة لتجنب NameError
                test_content = get_txt(t_file)
                book_content = get_txt(b_file, pg_range)
                policy_content = get_txt(p_file)

                prompt = f"""
                بصفتك خبير تربوي، حلل الاختبار بناءً على 'نموذج تقرير تطبيق الذكاء الاصطناعي':
                
                المخرجات المطلوبة (جداول Markdown):
                1. جدول تحليل المفردات الامتحانية [cite: 2]: (المفردة، الهدف، AO1/AO2، الدرجة، الملاحظة الفنية، التعديل)[cite: 3].
                2. الجدول العامل للاختبار القصير [cite: 4]: (عدد المفردات، عدد الدروس، مجموع درجات AO1/AO2، المشتتات المنطقية، جودة الرسوم)[cite: 5].
                3. التقدير العام [cite: 6]: تقييم مختصر ونسبة المطابقة[cite: 7].

                بيانات الاختبار: {test_content}
                بيانات الكتاب: {book_content[:7000]}
                """
                
                res = model.generate_content(prompt)
                st.markdown(res.text)
                st.success("تم التحليل وفق المعايير الرسمية.")

    except Exception as e:
        st.error(f"تنبيه: تأكد من تحديث المكتبات. الخطأ: {e}")
