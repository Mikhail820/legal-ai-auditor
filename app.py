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
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.error(
    "⚠️ ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР: "
    "Результаты сформированы ИИ и не являются юридическим заключением. "
    "Обязательно проверьте документ у лицензированного юриста."
)

# ==================================================
# 2. УМНЫЙ ИНИТ МОДЕЛИ (УСТРАНЯЕМ 404)
# ==================================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.warning("⚙️ Добавьте GOOGLE_API_KEY в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def init_model():
    """Перебирает имена моделей, чтобы избежать ошибки 404"""
    # Список имен от самых новых к стандартным
    variants = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "models/gemini-1.5-flash"]
    for v in variants:
        try:
            m = genai.GenerativeModel(model_name=v)
            # Тестовый микро-вызов для проверки доступности имени
            m.generate_content("test", generation_config={"max_output_tokens": 1})
            return m
        except Exception:
            continue
    # Если ничего не подошло, пробуем старый добрый Pro
    return genai.GenerativeModel("gemini-pro")

model = init_model()

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return "".join(p.extract_text() or "" for p in reader.pages)[:30000]
        if filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)[:30000]
        return file_bytes.decode("utf-8", errors="ignore")[:30000]
    except Exception as e:
        return f"Ошибка: {e}"

def save_to_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    clean = re.sub(r'[*_#>`]', '', content)
    for line in clean.split("\n"):
        if line.strip(): doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ==================================================
# 4. ИНТЕРФЕЙС
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    depth = st.select_slider("Глубина", ["Базовая", "Стандартная", "Глубокая"], "Стандартная")
    juris = st.selectbox("Юрисдикция", ["Россия / СНГ", "ЕС", "США"])
    if st.button("🗑️ Сброс"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

t1, t2, t3 = st.tabs(["🚀 АНАЛИЗ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТ"])

# --- TAB 1 ---
with t1:
    m1 = st.radio("Источник", ["Файл / Фото", "Текст"], horizontal=True, key="m1")
    d1 = st.file_uploader("Документ", type=["pdf","docx","jpg","png","jpeg"], key="u1") if m1=="Файл / Фото" else st.text_area("Текст", height=300, key="t1")
    
    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if d1:
            with st.spinner("⚖️ ИИ анализирует..."):
                try:
                    if hasattr(d1, 'type') and d1.type.startswith("image"):
                        res = model.generate_content([f"Юрист. Глубина: {depth}. Юрисдикция: {juris}. Найди риски.", Image.open(d1)])
                    else:
                        txt = extract_text(d1.getvalue(), d1.name) if hasattr(d1, 'name') else d1
                        res = model.generate_content(f"Юрист. Анализ текста: {txt}")
                    st.session_state.rep1 = res.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button("📥 Скачать (.docx)", save_to_docx(st.session_state.rep1, "Audit"), "Audit.docx")

# --- TAB 2 ---
with t2:
    ca, cb = st.columns(2)
    fa = ca.file_uploader("Документ A", type=["pdf","docx"], key="fa")
    fb = cb.file_uploader("Документ B", type=["pdf","docx"], key="fb")
    if st.button("⚖️ Сравнить", use_container_width=True):
        if fa and fb:
            with st.spinner("Сверяю..."):
                t_a, t_b = extract_text(fa.getvalue(), fa.name), extract_text(fb.getvalue(), fb.name)
                st.session_state.rep2 = model.generate_content(f"Сравни. Таблица: Пункт | А | Б | Риск.\n\nА:{t_a}\n\nБ:{t_b}").text
    if "rep2" in st.session_state: st.markdown(st.session_state.rep2)

# --- TAB 3 ---
with t3:
    m3 = st.radio("Источник", ["Файл / Фото", "Текст"], horizontal=True, key="m3")
    cl = st.file_uploader("Претензия", type=["pdf","docx","jpg","png"], key="u3") if m3=="Файл / Фото" else st.text_area("Текст", key="t3")
    gl = st.text_area("Цель ответа", key="g3")
    if st.button("✍️ Создать ответ", type="primary", use_container_width=True):
        if cl:
            with st.spinner("Пишу..."):
                if hasattr(cl, 'type') and cl.type.startswith("image"):
                    r = model.generate_content([f"Ответ. Цель: {gl}", Image.open(cl)])
                else:
                    t = extract_text(cl.getvalue(), cl.name) if hasattr(cl, 'name') else cl
                    r = model.generate_content(f"Напиши ответ. Цель: {gl}. Текст: {t}")
                st.session_state.rep3 = r.text
    if "rep3" in st.session_state: st.markdown(st.session_state.rep3)
