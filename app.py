import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. НАСТРОЙКИ СТРАНИЦЫ
# ==================================================
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. ДВИЖОК GEMINI (ФОРСИРОВАНИЕ V1)
# ==================================================
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден в Secrets.")
        st.stop()
    
    # Настройка конфигурации с явным указанием транспорта
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Пытаемся создать модель. Используем имя без префикса, 
        # так как transport='rest' сам корректирует эндпоинты.
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        st.error(f"Ошибка инициализации: {e}")
        return None

model = init_gemini()

# ==================================================
# 3. ПОЛЕЗНЫЕ ФУНКЦИИ
# ==================================================
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
    # Очистка текста от Markdown разметки
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. БОКОВАЯ ПАНЕЛЬ
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "ЕС", "США", "Международная"])
    depth = st.select_slider("Глубина анализа", options=["Базовая", "Стандартная", "Экспертная"])
    
    if st.button("🗑️ Очистить кэш"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ Внимание: Система ИИ не заменяет юриста. Проверяйте результаты.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

# --- TAB 1: АУДИТ ---
with tab1:
    mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
    
    if mode == "Файл / Фото":
        uploaded_file = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
    else:
        text_input = st.text_area("Вставьте текст договора сюда:", height=300)

    if st.button("🔍 ЗАПУСТИТЬ АУДИТ"):
        # Проверка данных
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
            
        if not data_to_analyze:
            st.error("Пожалуйста, предоставьте документ или текст.")
        else:
            with st.spinner("Юрист ИИ изучает документ..."):
                try:
                    prompt = f"Ты эксперт-юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Выполни аудит рисков и дай рекомендации."
                    
                    if is_image:
                        response = model.generate_content([prompt, data_to_analyze])
                    else:
                        response = model.generate_content(f"{prompt}\n\nДОКУМЕНТ:\n{data_to_analyze}")
                    
                    st.session_state.audit_result = response.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")
                    st.info("Попробуйте нажать 'Очистить кэш' в боковой панели и перезагрузить страницу.")

    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.audit_result, "Legal_Audit"), "Audit_Report.docx")

# --- TAB 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение редакций")
    col1, col2 = st.columns(2)
    f1 = col1.file_uploader("Версия 1", type=["pdf", "docx"], key="compare_f1")
    f2 = col2.file_uploader("Версия 2", type=["pdf", "docx"], key="compare_f2")
    
    if st.button("⚖️ СРАВНИТЬ ВЕРСИИ") and f1 and f2:
        with st.spinner("Сравниваем..."):
            t1 = extract_text(f1.getvalue(), f1.name)
            t2 = extract_text(f2.getvalue(), f2.name)
            res = model.generate_content(f"Сравни тексты и составь таблицу отличий с оценкой рисков.\n\nТекст 1: {t1}\n\nТекст 2: {t2}")
            st.markdown(res.text)

# --- TAB 3: ОТВЕТЫ ---
with tab3:
    st.subheader("Генератор юридических писем")
    claim = st.text_area("Текст входящей претензии:")
    goal = st.text_input("Ваша позиция (цель ответа):")
    
    if st.button("✍️ СОЗДАТЬ ПИСЬМО") and claim:
        with st.spinner("Формируем ответ..."):
            res = model.generate_content(f"Напиши официальный ответ. Позиция: {goal}. Текст претензии: {claim}")
            st.session_state.letter_text = res.text
            st.markdown(st.session_state.letter_text)
            st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.letter_text, "Response_Letter"), "Response.docx")
                 
