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
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    doc.add_heading('Юридический анализ документа', 0)
    
    clean_text = report_text.replace('**', '').replace('###', '').replace('🔴', 'РИСК:').replace('🟡', 'ВНИМАНИЕ:').replace('🟢', 'ОК:')
    sections = clean_text.split('\n\n')
    
    for section in sections:
        if '|' in section:
            lines = [l.strip() for l in section.split('\n') if l.strip()]
            if len(lines) > 1:
                table = doc.add_table(rows=0, cols=lines[0].count('|') + 1)
                table.style = 'Table Grid'
                for line in lines:
                    if '---' in line: continue
                    row_cells = table.add_row().cells
                    for i, content in enumerate(line.split('|')):
                        if i < len(row_cells): row_cells[i].text = content.strip()
        else:
            doc.add_paragraph(section)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- 3. ИНТЕРФЕЙС ---

st.title("⚖️ LegalAI Universal")
st.subheader("Универсальный аудит: Файлы, Фото или Текст из буфера")

tab1, tab2 = st.tabs(["🚀 Анализ документа", "🔍 Сравнение версий"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("### 📥 Ввод данных")
        
        # Выбор способа ввода
        input_method = st.radio("Выберите способ загрузки:", ["Загрузить файл/фото", "Вставить текст из буфера"])
        
        final_text = ""
        u_file = None
        
        if input_method == "Загрузить файл/фото":
            u_file = st.file_uploader("Загрузите PDF, DOCX или Фото", type=["pdf", "docx", "jpg", "png", "jpeg"])
        else:
            final_text = st.text_area("Вставьте текст документа здесь:", height=300, placeholder="Скопируйте текст договора или акта и вставьте его сюда...")

        if st.button("🚀 Провести экспертизу"):
            # Проверка наличия данных
            if (input_method == "Загрузить файл/фото" and u_file) or (input_method == "Вставить текст из буфера" and final_text):
                with st.spinner("ИИ проводит юридическую экспертизу..."):
                    try:
                        if u_file and u_file.type in ["image/jpeg", "image/png"]:
                            img = Image.open(u_file)
                            prompt = "Определи тип документа на фото. Проведи аудит, выдели риски и составь таблицу правок."
                            res = model.generate_content([prompt, img])
                        else:
                            # Если загружен файл-текст, извлекаем его, иначе берем из text_area
                            content_to_analyze = extract_text(u_file) if u_file else final_text
                            
                            prompt = f"""Ты ведущий юрист РФ. 
                            1. Определи тип документа. 
                            2. Дай оценку безопасности (🔴/🟡/🟢). 
                            3. Проанализируй содержание на соответствие законам РФ. 
                            4. Найди критические риски. 
                            5. Составь таблицу: 'Пункт' | 'Риск' | 'Рекомендация'. 
                            Документ: {content_to_analyze[:18000]}"""
                            res = model.generate_content(prompt)
                        
                        st.session_state['full_res'] = res.text
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                st.warning("Пожалуйста, загрузите файл или вставьте текст.")

    with col2:
        if 'full_res' in st.session_state:
            st.write("### 📝 Результат анализа")
            st.markdown(st.session_state['full_res'])
            st.download_button(
                "📥 Скачать отчет в Word",
                data=create_docx(st.session_state['full_res']),
                file_name="legal_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

with tab2:
    st.write("### 🔍 Сравнение двух редакций")
    c_a, c_b = st.columns(2)
    f_old = c_a.file_uploader("Версия 1", type=["pdf", "docx"], key="v1")
    f_new = c_b.file_uploader("Версия 2", type=["pdf", "docx"], key="v2")
    
    if st.button("🔎 Найти отличия"):
        if f_old and f_new:
            with st.spinner("Сравниваю изменения..."):
                t1, t2 = extract_text(f_old), extract_text(f_new)
                res = model.generate_content(f"Найди изменения в правах и обязанностях сторон: \n1: {t1[:9000]} \n2: {t2[:9000]}")
                st.markdown(res.text)

st.markdown("---")
st.caption("LegalAI Universal 2026. Поддержка PDF, Word, Фото и ручного ввода.")
        
