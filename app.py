import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
import io
from PIL import Image

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="LegalAI Ultimate 2026", 
    page_icon="🛡️", 
    layout="wide"
)

# Инициализация ИИ (Зафиксировано на работающей версии 2.5)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash') 
else:
    st.error("Добавьте GOOGLE_API_KEY в настройки (Secrets)!")
    st.stop()

# --- 2. ФУНКЦИИ ОБРАБОТКИ ТЕКСТА И ФАЙЛОВ ---

def extract_text(file):
    """Извлекает текст из PDF, DOCX или TXT"""
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages])
        elif file.name.endswith(".docx"):
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        return file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return ""

def create_docx(report_text):
    """Создает профессиональный Word-отчет с таблицей правок"""
    doc = Document()
    
    # Настройка шрифтов для кириллицы
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    doc.add_heading('Юридическое заключение LegalAI', 0)
    
    # Разбиваем текст от ИИ на разделы
    sections = report_text.split('###')
    for section in sections:
        clean_section = section.strip()
        if not clean_section:
            continue
            
        # Если блок содержит разметку таблицы Markdown
        if '|' in clean_section and '--' in clean_section:
            lines = [l.strip() for l in clean_section.split('\n') if l.strip()]
            if len(lines) > 1:
                # Создаем таблицу в Word
                cols_count = lines[0].count('|') + 1
                table = doc.add_table(rows=0, cols=cols_count)
                table.style = 'Table Grid'
                
                for line in lines:
                    if '---' in line: continue # Пропускаем разделительную строку
                    cells_data = [c.strip() for c in line.split('|') if c.strip() or '|' in line]
                    row_cells = table.add_row().cells
                    for i, content in enumerate(cells_data):
                        if i < len(row_cells):
                            row_cells[i].text = content
        else:
            # Обычный текст
            doc.add_paragraph(clean_section)

    # Сохранение в буфер памяти
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- 3. ИНТЕРФЕЙС (ПРОФЕССИОНАЛЬНЫЙ ЛЕНДИНГ) ---

st.title("🛡️ LegalAI Ultimate 2026")
st.subheader("Интеллектуальная защита ваших юридических интересов")

# Рекламные блоки для привлечения внимания
c_m1, c_m2, c_m3 = st.columns(3)
with c_m1:
    st.info("🔍 **Глубокий аудит**\n\nПроверка на соответствие ГК РФ и поиск скрытых ловушек за 10 секунд.")
with c_m2:
    st.success("⚖️ **Таблица правок**\n\nГотовые юридические формулировки для оспаривания условий.")
with c_m3:
    st.warning("🔍 **Сравнение версий**\n\nКонтроль за изменениями: убедитесь, что вас не обманули.")

st.markdown("---")

tab1, tab2 = st.tabs(["🧐 Аудит и Анализ", "🔍 Сравнение документов"])

# ВКЛАДКА 1: АУДИТ
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("### 📁 Шаг 1: Загрузка")
        category = st.selectbox("Категория договора:", ["Банковский вклад", "Кредит/Ипотека", "Аренда", "Трудовой", "Услуги/IT"])
        uploaded_file = st.file_uploader("Загрузите PDF, DOCX или ФОТО страницы", type=["pdf", "docx", "jpg", "png", "jpeg"])
        analyze_btn = st.button("🚀 Начать полную проверку")

    with col2:
        st.write("### 📝 Шаг 2: Экспертное заключение")
        if analyze_btn and uploaded_file:
            with st.spinner("ИИ анализирует документ и готовит отчет..."):
                try:
                    # Обработка изображений (OCR) или текста
                    if uploaded_file.type in ["image/jpeg", "image/png"]:
                        img = Image.open(uploaded_file)
                        prompt = [f"Проведи юридический аудит этого скана ({category}). Найди 5 рисков и составь таблицу правок.", img]
                    else:
                        text_data = extract_text(uploaded_file)
                        prompt = f"""Ты - ведущий юрист РФ. Категория: {category}. Проведи аудит текста: {text_data[:15000]}. 
                        1. Выдай вердикт (🔴 Опасно / 🟡 Внимательно / 🟢 Безопасно).
                        2. Объясни суть договора простыми словами.
                        3. Найди 5 рисков со ссылками на ГК РФ.
                        4. Составь таблицу правок: 'Пункт' | 'В чем риск' | 'Предлагаемая редакция'."""
                    
                    response = model.generate_content(prompt)
                    
                    # Вывод результата на экран
                    st.markdown(response.text)
                    
                    # Генерация и кнопка скачивания Word (решает проблему кодировки)
                    st.download_button(
                        label="📥 Скачать профессиональный отчет (.docx)",
                        data=create_docx(response.text),
                        file_name="Legal_Audit_Report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Ошибка ИИ: {e}")

# ВКЛАДКА 2: СРАВНЕНИЕ
with tab2:
    st.write("### 🔍 Сравнение двух редакций")
    st.write("Помогает увидеть, что именно изменил контрагент во второй версии документа.")
    c_old, c_new = st.columns(2)
    f_old = c_old.file_uploader("Оригинал (Ваша версия)", type=["pdf", "docx"], key="v1")
    f_new = c_new.file_uploader("Новая версия (От партнера)", type=["pdf", "docx"], key="v2")
    
    if st.button("🔎 Найти отличия"):
        if f_old and f_new:
            with st.spinner("Сравниваю условия..."):
                t1 = extract_text(f_old)
                t2 = extract_text(f_new)
                compare_prompt = f"Сравни тексты и выдели все изменения. Убедись, что наши правки внесены правильно. \n1: {t1[:8000]} \n2: {t2[:8000]}"
                res = model.generate_content(compare_prompt)
                st.markdown(res.text)

# --- ПОДВАЛ ---
st.markdown("---")
st.caption("LegalAI Ultimate 2026. Работает на модели Gemini 2.5 Flash. Не является юридической консультацией.")
    
