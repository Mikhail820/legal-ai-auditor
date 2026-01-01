import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document

st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash')
else:
    st.error("Ключ API не найден!")
    st.stop()

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

if st.button("🚀 Начать проверку"):
    content = ""
    if file:
        try:
            if file.name.endswith(".pdf"):
                reader = PdfReader(file)
                content = "".join([p.extract_text() for p in reader.pages])
            elif file.name.endswith(".docx"):
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Ошибка чтения: {e}")
    else:
        content = txt

    if content:
        with st.spinner("Анализирую (это может занять до 30 сек)..."):
            try:
                # Промпт для качественного ответа
                prompt = f"Ты эксперт-юрист. Категория: {cat}. Найди 5 рисков для клиента в этом тексте и предложи исправления: {content}"
                res = model.generate_content(prompt)
                st.success("Готово!")
                st.markdown(res.text)
            except Exception as e:
                st.warning("Перегрузка. Пробую резерв...")
                try:
                    # Запасной вариант - проверенная временем 1.5 Flash
                    res = genai.GenerativeModel('models/gemini-1.5-flash').generate_content(prompt)
                    st.markdown(res.text)
                except Exception as e2:
                    st.error("Превышен лимит запросов. Подождите 1 минуту.")
    else:
        st.warning("Текст не найден!")
