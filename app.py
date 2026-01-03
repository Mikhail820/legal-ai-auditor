import streamlit as st
import requests

st.title("🕵️ Сканер доступных моделей")

api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("Ключ не найден в Secrets!")
    st.stop()

# Эндпоинт для получения списка моделей
url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

if st.button("Найти рабочую модель"):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models_data = response.json()
            st.success("Список получен!")
            
            # Выводим только те модели, которые поддерживают генерацию текста
            available_models = []
            for m in models_data.get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # Убираем префикс 'models/', оставляем только имя
                    name = m['name'].replace('models/', '')
                    available_models.append(name)
            
            if available_models:
                st.write("### Твои рабочие модели:")
                st.info("Скопируй одну из них и напиши мне:")
                for name in available_models:
                    st.code(name)
            else:
                st.warning("Ключ работает, но нет доступных моделей для генерации.")
        else:
            st.error(f"Ошибка {response.status_code}")
            st.json(response.json())
    except Exception as e:
        st.error(f"Ошибка связи: {e}")
                
