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
from fpdf import FPDF # Библиотека fpdf2

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
        else:
            st.error(f"Ошибка API: {response.text}")
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
    return None

# --- 3. HELPERS (PDF & DOCX) ---
def create_pdf(text, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    # Очистка текста от символов, которые не поддерживает стандартный шрифт PDF
    clean_text = text.replace('🔴', '[RISK]').replace('*', '').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output()

def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    for line in text.replace('*', '').split('\n'):
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
    except: return "Ошибка чтения."

def extract_from_url(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(["script", "style", "nav", "footer"]): s.decompose()
        return soup.get_text(separator=' ')[:30000]
    except: return "Ошибка загрузки."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Параметры")
    audience = st.radio("Аудитория:", ["Гражданин", "Предприниматель", "Юрист"])
    jurisdiction = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "Международная"])
    
    st.divider()
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

    st.markdown("""
    <div class="disclaimer-box">
    <b>⚠️ ПРЕДУПРЕЖДЕНИЕ:</b><br>
    Этот сервис использует ИИ. Результаты не являются юридической консультацией.
    </div>
    """, unsafe_allow_html=True)

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
                        p = f"Ты эксперт-юрист. Роль: {audience}. Юрисдикция: {jurisdiction}. Найди риски и выдели их 🔴."
                        res = call_gemini_direct(p, target_content) if is_image else call_gemini_direct(f"{p}\n\nДОК:\n{target_content}")
                        if res: st.session_state.audit_res = res

    if "audit_res" in st.session_state:
        with col_res:
            for block in st.session_state.audit_res.split('\n'):
                if "🔴" in block: st.markdown(f'<div class="critical-risk">{block}</div>', unsafe_allow_html=True)
                else: st.markdown(block)
            
            # БЛОК СКАЧИВАНИЯ
            c1, c2 = st.columns(2)
            c1.download_button("📥 Скачать Word", create_docx(st.session_state.audit_res, "Аудит"), "Audit.docx")
            
            # Кнопка PDF
            try:
                pdf_data = create_pdf(st.session_state.audit_res, "Юридический Аудит")
                c2.download_button("📥 Скачать PDF", data=pdf_data, file_name="Legal_Audit.pdf", mime="application/pdf")
            except:
                c2.error("Ошибка генерации PDF")

# Остальные вкладки (tab2, tab3) остаются как в прошлом коде
with tab3:
    st.subheader("Генератор документов")
    doc_type = st.selectbox("Тип документа:", ["Протокол разногласий (Таблица)", "Претензия", "Сопроводительное письмо"])
    context = st.text_area("Данные для документа:")
    if st.button("✍️ СГЕНЕРИРОВАТЬ") and context:
        with st.spinner("Пишем..."):
            res = call_gemini_direct(f"Напиши {doc_type} на основе этого текста:\n{context}")
            if res:
                st.session_state.doc_res = res
                st.markdown(res)
                st.download_button("📥 Скачать документ", create_docx(st.session_state.doc_res, doc_type), f"{doc_type}.docx")
                                 
