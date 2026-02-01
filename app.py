import streamlit as st
import fitz 
import google.generativeai as genai
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# إعداد الصفحة والاتجاه
st.set_page_config(page_title="المقوم التربوي الاحترافي", layout="wide")

# تنسيق الواجهة لتبدو احترافية
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .report-container { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; }
    .eval-box { background-color: #f0f9ff; padding: 20px; border-right: 10px solid #007bff; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API:", type="password")
    pg_range = st.text_input("الصفحات المستهدفة (مثلاً 12-15):")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 الوثيقة", type="pdf")
        with col3: b_file = st.file_uploader("📚 الكتاب", type="pdf")
        
        if t_file and st.button("🚀 تحليل عميق وشامل"):
            with st.spinner("جاري فحص الرسوم والبيانات والمطابقة..."):
                def extract(file, r=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    if r:
                        try:
                            s, e = map(int, r.split('-'))
                            return "".join([doc[i].get_text() for i in range(s-1, min(e, len(doc)))])
                        except: return "".join([p.get_text() for p in doc])
                    return "".join([p.get_text() for p in doc])

                test_txt = extract(t_file)
                pol_txt = extract(p_file) if p_file else "وثيقة عمان"
                book_txt = extract(b_file, pg_range) if b_file else "محتوى المادة"

                # البرومبت المطور لمنع انهيار الجدول
                prompt = f"""
                أنت خبير تربوي. حلل الاختبار بناءً على المرفقات.
                البيانات: [كتاب: {book_txt} | وثيقة: {pol_txt} | اختبار: {test_txt}]
                
                المطلوب حرفياً وبدون أي كلام جانبي:
                1. جدول Markdown صحيح (أعمدة: المفردة، الدرجة، الهدف، مطابقة الهدف، الملاحظة الفنية، التعديل المقترح).
                2. ركز الملاحظة على (الرسوم البيانية والصور والأشكال) ومدى دقتها علمياً مقارنة بالكتاب.
                3. بعد الجدول، اترك مسافة كبيرة ثم ضع: "التقييم النهائي الشامل" متبوعاً بعبارة تقييمية ونسبة المطابقة (%).
                """
                
                res = model.generate_content(prompt)
                st.session_state.report = res.text

        if "report" in st.session_state:
            st.markdown("---")
            # عرض التقرير في حاوية منظمة لضمان ظهور الجدول كجدول
            with st.container():
                st.markdown(st.session_state.report)
            
            # زر التحميل كملف نصي منظم (لضمان سلامة اللغة العربية)
            st.download_button("📥 تحميل التقرير (Text)", st.session_state.report, "Final_Audit.txt")

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
