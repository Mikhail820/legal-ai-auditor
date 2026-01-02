import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
import io
from PIL import Image
import re

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="LegalAI Mobile", page_icon="⚖️", layout="wide")

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
    except Exception as e: return f"Ошибка: {e}"
    return ""

def create_docx_pro(report_text):
    doc = Document()
    doc.add_heading('ЮРИДИЧЕСКИЙ АНАЛИЗ', 0)
    lines = report_text.split('\n')
    table_rows = []
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith('|') and clean_line.endswith('|'):
            if re.match(r'^\|[ \-:|]+\|$', clean_line): continue
            cells = [c.strip() for c in clean_line.split('|') if c.strip()]
            if cells: table_rows.append(cells)
        else:
            if table_rows:
                num_cols = max(len(r) for r in table_rows)
                table = doc.add_table(rows=0, cols=num_cols)
                table.style = 'Table Grid'
                for r_idx, r_data in enumerate(table_rows):
                    row_cells = table.add_row().cells
                    for c_idx, val in enumerate(r_data):
                        if c_idx < num_cols: row_cells[c_idx].text = val
                table_rows = []
            if clean_line: doc.add_paragraph(clean_line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---

st.title("⚖️ LegalAI Enterprise")

# Секция настроек (теперь видна сразу на телефоне)
with st.expander("⚙️ НАСТРОЙКИ АНАЛИЗА", expanded=True):
    depth = st.select_slider(
        "Глубина проверки:", 
        options=["Базовая", "Стандартная", "Глубокая"], 
        value="Стандартная"
    )
    if st.button("🗑️ СБРОСИТЬ ВСЕ ДАННЫЕ", use_container_width=True):
        st.session_state.clear()
        st.rerun()

tab_audit, tab_diff = st.tabs(["🚀 АНАЛИЗ", "🔍 СРАВНЕНИЕ"])

with tab_audit:
    mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
    
    if mode == "Файл / Фото":
        u_file = st.file_uploader("Загрузить документ или фото", type=['pdf','docx','txt','jpg','png','jpeg'])
        txt_u = ""
    else:
        txt_u = st.text_area("Вставьте текст договора:", height=200, key="main_text_input")
        u_file = None

    if st.button("🚀 НАЧАТЬ ПРОВЕРКУ", type="primary", use_container_width=True):
        content = Image.open(u_file) if u_file and u_file.type.startswith('image') else (extract_text(u_file) if u_file else txt_u)
        if content:
            with st.spinner("ИИ анализирует..."):
                p_logic = {
                    "Базовая": "Только штрафы и сроки.",
                    "Стандартная": "Штрафы, расторжение, подсудность, сроки.",
                    "Глубокая": "Полный аудит: интеллектуальная собственность, скрытые обязанности, баланс сторон."
                }
                sys_prompt = f"""
                ТЫ — ЮРИСТ. ГЛУБИНА: {depth}. {p_logic[depth]}
                ОТЧЕТ СТРОГО ПО ФОРМАТУ:
                1. JURISDICTION: [Страна]
                2. VERDICT: [🟢/🟡/🔴]
                3. ТАБЛИЦА РИСКОВ:
                | ПУНКТ | РИСК | ИСПРАВЛЕНИЕ |
                |---|---|---|
                4. ГОТОВЫЙ ОТВЕТ: [Текст для контрагента]
                """
                try:
                    res = model.generate_content([sys_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{sys_prompt}\n\n{content}")
                    st.session_state['rep'] = res.text
                except Exception as e: st.error(f"Ошибка: {e}")

    if 'rep' in st.session_state:
        st.divider()
        st.markdown(st.session_state['rep'])
        st.download_button("📥 СКАЧАТЬ WORD ОТЧЕТ", data=create_docx_pro(st.session_state['rep']), file_name="Report.docx", use_container_width=True)

with tab_diff:
    st.subheader("Сравнение версий")
    f1 = st.file_uploader("Оригинал", key="f1")
    f2 = st.file_uploader("Правки", key="f2")
    if st.button("🔎 СРАВНИТЬ", use_container_width=True):
        if f1 and f2:
            t1, t2 = extract_text(f1), extract_text(f2)
            res_d = model.generate_content(f"Сравни и найди только УХУДШЕНИЯ для клиента:\n1: {t1[:8000]}\n2: {t2[:8000]}")
            st.markdown(res_d.text)
            
