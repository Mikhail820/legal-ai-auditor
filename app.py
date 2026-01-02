import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image

# --- 1. CONFIGURATION & UI STYLES ---
st.set_page_config(page_title="LegalAI Universal Enterprise", page_icon="⚖️", layout="wide")

# Профессиональный дизайн интерфейса
st.markdown("""
<style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004e98; color: white; }
    .stButton>button:hover { background-color: #003366; color: white; border: none; }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Инициализация ИИ (Gemini 2.5 Flash)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Temperature 0.1 для исключения "фантазий" ИИ
    model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config={"temperature": 0.1}) 
else:
    st.error("🚨 Ключ Google API не найден в Secrets!")
    st.stop()

# --- 2. CORE BUSINESS LOGIC ---

def read_txt_safe(file):
    """Чтение TXT с автоматическим определением кодировки"""
    raw_data = file.read()
    for encoding in ['utf-8', 'windows-1251', 'cp1251', 'latin-1']:
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return "Error: Encoding mismatch."

def extract_text(file):
    """Универсальный извлекатель текста из PDF, DOCX, TXT"""
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages])
        elif file.name.endswith(".docx"):
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        elif file.name.endswith(".txt"):
            return read_txt_safe(file)
        return "Unsupported format."
    except Exception as e:
        return f"Extraction Error: {e}"

def create_pro_docx(report_text):
    """Генерация юридически чистого Word-файла с таблицами"""
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Заголовок отчета
    title = doc.add_heading('Юридическое заключение / Legal Opinion', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    clean_text = report_text.replace('**', '').replace('###', '').replace('`', '')
    lines = clean_text.split('\n')
    
    table_buffer = []
    
    for line in lines:
        stripped = line.strip()
        # Детекция строк таблицы, игнорируя Markdown-разделители (|---|)
        if '|' in stripped and set(stripped.replace('|', '').replace(' ', '')) != {'-'}:
            row_cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if row_cells: table_buffer.append(row_cells)
        else:
            if table_buffer:
                num_cols = max(len(r) for r in table_buffer)
                w_table = doc.add_table(rows=0, cols=num_cols)
                w_table.style = 'Table Grid'
                for r_idx, r_data in enumerate(table_buffer):
                    row_cells = w_table.add_row().cells
                    for c_idx, val in enumerate(r_data):
                        if c_idx < num_cols:
                            run = row_cells[c_idx].paragraphs[0].add_run(val)
                            if r_idx == 0: run.font.bold = True # Заголовок таблицы жирным
                table_buffer = []
            
            if stripped and not set(stripped.replace('|', '').replace(' ', '')) == {'-'}:
                p = doc.add_paragraph(stripped)
                if len(stripped) < 60 and (stripped.isupper() or stripped.endswith(':')):
                    p.runs[0].font.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. UI LAYOUT ---

# Sidebar (Боковая панель)
with st.sidebar:
    st.title("⚙️ LegalAI Config")
    st.write("**Mode:** International / Critical Focus")
    st.write("**AI Model:** Gemini 2.5 Flash")
    st.divider()
    st.markdown("⚠️ **Отказ от ответственности:**\nДанный отчет сформирован ИИ и не является официальной юридической консультацией.")

# Main Screen
st.title("⚖️ LegalAI Universal Enterprise")
st.markdown("##### Платформа автоматического аудита международных и локальных документов")

tab1, tab2 = st.tabs(["🚀 Анализ и Риски", "🔍 Сравнение редакций"])

with tab1:
    left, right = st.columns([1, 1.3], gap="large")
    
    with left:
        st.subheader("1. Загрузка данных")
        mode = st.radio("Источник:", ["Файл / Фото", "Текст"], horizontal=True)
        
        doc_data = ""
        u_file = None
        is_img = False
        
        if mode == "Файл / Фото":
            u_file = st.file_uploader("Загрузите PDF, DOCX, TXT или Фото", type=['pdf','docx','txt','jpg','png','jpeg'])
        else:
            doc_data = st.text_area("Вставьте текст документа:", height=300)
            
        btn = st.button("🚀 Начать экспертизу")

    with right:
        st.subheader("2. Результат анализа")
        
        if btn:
            payload = ""
            if u_file:
                if u_file.type in ['image/jpeg', 'image/png']:
                    payload = Image.open(u_file)
                    is_img = True
                else:
                    payload = extract_text(u_file)
            else:
                payload = doc_data
            
            if payload:
                with st.spinner("⚖️ ИИ анализирует критические моменты..."):
                    # ПРОМПТ ДЛЯ МЕЖДУНАРОДНОЙ ЭКСПЕРТИЗЫ
                    sys_prompt = """
                    Ты — ведущий юрист международной фирмы. Твоя цель: найти КРИТИЧЕСКИЕ (летальные) риски.
                    1. Определи тип документа и юрисдикцию (страну/право).
                    2. Вынеси вердикт: 🔴 КРАЙНЕ ОПАСНО, 🟡 НУЖНЫ ПРАВКИ, 🟢 БЕЗОПАСНО.
                    3. Найди только критические уязвимости. Мелкие опечатки игнорируй.
                    4. Сделай краткое резюме "Суть документа на простом языке".
                    5. Оформи таблицу: | Критический риск | Последствие | Рекомендация |
                    6. Если документ на английском, пиши отчет на русском, сохраняя термины в скобках.
                    """
                    
                    try:
                        if is_img:
                            res = model.generate_content([sys_prompt, payload])
                        else:
                            res = model.generate_content(f"{sys_prompt}\n\nDOCUMENT:\n{payload[:20000]}")
                        
                        st.session_state['final_report'] = res.text
                    except Exception as e:
                        st.error(f"AI Error: {e}")

        if 'final_report' in st.session_state:
            report = st.session_state['final_report']
            
            # Извлекаем метрики для Dashboard
            jur = "Auto-detect"
            vdt = "Pending"
            for line in report.split('\n'):
                if "Юрисдикция" in line or "JURISDICTION" in line: jur = line.split(':')[-1]
                if "вердикт" in line.lower() or "VERDICT" in line: vdt = line.split(':')[-1]

            m1, m2 = st.columns(2)
            m1.metric("Юрисдикция", jur.strip())
            m2.metric("Вердикт", vdt.strip())
            
            st.divider()
            
            # Кнопка скачивания
            word_file = create_pro_docx(report)
            st.download_button(
                label="📥 Скачать официальный отчет (.docx)",
                data=word_file,
                file_name="Legal_AI_Report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            with st.expander("📄 Посмотреть полный текст анализа", expanded=True):
                st.markdown(report)

with tab2:
    st.subheader("Сравнение двух версий одного документа")
    c1, c2 = st.columns(2)
    with c1: f1 = st.file_uploader("Оригинал", key="comp1")
    with c2: f2 = st.file_uploader("Версия с правками", key="comp2")
    
    if st.button("🔎 Найти юридические изменения"):
        if f1 and f2:
            t1, t2 = extract_text(f1), extract_text(f2)
            comp_res = model.generate_content(f"Сравни эти документы. Выдели только те изменения, которые меняют ответственность сторон или сроки: \n1: {t1[:9000]} \n2: {t2[:9000]}")
            st.markdown(comp_res.text)

st.divider()
st.caption("LegalAI Universal Enterprise 2026 | Powered by Gemini 2.5")
