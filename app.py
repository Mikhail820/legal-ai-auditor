import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
import io
import base64
from pathlib import Path
import time

# --- reportlab для PDF ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white

# --- 1. НАСТРОЙКИ СТИЛЕЙ ---
st.set_page_config(page_title="LegalAI Enterprise Max", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; background-color: #FF4B4B; color: white; border: none; }
.stDownloadButton>button { width: 100%; border-radius: 10px; background-color: #28a745; color: white; }
.main-header { font-size: 2.5rem; color: #FF4B4B; text-align: center; margin-bottom: 1.5rem; font-weight: 800; }
.risk-card { background-color: #ffffff; border-left: 6px solid #ff4b4b; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
.score-container { background: #f0f2f6; padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #dee2e6; margin-bottom: 20px; }
.disclaimer { font-size: 0.8rem; color: #7f8c8d; padding: 15px; background: #fff3f3; border-radius: 10px; border: 1px solid #fab1a0; }
</style>
""", unsafe_allow_html=True)

DISCLAIMER_TEXT = "⚠️ ВНИМАНИЕ: Анализ выполнен ИИ. Не является юридической консультацией. Проконсультируйтесь с юристом."
TARGET_MODEL = "gemini-2.5-flash-lite"

# --- 2. ФУНКЦИИ GEMINI ---
def call_gemini(prompt, content, is_image=False):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    try:
        if is_image:
            img_b64 = base64.b64encode(content).decode("utf-8")
            payload = {"contents":[{"parts":[{"text": prompt},{"inline_data":{"mime_type":"image/jpeg","data":img_b64}}]}]}
        else:
            content = content[:15000]  # Ограничение на кусок
            payload = {"contents":[{"parts":[{"text": prompt},{"text": content}]}]}
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        data = r.json()
        if "candidates" not in data:
            raise Exception(data)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return None

def call_gemini_retry(prompt, content, retries=3, delay=3):
    for attempt in range(retries):
        res = call_gemini(prompt, content)
        if res:
            return res
        time.sleep(delay + attempt*2)
    st.warning("⚠️ Gemini временно недоступен. Попробуйте позже.")
    return None

# --- 3. Файлы и отчеты ---
def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            return " ".join([p.extract_text() for p in PdfReader(io.BytesIO(file_bytes)).pages if p.extract_text()])
        elif filename.lower().endswith(".docx"):
            return "\n".join([p.text for p in Document(io.BytesIO(file_bytes)).paragraphs])
    except:
        return "Ошибка чтения."
    return ""

def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(DISCLAIMER_TEXT).italic = True
    doc.add_paragraph("-"*40)
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 4. PDF с таблицами ---
def create_pdf_firm_table(text, title="Анализ документа"):
    buffer = io.BytesIO()
    fonts_path = Path("fonts/PTSans-Regular.ttf")
    pdfmetrics.registerFont(TTFont("PTSans", str(fonts_path)))

    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TitleStyle", fontName="PTSans", fontSize=20, leading=24, textColor=HexColor("#FF4B4B"), spaceAfter=15, alignment=1))
    styles.add(ParagraphStyle("BodyStyle", fontName="PTSans", fontSize=11, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle("DisclaimerStyle", fontName="PTSans", fontSize=8, textColor=HexColor("#7f8c8d"), spaceAfter=10))
    story = []
    story.append(Paragraph(title, styles["TitleStyle"]))
    story.append(Paragraph(DISCLAIMER_TEXT, styles["DisclaimerStyle"]))
    story.append(Spacer(1,12))

    # Таблица ключевых блоков
    data = []
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if "LEGAL SCORE" in line:
            data.append(["LEGAL SCORE", line])
        elif "🔴" in line:
            data.append(["Критические риски 🔴", line])
        elif "💸" in line:
            data.append(["Потери 💸", line])
        elif "⚠️" in line:
            data.append(["Ловушки ⚠️", line])
        else:
            story.append(Paragraph(line, styles["BodyStyle"]))

    if data:
        table_style = TableStyle([
            ('BACKGROUND',(0,0),(0,-1),HexColor("#FF4B4B")),
            ('TEXTCOLOR',(0,0),(0,-1),white),
            ('BACKGROUND',(1,0),(1,-1),HexColor("#f0f2f6")),
            ('TEXTCOLOR',(1,0),(1,-1),black),
            ('ALIGN',(0,0),(-1,-1),'LEFT'),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('FONTNAME',(0,0),(-1,-1),'PTSans'),
            ('FONTSIZE',(0,0),(-1,-1),11),
            ('BOX',(0,0),(-1,-1),1,black),
            ('INNERGRID',(0,0),(-1,-1),0.5,black),
        ])
        table = Table(data, colWidths=[70*mm,100*mm])
        table.setStyle(table_style)
        story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- 5. Боковая панель ---
with st.sidebar:
    st.header("⚙️ Конфигурация")
    role = st.radio("Кто вы:", ["Предприниматель","Юрист","Физическое лицо"])
    loc = st.selectbox("Страна:", ["РФ","Казахстан","Узбекистан","Международное право"])
    detail = st.select_slider("Глубина анализа:", options=["Кратко","Стандарт","Максимум"])
    st.divider()
    st.markdown(f'<div class="disclaimer">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

# --- 6. Основной интерфейс ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Max</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🚀 УМНЫЙ АУДИТ","🔍 СРАВНЕНИЕ","📋 ПРОТОКОЛЫ И ПИСЬМА"])

with tab1:
    c1,c2 = st.columns([1,1.3])
    with c1:
        dtype = st.selectbox("Тип документа:", [
