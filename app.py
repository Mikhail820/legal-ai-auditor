import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image

# --- 1. КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="LegalAI Enterprise Full", page_icon="⚖️", layout="wide")

# Инициализация ИИ
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config={"temperature": 0.0}) 
else:
    st.error("🚨 Ключ API не найден в Secrets.")
    st.stop()

# --- 2. ФУНКЦИИ ОБРАБОТКИ ---

def read_txt_safe(file):
    raw = file.read()
    for enc in ['utf-8', 'windows-1251', 'cp1251']:
        try: return raw.decode(enc)
        except: continue
    return "Ошибка кодировки текста."

def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
        elif file.name.endswith(".txt"):
            return read_txt_safe(file)
    except Exception as e:
        return f"Ошибка: {e}"

def create_docx(report_text):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(11)
    doc.add_heading('ОТЧЕТ ЮРИДИЧЕСКОГО АНАЛИЗА', 0)
    
    clean_text = report_text.replace('**', '').replace('###', '').replace('`', '')
    lines = clean_text.split('\n')
    
    table_buffer = []
    for line in lines:
        stripped = line.strip()
        if '|' in stripped and set(stripped.replace('|', '').replace(' ', '')) != {'-'}:
            row = [c.strip() for c in stripped.split('|') if c.strip()]
            if row: table_buffer.append(row)
        else:
            if table_buffer:
                table = doc.add_table(rows=0, cols=max(len(r) for r in table_buffer))
                table.style = 'Table Grid'
                for r_idx, r_data in enumerate(table_buffer):
                    cells = table.add_row().cells
                    for c_idx, val in enumerate(r_data):
                        if c_idx < len(cells): cells[c_idx].text = val
                table_buffer = []
            if stripped and not set(stripped.replace('|', '').replace(' ', '')) == {'-'}:
                doc.add_paragraph(stripped)
    
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. ИНТЕРФЕЙС ---

with st.sidebar:
    st.title("🛡️ Контроль")
    st.info("Режим: Критические риски")
    st.warning("⚠️ Внимание: Отчет генерируется ИИ. Не является финансовой или юридической консультацией.")
    st.divider()
    st.markdown("""
    **Легенда:**
    🟢 - Нормальные условия
    🟡 - Рекомендуются правки
    🔴 - Кабальные условия
    """)

st.title("⚖️ LegalAI International")
tab_audit, tab_diff = st.tabs(["🚀 Анализ документа", "🔍 Сравнение редакций"])

# --- ВКЛАДКА АУДИТА ---
with tab_audit:
    col_in, col_out = st.columns([1, 1.2], gap="large")
    
    with col_in:
        st.subheader("Ввод данных")
        src = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
        
        input_data = ""
        u_file = None
        is_visual = False
        
        if src == "Файл / Фото":
            u_file = st.file_uploader("Загрузите PDF, DOCX, TXT или Фото", type=['pdf','docx','txt','jpg','png','jpeg'])
        else:
            input_data = st.text_area("Вставьте текст здесь:", height=300)
            
        btn = st.button("🚀 Проверить критические риски")

    with col_out:
        st.subheader("Результат")
        if btn:
            payload = ""
            if u_file:
                if u_file.type in ['image/jpeg', 'image/png']:
                    payload, is_visual = Image.open(u_file), True
                else:
                    payload = extract_text(u_file)
            else:
                payload = input_data
            
            if payload:
                with st.spinner("Анализируем..."):
                    sys_prompt = """
                    ТЫ — СТРОГИЙ ЮРИДИЧЕСКИЙ АУДИТОР. ПИШИ ТОЛЬКО ПО СУЩЕСТВУ. 
                    БЕЗ ПРИВЕТСТВИЙ И ВВОДНЫХ ФРАЗ.
                    
                    СТРУКТУРА:
                    1. JURISDICTION: [Страна/Право]
                    2. VERDICT: [🟢/🟡/🔴]
                    3. ГЛАВНАЯ СУТЬ: [О чем договор простыми словами]
                    4. ТАБЛИЦА КРИТИЧЕСКИХ РИСКОВ:
                    | ПУНКТ | ЧЕМ ЭТО ПЛОХО | КАК ИСПРАВИТЬ |
                    |---|---|---|
                    | [Название] | [Риск для кошелька/прав] | [Фраза для замены] |
                    
                    ПРАВИЛА:
                    - Не выдумывай риски. Если договор стандартный — пиши "Критических рисков нет".
                    - Штраф до 0.1% в день — это НОРМА (🟢).
                    - Штраф от 1% в день или запрет на выход из договора — это КРИТИЧЕСКИ (🔴).
                    """
                    try:
                        if is_visual: res = model.generate_content([sys_prompt, payload])
                        else: res = model.generate_content(f"{sys_prompt}\n\nДОКУМЕНТ:\n{payload[:18000]}")
                        
                        st.session_state['report'] = res.text
                        st.markdown(res.text)
                        
                        doc_file = create_docx(res.text)
                        st.download_button("📥 Скачать Word-отчет", data=doc_file, file_name="Legal_Audit.docx")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

# --- ВКЛАДКА СРАВНЕНИЯ ---
with tab_diff:
    st.subheader("Сравнение двух версий договора")
    d_col1, d_col2 = st.columns(2)
    with d_col1: f1 = st.file_uploader("Оригинал", key="f1")
    with d_col2: f2 = st.file_uploader("Версия с правками", key="f2")
    
    if st.button("🔎 Найти опасные изменения"):
        if f1 and f2:
            with st.spinner("Сравниваем..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                diff = model.generate_content(f"Сравни тексты. Выдели только те изменения, которые УХУДШАЮТ положение Заказчика (увеличивают штрафы, сроки, убирают права): \n1: {t1[:9000]} \n2: {t2[:9000]}")
                st.markdown(diff.text)
        else:
            st.warning("Загрузите оба файла.")

st.markdown("---")
st.caption("LegalAI Enterprise 2026. Конфиденциальный аудит.")
