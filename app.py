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

# --- 1. CONFIG ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

# Выбранная рабочая модель из твоего списка
TARGET_MODEL = "gemini-2.0-flash"

# --- 2. CORE ENGINE (Прямой HTTP запрос) ---
def call_gemini(prompt, image_bytes=None):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    # Используем стабильный эндпоинт v1
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    
    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
    else:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        raise Exception(f"Ошибка {response.status_code}: {response.text}")

# --- 3. UTILS ---
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
        return f"Ошибка чтения: {e}"

def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сформировано LegalAI Pro. Требуется проверка юристом.\n")
    for line in re.sub(r'[*#_]', '', text).split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. UI ---
st.title("⚖️ LegalAI Enterprise Pro")
st.caption(f"Работает на базе {TARGET_MODEL}")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

# ТАБ 1: АУДИТ
with tab1:
    col_in, col_res = st.columns([1, 1.2])
    with col_in:
        up_file = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
        btn_audit = st.button("🚀 ЗАПУСТИТЬ АУДИТ", type="primary")

    if btn_audit and up_file:
        with col_res:
            with st.spinner("Анализируем риски..."):
                try:
                    p = "Ты опытный юрист. Проведи аудит рисков этого документа и предложи правки."
                    if up_file.type.startswith("image"):
                        res = call_gemini(p, up_file.getvalue())
                    else:
                        txt = extract_text(up_file.getvalue(), up_file.name)
                        res = call_gemini(f"{p}\n\nДОКУМЕНТ:\n{txt}")
                    st.session_state.audit_res = res
                    st.markdown(res)
                except Exception as e: st.error(e)
    
    if "audit_res" in st.session_state:
        with col_res:
            st.download_button("📥 Скачать Word", create_docx(st.session_state.audit_res, "Legal Audit"), "audit.docx")

# ТАБ 2: СРАВНЕНИЕ
with tab2:
    st.subheader("Сравнение редакций")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Оригинал", type=["pdf", "docx"], key="f1")
    f2 = c2.file_uploader("Правки", type=["pdf", "docx"], key="f2")
    
    if st.button("⚖️ СРАВНИТЬ") and f1 and f2:
        with st.spinner("Ищем отличия..."):
            t1, t2 = extract_text(f1.getvalue(), f1.name), extract_text(f2.getvalue(), f2.name)
            res = call_gemini(f"Сравни два текста и выведи таблицу изменений.\n1: {t1}\n2: {t2}")
            st.markdown(res)

# ТАБ 3: ОТВЕТЫ
with tab3:
    st.subheader("Генератор ответов")
    claim = st.text_area("Текст претензии:")
    if st.button("✍️ СОЗДАТЬ ОТВЕТ") and claim:
        with st.spinner("Пишем письмо..."):
            res = call_gemini(f"Напиши профессиональный ответ на эту претензию: {claim}")
            st.session_state.ans_res = res
            st.markdown(res)
            st.download_button("📥 Скачать ответ", create_docx(st.session_state.ans_res, "Official Response"), "response.docx")
        
