import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io

st.set_page_config(page_title="LegalAI Enterprise", page_icon="⚖️", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Добавьте GOOGLE_API_KEY в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

SYSTEM_PROMPT = """
Ты — профессиональный корпоративный юрист. Твоя задача:
1. Анализировать документы на наличие юридических рисков.
2. Сравнивать версии договоров, выделяя изменения.
3. Составлять официальные ответы на претензии.
Пиши структурировано, используй таблицы для сравнения и списки для рисков.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

def extract_text(file) -> str:
    fname = file.name.lower()
    try:
        if fname.endswith(".pdf"):
            pdf = PdfReader(io.BytesIO(file.getvalue()))
            return "\n".join([page.extract_text() for page in pdf.pages])
        elif fname.endswith(".docx"):
            doc = Document(io.BytesIO(file.getvalue()))
            return "\n".join([p.text for p in doc.paragraphs])
        elif fname.endswith(".txt"):
            return file.getvalue().decode("utf-8")
        return ""
    except Exception as e:
        return f"Ошибка чтения: {e}"

def create_docx(text: str):
    doc = Document()
    doc.add_heading("Юридический отчет LegalAI", 0)
    for line in text.split('\n'):
        clean_line = line.replace('**', '').replace('###', '').replace('##', '').strip()
        if clean_line:
            doc.add_paragraph(clean_line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

st.title("⚖️ LegalAI Enterprise Pro")

with st.sidebar:
    st.header("Настройки")
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "Беларусь", "Международное право"])
    depth = st.select_slider("Глубина анализа", ["Базовая", "Стандартная", "Детальная"])
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🔍 Анализ договора", "🔄 Сравнение версий", "✉️ Ответ на претензию"])

with tab1:
    up_file = st.file_uploader("Загрузите документ или фото", type=["pdf", "docx", "png", "jpg", "jpeg"], key="audit_up")
    if st.button("Запустить аудит", type="primary"):
        if up_file:
            with st.spinner("Анализ..."):
                try:
                    if up_file.type.startswith("image"):
                        res = model.generate_content([f"Юр. аудит документа на фото. Юрисдикция: {jurisdiction}", Image.open(up_file)])
                    else:
                        text = extract_text(up_file)
                        res = model.generate_content(f"Анализ рисков. Юрисдикция: {jurisdiction}. Глубина: {depth}.\n\nТекст:\n{text}")
                    st.session_state.audit_result = res.text
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать отчет (.docx)", create_docx(st.session_state.audit_result), "Audit.docx")

with tab2:
    col1, col2 = st.columns(2)
    with col1: f1 = st.file_uploader("Ваша версия", type=["pdf", "docx"], key="orig")
    with col2: f2 = st.file_uploader("Версия контрагента", type=["pdf", "docx"], key="mod")
    if st.button("Найти отличия"):
        if f1 and f2:
            with st.spinner("Сравнение..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                res = model.generate_content(f"Сравни два текста. Таблица изменений и риски.\n\nТекст 1:\n{t1}\n\nТекст 2:\n{t2}")
                st.session_state.diff_result = res.text
    if "diff_result" in st.session_state:
        st.markdown(st.session_state.diff_result)

with tab3:
    claim_text = st.text_area("Текст претензии", height=200)
    strategy = st.radio("Стратегия", ["Мирная", "Защитная", "Встречная"], horizontal=True)
    if st.button("Создать черновик ответа"):
        if claim_text:
            with st.spinner("Подготовка..."):
                res = model.generate_content(f"Напиши ответ. Стратегия: {strategy}. Юрисдикция: {jurisdiction}.\n\nПретензия:\n{claim_text}")
                st.session_state.reply_result = res.text
    if "reply_result" in st.session_state:
        st.markdown(st.session_state.reply_result)
        st.download_button("📥 Скачать ответ (.docx)", create_docx(st.session_state.reply_result), "Reply.docx")

st.divider()
st.caption("⚠️ ИИ может ошибаться. Проверьте результат у юриста.")
