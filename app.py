import streamlit as st
import requests
import re
import base64
import random
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup

# --- 1. НАСТРОЙКИ И БЕЗОПАСНОСТЬ ---
st.set_page_config(page_title="LegalAI Analyzer", layout="wide", page_icon="🛡️")

def anonymize_text(text):
    """Скрывает чувствительные данные (ФЗ-152)"""
    patterns = {
        r'\b\d{4}\s\d{6}\b': '[ПАСПОРТ]',
        r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b': '[ТЕЛЕФОН]',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL]',
    }
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    return text

# --- 2. ЛОГИКА API (ПУЛ КЛЮЧЕЙ) ---
def get_api_key():
    # Ищет ключи GOOGLE_API_KEY_1, _2, _3 в Secrets
    keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 4)]
    valid_keys = [k for k in keys if k]
    return random.choice(valid_keys) if valid_keys else st.secrets.get("GOOGLE_API_KEY")

def call_gemini(prompt, content, is_img=False):
    api_key = get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    if not is_img:
        content = anonymize_text(content)
    
    parts = [{"text": f"{prompt}\n\nCONTENT:\n{content}"}]
    if is_img:
        parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(content).decode()}}]
    
    payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}}
    try:
        r = requests.post(url, json=payload, timeout=30).json()
        return r['candidates'][0]['content']['parts'][0]['text']
    except: return "⚠️ Ошибка связи с ИИ. Попробуйте другой метод ввода или проверьте ключи."

# --- 3. ИЗВЛЕЧЕНИЕ ТЕКСТА (ФАЙЛЫ И URL) ---
def extract_from_file(file):
    if file.name.endswith(".pdf"):
        return " ".join([p.extract_text() for p in PdfReader(file).pages])
    elif file.name.endswith(".docx"):
        return "\n".join([p.text for p in Document(file).paragraphs])
    return ""

def extract_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(["script", "style", "nav", "header", "footer"]): s.decompose()
        return soup.get_text(separator=' ')[:25000] # Лимит для стабильности
    except Exception as e:
        return f"Ошибка загрузки URL: {str(e)}"

# --- 4. ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("⚖️ LegalAI Pro")
    audience = st.radio("Анализировать как:", ["Гражданин", "Предприниматель", "Юрист"])
    st.divider()
    st.info("💡 ИИ подстроится под ваш уровень знаний и цели.")

st.header("Проверка юридической безопасности")

# Вкладки для разных типов ввода
tab1, tab2 = st.tabs(["📄 Файл или Фото", "🔗 Ссылка на оферту"])

with tab1:
    up = st.file_uploader("Загрузите договор", type=["pdf", "docx", "jpg", "png"])

with tab2:
    url_input = st.text_input("Вставьте ссылку на страницу с договором")

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
        with st.spinner("Читаю сайт..."):
            txt_to_analyze = extract_from_url(url_input)

    if txt_to_analyze:
        with st.spinner("ИИ изучает документ..."):
            prompts = {
                "Гражданин": "Найди ловушки, скрытые платежи и объясни всё простыми словами. Score 0-100.",
                "Предприниматель": "Оцени риски убытков, сроки, штрафы и условия выхода. Score 0-100.",
                "Юрист": "Проверь на соответствие законам РФ, найди лазейки и юридические ошибки. Score 0-100."
            }
            main_p = f"Role: Senior Lawyer. Audience: {audience}. {prompts[audience]} Format: SCORE: X/100, ### 🔴 РИСКИ, ### 🟡 СОВЕТЫ, ### 🟢 ЧЕК-ЛИСТ."
            
            st.session_state.res = call_gemini(main_p, txt_to_analyze, is_img=is_image)
    else:
        st.error("Пожалуйста, предоставьте файл или ссылку.")

# --- 5. ВЫВОД РЕЗУЛЬТАТОВ ---
if "res" in st.session_state:
    res = st.session_state.res
    col_res, col_check = st.columns([2, 1])
    
    with col_res:
        st.markdown(res)
    
    with col_check:
        st.subheader("✅ Что нужно сделать:")
        steps = re.findall(r"-\s*(.*?)(?:\n|$)", res)
        for i, step in enumerate(steps[:8]):
            st.checkbox(step.strip(), key=f"step_{i}")
