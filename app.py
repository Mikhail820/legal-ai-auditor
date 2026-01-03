import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re

# ==================================================
# 1. ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ
# ==================================================
st.set_page_config(
    page_title="LegalAI Enterprise Pro",
    page_icon="⚖️",
    layout="wide"
)

st.error(
    "⚠️ ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР: "
    "Результаты сформированы ИИ и не являются юридическим заключением. "
    "Обязательно проверьте документ у лицензированного юриста."
)

# ==================================================
# 2. ИНИЦИАЛИЗАЦИЯ GEMINI (STABLE)
# ==================================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.warning("⚙️ Добавьте GOOGLE_API_KEY в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config={
        "temperature": 0.2,
        "top_p": 0.9,
        "max_output_tokens": 4096
    }
)

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
@st.cache_data(show_spinner=False, max_entries=10)
def extract_text(file_bytes: bytes, filename: str) -> str | None:
    """Извлекает текст из PDF / DOCX / TXT. Изображения не трогает."""
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return "".join(p.extract_text() or "" for p in reader.pages)[:30000]

        if name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)[:30000]

        if name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:30000]

        return None
    except Exception as e:
        return f"Ошибка извлечения текста: {e}"

def clean_markdown(text: str) -> str:
    return re.sub(r'[*_#>`]', '', text)

def save_to_docx(content: str, title: str):
    doc = Document()
    doc.add_heading(title, 0)

    p = doc.add_paragraph()
    run = p.add_run("Сформировано LegalAI Enterprise. Требуется проверка юриста.")
    run.bold = True

    for line in clean_markdown(content).split("\n"):
        if line.strip():
            doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. SIDEBAR
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")

    depth = st.select_slider(
        "Глубина анализа",
        options=["Базовая", "Стандартная", "Глубокая"],
        value="Стандартная"
    )

    jurisdiction = st.selectbox(
        "Юрисдикция",
