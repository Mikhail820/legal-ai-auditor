import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. ГЛОБАЛЬНАЯ НАСТРОЙКА И СТИЛИ
# ==================================================
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    .report-box { padding: 20px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. ИНИЦИАЛИЗАЦИЯ МОДЕЛИ (ЗАЩИТА ОТ 404 И 429)
# ==================================================
def init_gemini():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден в Secrets.")
        st.stop()
    
    # Используем REST транспорт для стабильности и обхода 404
    genai.configure(api_key=api_key, transport='rest')
    
    # Выбираем 1.5 Flash - у неё самые высокие бесплатные лимиты
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Ошибка при подключении к ИИ: {e}")
        return None

model = init_gemini()

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text(file_bytes, filename):
    try:
        name = filename.lower()
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])[:40000]
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:40000]
        return ""
    except Exception as e:
        return f"Ошибка чтения файла {filename}: {e}"

def generate_docx(content, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сформировано LegalAI Pro. Данный документ требует проверки юристом.\n")
    # Очистка Markdown
    clean_text = re.sub(r'[*#_`>]', '', content)
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. БОКОВАЯ ПАНЕЛЬ (SIDEBAR)
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Настройки")
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция анализа", ["РФ", "Казахстан", "ЕС", "США", "Международная"])
    depth = st.select_slider("Детальность", options=["Кратко", "Стандарт", "Максимум"])
    
    st.divider()
    if st.button("🗑️ Очистить историю"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС (ТАБЫ)
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.caption("Профессиональный ИИ-аудит документов и генерация ответов")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ ВЕРСИЙ", "✉️ ОТВЕТЫ НА ПРЕТЕНЗИИ"])

# --- TAB 1: АУДИТ ---
with tab1:
    st.subheader("Поиск скрытых рисков в договоре")
    col_in, col_res = st.columns([1, 1.2])
    
    with col_in:
        input_mode = st.radio("Источник:", ["Файл / Скан", "Текст"], horizontal=True)
        if input_mode == "Файл / Скан":
            up_file = st.file_uploader("Загрузите контракт (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
        else:
            raw_text = st.text_area("Вставьте текст здесь:", height=300)
            
        btn_audit = st.button("🚀 НАЧАТЬ АУДИТ", type="primary")

    if btn_audit:
        with col_res:
            with st.spinner("Юрист ИИ изучает условия..."):
                try:
                    p = f"Ты эксперт-юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Проведи аудит рисков. Найди невыгодные условия."
                    if input_mode == "Файл / Скан" and up_file:
                        if up_file.type.startswith("image"):
                            res = model.generate_content([p, Image.open(up_file)])
                        else:
                            txt = extract_text(up_file.getvalue(), up_file.name)
                            res = model.generate_content(f"{p}\n\nТЕКСТ:\n{txt}")
                        st.session_state.audit_result = res.text
                    elif input_mode == "Текст" and raw_text:
                        res = model.generate_content(f"{p}\n\nТЕКСТ:\n{raw_text}")
                        st.session_state.audit_result = res.text
                except Exception as e:
                    st.error(f"Ошибка API: {e}")

    if "audit_result" in st.session_state:
        with col_res:
            st.markdown(st.session_state.audit_result)
            st.download_button("📥 Скачать аудит (DOCX)", generate_docx(st.session_state.audit_result, "Аудит Рисков"), "Legal_Audit.docx")

# --- TAB 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение оригинального текста и правок контрагента")
    c1, c2 = st.columns(2)
    f_old = c1.file_uploader("Документ 1 (Оригинал)", type=["pdf", "docx"], key="f_old")
    f_new = c2.file_uploader("Документ 2 (С правками)", type=["pdf", "docx"], key="f_new")
    
    if st.button("⚖️ СРАВНИТЬ И НАЙТИ ИЗМЕНЕНИЯ") and f_old and f_new:
        with st.spinner("Сравниваем версии..."):
            t_old = extract_text(f_old.getvalue(), f_old.name)
            t_new = extract_text(f_new.getvalue(), f_new.name)
            p_diff = "Сравни два текста. Выведи таблицу изменений: Пункт | Что было | Что стало | Оценка риска для нас."
            res_diff = model.generate_content(f"{p_diff}\n\nТекст 1: {t_old}\n\nТекст 2: {t_new}")
            st.markdown(res_diff.text)

# --- TAB 3: ОТВЕТЫ ---
with tab3:
    st.subheader("Генератор официальных ответов")
    claim_area = st.text_area("Текст входящей претензии или письма:", height=200)
    user_position = st.text_input("Ваша позиция (например: 'Отказ', 'Частичное признание', 'Просьба об отсрочке')")
    
    if st.button("✍️ ПОДГОТОВИТЬ ОТВЕТ"):
        if claim_area:
            with st.spinner("Формируем юридически грамотный ответ..."):
                p_ans = f"Напиши официальный ответ на юридическую претензию. Юрисдикция: {jurisdiction}. Моя цель: {user_position}."
                res_ans = model.generate_content(f"{p_ans}\n\nПРЕТЕНЗИЯ:\n{claim_area}")
                st.session_state.ans_text = res_ans.text
                st.markdown(st.session_state.ans_text)
                st.download_button("📥 Скачать письмо (DOCX)", generate_docx(st.session_state.ans_text, "Официальный_Ответ"), "Legal_Response.docx")

st.divider()
st.caption("LegalAI Enterprise Pro — Ваш интеллектуальный юридический помощник.")
