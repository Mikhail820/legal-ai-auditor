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
    st.error("🚨 Добавьте GOOGLE_API_KEY в Secrets!")
    st.stop()

# --- 2. ФУНКЦИИ ---

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
        return f"Ошибка: {e}"
    return ""

def create_docx_with_tables(report_text):
    """Исправленная функция генерации Word с таблицами"""
    doc = Document()
    doc.add_heading('ЮРИДИЧЕСКИЙ ОТЧЕТ', 0)
    
    lines = report_text.split('\n')
    table_data = []
    
    for line in lines:
        if '|' in line and '---' not in line:
            row = [cell.strip() for cell in line.split('|') if cell.strip()]
            if row: table_data.append(row)
        else:
            if table_data:
                table = doc.add_table(rows=0, cols=len(table_data[0]))
                table.style = 'Table Grid'
                for r in table_data:
                    row_cells = table.add_row().cells
                    for i, val in enumerate(r):
                        row_cells[i].text = val
                table_data = []
            if line.strip():
                doc.add_paragraph(line.strip())
    
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС И НАСТРОЙКИ ---

with st.sidebar:
    st.title("⚙️ Настройки")
    
    # ВЫБОР СТЕПЕНИ АНАЛИЗА
    analysis_level = st.select_slider(
        "Глубина проверки:",
        options=["Базовая", "Стандартная", "Глубокая"],
        value="Стандартная"
    )
    
    st.divider()
    
    if st.button("🗑️ Очистить всё", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.info(f"Текущий режим: {analysis_level}")

st.title("⚖️ LegalAI International System")

tab1, tab2 = st.tabs(["🚀 Аудит документа", "🔍 Сравнение версий"])

with tab1:
    col_in, col_out = st.columns([1, 1.2], gap="large")
    
    with col_in:
        st.subheader("Ввод данных")
        mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
        
        u_file = None
        txt_input = ""
        
        if mode == "Файл / Фото":
            u_file = st.file_uploader("Загрузите документ", type=['pdf','docx','txt','jpg','png','jpeg'], key="file_audit")
        else:
            txt_input = st.text_area("Вставьте текст:", height=300, key="text_audit")
            
        if st.button("🚀 Начать проверку", type="primary", use_container_width=True):
            content = ""
            is_img = False
            
            if u_file:
                if u_file.type in ['image/jpeg', 'image/png']:
                    content, is_img = Image.open(u_file), True
                else:
                    content = extract_text(u_file)
            else:
                content = txt_input
                
            if content:
                with st.spinner(f"Выполняется {analysis_level} анализ..."):
                    prompts = {
                        "Базовая": "Проверь только штрафы и сроки оплаты.",
                        "Стандартная": "Проверь штрафы, сроки, условия расторжения и подсудность.",
                        "Глубокая": "Полный аудит: риски интеллектуальной собственности, скрытые комиссии, баланс прав сторон и все лазейки."
                    }
                    
                    sys_msg = f"""
                    ТЫ — ЭКСПЕРТ-ЮРИСТ. ГЛУБИНА: {analysis_level}. {prompts[analysis_level]}
                    ОТЧЕТ СТРОГО ПО ФОРМАТУ:
                    1. JURISDICTION: [Страна]
                    2. VERDICT: [🟢/🟡/🔴]
                    3. ТАБЛИЦА РИСКОВ:
                    | ПУНКТ | РИСК | РЕКОМЕНДАЦИЯ |
                    |---|---|---|
                    [Заполни таблицу]
                    
                    БЕЗ ВВОДНЫХ СЛОВ.
                    """
                    
                    try:
                        res = model.generate_content([sys_msg, content]) if is_img else model.generate_content(f"{sys_msg}\n\n{content[:20000]}")
                        st.session_state['main_report'] = res.text
                    except Exception as e:
                        st.error(f"Ошибка ИИ: {e}")

    with col_out:
        st.subheader("Результат")
        if 'main_report' in st.session_state:
            report = st.session_state['main_report']
            st.markdown(report)
            
            word_file = create_docx_with_tables(report)
            st.download_button("📥 Скачать Word", data=word_file, file_name="Legal_Audit.docx", use_container_width=True)

with tab2:
    st.subheader("Сравнение редакций")
    c1, c2 = st.columns(2)
    with c1: f1 = st.file_uploader("Оригинал", key="comp1")
    with c2: f2 = st.file_uploader("Правки", key="comp2")
    
    if st.button("🔎 Сравнить", use_container_width=True):
        if f1 and f2:
            with st.spinner("Сравнение..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                diff_res = model.generate_content(f"Сравни тексты и выдели только изменения, ухудшающие положение Заказчика:\n1: {t1[:9000]}\n2: {t2[:9000]}")
                st.markdown(diff_res.text)
            
