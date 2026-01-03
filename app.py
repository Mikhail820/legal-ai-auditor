import streamlit as st
import requests
import json

st.title("Проверка связи с Gemini API")

# 1. Получаем ключ
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("🔑 Ошибка: Вставь GOOGLE_API_KEY в Secrets (Settings -> Secrets)")
    st.stop()

# 2. Формируем ПРЯМОЙ запрос к стабильной версии v1
# Это исключает ошибку 404, так как мы не используем v1beta
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"

headers = {'Content-Type': 'application/json'}
payload = {
    "contents": [
        {
            "parts": [{"text": "Привет! Если ты меня слышишь, ответь: 'Связь установлена!'"}]
        }
    ]
}

if st.button("Проверить соединение"):
    with st.spinner("Отправка прямого запроса на v1..."):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            if response.status_code == 200:
                # Извлекаем текст из JSON ответа Google
                result = response.json()
                answer = result['candidates'][0]['content']['parts'][0]['text']
                st.success("✅ Ответ получен!")
                st.balloons()
                st.write(f"**ИИ говорит:** {answer}")
            elif response.status_code == 429:
                st.warning("⚠️ Ошибка 429: Лимит запросов исчерпан. Подожди 60 секунд.")
            else:
                st.error(f"❌ Ошибка {response.status_code}")
                st.json(response.json()) # Показываем полную ошибку для диагностики
                
        except Exception as e:
            st.error(f"Критическая ошибка: {e}")

st.info("Если этот тест пройдет — мы сможем нанизывать функции на этот каркас.")
