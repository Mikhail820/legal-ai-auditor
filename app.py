import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. CONFIG
# ==================================================
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. GEMINI ENGINE (FIXING 404 ONCE AND FOR ALL)
# ==================================================
def get_model():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден.")
        st.stop()
    
    # Жесткая установка транспорта REST для стабильности в облаке
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Пытаемся получить список моделей для диагностики (если 404, то ключ не тот)
        # Это также "прогревает" соединение
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Принудительно выбираем flash из списка или по прямому имени
        target_model = "models/gemini-1.5-flash"
        
        return genai.GenerativeModel(model_name=target_model)
    except Exception as e:
        st.error(f"Ошибка инициализации API: {e}")
        return None

model = get_model()

# ==================================================
# 3. UTILS
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        name = filename.lower()
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:35000]
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:35000]
        elif name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:35000]
        return ""
    except Exception as e:
        return f"Ошибка чтения: {e}"

def save_to_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сформировано LegalAI Pro. Требуется юридическая проверка.\n")
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. UI SIDEBAR
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "ЕС", "США", "Международная"])
    depth = st.select_slider("Глубина анализа", options=["Базовая", "Стандартная", "Экспертная"])
    
    if st.button("🗑️ Очистить кэш"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. MAIN INTERFACE
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ Внимание: Результаты ИИ носят справочный характер.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТЫ"])

# --- TAB 1: AUDIT ---
with tab1:
    mode = st.radio("Источник данных:", ["Файл / Фото", "Текст"], horizontal=True)
    
    if mode == "Файл / Фото":
        file_data = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
    else:
        file_data = st.text_area("Вставьте текст договора:", height=300)

    if st.button("🔍 ЗАПУСТИТЬ АУДИТ"):
        if not file_data:
            st.error("Загрузите файл или вставьте текст!")
        elif not model:
            st.error("Модель не инициализирована. Проверьте ключ API.")
        else:
            with st.spinner("Анализируем документ..."):
                try:
                    prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Выполни полный аудит рисков и дай рекомендации по правкам."
                    
                    if mode == "Файл / Фото" and hasattr(file_data, 'type'):
                        if file_data.type.startswith("image"):
                            img = Image.open(file_data)
                            response = model.generate_content([prompt, img])
                        else:
                            content = extract_text(file_data.getvalue(), file_data.name)
                            response = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{content}")
                    else:
                        response = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{file_data}")
                    
                    st.session_state.audit_result = response.text
                except Exception as e:
                    st.error(f"Ошибка выполнения запроса: {e}")

    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.audit_result, "Legal_Audit"), "Audit_Report.docx")

# --- TAB 2: COMPARE ---
with tab2:
    st.subheader("Сравнение версий")
    col1, col2 = st.columns(2)
    f1 = col1.file_uploader("Документ 1", type=["pdf", "docx"], key="f1")
    f2 = col2.file_uploader("Документ 2", type=["pdf", "docx"], key="f2")
    
    if st.button("⚖️ СРАВНИТЬ") and f1 and f2:
        with st.spinner("Сравниваем..."):
            t1 = extract_text(f1.getvalue(), f1.name)
            t2 = extract_text(f2.getvalue(), f2.name)
            res = model.generate_content(f"Найди отличия между текстом 1 и текстом 2. Составь таблицу изменений.\n\n1: {t1}\n\n2: {t2}")
            st.markdown(res.text)

# --- TAB 3: RESPONSES ---
with tab3:
    st.subheader("Генератор ответов")
    claim = st.text_area("Суть претензии:")
    goal = st.text_input("Желаемый результат:")
    
    if st.button("✍️ СГЕНЕРИРОВАТЬ ПИСЬМО") and claim:
        with st.spinner("Пишем ответ..."):
            res = model.generate_content(f"Напиши официальный юридический ответ. Цель: {goal}. Текст претензии: {claim}")
            st.session_state.ans_text = res.text
            st.markdown(st.session_state.ans_text)
            st.download_button("📥 Скачать DOCX", save_to_docx(st.session_state.ans_text, "Letter"), "Response_Letter.docx")
        
