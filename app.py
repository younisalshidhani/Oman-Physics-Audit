import streamlit as st
import fitz 
import google.generativeai as genai
from fpdf import FPDF
import base64

# إعداد الصفحة والاتجاه العربي الكامل
st.set_page_config(page_title="المقوم التربوي الاحترافي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .eval-footer { 
        background-color: #f0f7ff; 
        padding: 25px; 
        border-radius: 12px; 
        border-right: 10px solid #28a745;
        margin-top: 50px;
        line-height: 1.8;
    }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ خيارات التدقيق")
    api_key = st.text_input("مفتاح API:", type="password")
    pg_range = st.text_input("نطاق صفحات الكتاب (مثلاً 20-25):")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        st.write("### 📁 المستندات المرجعية")
        col1, col2, col3 = st.columns(3)
        with col1: t_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: p_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: b_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if t_file and st.button("🚀 تنفيذ التحليل الفني الشامل"):
            with st.spinner("جاري التمعن في الرسوم والتفاصيل العلمية..."):
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

                prompt = f"""
                أنت خبير جودة تربوي عماني. حلل الاختبار بناءً على المرفقات بدقة متناهية.
                المطلوب:
                1. جدول Markdown: (المفردة | الدرجة | الهدف | مطابقة الهدف | الملاحظة الفنية | التعديل المقترح).
                2. الملاحظات الفنية: ركز على دقة (الرسوم البيانية، الصور، الأشكال) ومطابقتها لصفحات الكتاب المرفقة.
                3. التنسيق: اختصر الملاحظات جداً دون إغفال النقاط المهمة.
                
                البيانات:
                - الكتاب (الصفحات المحددة): {book_txt}
                - الوثيقة: {pol_txt}
                - الاختبار: {test_txt}
                
                خاتمة التقرير:
                أضف قسماً بعنوان "التقييم النهائي الشامل" يتضمن عبارة تقييمية منظمة، تليها نسبة المطابقة (%) في سطر منفصل وبحجم بارز.
                """
                
                res = model.generate_content(prompt)
                st.session_state.report = res.text

        if "report" in st.session_state:
            st.markdown("---")
            # عرض التقرير مع تنظيم الفقرات السفلية
            formatted_report = st.session_state.report.replace("التقييم النهائي الشامل", '<div class="eval-footer"><h3>التقييم النهائي الشامل</h3>')
            if "التقييم النهائي الشامل" in st.session_state.report:
                formatted_report += "</div>"
            
            st.markdown(formatted_report, unsafe_allow_html=True)
            
            # زر التحميل PDF (مبسط لتجنب أخطاء الخطوط العربية في المكتبات البرمجية)
            st.download_button("📥 تحميل النص كملف تدقيق", st.session_state.report, "Audit_Report.txt")

    except Exception as e:
        st.error(f"خطأ: {e}")
else:
    st.info("أدخل API Key للبدء.")
