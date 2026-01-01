import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# 1. Настройка стиля
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. Инициализация ИИ (с исправленной моделью)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Добавили -latest для исправления ошибки NotFound
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    st.error("Ключ API не найден в настройках Streamlit!")
    st.stop()

# 3. Шапка
st.title("⚖️ LegalAI: Ваш персональный ИИ-юрист")
st.info("Загрузите договор, выберите нишу и получите мгновенный аудит рисков.")

# 4. Интерфейс
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🛠 Настройки")
    category = st.selectbox(
        "Тип договора:",
        ["Туризм", "Образование", "Недвижимость", "Труд", "Медицина", "Авто", "IT", "Общий"]
    )
    
    uploaded_file = st.file_uploader("Загрузите файл (PDF, DOCX, JPG, PNG)", type=["pdf", "docx", "jpg", "png", "txt"])
    user_text = st.text_area("Или вставьте текст вручную:", height=200)

with col2:
    content = ""
    # Логика извлечения текста из разных форматов
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            content = "".join([page.extract_text() for page in reader.pages])
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(uploaded_file)
            content = "\n".join([p.text for p in doc.paragraphs])
        elif uploaded_file.type in ["image/jpeg", "image/png"]:
            image = Image.open(uploaded_file)
            st.image(image, width=200)
            res = model.generate_content(["Распознай юридический текст на фото:", image])
            content = res.text
        else:
            content = uploaded_file.read().decode("utf-8")
    elif user_text:
        content = user_text

    if st.button("🚀 Начать аудит"):
        if content:
            with st.spinner("Анализирую..."):
                prompt = f"Ты эксперт-юрист в нише {category}. Найди 5 главных рисков в этом договоре и дай вердикт (подписывать или нет): {content}"
                try:
                    response = model.generate_content(prompt)
                    st.markdown("### 📋 Результат анализа:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Произошла ошибка при обращении к ИИ: {e}")
        else:
            st.warning("Сначала добавьте текст договора.")
