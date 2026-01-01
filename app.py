import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# 1. Настройка страницы
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️")

# 2. Инициализация модели (Gemini 2.0 Flash)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Переключаемся на самую свежую модель 2.0
    model = genai.GenerativeModel('gemini-2.0-flash-exp') 
else:
    st.error("Ключ API не найден!")
    st.stop()

# 3. Интерфейс
st.title("⚖️ Юрист-Аудитор 2026")

# Добавили Банковские договоры в начало списка
cat = st.selectbox("Категория договора:", [
    "Банковское обслуживание (карты, вклады)", 
    "Кредиты и ипотека", 
    "Аренда недвижимости",
    "Трудовой договор",
    "Образование (курсы)",
    "Другое"
])

file = st.file_uploader("Загрузите договор (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
txt = st.text_area("Или вставьте текст вручную:")

# 4. Логика
if st.button("Проверить на риски"):
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
                content = file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Ошибка чтения файла: {e}")
    else:
        content = txt

    if content:
        with st.spinner("ИИ 2.0 анализирует документ..."):
            try:
                prompt = f"Ты старший юрист. Категория: {cat}. Найди 5 самых опасных ловушек в этом тексте и объясни, почему это плохо для клиента: {content}"
                res = model.generate_content(prompt)
                st.success("Анализ завершен!")
                st.markdown(res.text)
            except Exception as e:
                st.error(f"Ошибка модели 2.0: {e}")
                # Если 2.0 не сработает, пробуем проверенную 1.5 Pro
                st.info("Пробую запасную модель...")
                model_alt = genai.GenerativeModel('gemini-1.5-pro')
                res = model_alt.generate_content(prompt)
                st.markdown(res.text)
    else:
        st.warning("Пожалуйста, предоставьте текст.")
        
