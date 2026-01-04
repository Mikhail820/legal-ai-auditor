import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
from PIL import Image
import io
import re
import base64

# --- 1. CONFIG & STYLES ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    .main-header { font-size: 2.2rem; color: #FF4B4B; text-align: center; margin-bottom: 1rem; }
    .critical-risk { 
        background-color: #f0f2f6; 
        border-left: 5px solid #ff4b4b; 
        padding: 15px; 
        border-radius: 5px;
        color: #000000; 
        font-weight: 500;
        margin-bottom: 10px;
        line-height: 1.6;
    }
    .disclaimer-box { 
        font-size: 0.85rem; 
        color: #666; 
        padding: 15px; 
        background-color: #fff3f3; 
        border-radius: 8px; 
        border: 1px solid #ffcccc;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ТВОЯ МОДЕЛЬ (НЕ ТРОГАЕМ)
TARGET_MODEL = "gemini-2.5-flash-lite"
DISCLAIMER_TEXT = "ВНИМАНИЕ: Данный отчет сформирован искусственным интеллектом. Анализ носит информационный характер и не является официальным юридическим заключением. Рекомендуется проверка профессиональным юристом."

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
        else:
            st.error(f"Ошибка API: {response.text}")
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
    return None

# --- 3. HELPERS ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    
    # Добавляем дисклеймер в начало файла Word
    p = doc.add_paragraph()
    p.add_run(DISCLAIMER_TEXT).italic = True
    doc.add_paragraph("-" * 30)

    clean_text = text.replace('*', '').replace('#', '')
    for line in clean_text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

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
    except: return "Ошибка загрузки ссылки."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Параметры")
    audience = st.radio("Аудитория:", ["Гражданин", "Предприниматель", "Юрист"])
    jurisdiction = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "Международная"])
    
    st.divider()
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

    # Дисклеймер в интерфейсе
    st.markdown(f'<div class="disclaimer-box">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)

# --- 5. MAIN UI ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Pro</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ПИСЬМА И ПРОТОКОЛЫ"])

with tab1:
    col_in, col_res = st.columns([1, 1.2])
    with col_in:
        input_type = st.radio("Источник:", ["Файл / Скан", "Вставить текст", "Ссылка"], horizontal=True)
        target_content = None
        is_image = False
        
        if input_type == "Файл / Скан":
            up_file = st.file_uploader("Загрузите документ", type=["pdf", "docx", "png", "jpg"])
            if up_file:
                if up_file.type.startswith("image"):
                    target_content, is_image = up_file.getvalue(), True
                else:
                    target_content = extract_text(up_file.getvalue(), up_file.name)
        elif input_type == "Ссылка":
            url_input = st.text_input("Вставьте URL:")
            if url_input: target_content = extract_from_url(url_input)
        else:
            target_content = st.text_area("Вставьте текст:", height=300)

        if st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ", type="primary"):
            if target_content:
                with col_res:
                    with st.spinner("Анализирую..."):
                        p = f"Ты эксперт-юрист. Роль: {audience}. Юрисдикция: {jurisdiction}. Выдели критические риски 🔴."
                        res = call_gemini_direct(p, target_content) if is_image else call_gemini_direct(f"{p}\n\nДОК:\n{target_content}")
                        if res: st.session_state.audit_res = res

    if "audit_res" in st.session_state:
        with col_res:
            for block in st.session_state.audit_res.split('\n'):
                if "🔴" in block:
                    st.markdown(f'<div class="critical-risk">{block}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(block)
            
            st.download_button(
                label="📥 Скачать Word отчёт",
                data=create_docx(st.session_state.audit_res, "Юридический аудит"),
                file_name="Legal_Audit.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

with tab2:
    st.subheader("Сравнение версий")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Оригинал", type=["pdf", "docx"], key="f1")
    f2 = c2.file_uploader("Правки", type=["pdf", "docx"], key="f2")
    if st.button("⚖️ СРАВНИТЬ"):
        if f1 and f2:
            t1, t2 = extract_text(f1.getvalue(), f1.name), extract_text(f2.getvalue(), f2.name)
            res = call_gemini_direct(f"Сравни два документа и выведи таблицу изменений:\n1: {t1}\n2: {t2}")
            if res: st.markdown(res)

with tab3:
    st.subheader("Генератор документов")
    doc_type = st.selectbox("Что создать?", ["Протокол разногласий (Таблица)", "Претензия", "Сопроводительное письмо"])
    context = st.text_area("Детали ситуации:")
    if st.button("✍️ СГЕНЕРИРОВАТЬ"):
        if context:
            with st.spinner("Пишем..."):
                prompt = "Создай таблицу: пункт договора, наша версия, обоснование." if "Протокол" in doc_type else f"Напиши {doc_type}."
                res = call_gemini_direct(f"{prompt}\n\nКОНТЕКСТ:\n{context}")
                if res:
                    st.markdown(res)
                    st.download_button("📥 Скачать документ", create_docx(res, doc_type), f"{doc_type}.docx")
