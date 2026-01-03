import streamlit as st
import google.generativeai as genai

st.title("🧪 Тест SDK: Поиск моделей")

api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("Ключ API не найден!")
    st.stop()

# Настраиваем SDK
genai.configure(api_key=api_key)

if st.button("Запустить сканирование через SDK"):
    try:
        st.write("Обращаюсь к API через SDK...")
        
        # Пытаемся получить список моделей официально
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if available_models:
            st.success(f"SDK видит {len(available_models)} моделей!")
            for model_name in available_models:
                st.code(model_name)
                
            # Пробуем сделать тестовый запрос самой "лайтовой" моделью
            test_model_name = "models/gemini-2.5-flash-lite"
            if test_model_name in available_models:
                st.write(f"---")
                st.write(f"Пытаюсь отправить тестовый запрос к `{test_model_name}`...")
                model = genai.GenerativeModel(test_model_name)
                response = model.generate_content("Привет! Ты работаешь через SDK?")
                st.success("✅ SDK ОТВЕТИЛ:")
                st.write(response.text)
        else:
            st.warning("SDK не нашел ни одной модели с поддержкой генерации контента.")
            
    except Exception as e:
        st.error("❌ SDK ВЫДАЛ ОШИБКУ:")
        st.error(e)
        st.info("Если тут ошибка 404, значит SDK 'стучится' не в ту дверь, и нам нужно оставаться на `requests`.")
        
