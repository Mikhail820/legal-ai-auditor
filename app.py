import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
# ==================================================
st.set_page_config(
    page_title="LegalAI Enterprise Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизация интерфейса
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .stTextArea>div>div>textarea { color: #31333F; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. ИНИЦИАЛИЗАЦИЯ GEMINI
# ==================================================
def init_gemini():
    # Проверка ключа в secrets (для Streamlit Cloud) или env (для Render/Docker)
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден. Добавьте его в Secrets или переменные окружения.")
        st.stop()
    
    genai.configure(api_key=api_key)
    # Используем системную инструкцию для фиксации роли ИИ
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "temperature": 0.1, # Низкая температура для точности
            "top_p": 0.95,
            "max_output_tokens": 8192,
        }
    )

model = init_gemini()

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (UTILITIES)
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text(file_bytes: bytes, filename: str) -> str:
    """Извлечение текста из различных форматов документов."""
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:40000]

        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:40000]

        elif name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:40000]
        
        return ""
    except Exception as e:
        return f"Ошибка парсинга: {str(e)}"

def save_to_docx(content: str, title: str):
    """Генерация DOCX файла для скачивания."""
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сгенерировано LegalAI Pro. Требуется юридическая проверка.\n")
    
    # Очистка текста от лишних символов Markdown перед сохранением
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. ИНТЕРФЕЙС (SIDEBAR)
# ==================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3665/3665923.png", width=100)
    st.title("LegalAI Control")
    
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "ЕС", "США", "Международное право"])
    depth = st.select_slider("Глубина анализа", options=["Лайт", "Стандарт", "Эксперт"])
    
    if st.button("🗑️ Очистить кэш и сессию"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. ОСНОВНОЙ КОНТЕНТ (TABS)
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР: ИИ может ошибаться. Не является официальной консультацией.")

tab1, tab2, tab3 = st.tabs(["🔍 Анализ рисков", "📑 Сравнение", "✉️ Ответы"])

# --- TAB 1: АНАЛИЗ ---
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        src_type = st.radio("Источник:", ["Файл/Фото", "Текст"], horizontal=True)
        if src_type == "Файл/Фото":
            uploaded_file = st.file_uploader("Загрузите договор (PDF, DOCX, PNG, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
        else:
            raw_text = st.text_area("Вставьте текст договора:", height=300)

    if st.button("🔥 Начать аудит", key="audit_btn"):
        with st.spinner("Анализируем условия и ищем риски..."):
            try:
                if src_type == "Файл/Фото" and uploaded_file:
                    if uploaded_file.type.startswith("image"):
                        img = Image.open(uploaded_file)
                        prompt = f"Ты юрист ({jurisdiction}). Найди риски в этом документе на фото. Глубина: {depth}."
                        response = model.generate_content([prompt, img])
                    else:
                        text = extract_text(uploaded_file.getvalue(), uploaded_file.name)
                        prompt = f"Ты юрист ({jurisdiction}). Проведи аудит договора. Глубина: {depth}. Текст:\n{text}"
                        response = model.generate_content(prompt)
                    st.session_state.audit_result = response.text
                elif src_type == "Текст" and raw_text:
                    prompt = f"Ты юрист ({jurisdiction}). Проведи аудит текста. Глубина: {depth}. Текст:\n{raw_text}"
                    response = model.generate_content(prompt)
                    st.session_state.audit_result = response.text
            except Exception as e:
                st.error(f"Ошибка API: {e}")

    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать аудит (DOCX)", save_to_docx(st.session_state.audit_result, "Audit_Report"), "Legal_Audit.docx")

# --- TAB 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение версий документа")
    c1, c2 = st.columns(2)
    file_a = c1.file_uploader("Версия А (Оригинал)", type=["pdf", "docx"])
    file_b = c2.file_uploader("Версия Б (С правками)", type=["pdf", "docx"])

    if st.button("⚖️ Сравнить документы") and file_a and file_b:
        with st.spinner("Ищем отличия..."):
            txt_a = extract_text(file_a.getvalue(), file_a.name)
            txt_b = extract_text(file_b.getvalue(), file_b.name)
            prompt = f"Сравни два текста договора. Выведи таблицу изменений: Пункт | Что изменилось | Оценка риска для нас.\n\nТекст А: {txt_a}\n\nТекст Б: {txt_b}"
            res = model.generate_content(prompt)
            st.markdown(res.text)

# --- TAB 3: ОТВЕТЫ ---
with tab3:
    st.subheader("Генератор юридических ответов")
    context = st.text_area("Суть претензии или входящего письма:", height=150)
    goal = st.text_input("Ваша позиция (например: 'Категорически не согласны', 'Просим отсрочку')")
    
    if st.button("✍️ Сформировать письмо"):
        if context:
            with st.spinner("Пишем ответ..."):
                prompt = f"Напиши официальный юридический ответ. Юрисдикция: {jurisdiction}. Позиция: {goal}. Контекст: {context}"
                res = model.generate_content(prompt)
                st.session_state.letter_result = res.text
                st.markdown(res.text)
                st.download_button("📥 Скачать ответ (DOCX)", save_to_docx(st.session_state.letter_result, "Legal_Letter"), "Letter.docx")



