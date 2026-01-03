import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re

# ==================================================
# 1. КОНФИГУРАЦИЯ
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
# 2. GEMINI INIT (STABLE)
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
# 3. UTILITIES
# ==================================================
@st.cache_data(show_spinner=False, max_entries=10)
def extract_text(file_bytes: bytes, filename: str):
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
        ["Россия / СНГ", "ЕС", "США", "Международная"]
    )

    st.caption("Модель: Gemini 1.5 Flash")

    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

# ==================================================
# 5. TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(
    ["🚀 АНАЛИЗ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТ КОНТРАГЕНТУ"]
)

# ==================================================
# TAB 1 — АНАЛИЗ
# ==================================================
with tab1:
    mode = st.radio("Источник данных", ["Файл / Фото", "Текст"], horizontal=True)

    data = (
        st.file_uploader("Загрузите документ", type=["pdf", "docx", "jpg", "png", "jpeg"])
        if mode == "Файл / Фото"
        else st.text_area("Вставьте текст договора", height=300)
    )

    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if not data:
            st.warning("Добавьте документ или текст.")
            st.stop()

        with st.spinner("⚖️ Проводится юридический анализ..."):
            if mode == "Файл / Фото" and data.type and data.type.startswith("image"):
                prompt = (
                    f"Ты ведущий юрист.\n"
                    f"Юрисдикция: {jurisdiction}\n"
                    f"Глубина анализа: {depth}\n\n"
                    "Структура ответа:\n"
                    "1. Jurisdiction\n"
                    "2. Verdict (%)\n"
                    "3. Таблица рисков\n"
                    "4. Рекомендации"
                )
                response = model.generate_content([prompt, Image.open(data)])
            else:
                text = extract_text(data.getvalue(), data.name) if mode == "Файл / Фото" else data
                if not text:
                    st.error("Этот файл анализируется только как изображение.")
                    st.stop()

                full_prompt = f"""Ты профессиональный юрист.
Юрисдикция: {jurisdiction}
Глубина анализа: {depth}

====================
ТЕКСТ ДОКУМЕНТА:
====================
{text}
"""
                response = model.generate_content(full_prompt)

            st.session_state.rep1 = response.text

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button(
            "📥 Скачать отчёт (.docx)",
            save_to_docx(st.session_state.rep1, "Legal_Audit"),
            file_name="Legal_Audit.docx"
        )

# ==================================================
# TAB 2 — СРАВНЕНИЕ
# ==================================================
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        a = st.file_uploader("Документ A", type=["pdf", "docx"])
    with c2:
        b = st.file_uploader("Документ B", type=["pdf", "docx"])

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if not a or not b:
            st.warning("Загрузите оба документа.")
            st.stop()

        with st.spinner("Сравнение документов..."):
            txt_a = extract_text(a.getvalue(), a.name)
            txt_b = extract_text(b.getvalue(), b.name)

            full_prompt = f"""Ты юрист.
Юрисдикция: {jurisdiction}

Сравни документы.
Ответ в таблице:
Пункт | Было | Стало | Юридический риск

===== ДОКУМЕНТ A =====
{txt_a}

===== ДОКУМЕНТ B =====
{txt_b}
"""
            res = model.generate_content(full_prompt)
            st.session_state.rep2 = res.text

    if "rep2" in st.session_state:
        st.markdown(st.session_state.rep2)

# ==================================================
# TAB 3 — ОТВЕТ
# ==================================================
with tab3:
    mode = st.radio("Источник претензии", ["Файл / Фото", "Текст"], horizontal=True)

    claim = (
        st.file_uploader("Документ контрагента", type=["pdf", "docx", "jpg", "png"])
        if mode == "Файл / Фото"
        else st.text_area("Текст претензии", height=250)
    )

    goal = st.text_area(
        "Цель ответа",
        placeholder="Например: Отклонить претензию, сославшись на пункт 4.1 договора."
    )

    if st.button("✍️ Сформировать ответ", type="primary", use_container_width=True):
        if not claim:
            st.warning("Добавьте претензию.")
            st.stop()

        with st.spinner("Формируется официальный ответ..."):
            if mode == "Файл / Фото" and claim.type and claim.type.startswith("image"):
                response = model.generate_content(
                    [f"Напиши официальный юридический ответ. Цель: {goal}", Image.open(claim)]
                )
            else:
                text = extract_text(claim.getvalue(), claim.name) if mode == "Файл / Фото" else claim

                full_prompt = f"""Напиши официальный юридический ответ.

Цель:
{goal}

====================
ТЕКСТ ПРЕТЕНЗИИ:
====================
{text}
"""
                response = model.generate_content(full_prompt)

            st.session_state.rep3 = response.text

    if "rep3" in st.session_state:
        st.markdown(st.session_state.rep3)
        st.download_button(
            "📥 Скачать письмо (.docx)",
            save_to_docx(st.session_state.rep3, "Official_Response"),
            file_name="Official_Response.docx"
        )
