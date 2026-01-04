import streamlit as st
import requests
import re
import base64
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="LegalAI Analyzer", layout="wide", page_icon="🛡️")

def anonymize_text(text):
    """Скрывает паспортные данные и телефоны"""
    patterns = {
        r'\b\d{4}\s\d{6}\b': '[ПАСПОРТ]',
        r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b': '[ТЕЛЕФОН]',
    }
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    return text

# --- 2. API LOGIC (ПРЯМОЙ ВЫЗОВ) ---
def call_gemini(prompt, content, is_img=False):
    # Берем ключ напрямую из Secrets
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        return "❌ Ошибка: Ключ 'GOOGLE_API_KEY' не найден в настройках (Secrets)."

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    if not is_img:
        content = anonymize_text(content)
    
    parts = [{"text": f"{prompt}\n\nCONTENT:\n{content}"}]
    if is_img:
        parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(content).decode()}}]
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ Ошибка API: {res_json.get('error', {}).get('message', 'Неизвестная ошибка')}"
    except Exception as e:
        return f"⚠️ Ошибка связи: {str(e)}"

# --- 3. ИЗВЛЕЧЕНИЕ ТЕКСТА ---
def extract_from_file(file):
    try:
        if file.name.endswith(".pdf"):
            return " ".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
    except:
        return "Ошибка при чтении файла."
    return ""

def extract_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(["script", "style"]): s.decompose()
        return soup.get_text(separator=' ')[:20000]
    except:
        return "Не удалось загрузить текст по ссылке."

# --- 4. ИНТЕРФЕЙС ---
st.title("⚖️ LegalAI: Юридический Аудит")

with st.sidebar:
    audience = st.radio("Анализировать как:", ["Гражданин", "Предприниматель", "Юрист"])
    st.divider()
    st.write("🛡️ Данные обезличиваются перед отправкой.")

tab1, tab2 = st.tabs(["📄 Файл / Фото", "🔗 Ссылка"])

with tab1:
    up = st.file_uploader("Загрузите договор", type=["pdf", "docx", "jpg", "png"])

with tab2:
    url_input = st.text_input("Ссылка на оферту")

if st.button("🚀 НАЧАТЬ АУДИТ", type="primary"):
    txt_to_analyze = ""
    is_image = False
    
    if up:
        if up.type.startswith("image"):
            txt_to_analyze = up.getvalue()
            is_image = True
        else:
            txt_to_analyze = extract_from_file(up)
    elif url_input:
        txt_to_analyze = extract_from_url(url_input)

    if txt_to_analyze:
        with st.spinner("ИИ анализирует документ..."):
            prompts = {
                "Гражданин": "Найди ловушки и объясни их просто. Сделай SCORE: X/100.",
                "Предприниматель": "Оцени штрафы и риски для бизнеса. Сделай SCORE: X/100.",
                "Юрист": "Найди противоречия законам РФ. Сделай SCORE: X/100."
            }
            main_p = f"Role: Senior Lawyer. Audience: {audience}. {prompts[audience]} Format: SCORE, 🔴 РИСКИ, 🟡 СОВЕТЫ, 🟢 ЧЕК-ЛИСТ."
            
            result = call_gemini(main_p, txt_to_analyze, is_img=is_image)
            st.session_state.res = result
            st.markdown(result)
    else:
        st.error("Загрузите файл или вставьте ссылку.")
    
