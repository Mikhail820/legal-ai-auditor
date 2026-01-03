import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re
import os

# ==================================================
# 1. КОНФИГУРАЦИЯ И СТИЛИ
# ==================================================
st.set_page_config(
    page_title="LegalAI Enterprise Pro",
    page_icon="⚖️",
    layout="wide"
)

# Кастомный CSS для красоты интерфейса
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; }
    .status-box { padding: 20px; border-radius: 10px; background-color: #ffffff; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 2. ИНИЦИАЛИЗАЦИЯ ИСПРАВЛЕННОГО API
# ==================================================
def init_model():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 Ошибка: GOOGLE_API_KEY не найден в Secrets.")
        st.stop()
    
    # ПРИНУДИТЕЛЬНО используем REST транспорт для обхода ошибки v1beta/404
    genai.configure(api_key=api_key, transport='rest')
    
    try:
        # Используем стабильную версию модели
        return genai.GenerativeModel(model_name='gemini-1.5-flash')
    except Exception as e:
        st.error(f"Не удалось запустить модель: {e}")
        return None

model = init_model()

# ==================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (УТИЛИТЫ)
# ==================================================
@st.cache_data(show_spinner=False)
def extract_text_from_file(file_bytes, filename):
    """Извлекает текст из PDF, DOCX или TXT."""
    try:
        name = filename.lower()
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
            return text[:40000] # Лимит для стабильности
        
        elif name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])[:40000]
        
        elif name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:40000]
        
        return ""
    except Exception as e:
        return f"Ошибка при чтении файла {filename}: {e}"

def generate_docx(content, title):
    """Создает DOCX файл из текста ответа ИИ."""
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сгенерировано LegalAI Pro. Требуется проверка юристом.\n")
    
    # Очистка Markdown символов для чистого документа
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
    st.title("🛡️ LegalAI Control")
    st.divider()
    jurisdiction = st.selectbox("Юрисдикция", ["Российская Федерация", "Казахстан", "Евросоюз (GDPR/EU)", "США", "Международное право"])
    depth = st.select_slider("Глубина анализа", options=["Базовая", "Стандартная", "Глубокая (Expert)"])
    
    st.divider()
    if st.button("🗑️ Сбросить все данные"):
        st.session_state.clear()
        st.cache_data.clear()
        st.rerun()
    
    st.caption("Версия: 2.1.0 Pro")

# ==================================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС (TABS)
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.warning("⚠️ ДИСКЛЕЙМЕР: Система ИИ не заменяет лицензированного юриста. Проверяйте важные документы вручную.")

tab1, tab2, tab3 = st.tabs(["🚀 АУДИТ РИСКОВ", "🔍 СРАВНЕНИЕ ВЕРСИЙ", "✉️ ГЕНЕРАТОР ОТВЕТОВ"])

# --- TAB 1: АНАЛИЗ ДОКУМЕНТА ---
with tab1:
    st.subheader("Автоматический поиск юридических ловушек")
    
    col_in, col_out = st.columns([1, 1.5])
    
    with col_in:
        input_type = st.radio("Источник документа:", ["Файл / Фото", "Вставить текст"], horizontal=True)
        
        if input_type == "Файл / Фото":
            uploaded_file = st.file_uploader("Загрузите договор (PDF, DOCX, PNG, JPG)", type=["pdf", "docx", "png", "jpg", "jpeg"])
        else:
            manual_text = st.text_area("Вставьте текст договора сюда:", height=350)
            
        analyze_btn = st.button("🔍 ЗАПУСТИТЬ АУДИТ", type="primary")

    if analyze_btn:
        with col_out:
            with st.spinner("Юрист ИИ проводит глубокий анализ..."):
                try:
                    prompt = f"Ты старший юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. " \
                             f"Найди все скрытые риски, невыгодные условия и ошибки в этом документе. " \
                             f"Ответь структурированно: 1. Главный вердикт, 2. Таблица рисков, 3. Рекомендации по правкам."
                    
                    if input_type == "Файл / Фото" and uploaded_file:
                        if uploaded_file.type.startswith("image"):
                            img = Image.open(uploaded_file)
                            response = model.generate_content([prompt, img])
                        else:
                            text = extract_text_from_file(uploaded_file.getvalue(), uploaded_file.name)
                            response = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{text}")
                        st.session_state.audit_res = response.text
                    
                    elif input_type == "Вставить текст" and manual_text:
                        response = model.generate_content(f"{prompt}\n\nТЕКСТ:\n{manual_text}")
                        st.session_state.audit_res = response.text
                    else:
                        st.error("Пожалуйста, загрузите файл или введите текст.")

                except Exception as e:
                    st.error(f"Ошибка API: {e}. Проверьте ключ или версию модели.")

    if "audit_res" in st.session_state:
        with col_out:
            st.markdown(st.session_state.audit_res)
            st.download_button(
                label="📥 Скачать отчет в DOCX",
                data=generate_docx(st.session_state.audit_res, "Юридический_Аудит"),
                file_name="Legal_Audit_Report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# --- TAB 2: СРАВНЕНИЕ ДОКУМЕНТОВ ---
with tab2:
    st.subheader("Сравнение оригинала и правок")
    c1, c2 = st.columns(2)
    
    file_old = c1.file_uploader("Оригинальный документ (Версия А)", type=["pdf", "docx"], key="old")
    file_new = c2.file_uploader("Документ с правками (Версия Б)", type=["pdf", "docx"], key="new")
    
    if st.button("⚖️ НАЙТИ ИЗМЕНЕНИЯ") and file_old and file_new:
        with st.spinner("Сравниваем тексты и оцениваем риски изменений..."):
            txt_a = extract_text_from_file(file_old.getvalue(), file_old.name)
            txt_b = extract_text_from_file(file_new.getvalue(), file_new.name)
            
            diff_prompt = (
                f"Сравни два текста договора. Найди все отличия. "
                f"Выведи результат в виде таблицы: Пункт | Что было (А) | Что стало (Б) | В чем риск для нас."
            )
            res = model.generate_content(f"{diff_prompt}\n\nТекст А: {txt_a}\n\nТекст Б: {txt_b}")
            st.markdown(res.text)

# --- TAB 3: ГЕНЕРАЦИЯ ОТВЕТОВ ---
with tab3:
    st.subheader("Генератор официальных писем и претензий")
    
    claim_text = st.text_area("Вставьте текст входящей претензии или опишите ситуацию:", height=200)
    user_goal = st.text_input("Ваша цель (например: 'Оспорить штраф', 'Признать вину частично', 'Расторгнуть договор')")
    
    if st.button("✍️ СФОРМИРОВАТЬ ОТВЕТ"):
        if claim_text:
            with st.spinner("Подбираем юридические формулировки..."):
                reply_prompt = (
                    f"Напиши профессиональный официальный ответ на юридическую претензию. "
                    f"Юрисдикция: {jurisdiction}. Моя цель: {user_goal}. Тон: строго деловой. "
                    f"Используй ссылки на типовые статьи законов при необходимости."
                )
                res = model.generate_content(f"{reply_prompt}\n\nПРЕТЕНЗИЯ:\n{claim_text}")
                st.session_state.letter_res = res.text
                st.markdown(st.session_state.letter_res)
                
                st.download_button(
                    label="📥 Скачать письмо в DOCX",
                    data=generate_docx(st.session_state.letter_res, "Официальный_Ответ"),
                    file_name="Legal_Response.docx"
                )

# ==================================================
# 6. ФУТЕР
# ==================================================
st.divider()
st.caption("Разработано командой Senior Python Developers для LegalAI Enterprise.")
                    
