import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io
from PIL import Image
import re

# --- 1. ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ И БЕЗОПАСНОСТЬ ---
st.set_page_config(
    page_title="LegalAI Enterprise Pro", 
    page_icon="⚖️", 
    layout="wide"
)

# Неубираемый дисклеймер для защиты от ответственности
st.error("⚠️ ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР: Результаты сформированы ИИ и не являются официальным юридическим заключением. Обязательно проверьте документ у адвоката.")

# --- 2. ИНИЦИАЛИЗАЦИЯ ИИ (GOOGLE GEMINI) ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.warning("⚙️ Ошибка: Добавьте GOOGLE_API_KEY в настройки (Secrets).")
    st.stop()

# --- 3. ТЕХНИЧЕСКИЙ ЯДРО (ФУНКЦИИ) ---

@st.cache_data
def get_text_from_file(file_bytes, file_name):
    """Извлекает текст из PDF, DOCX или TXT с кэшированием"""
    try:
        if file_name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif file_name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            text = file_bytes.decode('utf-8', errors='ignore')
        
        # Лимит 30к символов для стабильности и экономии токенов
        return text[:30000] if text else "Текст не распознан."
    except Exception as e:
        return f"Ошибка при чтении файла {file_name}: {str(e)}"

def save_to_docx(content, title="LegalAI_Report"):
    """Создает чистый Word-файл, убирая артефакты Markdown"""
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph("Сформировано LegalAI Enterprise. Требуется подпись юриста.").bold = True
    
    # Очистка текста от спецсимволов ИИ (** жирный, ### заголовки)
    clean_text = content.replace('**', '').replace('__', '').replace('### ', '').replace('# ', '')
    
    for para in clean_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. БОКОВАЯ ПАНЕЛЬ (УПРАВЛЕНИЕ) ---
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    st.markdown("---")
    depth = st.select_slider(
        "Глубина анализа:",
        options=["Базовая", "Стандартная", "Глубокая"],
        value="Стандартная"
    )
    st.write("Используется модель: Gemini 1.5 Flash")
    
    if st.button("🗑️ СБРОСИТЬ ВСЁ (Очистить кэш)"):
        for key in ['rep1', 'rep2', 'rep3']:
            if key in st.session_state: del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

# --- 5. ОСНОВНОЙ ИНТЕРФЕЙС ---
tab1, tab2, tab3 = st.tabs(["🚀 АНАЛИЗ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТ КОНТРАГЕНТУ"])

# --- ВКЛАДКА 1: АНАЛИЗ ДОКУМЕНТА ---
with tab1:
    st.subheader("Проверка документа на юридические риски")
    mode1 = st.radio("Как подать данные?", ["Загрузить файл/фото", "Вставить текст из буфера"], horizontal=True, key="m1")
    
    content_input = None
    if mode1 == "Загрузить файл/фото":
        content_input = st.file_uploader("Файл (PDF, DOCX, JPG, PNG)", type=['pdf','docx','jpg','png','jpeg'], key="u1")
    else:
        content_input = st.text_area("Вставьте текст договора:", height=300, key="t1")

    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if content_input:
            with st.spinner("⚖️ Ведущий юрист ИИ изучает документ..."):
                try:
                    # Если это файл-картинка
                    if hasattr(content_input, 'type') and content_input.type.startswith('image'):
                        prompt = [f"Проведи юридический аудит (Глубина: {depth}). Структура: 1. Jurisdiction 2. Verdict (%) 3. Таблица рисков 4. Рекомендации.", Image.open(content_input)]
                    else:
                        # Если это документ или текст из буфера
                        text = get_text_from_file(content_input.getvalue(), content_input.name) if hasattr(content_input, 'name') else content_input
                        prompt = f"ТЫ ВЕДУЩИЙ ЮРИСТ. Проведи анализ текста: {text}. Глубина: {depth}. Структура: 1. Jurisdiction 2. Verdict 3. Risk Table 4. Key Actions."
                    
                    response = model.generate_content(prompt)
                    st.session_state.rep1 = response.text
                except Exception as e:
                    st.error(f"Ошибка анализа: {e}")

    if 'rep1' in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button("📥 СКАЧАТЬ ОТЧЕТ (.docx)", data=save_to_docx(st.session_state.rep1, "Audit_Report"), file_name="Legal_Audit.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ДОКУМЕНТОВ ---
with tab2:
    st.subheader("Сравнение оригинала и правок")
    c1, c2 = st.columns(2)
    
    with c1:
        mode_a = st.radio("Документ А (Оригинал):", ["Файл", "Текст"], key="ma")
        input_a = st.file_uploader("Загрузить А", type=['pdf','docx'], key="ua") if mode_a == "Файл" else st.text_area("Вставить А", key="ta")
    
    with c2:
        mode_b = st.radio("Документ Б (Правки):", ["Файл", "Текст"], key="mb")
        input_b = st.file_uploader("Загрузить Б", type=['pdf','docx'], key="ub") if mode_b == "Файл" else st.text_area("Вставить Б", key="tb")

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if input_a and input_b:
            with st.spinner("Ищу скрытые изменения..."):
                txt_a = get_text_from_file(input_a.getvalue(), input_a.name) if mode_a == "Файл" else input_a
                txt_b = get_text_from_file(input_b.getvalue(), input_b.name) if mode_b == "Файл" else input_b
                
                res = model.generate_content(f"Сравни два текста. Выдели важные изменения (цены, сроки, штрафы, подсудность). Составь таблицу: Пункт | Было | Стало | Риск для нас.\n\nДок А: {txt_a}\n\nДок Б: {txt_b}")
                st.session_state.rep2 = res.text

    if 'rep2' in st.session_state:
        st.markdown(st.session_state.rep2)

# --- ВКЛАДКА 3: ГЕНЕРАТОР ОТВЕТА ---
with tab3:
    st.subheader("Генератор официальных писем")
    mode3 = st.radio("Источник претензии:", ["Файл/Фото", "Текст из буфера"], horizontal=True, key="m3")
    
    input3 = None
    if mode3 == "Файл/Фото":
        input3 = st.file_uploader("Загрузите документ", type=['pdf','docx','jpg','png'], key="u3")
    else:
        input3 = st.text_area("Вставьте текст претензии:", height=200, key="t3")
        
    user_goal = st.text_area("Ваши требования (что должен сделать ИИ?):", placeholder="Например: Опровергнуть претензию, ссылаясь на пункт 4.1 договора о сроках оплаты.")

    if st.button("✍️ Создать текст ответа", use_container_width=True, type="primary"):
        if input3:
            with st.spinner("Формирую юридически грамотный ответ..."):
                if mode3 == "Файл/Фото" and input3.type.startswith('image'):
                    prompt3 = [f"Напиши официальный ответ контрагенту. Моя цель: {user_goal}. Тон: профессиональный, деловой.", Image.open(input3)]
                else:
                    text3 = get_text_from_file(input3.getvalue(), input3.name) if mode3 == "Файл/Фото" else input3
                    prompt3 = f"Напиши официальный ответ на основе этого текста: {text3}. Моя цель: {user_goal}. Используй ссылки на законодательство и деловой стиль."
                
                response = model.generate_content(prompt3)
                st.session_state.rep3 = response.text

    if 'rep3' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state.rep3)
        st.download_button("📥 СКАЧАТЬ ПИСЬМО (.docx)", data=save_to_docx(st.session_state.rep3, "Official_Response"), file_name="Official_Letter.docx")
