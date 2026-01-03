import streamlit as st
import google.generativeai as genai
from google.generativeai import types
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# 1. НАСТРОЙКИ СТРАНИЦЫ
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 2. ИНИЦИАЛИЗАЦИЯ (ПРИНУДИТЕЛЬНЫЙ ЭНДПОИНТ V1)
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден в Secrets.")
        st.stop()
    
    # Прямая настройка через REST транспорт
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Пытаемся инициализировать модель через полный путь
        # Если v1beta не работает, SDK попробует переключиться на v1 благодаря transport='rest'
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
        return model
    except Exception as e:
        st.error(f"Ошибка инициализации: {e}")
        return None

model = init_gemini()

# 3. УТИЛИТЫ ДЛЯ ФАЙЛОВ
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        name = filename.lower()
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:35000]
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:35000]
        elif name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:35000]
        return ""
    except Exception as e:
        return f"Ошибка чтения файла: {e}"

def save_to_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сгенерировано LegalAI Pro. Требуется юридическая проверка.\n")
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 4. ИНТЕРФЕЙС
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ Внимание: Результаты ИИ требуют проверки юристом.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

with tab1:
    mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
    if mode == "Файл / Фото":
        uploaded_file = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
    else:
        text_input = st.text_area("Вставьте текст договора:", height=300)

    if st.button("🔍 ЗАПУСТИТЬ АНАЛИЗ"):
        data_to_analyze = None
        is_image = False
        
        if mode == "Файл / Фото" and uploaded_file:
            if uploaded_file.type.startswith("image"):
                data_to_analyze = Image.open(uploaded_file)
                is_image = True
            else:
                data_to_analyze = extract_text(uploaded_file.getvalue(), uploaded_file.name)
        elif mode == "Текст" and text_input:
            data_to_analyze = text_input
            
        if data_to_analyze:
            with st.spinner("Анализируем..."):
                try:
                    prompt = "Ты юрист. Найди юридические риски в этом документе и дай рекомендации по их минимизации."
                    if is_image:
                        response = model.generate_content([prompt, data_to_analyze])
                    else:
                        response = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{data_to_analyze}")
                    
                    st.session_state.audit_result = response.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")
                    st.info("Это может быть связано с региональными ограничениями Google. Попробуйте создать новый API-ключ.")

    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.audit_result, "Audit"), "Report.docx")

with tab2:
    st.subheader("Сравнение редакций")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Файл 1", type=["pdf", "docx"], key="f1")
    f2 = c2.file_uploader("Файл 2", type=["pdf", "docx"], key="f2")
    if st.button("⚖️ СРАВНИТЬ") and f1 and f2:
        with st.spinner("Ищем отличия..."):
            t1 = extract_text(f1.getvalue(), f1.name)
            t2 = extract_text(f2.getvalue(), f2.name)
            res = model.generate_content(f"Сравни тексты и найди отличия.\n\n1: {t1}\n\n2: {t2}")
            st.markdown(res.text)

with tab3:
    st.subheader("Генератор ответов")
    claim = st.text_area("Текст претензии:")
    if st.button("✍️ СОЗДАТЬ ПИСЬМО") and claim:
        with st.spinner("Формируем ответ..."):
            res = model.generate_content(f"Напиши юридический ответ на претензию: {claim}")
            st.markdown(res.text)
    
