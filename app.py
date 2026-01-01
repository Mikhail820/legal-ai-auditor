import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# 1. Настройка страницы
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️", layout="wide")

# 2. Подключение API ключа
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # Используем стандартную модель, она самая надежная
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("❌ Ключ API не найден. Проверьте Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Ошибка настройки API: {e}")

# 3. Интерфейс
st.title("⚖️ ИИ-Юрист: Проверка договоров")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Настройки")
    category = st.selectbox("Ниша:", ["Туризм", "Кредиты/Займы", "Аренда", "Услуги", "Общее"])
    uploaded_file = st.file_uploader("Файл", type=["pdf", "docx", "txt", "jpg", "png"])
    user_text = st.text_area("Или текст:", height=150)

with col2:
    st.subheader("Анализ")
    content = ""
    
    # Обработка файла
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                content = "".join([page.extract_text() for page in reader.pages])
            elif "word" in uploaded_file.type:
                doc = Document(uploaded_file)
                content = "\n".join([p.text for p in doc.paragraphs])
            elif "image" in uploaded_file.type:
                image = Image.open(uploaded_file)
                st.image(image, width=200)
                if st.button("📷 Распознать текст"):
                    res = model.generate_content(["Прочитай документ:", image])
                    content = res.text
            else:
                content = uploaded_file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Ошибка чтения файла: {e}")

    if user_text:
        content = user_text

    # Кнопка запуска
    if st.button("🚀 Проверить риски"):
        if not content:
            st.warning("Сначала загрузите договор!")
        else:
            with st.spinner("Изучаю документ..."):
                try:
                    prompt = f"Ты юрист. Ниша: {category}. Найди 3 главных риска и объясни их простым языком. Текст: {content}"
                    response = model.generate_content(prompt)
                    st.success("Готово!")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Ошибка при анализе: {e}")
    category = st.selectbox("Тип договора:", ["Туризм", "Займы/Кредиты", "Аренда", "Услуги", "Другое"])
    uploaded_file = st.file_uploader("Файл (PDF, DOCX, Фото)", type=["pdf", "docx", "jpg", "png", "txt"])
    user_text = st.text_area("Или текст:", height=150)

with col2:
    st.subheader("Результат")
    content = ""
    
    # Обработка файлов
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                content = "".join([page.extract_text() for page in reader.pages])
            elif "word" in uploaded_file.type:
                doc = Document(uploaded_file)
                content = "\n".join([p.text for p in doc.paragraphs])
            elif "image" in uploaded_file.type:
                image = Image.open(uploaded_file)
                st.image(image, width=200)
                if st.button("🔍 Распознать текст с фото"):
                    res = model.generate_content(["Прочитай этот документ:", image])
                    content = res.text
                    st.write("Текст распознан!")
            else:
                content = uploaded_file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Ошибка чтения файла: {e}")

    # Если ввели текст вручную
    if user_text:
        content = user_text

    # Кнопка запуска
    if st.button("🚀 Найти риски"):
        if not content:
            st.warning("Сначала загрузите договор!")
        else:
            with st.spinner("Юрист читает документ..."):
                try:
                    # Прямой вызов модели
                    prompt = f"Ты опытный юрист. Ниша: {category}. Найди 5 опасных мест в тексте: {content}"
                    response = model.generate_content(prompt)
                    st.success("Готово!")
                    st.markdown(response.text)
                except Exception as e:
                    # ВАЖНО: Если ошибка, выводим подробности для отладки
                    st.error("⚠️ Произошла ошибка при анализе.")
                    st.code(str(e))
                    st.write("Попробуем получить список доступных моделей...")
                    try:
                        models = [m.name for m in genai.list_models()]
                        st.write("Доступные вам модели:", models)
                    except:
                        st.write("Не удалось получить список моделей.")
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
