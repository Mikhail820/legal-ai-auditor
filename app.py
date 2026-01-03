import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# 1. НАСТРОЙКИ ИНТЕРФЕЙСА
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 2. ИНИЦИАЛИЗАЦИЯ МОДЕЛИ (GEMINI 2.0 FLASH)
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: Ключ API не найден.")
        st.stop()
    
    # Настройка с использованием REST для стабильности
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Пробуем новейшую версию 2.0 Flash
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        return model
    except Exception:
        # Резервный вариант на случай, если 2.0 не включена для ключа
        return genai.GenerativeModel('gemini-1.5-flash')

model = init_gemini()

# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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
        return ""
    except Exception as e:
        return f"Ошибка парсинга: {e}"

def save_to_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 4. ИНТЕРФЕЙС
st.title("⚖️ LegalAI Enterprise Pro (v2.0 Flash)")
st.info("Используется модель нового поколения для максимальной точности анализа.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

with tab1:
    mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
    if mode == "Файл / Фото":
        up_file = st.file_uploader("Загрузите договор", type=["pdf", "docx", "png", "jpg", "jpeg"])
    else:
        manual_txt = st.text_area("Вставьте текст:", height=300)

    if st.button("🔍 ЗАПУСТИТЬ АНАЛИЗ"):
        target_data = None
        is_img = False
        
        if mode == "Файл / Фото" and up_file:
            if up_file.type.startswith("image"):
                target_data, is_img = Image.open(up_file), True
            else:
                target_data = extract_text(up_file.getvalue(), up_file.name)
        elif mode == "Текст" and manual_txt:
            target_data = manual_txt
            
        if target_data:
            with st.spinner("Нейросеть 2.0 анализирует документ..."):
                try:
                    prompt = "Ты ведущий юрист. Проведи глубокий аудит рисков этого документа. Выдели критические пункты."
                    if is_img:
                        res = model.generate_content([prompt, target_data])
                    else:
                        res = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{target_data}")
                    st.session_state.audit_out = res.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")

    if "audit_out" in st.session_state:
        st.markdown(st.session_state.audit_out)
        st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.audit_out, "Audit"), "Report.docx")

with tab2:
    st.subheader("Сравнение")
    c1, c2 = st.columns(2)
    f1, f2 = c1.file_uploader("Файл 1"), c2.file_uploader("Файл 2")
    if st.button("⚖️ СРАВНИТЬ") and f1 and f2:
        with st.spinner("Сравнение..."):
            t1, t2 = extract_text(f1.getvalue(), f1.name), extract_text(f2.getvalue(), f2.name)
            res = model.generate_content(f"Найди отличия между документами:\n1: {t1}\n2: {t2}")
            st.markdown(res.text)

with tab3:
    st.subheader("Ответы")
    claim = st.text_area("Суть проблемы:")
    if st.button("✍️ СОЗДАТЬ ОТВЕТ") and claim:
        with st.spinner("Генерация..."):
            res = model.generate_content(f"Напиши юридический ответ: {claim}")
            st.markdown(res.text)
        
