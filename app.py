import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io
from PIL import Image
import re

# --- 1. НАСТРОЙКИ СТРАНИЦЫ И БЕЗОПАСНОСТЬ ---
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

# Дисклеймер в самом верху (неизменный)
st.error("⚠️ ВНИМАНИЕ: Данный инструмент использует ИИ. Результаты не являются юридической консультацией. Проверяйте отчеты у квалифицированных юристов.")

# --- 2. ПОДКЛЮЧЕНИЕ К ИИ ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.error("Критическая ошибка: API ключ не найден в Secrets!")
    st.stop()

# --- 3. ТЕХНИЧЕСКИЕ ФУНКЦИИ ---
def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
        return file.read().decode('utf-8', errors='ignore')
    except: return "Ошибка чтения файла."

def create_docx_pro(report_text, title="ОТЧЕТ LEGALAI"):
    doc = Document()
    doc.add_paragraph("ВАЖНО: Документ подготовлен ИИ. Требуется проверка юристом.").bold = True
    doc.add_heading(title, 0)
    
    # Логика сохранения таблиц в Word
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

# --- 4. ИНТЕРФЕЙС ---
st.sidebar.title("Настройки")
depth = st.sidebar.select_slider("Глубина анализа:", options=["Базовая", "Стандартная", "Глубокая"], value="Глубокая")

tab1, tab2, tab3 = st.tabs(["🚀 АНАЛИЗ", "🔍 СРАВНЕНИЕ", "✉️ ГЕНЕРАТОР ОТВЕТА"])

# --- ВКЛАДКА 1: ПОЛНЫЙ АНАЛИЗ (Вернул всё как было) ---
with tab1:
    st.subheader("Юридический аудит документа")
    u_file = st.file_uploader("Загрузите договор (PDF, DOCX или ФОТО)", type=['pdf','docx','jpg','png','jpeg'], key="anal")
    
    if st.button("🚀 ЗАПУСТИТЬ ПОЛНУЮ ПРОВЕРКУ", use_container_width=True, type="primary"):
        if u_file:
            with st.spinner("Идет глубокий юридический анализ..."):
                content = Image.open(u_file) if u_file.type.startswith('image') else extract_text(u_file)
                
                # Тот самый мощный промпт, который мы настраивали
                sys_prompt = f"""ТЫ ВЕДУЩИЙ ЮРИСТ. Проведи анализ с глубиной: {depth}.
                ОБЯЗАТЕЛЬНО соблюдай структуру:
                1. Jurisdiction: Определи применимое право.
                2. Verdict: Насколько опасно подписывать (в %).
                3. Risk Table: Составь таблицу | Пункт | Риск | Рекомендация правки |.
                4. Key Findings: Самые критичные моменты.
                Используй ссылки на статьи закона (ГК РФ и др.)."""
                
                res = model.generate_content([sys_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{sys_prompt}\n\n{content}")
                st.session_state.full_report = res.text

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
        st.download_button("📥 СКАЧАТЬ ПОЛНЫЙ ОТЧЕТ", data=create_docx_pro(st.session_state.full_report), file_name="Legal_Report.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение двух редакций")
    col1, col2 = st.columns(2)
    old_f = col1.file_uploader("Ваша версия", type=['pdf','docx'])
    new_f = col2.file_uploader("Версия контрагента", type=['pdf','docx'])
    
    if st.button("⚖️ НАЙТИ ОТЛИЧИЯ"):
        if old_f and new_f:
            with st.spinner("Сравниваю тексты..."):
                t1, t2 = extract_text(old_f), extract_text(new_f)
                res = model.generate_content(f"Найди отличия между текстами. Составь таблицу изменений и оцени их риск для нас.\n\nТекст 1: {t1[:10000]}\n\nТекст 2: {t2[:10000]}")
                st.session_state.diff_report = res.text

    if 'diff_report' in st.session_state:
        st.markdown(st.session_state.diff_report)

# --- ВКЛАДКА 3: ГЕНЕРАТОР ОТВЕТА (Новое дополнение) ---
with tab3:
    st.subheader("Генератор официального письма")
    doc_in = st.file_uploader("Загрузите документ контрагента для ответа", type=['pdf','docx','jpg','png'], key="gen")
    user_goal = st.text_area("Что вы хотите получить в итоге? (Например: отказ от штрафа, снижение цены)", placeholder="Опишите ваши требования...")
    
    if st.button("✍️ СОСТАВИТЬ ПИСЬМО"):
        if doc_in:
            with st.spinner("Составляю текст письма..."):
                content = Image.open(doc_in) if doc_in.type.startswith('image') else extract_text(doc_in)
                reply_prompt = f"""Напиши профессиональный официальный ответ на этот документ. 
                Пожелания заказчика: {user_goal}. Стиль: Официально-деловой, твердый, но корректный. 
                Используй юридическую аргументацию. Оформи как готовое письмо."""
                
                response = model.generate_content([reply_prompt, content]) if isinstance(content, Image.Image) else model.generate_content(f"{reply_prompt}\n\n{content}")
                st.session_state.reply_final = response.text

    if 'reply_final' in st.session_state:
        st.markdown(st.session_state.reply_final)
        st.download_button("📥 СКАЧАТЬ ГОТОВОЕ ПИСЬМО", data=create_docx_pro(st.session_state.reply_final, "ОФИЦИАЛЬНОЕ ПИСЬМО"), file_name="Official_Letter.docx")
    
