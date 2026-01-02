import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image

# --- 1. НАСТРОЙКИ И ДИЗАЙН ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #1a237e; color: white; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #0d47a1; border: none; }
    .main { background-color: #fcfcfc; }
</style>
""", unsafe_allow_html=True)

# Инициализация ИИ
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config={"temperature": 0.0}) 
else:
    st.error("🚨 Ключ API не найден. Добавьте GOOGLE_API_KEY в Settings > Secrets.")
    st.stop()

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def read_txt_safe(file):
    raw = file.read()
    for enc in ['utf-8', 'windows-1251', 'cp1251']:
        try:
            return raw.decode(enc)
        except:
            continue
    return "Error: Encoding fail."

def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
        elif file.name.endswith(".txt"):
            return read_txt_safe(file)
    except Exception as e:
        return f"Ошибка чтения: {e}"

def create_pro_docx(report_text):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(11)
    
    title = doc.add_heading('Юридическое заключение / Legal Audit Report', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
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
                        if c_idx < len(cells):
                            run = cells[c_idx].paragraphs[0].add_run(val)
                            if r_idx == 0: run.font.bold = True
                table_buffer = []
            if stripped and not set(stripped.replace('|', '').replace(' ', '')) == {'-'}:
                p = doc.add_paragraph(stripped)
                if len(stripped) < 60 and (stripped.isupper() or stripped.endswith(':')):
                    p.runs[0].font.bold = True
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. ИНТЕРФЕЙС ---

with st.sidebar:
    st.title("🛡️ Контроль качества")
    st.write("**Режим:** Анализ критических рисков")
    st.write("**Международный охват:** Включен")
    st.divider()
    st.markdown("""
    **Шкала оценки:**
    🟢 - Стандартные условия
    🟡 - Нужны точечные правки
    🔴 - Кабальные условия / Риск потери прав
    """)

st.title("⚖️ LegalAI International Enterprise")
st.write("Профессиональный аудит документов с фокусировкой на защите интересов.")

tab_audit, tab_diff = st.tabs(["🚀 Анализ документа", "🔍 Сравнение редакций"])

with tab_audit:
    ui_left, ui_right = st.columns([1, 1.2], gap="large")
    
    with ui_left:
        st.subheader("📥 Ввод данных")
        input_type = st.radio("Источник:", ["Файл или Фото", "Текст"], horizontal=True)
        
        raw_text = ""
        file_obj = None
        is_visual = False
        
        if input_type == "Файл или Фото":
            file_obj = st.file_uploader("PDF, DOCX, TXT или Фото", type=['pdf','docx','txt','jpg','png','jpeg'])
        else:
            raw_text = st.text_area("Вставьте текст договора:", height=300)
            
        start_btn = st.button("🚀 Начать аудит")

    with ui_right:
        st.subheader("📝 Экспертное заключение")
        
        if start_btn:
            data_to_send = None
            if file_obj:
                if file_obj.type in ['image/jpeg', 'image/png']:
                    data_to_send = Image.open(file_obj)
                    is_visual = True
                else:
                    data_to_send = extract_text(file_obj)
            else:
                data_to_send = raw_text
                
            if data_to_send:
                with st.spinner("⚖️ Работает ИИ-юрист..."):
                    system_prompt = """
                    РОЛЬ: Старший юрист международной фирмы.
                    ЗАДАЧА: Отделить рыночные условия от КАТАСТРОФИЧЕСКИХ рисков.
                    
                    ИНСТРУКЦИЯ ПО ВЕРДИКТАМ:
                    - 🟢 БЕЗОПАСНО: Пени до 0.1%/день, расторжение 14-30 дней, стандартная подсудность.
                    - 🟡 ЖЕЛТЫЙ: Мелкие дисбалансы (нет ответственности исполнителя, размытые сроки).
                    - 🔴 КРИТИЧЕСКИ: Штрафы >1% в день, запрет на расторжение (ст. 782 ГК РФ), лишение прав на IP, подсудность в закрытых юрисдикциях.
                    
                    ОТЧЕТ:
                    1. JURISDICTION: [Определи страну/право]
                    2. VERDICT: [🟢/🟡/🔴]
                    3. СУТЬ: [Кратко на простом языке]
                    4. КРИТИЧЕСКИЕ РИСКИ: [Только если они есть. Если документ чист, так и напиши].
                    5. ТАБЛИЦА ПРАВОК: | Пункт | Риск | Рекомендация |
                    
                    Язык отчета: Русский.
                    """
                    
                    try:
                        if is_visual:
                            res = model.generate_content([system_prompt, data_to_send])
                        else:
                            res = model.generate_content(f"{system_prompt}\n\nДОКУМЕНТ:\n{data_to_send[:18000]}")
                        st.session_state['last_audit'] = res.text
                    except Exception as e:
                        st.error(f"Ошибка ИИ: {e}")

        if 'last_audit' in st.session_state:
            res_text = st.session_state['last_audit']
            
            jur = "Auto-detect"
            vdt = "Analysis done"
            for line in res_text.split('\n'):
                if "JURISDICTION" in line: jur = line.split(':')[-1]
                if "VERDICT" in line: vdt = line.split(':')[-1]
            
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("Юрисдикция", jur.strip())
            m_col2.metric("Вердикт", vdt.strip())
            
            st.divider()
            
            doc_file = create_pro_docx(res_text)
            st.download_button("📥 Скачать Word-отчет", data=doc_file, file_name="Legal_Report.docx", use_container_width=True)
            
            with st.expander("📄 Детальный разбор", expanded=True):
                st.markdown(res_text)

with tab_diff:
    st.subheader("Сравнение версий")
    d1, d2 = st.columns(2)
    with d1: f1 = st.file_uploader("Оригинал", key="d1")
    with d2: f2 = st.file_uploader("Новая версия", key="d2")
    if st.button("🔎 Найти опасные изменения"):
        if f1 and f2:
            with st.spinner("Сравнение..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                diff = model.generate_content(f"Сравни тексты и выдели только те изменения, которые УХУДШАЮТ положение Заказчика: \n1: {t1[:9000]} \n2: {t2[:9000]}")
                st.markdown(diff.text)

st.markdown("---")
st.caption("LegalAI Enterprise 2026. Конфиденциальность гарантирована.")
        
