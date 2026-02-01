import streamlit as st
import fitz 
import google.generativeai as genai
from fpdf import FPDF
import base64

# إعداد الصفحة والاتجاه
st.set_page_config(page_title="المقوم التربوي الاحترافي", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .evaluation-box { 
        background-color: #e8f4fd; 
        padding: 20px; 
        border-radius: 15px; 
        border: 2px solid #3498db;
        margin-top: 30px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# وظيفة تصدير PDF (دعم أساسي للنص)
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # ملاحظة: FPDF تحتاج إعدادات خاصة للغة العربية، هنا سنقوم بتصدير النص الخام
    pdf.multi_cell(0, 10, txt=text.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

with st.sidebar:
    st.header("⚙️ الإعدادات والتحكم")
    api_key = st.text_input("مفتاح API:", type="password")
    selected_pages = st.text_input("حدد صفحات الكتاب (مثلاً: 30-35):", placeholder="اتركه فارغاً لكل الكتاب")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        st.write("### 📁 المستندات المرجعية")
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: policy_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: book_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if test_file and st.button("🚀 إجراء المطابقة النهائية"):
            with st.spinner("جاري التمعن في الصفحات المحددة والمطابقة..."):
                def get_text(file, pages_range=None):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    text = ""
                    # إذا تم تحديد صفحات، نقوم باستخراجها فقط
                    if pages_range:
                        try:
                            start, end = map(int, pages_range.split('-'))
                            for i in range(start-1, min(end, len(doc))):
                                text += doc[i].get_text()
                        except: text = "".join([page.get_text() for page in doc])
                    else:
                        text = "".join([page.get_text() for page in doc])
                    return text

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "المعايير العامة"
                b_text = get_text(book_file, selected_pages) if book_file else "محتوى الكتاب"

                prompt = f"""
                بصفتك خبير جودة، حلل الاختبار بناءً على المراجع المرفقة (خاصة صفحات الكتاب المحددة).
                
                الجدول: (المفردة | الدرجة | الهدف | مطابقة الهدف | الملاحظة الفنية | التعديل المقترح).
                * ركز بشدة على دقة (الرسوم البيانية، الصور، الأشكال) ومطابقتها للكتاب.
                * اختصر الملاحظات لتكون تقنية بحتة.
                
                المراجع:
                - الصفحات المستهدفة من الكتاب: {b_text[:5000]} 
                - وثيقة التقويم: {p_text[:2000]}
                - نص الاختبار: {t_text}
                
                في نهاية التقرير:
                ضع "العبارة التقييمية النهائية" ونسبة المطابقة (%) بشكل بارز جداً ومنفصل.
                """
                
                response = model.generate_content(prompt)
                st.session_state.last_report = response.text

        if "last_report" in st.session_state and st.session_state.last_report:
            st.markdown("---")
            st.markdown(st.session_state.last_report)
            
            # زر التصدير
            pdf_data = create_pdf(st.session_state.last_report)
            st.download_button(label="📥 تحميل التقرير كـ PDF", 
                               data=pdf_data, 
                               file_name="Audit_Report.pdf", 
                               mime="application/pdf")

    except Exception as e:
        st.error(f"تنبيه: {e}")
else:
    st.info("يرجى إدخال مفتاح API للبدء.")
