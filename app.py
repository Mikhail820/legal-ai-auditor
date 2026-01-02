import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="LegalAI Audit", page_icon="⚖️", layout="wide")

# Инициализация ИИ
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config={"temperature": 0.0}) 
else:
    st.error("🚨 Ключ API не найден.")
    st.stop()

# --- 2. ФУНКЦИИ ---

def read_txt_safe(file):
    raw = file.read()
    for enc in ['utf-8', 'windows-1251', 'cp1251']:
        try:
            return raw.decode(enc)
        except:
            continue
    return "Ошибка кодировки."

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
    
    doc.add_heading('РЕЗУЛЬТАТ ПРОВЕРКИ ДОКУМЕНТА', 0)
    
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
                            cells[c_idx].text = val
                table_buffer = []
            if stripped and not set(stripped.replace('|', '').replace(' ', '')) == {'-'}:
                doc.add_paragraph(stripped)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. ИНТЕРФЕЙС ---

st.title("⚖️ Понятный Юридический Аудит")
st.write("Загрузите договор, чтобы узнать, где вас пытаются обмануть.")

ui_left, ui_right = st.columns([1, 1.2], gap="large")

with ui_left:
    file_obj = st.file_uploader("Загрузите файл (PDF, DOCX, TXT, Фото)", type=['pdf','docx','txt','jpg','png','jpeg'])
    start_btn = st.button("🚀 ПРОВЕРИТЬ ДОКУМЕНТ")

with ui_right:
    if start_btn and file_obj:
        with st.spinner("Разбираем документ..."):
            is_visual = file_obj.type in ['image/jpeg', 'image/png']
            content = Image.open(file_obj) if is_visual else extract_text(file_obj)
            
            # ЖЕСТКИЙ ПРОМПТ ДЛЯ ПОНЯТНОГО ОТЧЕТА
            system_prompt = """
            ТЫ — ЮРИДИЧЕСКИЙ РЕВИЗОР. ПИШИ КОРОТКО, ПО ДЕЛУ, БЕЗ ВСТУПЛЕНИЙ.
            
            СТРУКТУРА ОТВЕТА:
            1. ЮРИСДИКЦИЯ: [Страна]
            2. ВЕРДИКТ: [🟢 МОЖНО ПОДПИСАТЬ / 🟡 НУЖНЫ ПРАВКИ / 🔴 ОПАСНО]
            3. ГЛАВНАЯ СУТЬ: [1 предложение: о чем этот договор]
            4. ТАБЛИЦА РИСКОВ (ОБЯЗАТЕЛЬНО):
            | ПУНКТ | ЧЕМ ЭТО ПЛОХО (ПРОСТЫМИ СЛОВАМИ) | КАК ИСПРАВИТЬ |
            |---|---|---|
            | [Номер/Название] | [Риск для кошелька или прав] | [Четкая фраза для замены] |
            
            ПРАВИЛА ОЦЕНКИ:
            - Штраф до 0.1% в день — это НОРМА (🟢).
            - Штраф больше 1% в день или запрет на расторжение — это ОПАСНО (🔴).
            - Если документ чист, в таблице напиши "Критических рисков не обнаружено".
            
            НЕ ФАНТАЗИРУЙ. ЕСЛИ РИСКА НЕТ — НЕ ВЫДУМЫВАЙ ЕГО.
            """
            
            try:
                if is_visual:
                    res = model.generate_content([system_prompt, content])
                else:
                    res = model.generate_content(f"{system_prompt}\n\nДОКУМЕНТ:\n{content[:18000]}")
                
                report = res.text
                st.session_state['report'] = report
                
                # Метрики
                v_color = "🟢" if "🟢" in report else "🔴" if "🔴" in report else "🟡"
                st.metric("Статус безопасности", v_color)
                
                st.markdown(report)
                
                # Кнопка Word
                doc_file = create_pro_docx(report)
                st.download_button("📥 Скачать понятный отчет (Word)", data=doc_file, file_name="Audit_Report.docx")
                
            except Exception as e:
                st.error(f"Ошибка: {e}")
                
