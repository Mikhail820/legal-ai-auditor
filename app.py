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
# 2. GEMINI INIT (FIXED 404)
# ==================================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.warning("⚙️ Добавьте GOOGLE_API_KEY в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
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
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
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
    mode1 = st.radio("Источник данных", ["Файл / Фото", "Текст"], horizontal=True, key="m1")
    data1 = (
        st.file_uploader("Загрузите документ", type=["pdf", "docx", "jpg", "png", "jpeg"], key="up1")
        if mode1 == "Файл / Фото"
        else st.text_area("Вставьте текст договора", height=300, key="tx1")
    )

    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if not data1:
            st.warning("Добавьте документ или текст.")
        else:
            with st.spinner("⚖️ Проводится юридический анализ..."):
                try:
                    is_img = hasattr(data1, 'type') and data1.type.startswith("image")
                    if is_img:
                        prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Структура: Jurisdiction, Verdict (%), Таблица рисков, Рекомендации."
                        response = model.generate_content([prompt, Image.open(data1)])
                    else:
                        text = extract_text(data1.getvalue(), data1.name) if hasattr(data1, 'getvalue') else data1
                        full_prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}.\n\nТЕКСТ:\n{text}"
                        response = model.generate_content(full_prompt)
                    st.session_state.rep1 = response.text
                except Exception as e:
                    st.error(f"Ошибка анализа: {e}")

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button("📥 Скачать отчёт", save_to_docx(st.session_state.rep1, "Audit"), file_name="Legal_Audit.docx", key="dl1")

# ==================================================
# TAB 2 — СРАВНЕНИЕ
# ==================================================
with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        a = st.file_uploader("Документ A", type=["pdf", "docx"], key="ua")
    with col_b:
        b = st.file_uploader("Документ B", type=["pdf", "docx"], key="ub")

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if a and b:
            with st.spinner("Сравнение..."):
                try:
                    t_a = extract_text(a.getvalue(), a.name)
                    t_b = extract_text(b.getvalue(), b.name)
                    prompt = f"Ты юрист. Сравни. Таблица: Пункт | Было | Стало | Риск.\n\nА:\n{t_a}\n\nБ:\n{t_b}"
                    st.session_state.rep2 = model.generate_content(prompt).text
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if "rep2" in st.session_state:
        st.markdown(st.session_state.rep2)

# ==================================================
# TAB 3 — ОТВЕТ
# ==================================================
with tab3:
    mode3 = st.radio("Источник", ["Файл / Фото", "Текст"], horizontal=True, key="m3")
    claim = (
        st.file_uploader("Претензия", type=["pdf", "docx", "jpg", "png"], key="up3")
        if mode3 == "Файл / Фото"
        else st.text_area("Текст претензии", height=200, key="tx3")
    )
    goal = st.text_area("Цель ответа", key="goal3")

    if st.button("✍️ Создать ответ", type="primary", use_container_width=True):
        if claim:
            with st.spinner("Формирование..."):
                try:
                    if hasattr(claim, 'type') and claim.type.startswith("image"):
                        res = model.generate_content([f"Ответ. Цель: {goal}", Image.open(claim)])
                    else:
                        txt = extract_text(claim.getvalue(), claim.name) if hasattr(claim, 'getvalue') else claim
                        res = model.generate_content(f"Напиши ответ. Цель: {goal}\n\nТекст:\n{txt}")
                    st.session_state.rep3 = res.text
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if "rep3" in st.session_state:
        st.markdown(st.session_state.rep3)
        st.download_button("📥 Скачать ответ", save_to_docx(st.session_state.rep3, "Letter"), file_name="Letter.docx", key="dl3")
