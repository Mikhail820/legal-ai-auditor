import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

# 1. Настройка
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️")

# 2. Инициализация (используем Gemini 3 Flash как основную)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Исправленный путь к модели
    model = genai.GenerativeModel('models/gemini-3-flash')
else:
    st.error("Ключ API не найден!")
    st.stop()

# 3. Интерфейс
st.title("⚖️ Юрист-Аудитор 2026")

cat = st.selectbox("Категория договора:", [
    "Банковское обслуживание (карты, вклады)", 
    "Кредиты и ипотека", 
    "Аренда недвижимости",
    "Трудовой договор",
    "Другое"
])

file = st.file_uploader("Загрузите файл", type=["pdf", "docx", "txt"])
txt = st.text_area("Или вставьте текст:")

# 4. Анализ
if st.button("🚀 Начать проверку"):
    content = ""
    if file:
        try:
            if file.type == "application/pdf":
                reader = PdfReader(file)
                content = "".join([p.extract_text() for p in reader.pages])
            elif "word" in file.type:
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode("utf-8")
        except:
            st.error("Ошибка при чтении файла")
    else:
        content = txt

    if content:
        with st.spinner("Gemini 3 анализирует..."):
            try:
                prompt = f"Ты опытный юрист. Категория: {cat}. Найди 5 рисков в этом тексте: {content}"
                res = model.generate_content(prompt)
                st.success("Готово!")
                st.markdown(res.text)
            except Exception as e:
                # Если 429 или 404, пробуем Gemini 1.5 Flash (она самая "живучая")
                st.warning("Основная модель занята, подключаю резерв...")
                try:
                    alt_model = genai.GenerativeModel('models/gemini-1.5-flash')
                    res = alt_model.generate_content(prompt)
                    st.markdown(res.text)
                except Exception as e2:
                    st.error(f"Все модели заняты. Подождите 1 минуту. Ошибка: {e2}")
    else:
        st.warning("Добавьте текст!")
