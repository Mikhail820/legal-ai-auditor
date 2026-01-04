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

# ===== PDF =====
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white

# ===== CONFIG =====
st.set_page_config(page_title="LegalAI Enterprise Max", page_icon="⚖️", layout="wide")

DISCLAIMER_TEXT = "⚠️ ВНИМАНИЕ: Анализ выполнен ИИ. Не является юридической консультацией."
TARGET_MODEL = "gemini-2.5-flash-lite"

# ===== GEMINI =====
def call_gemini(prompt, content):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"text": content[:15000]}
            ]
        }]
    }

    try:
        r = requests.post(url, json=payload, timeout=120)
        data = r.json()
        if "candidates" not in data:
            raise Exception(data)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return None

def call_gemini_retry(prompt, content, retries=3):
    for i in range(retries):
        res = call_gemini(prompt, content)
        if res:
            return res
        time.sleep(3 + i * 2)
    st.error("❌ Gemini временно недоступен (503). Попробуйте позже.")
    return None

# ===== FILES =====
def extract_text(file_bytes, filename):
    try:
        if filename.endswith(".pdf"):
            return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(file_bytes)).pages if p.extract_text())
        if filename.endswith(".docx"):
            return "\n".join(p.text for p in Document(io.BytesIO(file_bytes)).paragraphs)
    except:
        return ""
    return ""

# ===== WORD =====
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(DISCLAIMER_TEXT).italic = True
    doc.add_paragraph("-" * 40)
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ===== PDF TABLE =====
def create_pdf(text, title):
    buffer = io.BytesIO()
    pdfmetrics.registerFont(TTFont("PTSans", "fonts/PTSans-Regular.ttf"))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Title", fontName="PTSans", fontSize=20, textColor=HexColor("#FF4B4B"), alignment=1))
    styles.add(ParagraphStyle("Body", fontName="PTSans", fontSize=11))
    styles.add(ParagraphStyle("Small", fontName="PTSans", fontSize=8, textColor=HexColor("#7f8c8d")))

    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 10),
        Paragraph(DISCLAIMER_TEXT, styles["Small"]),
        Spacer(1, 12)
    ]

    table_data = []
    for line in text.split("\n"):
        if "LEGAL SCORE" in line:
            table_data.append(["LEGAL SCORE", line])
        elif "🔴" in line:
            table_data.append(["Критические риски", line])
        elif "💸" in line:
            table_data.append(["Потери", line])
        elif "⚠️" in line:
            table_data.append(["Ловушки", line])
        else:
            story.append(Paragraph(line, styles["Body"]))

    if table_data:
        table = Table(table_data, colWidths=[60*mm, 100*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), HexColor("#FF4B4B")),
            ("TEXTCOLOR", (0,0), (0,-1), white),
            ("GRID", (0,0), (-1,-1), 0.5, black),
            ("FONTNAME", (0,0), (-1,-1), "PTSans"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
        ]))
        story.append(Spacer(1, 10))
        story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ===== UI =====
st.markdown("<h1 style='color:#FF4B4B;text-align:center'>⚖️ LegalAI Enterprise Max</h1>", unsafe_allow_html=True)

tab1, _, _ = st.tabs(["🚀 УМНЫЙ АУДИТ", "—", "—"])

with tab1:
    col1, col2 = st.columns([1, 1.4])

    with col1:
        dtype = st.selectbox(
            "Тип документа:",
            [
                "Договор услуг",
                "Договор поставки",
                "Аренда",
                "NDA",
                "Займ / инвестиции",
                "Подряд / IT",
                "Трудовой договор",
                "Другое"
            ]
        )

        src = st.radio("Источник:", ["Файл", "Текст", "Ссылка"])

        input_data = None
        if src == "Файл":
            f = st.file_uploader("PDF / DOCX", type=["pdf", "docx"])
            if f:
                input_data = extract_text(f.getvalue(), f.name)
        elif src == "Ссылка":
            url = st.text_input("URL")
            if url:
                input_data = BeautifulSoup(requests.get(url).text, "html.parser").get_text()[:15000]
        else:
            input_data = st.text_area("Вставьте текст", height=250)

        if st.button("🚀 АНАЛИЗ"):
            if input_data:
                with col2:
                    with st.spinner("Анализирую..."):
                        prompt = f"""
Ты юрист по рискам.
Тип документа: {dtype}

Дай:
1. LEGAL SCORE
2. 🔴 КРИТИЧЕСКИЕ РИСКИ
3. 💸 ПОТЕРИ
4. ⚠️ ЛОВУШКИ
5. ✅ ИТОГ
"""
                        res = call_gemini_retry(prompt, input_data)
                        if res:
                            st.session_state.audit = res

    if "audit" in st.session_state:
        col2.markdown(st.session_state.audit)
        col2.download_button("📄 PDF", create_pdf(st.session_state.audit, f"Анализ: {dtype}"), "report.pdf")
        col2.download_button("📝 Word", create_docx(st.session_state.audit, f"Анализ: {dtype}"), "report.docx")
