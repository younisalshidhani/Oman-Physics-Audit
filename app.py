import streamlit as st
import fitz 
import google.generativeai as genai

st.set_page_config(page_title="المقوم الذكي العماني", layout="wide")

# تصميم رأس الصفحة بشكل احترافي
st.markdown("""
    <div style="background-color:#f0f2f6;padding:20px;border-radius:10px;border-right:8px solid #007bff">
        <h1 style="margin:0">🛡️ المقوم الذكي: فيزياء 12</h1>
        <p style="margin:0;color:#555">المطابقة الثلاثية: اختبار - وثيقة - كتاب</p>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("أدخل مفتاح API:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # استخدام Gemini 2.5 Flash للسرعة والدقة
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        st.write("### 📁 رفع المستندات")
        col1, col2, col3 = st.columns(3)
        with col1: test_file = st.file_uploader("📄 ملف الاختبار", type="pdf")
        with col2: policy_file = st.file_uploader("📜 وثيقة التقويم", type="pdf")
        with col3: book_file = st.file_uploader("📚 كتاب الطالب", type="pdf")
        
        if test_file and st.button("🚀 تحليل وحساب النسبة"):
            with st.spinner("جاري التحليل التربوي الدقيق..."):
                def get_text(file):
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    return "".join([page.get_text() for page in doc])

                t_text = get_text(test_file)
                p_text = get_text(policy_file) if policy_file else "10 درجات، فيزياء 12"
                b_text = get_text(book_file) if book_file else "تأثير دوبلر ص 32"

                prompt = f"""
                بصفتك خبير تربوي عماني، حلل الاختبار بناءً على المراجع المرفقة بدقة وموضوعية.
                
                المراجع:
                - الوثيقة: {p_text}
                - الكتاب: {b_text}
                - الاختبار: {t_text}
                
                المطلوب:
                1. جدول Markdown بالأعمدة: (المفردة | الدرجة | الهدف | الملاحظة | التعديل).
                2. اجعل الملاحظات "مركزة" (فنية أو علمية) دون إطالة.
                3. احسب "نسبة المطابقة" بناءً على: (صحة المحتوى، توزيع الدرجات، مطابقة الأهداف).
                4. لا تكن متشدداً جداً؛ إذا كان السؤال صحيحاً علمياً وتربوياً، صنفه كـ "مطابق".
                
                الخاتمة: اذكر "التوصية" و "النسبة" بشكل بارز.
                """
                
                response = model.generate_content(prompt)
                
                st.markdown("---")
                # عرض النسبة في بطاقة بارزة
                st.success("✅ اكتمل التدقيق")
                st.markdown(response.text)
                
    except Exception as e:
        st.error(f"خطأ: {e}")
else:
    st.warning("يرجى إدخال مفتاح API في القائمة الجانبية.")
