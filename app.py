Вот чистый, оптимизированный код, который можно сразу копировать в файл `app.py`.

**Требования:**
Установите библиотеки перед запуском:
`pip install streamlit google-generativeai PyPDF2 python-docx Pillow`

```python
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io

# ==================================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ И МОДЕЛИ
# ==================================================
st.set_page_config(page_title="LegalAI Enterprise", page_icon="⚖️", layout="wide")

# Настройка API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Добавьте GOOGLE_API_KEY в Secrets (Streamlit Cloud или .streamlit/secrets.toml)")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Системная инструкция для фиксации роли ИИ
SYSTEM_PROMPT = """
Ты — профессиональный корпоративный юрист. Твоя задача:
1. Анализировать документы на наличие скрытых юридических рисков.
2. Сравнивать версии договоров, выделяя изменения.
3. Составлять официальные ответы на претензии.
Пиши четко, структурировано, используй таблицы для сравнения и списки для рисков.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# ==================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
def extract_text(file) -> str:
    """Извлечение текста из PDF, DOCX или TXT"""
    fname = file.name.lower()
    try:
        if fname.endswith(".pdf"):
            pdf = PdfReader(io.BytesIO(file.getvalue()))
            return "\n".join([page.extract_text() for page in pdf.pages])
        elif fname.endswith(".docx"):
            doc = Document(io.BytesIO(file.getvalue()))
            return "\n".join([p.text for p in doc.paragraphs])
        elif fname.endswith(".txt"):
            return file.getvalue().decode("utf-8")
        return ""
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"

def create_docx(text: str):
    """Конвертация Markdown-ответа в файл Word"""
    doc = Document()
    doc.add_heading("Отчет LegalAI Enterprise", 0)
    for line in text.split('\n'):
        line = line.replace('**', '').replace('###', '').strip()
        if line:
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 3. ИНТЕРФЕЙС
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.caption("Интеллектуальный помощник для работы с юридическими документами")

with st.sidebar:
    st.header("Настройки")
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "Узбекистан", "Международное право"])
    depth = st.select_slider("Глубина анализа", ["Базовая", "Стандартная", "Детальная"])
    if st.button("🗑️ Очистить кэш"):
        st.session_state.clear()
        st.rerun()

tabs = st.tabs(["🔍 Анализ договора", "🔄 Сравнение версий", "✉️ Ответ на претензию"])

# --- ВКЛАДКА 1: АНАЛИЗ ---
with tabs[0]:
    st.subheader("Поиск рисков и аудит")
    up_file = st.file_uploader("Загрузите договор (PDF, DOCX, JPG)", type=["pdf", "docx", "png", "jpg"])
    
    if st.button("Начать юридический аудит", type="primary"):
        if up_file:
            with st.spinner("ИИ анализирует документ..."):
                if up_file.type.startswith("image"):
                    response = model.generate_content([f"Проведи детальный юридический аудит. Юрисдикция: {jurisdiction}", Image.open(up_file)])
                else:
                    text = extract_text(up_file)
                    response = model.generate_content(f"Проведи юридический анализ текста. Глубина: {depth}. Юрисдикция: {jurisdiction}.\n\nТекст:\n{text}")
                st.session_state.audit = response.text
        else:
            st.warning("Пожалуйста, загрузите файл.")

    if "audit" in st.session_state:
        st.markdown(st.session_state.audit)
        st.download_button("📥 Скачать в Word", create_docx(st.session_state.audit), "Audit_Report.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ---
with tabs[1]:
    st.subheader("Сравнение правок сторон")
    col1, col2 = st.columns(2)
    with col1: file1 = st.file_uploader("Оригинал (Ваш)", type=["pdf", "docx"])
    with col2: file2 = st.file_uploader("Версия контрагента", type=["pdf", "docx"])
    
    if st.button("Сравнить и найти отличия"):
        if file1 and file2:
            with st.spinner("Сравнение условий..."):
                t1, t2 = extract_text(file1), extract_text(file2)
                prompt = "Сравни два текста договора. Выведи таблицу: Пункт | Оригинал | Изменения | Риск для нас."
                response = model.generate_content(f"{prompt}\n\nТекст 1:\n{t1}\n\nТекст 2:\n{t2}")
                st.session_state.diff = response.text
        else:
            st.warning("Загрузите оба файла.")

    if "diff" in st.session_state:
        st.markdown(st.session_state.diff)

# --- ВКЛАДКА 3: ОТВЕТ ---
with tabs[2]:
    st.subheader("Генератор ответов")
    claim = st.text_area("Вставьте текст претензии или письма от контрагента", height=200)
    goal = st.text_input("Какую цель преследуем?", placeholder="Например: Аргументированно отказать в выплате штрафа")
    
    if st.button("Сформировать проект ответа"):
        if claim:
            with st.spinner("Пишем официальное письмо..."):
                prompt = f"Напиши официальный юридический ответ. Цель: {goal}. Юрисдикция: {jurisdiction}.\n\nПретензия:\n{claim}"
                response = model.generate_content(prompt)
                st.session_state.letter = response.text
        else:
            st.warning("Введите текст претензии.")

    if "letter" in st.session_state:
        st.markdown("### Черновик ответа:")
        st.info(st.session_state.letter)
        st.download_button("📥 Скачать ответ (.docx)", create_docx(st.session_state.letter), "Response_Letter.docx")

# Дисклеймер в футере
st.divider()
st.caption("⚠️ ВНИМАНИЕ: Данный инструмент использует ИИ. Результаты не являются юридической консультацией. Проверьте документ у юриста.")
```

### Как настроить ключи:
Если вы запускаете локально:
1. Создайте папку `.streamlit` в папке с проектом.
2. Создайте в ней файл `secrets.toml`.
3. Напишите там: `GOOGLE_API_KEY = "ваш_ключ_от_gemini"`.

Если вы запускаете на Streamlit Cloud:
1. Зайдите в настройки вашего приложения (Settings -> Secrets).
2. Вставьте туда `GOOGLE_API_KEY = "ваш_ключ_от_gemini"`.
