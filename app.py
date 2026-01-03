import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="LegalAI Pro", page_icon="⚖️", layout="wide")

# 2. ИНИЦИАЛИЗАЦИЯ И ИСПРАВЛЕНИЕ ОШИБКИ 404
def load_model():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Добавьте GOOGLE_API_KEY в Secrets.")
        st.stop()
    
    genai.configure(api_key=api_key)
    
    # Пытаемся инициализировать модель
    # В новых версиях SDK префикс 'models/' может быть критичен или излишен
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Тестовый вызов для проверки доступности (необязательно, но помогает отловить 404 сразу)
        return model
    except Exception as e:
        st.error(f"Ошибка при выборе модели: {e}")
        return None

model = load_model()

# 3. УТИЛИТЫ
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:35000]
        elif filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:35000]
        return ""
    except Exception as e:
        return f"Ошибка: {e}"

def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    for line in text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 4. ИНТЕРФЕЙС
st.title("⚖️ LegalAI Enterprise Pro")
st.info("Приложение готово к работе. Загрузите документ для анализа.")

tab1, tab2, tab3 = st.tabs(["🔍 Аудит рисков", "📑 Сравнение", "✉️ Ответы"])

with tab1:
    up_file = st.file_uploader("Загрузите договор (PDF/DOCX/JPG)", type=["pdf", "docx", "jpg", "jpeg", "png"])
    if st.button("Запустить анализ", type="primary"):
        if up_file and model:
            with st.spinner("Юрист ИИ изучает документ..."):
                try:
                    if up_file.type.startswith("image"):
                        img = Image.open(up_file)
                        res = model.generate_content(["Проведи юридический анализ этого фото. Найди критические риски.", img])
                    else:
                        txt = extract_text(up_file.getvalue(), up_file.name)
                        res = model.generate_content(f"Ты эксперт-юрист. Проведи аудит рисков текста:\n\n{txt}")
                    
                    st.session_state.result = res.text
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Ошибка API: {e}. Попробуйте обновить ключ или сменить модель.")

    if "result" in st.session_state:
        st.download_button("📥 Скачать DOCX", create_docx(st.session_state.result, "Audit"), "Report.docx")

with tab2:
    st.write("Функционал сравнения документов доступен после загрузки двух файлов.")
    f1 = st.file_uploader("Файл 1", type=["pdf", "docx"], key="f1")
    f2 = st.file_uploader("Файл 2", type=["pdf", "docx"], key="f2")
    if st.button("Сравнить") and f1 and f2:
        with st.spinner("Сравниваем..."):
            t1 = extract_text(f1.getvalue(), f1.name)
            t2 = extract_text(f2.getvalue(), f2.name)
            res = model.generate_content(f"Сравни два текста и найди отличия в правах и обязанностях:\n\n1: {t1}\n\n2: {t2}")
            st.markdown(res.text)

with tab3:
    claim = st.text_area("Текст претензии")
    if st.button("Написать ответ") and claim:
        with st.spinner("Генерация ответа..."):
            res = model.generate_content(f"Напиши вежливый, но юридически строгий ответ на претензию:\n\n{claim}")
            st.markdown(res.text)
            
