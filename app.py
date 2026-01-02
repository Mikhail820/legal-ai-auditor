import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image

# --- 1. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

# Инициализация ИИ
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config={"temperature": 0.0}) 
else:
    st.error("🚨 Ключ API не найден в Secrets (GOOGLE_API_KEY).")
    st.stop()

# --- 2. ФУНКЦИИ ОЧИСТКИ И ОБРАБОТКИ ---

def clear_session():
    """Полная очистка всех данных"""
    st.session_state['report'] = None
    st.session_state['diff_report'] = None
    # Очистка через перезагрузку для сброса виджетов
    st.rerun()

def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
        elif file.name.endswith(".txt"):
            raw = file.read()
            for enc in ['utf-8', 'windows-1251', 'cp1251']:
                try: return raw.decode(enc)
                except: continue
    except Exception as e:
        return f"Ошибка чтения: {e}"
    return ""

# --- 3. БОКОВАЯ ПАНЕЛЬ (НАСТРОЙКИ) ---

with st.sidebar:
    st.title("⚙️ Параметры")
    
    # 1. Степень анализа
    depth = st.select_slider(
        "Глубина проверки:",
        options=["Базовый", "Стандарт", "Глубокий"],
        value="Стандарт",
        help="Базовый: только штрафы. Глубокий: скрытые риски и права собственности."
    )
    
    st.divider()
    
    # 2. Кнопка удаления данных
    if st.button("🗑️ Очистить всё", use_container_width=True):
        clear_session()
    
    st.divider()
    st.markdown("### Памятка:")
    st.caption("🟢 - Безопасно\n🟡 - Требует внимания\n🔴 - Критично")

# --- 4. ОСНОВНОЙ ИНТЕРФЕЙС ---

st.title("⚖️ LegalAI International")
tab_audit, tab_diff = st.tabs(["🚀 Анализ документа", "🔍 Сравнение редакций"])

with tab_audit:
    ui_in, ui_out = st.columns([1, 1.2], gap="large")
    
    with ui_in:
        st.subheader("Ввод данных")
        input_mode = st.radio("Способ:", ["Файл / Фото", "Вставить текст"], horizontal=True)
        
        doc_content = ""
        u_file = None
        
        if input_mode == "Файл / Фото":
            u_file = st.file_uploader("Загрузите документ", type=['pdf','docx','txt','jpg','png','jpeg'], key="uploader_main")
        else:
            doc_content = st.text_area("Текст договора:", height=300, key="text_main", placeholder="Вставьте текст здесь...")
            
        if st.button("🚀 Начать анализ", type="primary", use_container_width=True):
            payload = ""
            is_img = False
            
            if u_file:
                if u_file.type in ['image/jpeg', 'image/png']:
                    payload, is_img = Image.open(u_file), True
                else:
                    payload = extract_text(u_file)
            else:
                payload = doc_content
            
            if payload:
                with st.spinner(f"Выполняю {depth} аудит..."):
                    # Логика промпта в зависимости от глубины
                    depth_prompts = {
                        "Базовый": "Фокусируйся исключительно на финансовых рисках, пенях и сроках оплаты.",
                        "Стандарт": "Проверь штрафы, сроки, условия расторжения и подсудность.",
                        "Глубокий": "Полный юридический аудит: права на ИС, скрытые штрафы, односторонние отказы, неясные формулировки и баланс интересов."
                    }
                    
                    full_prompt = f"""
                    РОЛЬ: Юридический ревизор. ГЛУБИНА: {depth}.
                    {depth_prompts[depth]}
                    
                    ФОРМАТ ОТЧЕТА (СТРОГО):
                    1. JURISDICTION: [Страна]
                    2. VERDICT: [🟢/🟡/🔴]
                    3. СУТЬ: [Кратко]
                    4. ТАБЛИЦА РИСКОВ:
                    | ПУНКТ | РИСК (ПОНЯТНО) | КАК ИСПРАВИТЬ |
                    |---|---|---|
                    
                    БЕЗ ПРИВЕТСТВИЙ. Если рисков нет, напиши "Критические риски отсутствуют".
                    """
                    
                    try:
                        if is_img:
                            res = model.generate_content([full_prompt, payload])
                        else:
                            res = model.generate_content(f"{full_prompt}\n\nДОКУМЕНТ:\n{payload[:19000]}")
                        st.session_state['report'] = res.text
                    except Exception as e:
                        st.error(f"Ошибка ИИ: {e}")

    with ui_out:
        st.subheader("Заключение")
        if st.session_state.get('report'):
            st.markdown(st.session_state['report'])
            # Тут можно добавить кнопку скачивания Word из прошлых версий

# --- 5. ВКЛАДКА СРАВНЕНИЯ ---
with tab_diff:
    st.subheader("Сравнение версий договора")
    c1, c2 = st.columns(2)
    with c1: f1 = st.file_uploader("Оригинал (v1)", key="c1")
    with c2: f2 = st.file_uploader("Версия с правками (v2)", key="c2")
    
    if st.button("🔎 Сравнить и найти риски", use_container_width=True):
        if f1 and f2:
            with st.spinner("Ищу скрытые изменения..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                diff_prompt = "Сравни тексты. Выдели только те изменения, которые УХУДШАЮТ положение Заказчика. Оформи таблицей: Изменение | Риск."
                res_diff = model.generate_content(f"{diff_prompt}\n\n1: {t1[:9000]}\n2: {t2[:9000]}")
                st.session_state['diff_report'] = res_diff.text
                st.markdown(res_diff.text)
        
