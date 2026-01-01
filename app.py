import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# Настройка
st.set_page_config(page_title="LegalAI", page_icon="⚖️")

# Ключ
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("Нет ключа API!")
        st.stop()
except Exception as e:
    st.error(f"Ошибка ключа: {e}")

# Интерфейс
st.title("⚖️ Юрист-Аудитор")
category = st.selectbox("Ниша:", ["Кредиты", "Туризм", "Аренда", "Работа", "Другое"])
uploaded_file = st.file_uploader("Файл", type=["pdf", "docx", "txt"])
user_text = st.text_area("Или текст:", height=150)

# Логика
if st.button("Проверить"):
    content = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                content = "".join([p.extract_text() for p in reader.pages])
            elif "word" in uploaded_file.type:
                doc = Document(uploaded_file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = uploaded_file.read().decode("utf-8")
        except:
            st.error("Не удалось прочитать файл.")
    elif user_text:
        content = user_text

    if content:
        with st.spinner("Анализирую..."):
            try:
                msg = f"Ты юрист. Ниша: {category}. Найди риски в тексте: {content}"
                response = model.generate_content(msg)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Ошибка ИИ: {e}")
    else:
        st.warning("Нет текста!")
