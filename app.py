import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
import io
from PIL import Image

# --- 1. НАСТРОЙКА ---
st.set_page_config(page_title="LegalAI Universal", page_icon="⚖️", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash') 
else:
    st.error("Добавьте GOOGLE_API_KEY в Secrets!")
    st.stop()

# --- 2. ФУНКЦИИ ---

def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages])
        elif file.name.endswith(".docx"):
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        return file.read().decode("utf-8")
    except Exception as e:
        return f"Ошибка чтения файла: {e}"

def create_docx(report_text):
    doc = Document()
    # Настройка стиля
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    doc.add_heading('Юридическое заключение LegalAI', 0)
    
    # Очищаем текст от Markdown артефактов
    clean_text = report_text.replace('**', '').replace('###', '')
    
    lines = clean_text.split('\n')
    in_table = False
    table_data = []

    for line in lines:
        if '|' in line and '-' not in line:
            # Это строка таблицы
            in_table = True
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                table_data.append(cells)
        else:
            if in_table:
                # Рисуем таблицу, когда она закончилась в тексте
                if table_data:
                    num_cols = max(len(row) for row in table_data)
                    word_table = doc.add_table(rows=0, cols=num_cols)
                    word_table.style = 'Table Grid'
                    for row_data in table_data:
                        row_cells = word_table.add_row().cells
                        for i, content in enumerate(row_data):
                            if i < num_cols:
                                row_cells[i].text = content
                table_data = []
                in_table = False
            
            if line.strip():
                doc.add_paragraph(line.strip())

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- 3. ИНТЕРФЕЙС ---

st.title("⚖️ LegalAI Universal Pro")
st.subheader("Автоматический аудит: Файлы, Фото или Текст")

tab1, tab2 = st.tabs(["🚀 Анализ", "🔍 Сравнение"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        method = st.radio("Способ ввода:", ["Файл/Фото", "Текст из буфера"])
        input_content = ""
        u_file = None
        
        if method == "Файл/Фото":
            u_file = st.file_uploader("Загрузите документ", type=["pdf", "docx", "jpg", "png", "jpeg"])
        else:
            input_content = st.text_area("Вставьте текст здесь:", height=300)

        if st.button("🚀 Провести экспертизу"):
            data_to_send = ""
            if u_file:
                if u_file.type in ["image/jpeg", "image/png"]:
                    with st.spinner("Распознаю фото..."):
                        img = Image.open(u_file)
                        res = model.generate_content(["Ты юрист. Определи тип документа, найди риски и сделай таблицу правок.", img])
                        st.session_state['res'] = res.text
                else:
                    data_to_send = extract_text(u_file)
            else:
                data_to_send = input_content

            if data_to_send:
                with st.spinner("ИИ анализирует..."):
                    prompt = f"""Ты топ-юрист РФ. 
                    1. Определи тип документа. 
                    2. Оценка (🔴/🟡/🟢). 
                    3. Найди риски. 
                    4. Создай таблицу: Пункт | Риск | Рекомендация. 
                    Текст: {data_to_send[:18000]}"""
                    res = model.generate_content(prompt)
                    st.session_state['res'] = res.text

    with col2:
        if 'res' in st.session_state:
            st.markdown(st.session_state['res'])
            st.download_button(
                "📥 Скачать отчет в Word (.docx)",
                data=create_docx(st.session_state['res']),
                file_name="legal_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

with tab2:
    st.write("### Сравнение редакций")
    f1 = st.file_uploader("Версия 1", type=["pdf", "docx"], key="v1")
    f2 = st.file_uploader("Версия 2", type=["pdf", "docx"], key="v2")
    if st.button("🔎 Сравнить"):
        if f1 and f2:
            t1, t2 = extract_text(f1), extract_text(f2)
            res = model.generate_content(f"Сравни изменения: \n1: {t1[:9000]} \n2: {t2[:9000]}")
            st.markdown(res.text)
    
