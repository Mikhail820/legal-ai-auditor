import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io
from PIL import Image
import re

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="LegalAI Pro - Инструменты", page_icon="⚖️", layout="wide")

# --- ПОДКЛЮЧЕНИЕ К ИИ ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Используем модель Flash для скорости и экономии токенов
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.error("Ошибка: GOOGLE_API_KEY не найден в Secrets!")
    st.stop()

# --- ФУНКЦИИ-ПОМОЩНИКИ ---
def extract_text(file):
    """Извлекает текст из PDF, DOCX и TXT"""
    try:
        if file.name.endswith(".pdf"):
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
        return file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"

def create_docx(text, title="ЮРИДИЧЕСКИЙ ДОКУМЕНТ"):
    """Создает Word-файл из текста"""
    doc = Document()
    doc.add_heading(title, 0)
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- ИНТЕРФЕЙС ---
st.title("⚖️ LegalAI Pro: Анализ и Коммуникации")
st.caption("Универсальный помощник для работы с договорами и претензиями")

# Сайдбар с настройками
with st.sidebar:
    st.header("Настройки ИИ")
    depth = st.select_slider("Глубина проработки:", options=["Базовая", "Стандарт", "Эксперт"], value="Стандарт")
    st.divider()
    st.info("Без авторизации: Доступны все функции")

# Создание вкладок
tab1, tab2, tab3 = st.tabs(["🔍 АНАЛИЗ ДОКУМЕНТА", "🔄 СРАВНЕНИЕ ВЕРСИЙ", "✉️ ГЕНЕРАТОР ОТВЕТА"])

# --- ВКЛАДКА 1: АНАЛИЗ ---
with tab1:
    st.subheader("Поиск рисков и аудит")
    up_file = st.file_uploader("Загрузите файл или фото договора", type=['pdf','docx','jpg','png','jpeg'], key="anal_up")
    
    if st.button("🚀 Начать анализ", use_container_width=True):
        if up_file:
            with st.spinner("ИИ изучает документ..."):
                # Проверка: фото или текст
                content = Image.open(up_file) if up_file.type.startswith('image') else extract_text(up_file)
                
                prompt = f"""Ты опытный юрист. Проведи анализ документа. Глубина: {depth}.
                1. Оцени общую безопасность.
                2. Составь таблицу: | Пункт | Риск | Рекомендация |.
                3. Напиши краткий вердикт: подписывать или нет."""
                
                # Запрос к Gemini
                response = model.generate_content([prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{prompt}\n\n{content}")
                st.session_state.analysis_res = response.text
        else:
            st.warning("Сначала загрузите файл")

    if 'analysis_res' in st.session_state:
        st.markdown(st.session_state.analysis_res)
        st.download_button("📥 Скачать анализ в Word", data=create_docx(st.session_state.analysis_res), file_name="Legal_Analysis.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Что изменилось в новой версии?")
    c1, c2 = st.columns(2)
    file_old = c1.file_uploader("Оригинал (DOCX/PDF)", type=['pdf','docx'], key="old")
    file_new = c2.file_uploader("Версия от контрагента", type=['pdf','docx'], key="new")
    
    if st.button("⚖️ Сравнить и найти отличия", use_container_width=True):
        if file_old and file_new:
            with st.spinner("Сравниваю тексты..."):
                t_old, t_new = extract_text(file_old), extract_text(file_new)
                diff_prompt = "Сравни два текста договора. Выдели только существенные изменения (цены, сроки, штрафы, подсудность). Оформи в виде таблицы: Старая версия | Новая версия | В чем риск."
                res = model.generate_content(f"{diff_prompt}\n\nОригинал: {t_old[:15000]}\n\nНовый: {t_new[:15000]}")
                st.session_state.diff_res = res.text

    if 'diff_res' in st.session_state:
        st.markdown(st.session_state.diff_res)

# --- ВКЛАДКА 3: ГЕНЕРАТОР ОТВЕТА ---
with tab3:
    st.subheader("Написание официального письма")
    st.write("ИИ составит текст письма на основе документа и вашей позиции.")
    
    doc_in = st.file_uploader("Загрузите документ, на который нужно ответить", type=['pdf','docx','jpg','png'], key="gen_up")
    user_wish = st.text_area("Ваши пожелания к ответу:", placeholder="Например: Согласиться на сроки, но потребовать убрать пункт о предоплате.")
    
    if st.button("✍️ Создать текст ответа", use_container_width=True):
        if doc_in:
            with st.spinner("Пишу письмо..."):
                content = Image.open(doc_in) if doc_in.type.startswith('image') else extract_text(doc_in)
                reply_prompt = f"""Ты юридический консультант. Напиши официальный ответ контрагенту на основе этого документа.
                Моя позиция: {user_wish if user_wish else "Вежливо обсудить условия и защитить мои интересы"}.
                Стиль: Официально-деловой. Обязательно добавь ссылки на ГК РФ. Сделай структуру: Шапка, Суть, Предложение, Подпись."""
                
                response = model.generate_content([reply_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{reply_prompt}\n\n{content}")
                st.session_state.reply_res = response.text

    if 'reply_res' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state.reply_res)
        st.download_button("📥 Скачать готовое письмо", data=create_docx(st.session_state.reply_res, "ОФИЦИАЛЬНОЕ ПИСЬМО"), file_name="Letter_Reply.docx")
