import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
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
    </style>
    """, unsafe_allow_html=True)

TARGET_MODEL = "gemini-2.5-flash-lite"

# --- 2. CORE ENGINE ---
def call_gemini_direct(prompt, image_bytes=None):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"
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
        elif response.status_code == 429:
            st.error("⏳ Лимит API. Подождите 30 секунд.")
        else:
            st.error(f"Ошибка API {response.status_code}: {response.text}")
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

# --- 4. SIDEBAR (Настройки и Сброс) ---
with st.sidebar:
    st.header("⚙️ Параметры анализа")
    jurisdiction = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "ЕС", "Международная"])
    analysis_depth = st.select_slider("Детальность:", options=["Кратко", "Стандарт", "Максимум"])
    
    st.divider()
    if st.button("🗑️ Сбросить всё", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. MAIN UI ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Pro</div>', unsafe_allow_html=True)
st.caption(f"Интеллектуальный помощник на базе {TARGET_MODEL}")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

with tab1:
    col_in, col_res = st.columns([1, 1.2])
    with col_in:
        input_type = st.radio("Источник:", ["Файл / Скан", "Вставить текст"], horizontal=True)
        
        target_content = None
        is_image = False
        
        if input_type == "Файл / Скан":
            up_file = st.file_uploader("Загрузите договор", type=["pdf", "docx", "png", "jpg", "jpeg"])
            if up_file:
                if up_file.type.startswith("image"):
                    target_content, is_image = up_file.getvalue(), True
                else:
                    target_content = extract_text(up_file.getvalue(), up_file.name)
        else:
            target_content = st.text_area("Вставьте текст договора из буфера:", height=300)

        if st.button("🚀 ЗАПУСТИТЬ ААНАЛИЗ", type="primary"):
            if target_content:
                with col_res:
                    with st.spinner("Юрист ИИ изучает документ..."):
                        p = f"Ты эксперт-юрист. Юрисдикция: {jurisdiction}. Глубина анализа: {analysis_depth}. Найди все риски и предложи правки."
                        if is_image:
                            res = call_gemini_direct(p, target_content)
                        else:
                            res = call_gemini_direct(f"{p}\n\nДОКУМЕНТ:\n{target_content}")
                        
                        if res:
                            st.session_state.audit_res = res
            else:
                st.warning("Сначала загрузите файл или вставьте текст.")

    if "audit_res" in st.session_state:
        with col_res:
            st.markdown(st.session_state.audit_res)
            st.download_button("📥 Скачать в Word", create_docx(st.session_state.audit_res, "Аудит Рисков"), "Legal_Audit.docx")

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
    user_goal = st.text_input("Ваша позиция (напр. 'Отказ', 'Мирная'):", value="Защита интересов")
    if st.button("✍️ СФОРМИРОВАТЬ ОТВЕТ") and claim:
        with st.spinner("Пишем письмо..."):
            res = call_gemini_direct(f"Напиши официальный ответ на претензию. Юрисдикция: {jurisdiction}. Позиция: {user_goal}.\n\nТЕКСТ:\n{claim}")
            if res:
                st.session_state.ans_res = res
                st.markdown(res)
                st.download_button("📥 Скачать ответ", create_docx(st.session_state.ans_res, "Официальный Ответ"), "Response.docx")
