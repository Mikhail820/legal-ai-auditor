import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
# ==================================================
st.set_page_config(
    page_title="LegalAI Enterprise Pro",
    page_icon="⚖️",
    layout="wide"
)

# Стилизация
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. ИНИЦИАЛИЗАЦИЯ GEMINI (ФИКС ОШИБКИ 404)
# ==================================================
def init_model():
    # Получаем ключ из secrets или окружения
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден в настройках (Secrets).")
        st.stop()
    
    # Принудительно используем REST для обхода проблем с v1beta
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Прямое указание полного пути модели исправляет 404 Not Found
        return genai.GenerativeModel(model_name='models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"Не удалось инициализировать модель: {e}")
        return None

model = init_model()

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        name = filename.lower()
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:40000]
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:40000]
        elif name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:40000]
        return ""
    except Exception as e:
        return f"Ошибка чтения: {e}"

def save_to_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сформировано LegalAI Pro. Требуется проверка юристом.\n")
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. САЙДБАР
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "ЕС", "США", "Международная"])
    depth = st.select_slider("Глубина анализа", options=["Базовая", "Стандартная", "Экспертная"])
    
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. ОСНОВНОЙ КОНТЕНТ
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ Результаты ИИ требуют обязательной проверки профессиональным юристом.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

# --- ТАБ 1: АНАЛИЗ ---
with tab1:
    mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
    
    if mode == "Файл / Фото":
        data = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
    else:
        data = st.text_area("Вставьте текст договора:", height=300)

    if st.button("🔍 ЗАПУСТИТЬ АНАЛИЗ"):
        if data and model:
            with st.spinner("Проводим юридический аудит..."):
                try:
                    prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Найди риски и дай рекомендации."
                    
                    if mode == "Файл / Фото" and hasattr(data, 'type'):
                        if data.type.startswith("image"):
                            img = Image.open(data)
                            res = model.generate_content([prompt, img])
                        else:
                            txt = extract_text(data.getvalue(), data.name)
                            res = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{txt}")
                    else:
                        res = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{data}")
                    
                    st.session_state.audit_res = res.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")

    if "audit_res" in st.session_state:
        st.markdown(st.session_state.audit_res)
        st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.audit_res, "Audit"), "Legal_Audit.docx")

# --- ТАБ 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение двух версий")
    c1, c2 = st.columns(2)
    f_a = c1.file_uploader("Версия А", type=["pdf", "docx"])
    f_b = c2.file_uploader("Версия Б", type=["pdf", "docx"])
    
    if st.button("⚖️ СРАВНИТЬ") and f_a and f_b:
        with st.spinner("Ищем отличия..."):
            t_a = extract_text(f_a.getvalue(), f_a.name)
            t_b = extract_text(f_b.getvalue(), f_b.name)
            res = model.generate_content(f"Найди отличия между текстом А и Б. Выведи таблицу изменений.\n\nА: {t_a}\n\nБ: {t_b}")
            st.markdown(res.text)

# --- ТАБ 3: ОТВЕТЫ ---
with tab3:
    st.subheader("Генератор официальных ответов")
    context = st.text_area("Текст претензии:")
    goal = st.text_input("Цель ответа:")
    
    if st.button("✍️ СОЗДАТЬ ОТВЕТ") and context:
        with st.spinner("Пишем письмо..."):
            res = model.generate_content(f"Напиши юридический ответ. Цель: {goal}. Текст претензии: {context}")
            st.session_state.ans_res = res.text
            st.markdown(res.text)
            st.download_button("📥 Скачать письмо", save_to_docx(st.session_state.ans_res, "Letter"), "Letter.docx")
        
