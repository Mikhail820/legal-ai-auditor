import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup # Для работы со ссылками
from PIL import Image
import io
import re
import os
import base64

# --- 1. CONFIG & STYLES ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    .main-header { font-size: 2.2rem; color: #FF4B4B; text-align: center; margin-bottom: 1rem; }
    /* Стили для подсветки */
    .critical-risk { background-color: #ffe5e5; border-left: 5px solid #ff4b4b; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Оставляем твою модель, раз она работает
TARGET_MODEL = "gemini-2.5-flash-lite"

# --- 2. CORE ENGINE ---
def call_gemini_direct(prompt, image_bytes=None):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    # Используем v1beta для новых функций
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TARGET_MODEL}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    else:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            st.error(f"Ошибка API: {response.text}")
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
    return None

# --- 3. HELPERS ---
def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:40000]
        elif filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:40000]
        return ""
    except: return "Ошибка чтения файла."

def extract_from_url(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(["script", "style", "nav", "footer"]): s.decompose()
        return soup.get_text(separator=' ')[:30000]
    except: return "Не удалось загрузить текст по ссылке."

def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    clean_text = re.sub(r'[*#_`>]', '', text)
    for line in clean_text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Параметры анализа")
    # Добавили выбор аудитории
    audience = st.radio("Аудитория:", ["Гражданин", "Предприниматель", "Юрист"])
    jurisdiction = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "ЕС", "Международная"])
    analysis_depth = st.select_slider("Детальность:", options=["Кратко", "Стандарт", "Максимум"])
    
    st.divider()
    if st.button("🗑️ Сбросить всё", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. MAIN UI ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Pro</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

with tab1:
    col_in, col_res = st.columns([1, 1.2])
    with col_in:
        # Добавили "Ссылка" в варианты
        input_type = st.radio("Источник:", ["Файл / Скан", "Вставить текст", "Ссылка"], horizontal=True)
        
        target_content = None
        is_image = False
        
        if input_type == "Файл / Скан":
            up_file = st.file_uploader("Загрузите договор", type=["pdf", "docx", "png", "jpg", "jpeg"])
            if up_file:
                if up_file.type.startswith("image"):
                    target_content, is_image = up_file.getvalue(), True
                else:
                    target_content = extract_text(up_file.getvalue(), up_file.name)
        elif input_type == "Ссылка":
            url_input = st.text_input("Вставьте URL оферты:")
            if url_input:
                target_content = extract_from_url(url_input)
        else:
            target_content = st.text_area("Вставьте текст договора:", height=300)

        if st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ", type="primary"):
            if target_content:
                with col_res:
                    with st.spinner("Юрист ИИ изучает документ..."):
                        # Промпт теперь учитывает аудиторию
                        p = f"Ты эксперт-юрист. Твоя аудитория: {audience}. Юрисдикция: {jurisdiction}. Глубина: {analysis_depth}. Найди риски. Используй 🔴 для критических рисков."
                        
                        if is_image:
                            res = call_gemini_direct(p, target_content)
                        else:
                            res = call_gemini_direct(f"{p}\n\nДОКУМЕНТ:\n{target_content}")
                        
                        if res:
                            st.session_state.audit_res = res
            else:
                st.warning("Предоставьте данные для анализа.")

    if "audit_res" in st.session_state:
        with col_res:
            # Подсветка: делим текст на блоки и ищем красный маркер
            for block in st.session_state.audit_res.split('\n'):
                if "🔴" in block:
                    st.markdown(f'<div class="critical-risk">{block}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(block)
            
            st.download_button("📥 Скачать в Word", create_docx(st.session_state.audit_res, "Аудит Рисков"), "Legal_Audit.docx")

# Вкладки tab2 и tab3 остаются без изменений, чтобы ничего не сломать
with tab2:
    st.subheader("Сравнение версий")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Версия А (Оригинал)", type=["pdf", "docx"], key="c1")
    f2 = c2.file_uploader("Версия Б (Правки)", type=["pdf", "docx"], key="c2")
    if st.button("⚖️ СРАВНИТЬ") and f1 and f2:
        with st.spinner("Сравниваем..."):
            t1, t2 = extract_text(f1.getvalue(), f1.name), extract_text(f2.getvalue(), f2.name)
            res = call_gemini_direct(f"Сравни два текста. Выведи таблицу изменений и риски. Юрисдикция: {jurisdiction}.\n1: {t1}\n2: {t2}")
            if res: st.markdown(res)

with tab3:
    st.subheader("Генератор ответов")
    claim = st.text_area("Текст претензии или письма:")
    user_goal = st.text_input("Ваша позиция:", value="Защита интересов")
    if st.button("✍️ СФОРМИРОВАТЬ ОТВЕТ") and claim:
        with st.spinner("Пишем письмо..."):
            res = call_gemini_direct(f"Напиши официальный ответ на претензию. Юрисдикция: {jurisdiction}. Позиция: {user_goal}.\n\nТЕКСТ:\n{claim}")
            if res:
                st.session_state.ans_res = res
                st.markdown(res)
                st.download_button("📥 Скачать ответ", create_docx(st.session_state.ans_res, "Официальный Ответ"), "Response.docx")
