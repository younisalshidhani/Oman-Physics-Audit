import streamlit as st
import fitz 
import google.generativeai as genai
from fpdf import FPDF
import io

# 1. إعداد الصفحة والواجهة العربية
st.set_page_config(page_title="المقوم التربوي الاحترافي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .main-header { background-color: #ffffff; padding: 20px; border-radius: 12px; border-right: 10px solid #2ecc71; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .eval-card { background-color: #f8fafc; padding: 25px; border: 1px solid #e2e8f0; border-radius: 10px; margin-top: 40px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    pg_range = st.text_input("نطاق الصفحات (مثلاً 10-15):", help="سيتم التمعن في هذه الصفحات فقط")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        st.write("### 📁 رفع الوثائق الحالية")
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 الوثيقة", type="pdf")
        with col3: b_file = st.file_uploader("📚 الكتاب", type="pdf")
        
        if t_file and st.button("🚀 تحليل ومطابقة مجهرية"):
            with st.spinner("جاري فحص الصور والكلمات والرسوم..."):
                def extract(file, r=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(s-1, min(e, len(doc)))])
                        except: return "".join([p.get_text() for p in doc])
                    return "".join([p.get_text() for p in doc])

                test_txt = extract(t_file)
                pol_txt = extract(p_file) if p_file else "معايير عمان"
                book_txt = extract(b_file, pg_range) if b_file else "محتوى الكتاب"

                # البرومبت المصمم خصيصاً لمنع انهيار الجداول وتكثيف التمعن
                prompt = f"""
                بصفتك خبير جودة تربوي، قم بالتمعن في الملفات المرفقة:
                كتاب الطالب (صفحات مختارة): {book_txt[:6000]}
                وثيقة التقويم: {pol_txt[:2000]}
                محتوى الاختبار: {test_txt}

                المطلوب (بصيغة تقنية مباشرة):
                1. جدول Markdown نظيف (المفردة | الدرجة | الهدف | مطابقة الهدف | الملاحظة | التعديل | الحالة).
                2. في عمود الملاحظة: ركز حصراً على (الرسوم البيانية، الصور، الكلمات العلمية) ومدى دقتها.
                3. استخدم (✅ مطابق، ⚠️ ملاحظة، 🚨 حرج) في عمود الحالة.
                4. التزم بإنشاء الجدول فوراً دون مقدمات لضمان التنسيق.
                
                خاتمة التقرير:
                أضف "العبارة التقييمية النهائية الشاملة" ونسبة المطابقة (%) في سطر مستقل ومنظم بوضوح.
                """
                
                res = model.generate_content(prompt)
                st.session_state.report = res.text

        if "report" in st.session_state:
            st.markdown("---")
            # عرض التقرير (مع ضمان التنسيق)
            st.markdown(st.session_state.report)
            
            # قسم تصدير PDF
            st.markdown("---")
            if st.button("📥 توليد تقرير PDF للتحميل"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=10)
                # تنظيف النص وتصديره (النص الخام لضمان السرعة)
                clean_text = st.session_state.report.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 8, txt=clean_text)
                
                buf = io.BytesIO()
                pdf.output(dest='S').encode('latin-1') # معالجة المخرجات
                st.download_button("💾 اضغط هنا لتحميل PDF", data=pdf.output(dest='S'), file_name="Report.pdf")

    except Exception as e:
        st.error(f"تنبيه: {e}")
else:
    st.info("أدخل API Key للبدء.")
