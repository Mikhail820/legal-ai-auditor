import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io
from PIL import Image
import re

# --- 1. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

# Дисклеймер
st.error("⚠️ ВНИМАНИЕ: Результаты не являются юридической консультацией. Проверяйте отчеты у юристов.")

# --- 2. ПОДКЛЮЧЕНИЕ К ИИ ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.error("Критическая ошибка: API ключ не найден!")
    st.stop()

# --- 3. ТЕХНИЧЕСКИЕ ФУНКЦИИ (С КЭШИРОВАНИЕМ) ---
@st.cache_data
def get_file_text(file_content, file_name):
    # Кэшируем извлечение текста, чтобы не нагружать процессор
    try:
        if file_name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_content))
            return "".join([p.extract_text() for p in reader.pages])
        elif file_name.endswith(".docx"):
            doc = Document(io.BytesIO(file_content))
            return "\n".join([p.text for p in doc.paragraphs])
        return file_content.decode('utf-8', errors='ignore')
    except: return "Ошибка чтения."

def create_docx_pro(report_text, title="ОТЧЕТ LEGALAI"):
    doc = Document()
    doc.add_paragraph("ВАЖНО: Требуется проверка юристом.").bold = True
    doc.add_heading(title, 0)
    
    table_rows = []
    for line in report_text.split('\n'):
        if line.strip().startswith('|') and line.strip().endswith('|'):
            if re.match(r'^[ \d\.\-\|:]+$', line): continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells: table_rows.append(cells)
        else:
            if table_rows:
                table = doc.add_table(rows=0, cols=max(len(r) for r in table_rows))
                table.style = 'Table Grid'
                for r_data in table_rows:
                    row_cells = table.add_row().cells
                    for i, val in enumerate(r_data):
                        if i < len(row_cells): row_cells[i].text = val
                table_rows = []
            if line.strip(): doc.add_paragraph(line)
            
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 4. УПРАВЛЕНИЕ СОСТОЯНИЕМ (СБРОС) ---
def reset_app():
    for key in ['full_report', 'diff_report', 'reply_final']:
        if key in st.session_state:
            del st.session_state[key]

# --- 5. ИНТЕРФЕЙС ---
st.sidebar.title("Управление")
depth = st.sidebar.select_slider("Глубина анализа:", options=["Базовая", "Стандартная", "Глубокая"], value="Глубокая")
if st.sidebar.button("🗑️ Очистить все результаты"):
    reset_app()
    st.rerun()

tab1, tab2, tab3 = st.tabs(["🚀 АНАЛИЗ", "🔍 СРАВНЕНИЕ", "✉️ ГЕНЕРАТОР ОТВЕТА"])

# --- ВКЛАДКА 1: АНАЛИЗ ---
with tab1:
    u_file = st.file_uploader("Загрузите договор", type=['pdf','docx','jpg','png','jpeg'], key="anal_file")
    if st.button("🚀 ЗАПУСТИТЬ ПОЛНУЮ ПРОВЕРКУ", use_container_width=True, type="primary"):
        if u_file:
            with st.spinner("Идет анализ..."):
                if u_file.type.startswith('image'):
                    content = Image.open(u_file)
                else:
                    content = get_file_text(u_file.read(), u_file.name)
                
                sys_prompt = f"ТЫ ЮРИСТ. Глубина: {depth}. Структура: 1. Jurisdiction 2. Verdict (%) 3. Risk Table | Пункт | Риск | Правка | 4. Key Findings."
                res = model.generate_content([sys_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{sys_prompt}\n\n{content}")
                st.session_state.full_report = res.text

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
        st.download_button("📥 СКАЧАТЬ ОТЧЕТ", data=create_docx_pro(st.session_state.full_report), file_name="Legal_Report.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ---
with tab2:
    c1, c2 = st.columns(2)
    old_f = c1.file_uploader("Оригинал", type=['pdf','docx'], key="f_old")
    new_f = c2.file_uploader("Новая версия", type=['pdf','docx'], key="f_new")
    if st.button("⚖️ СРАВНИТЬ"):
        if old_f and new_f:
            with st.spinner("Сравниваю..."):
                t1, t2 = get_file_text(old_f.read(), old_f.name), get_file_text(new_f.read(), new_f.name)
                res = model.generate_content(f"Найди отличия. Таблица: Пункт | Было | Стало | Риск.\n\nТекст 1: {t1[:10000]}\n\nТекст 2: {t2[:10000]}")
                st.session_state.diff_report = res.text
    if 'diff_report' in st.session_state:
        st.markdown(st.session_state.diff_report)

# --- ВКЛАДКА 3: ГЕНЕРАТОР ОТВЕТА ---
with tab3:
    doc_in = st.file_uploader("Документ контрагента", type=['pdf','docx','jpg','png'], key="f_gen")
    user_goal = st.text_area("Ваша цель (например: отклонить претензию):")
    if st.button("✍️ СОСТАВИТЬ ПИСЬМО"):
        if doc_in:
            with st.spinner("Пишу письмо..."):
                content = Image.open(doc_in) if doc_in.type.startswith('image') else get_file_text(doc_in.read(), doc_in.name)
                reply_prompt = f"Напиши официальный ответ. Цель: {user_goal}. Стиль: Юридический, ссылки на ГК РФ."
                response = model.generate_content([reply_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{reply_prompt}\n\n{content}")
                st.session_state.reply_final = response.text
    if 'reply_final' in st.session_state:
        st.markdown(st.session_state.reply_final)
        st.download_button("📥 СКАЧАТЬ ПИСЬМО", data=create_docx_pro(st.session_state.reply_final, "ОТВЕТ"), file_name="Letter.docx")
        
