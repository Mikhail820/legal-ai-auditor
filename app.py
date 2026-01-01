import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# 1. Настройка страницы
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️")

# 2. Инициализация модели с полным путем (исправляет ошибку 404)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Мы используем полный путь 'models/gemini-1.5-flash'
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.error("Ключ API не найден в Secrets!")
    st.stop()

# 3. Интерфейс
st.title("⚖️ Юрист-Аудитор 2026")
st.write("Проверьте любой договор на наличие скрытых ловушек.")

cat = st.selectbox("Категория договора:", ["Кредиты", "Туризм", "Аренда", "Труд", "Другое"])
file = st.file_uploader("Загрузите файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
txt = st.text_area("Или вставьте текст вручную:")

# 4. Логика работы
if st.button("Проверить на риски"):
    content = ""
    
    # Извлечение текста
    if file:
        try:
            if file.type == "application/pdf":
                pdf = PdfReader(file)
                content = "".join([p.extract_text() for p in pdf.pages])
            elif "word" in file.type:
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Не удалось прочитать файл: {e}")
    else:
        content = txt

    # Отправка в ИИ
    if content:
        with st.spinner("ИИ анализирует документ..."):
            try:
                prompt = f"Ты опытный юрист. Категория: {cat}. Найди 3-5 главных юридических рисков в этом тексте и объясни их: {content}"
                res = model.generate_content(prompt)
                st.success("Анализ готов!")
                st.markdown(res.text)
            except Exception as e:
                st.error(f"Ошибка ИИ: {e}")
                st.info("Попробуйте перезагрузить страницу или проверить лимиты API.")
    else:
        st.warning("Пожалуйста, предоставьте текст или файл для анализа.")
