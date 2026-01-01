import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# 1. Настройка
st.set_page_config(page_title="LegalAI")

# 2. API Ключ
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Ключ не найден!")
    st.stop()

# 3. Дизайн
st.title("⚖️ Юрист-Аудитор 2026")
cat = st.selectbox("Тип:", ["Кредиты", "Туризм", "Аренда", "Труд", "Другое"])
file = st.file_uploader("Файл (PDF/DOCX)", type=["pdf", "docx", "txt"])
txt = st.text_area("Или текст:")

# 4. Логика
if st.button("Проверить"):
    content = ""
    if file:
        try:
            if file.type == "application/pdf":
                pdf = PdfReader(file)
                content = "".join([p.extract_text() for p in pdf.pages])
            elif "word" in file.type:
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode()
        except:
            st.error("Ошибка чтения файла")
    else:
        content = txt

    if content:
        with st.spinner("Думаю..."):
            try:
                prompt = f"Ты юрист. Категория: {cat}. Найди риски: {content}"
                res = model.generate_content(prompt)
                st.markdown(res.text)
            except Exception as e:
                st.error(f"Ошибка: {e}")
    else:
        st.warning("Пусто!")
