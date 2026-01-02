import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import time

# 1. Настройка страницы
st.set_page_config(page_title="LegalAI Auditor", page_icon="⚖️")

# 2. Инициализация (самая стабильная модель для бесплатного тарифа)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    st.error("Ключ API не найден в Secrets!")
    st.stop()

# 3. Интерфейс
st.title("⚖️ Юрист-Аудитор 2026")
st.info("Бесплатная версия: лимит 1 запрос в 10 секунд.")

cat = st.selectbox("Категория договора:", [
    "Банковское обслуживание (карты, вклады)", 
    "Кредиты и ипотека", 
    "Аренда недвижимости",
    "Трудовой договор",
    "Другое"
])

file = st.file_uploader("Загрузите файл", type=["pdf", "docx", "txt"])
txt = st.text_area("Или текст:")

# 4. Логика
if st.button("🚀 Начать анализ"):
    # Небольшая задержка, чтобы сбросить минутный лимит Google
    time.sleep(2) 
    
    content = ""
    if file:
        try:
            if file.name.endswith(".pdf"):
                reader = PdfReader(file)
                content = "".join([p.extract_text() for p in reader.pages])
            elif file.name.endswith(".docx"):
                doc = Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode("utf-8")
        except:
            st.error("Ошибка чтения файла")
    else:
        content = txt

    if content:
        # Ограничиваем текст, если он слишком длинный (для бесплатного тарифа)
        content = content[:15000] 
        
        with st.spinner("Анализирую..."):
            try:
                prompt = f"Ты эксперт-юрист. Категория: {cat}. Найди 5 главных рисков для клиента и предложи, как их исправить. Текст: {content}"
                res = model.generate_content(prompt)
                st.success("Готово!")
                st.markdown(res.text)
            except Exception as e:
                if "429" in str(e):
                    st.error("Превышен лимит запросов. Подождите 1 минуту и попробуйте снова.")
                else:
                    st.error(f"Ошибка: {e}")
    else:
        st.warning("Добавьте текст!")
