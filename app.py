import streamlit as st
import google.generativeai as genai

# 1. Настройка страницы
st.set_page_config(page_title="Юрист-ИИ", layout="centered")
st.title("🛡️ Аудитор договоров 2026")

# 2. Подключение ключа (из Secrets)
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    st.success("ИИ готов к работе!")
else:
    st.error("Ключ не найден в настройках Streamlit!")
    st.stop()

# 3. Интерфейс
user_text = st.text_area("Вставьте текст договора здесь:", height=300)

if st.button("Найти риски"):
    if user_text:
        with st.spinner('Анализирую документ...'):
            # Тот самый промпт, который мы могли тестировать в AI Studio
            prompt = f"Ты профессиональный юрист. Проанализируй следующий текст договора и выдели основные юридические риски для меня. Пиши кратко и по делу: {user_text}"
            response = model.generate_content(prompt)
            st.subheader("Результат анализа:")
            st.write(response.text)
    else:
        st.warning("Сначала вставьте текст документа!")
      
