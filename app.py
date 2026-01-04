import streamlit as st
import requests
import re
import base64
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="LegalAI Pro 2.0", layout="wide", page_icon="⚖️")

def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

def anonymize_text(text):
    patterns = {
        r'\b\d{4}\s\d{6}\b': '[ПАСПОРТ]',
        r'\b\+?\d{1,3}[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b': '[ТЕЛЕФОН]',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL]',
    }
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    return text

# --- 2. API LOGIC (ПРЯМОЙ POST ЗАПРОС) ---
def call_gemini(prompt, content, is_img=False):
    # Только один ключ, без пула
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        return "❌ Ошибка: Ключ 'GOOGLE_API_KEY' не найден в Secrets."

    # Прямой URL к Gemini 2.0 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    if not is_img:
        content = anonymize_text(content)
    
    parts = [{"text": f"{prompt}\n\nCONTENT:\n{content}"}]
    if is_img:
        parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(content).decode()}}]
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000}
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
def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            return " ".join([p.extract_text() for p in PdfReader(file).pages])
        elif file.name.endswith(".docx"):
            return "\n".join([p.text for p in Document(file).paragraphs])
    except: return "Ошибка чтения файла."
    return ""

def extract_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Убираем лишний мусор со страницы
        for s in soup(["script", "style", "nav", "header", "footer"]): s.decompose()
        return soup.get_text(separator=' ')[:30000]
    except: return "Ошибка загрузки URL."

# --- 4. БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.title("⚖️ LegalAI Pro 2.0")
    audience = st.radio("Роль анализа:", ["Гражданин", "Предприниматель", "Юрист"])
    jurisdiction = st.selectbox("Юрисдикция:", ["РФ (ГК, КоАП)", "СНГ", "Международное право"])
    
    st.divider()
    if st.button("🔄 Сбросить всё", use_container_width=True):
        reset_app()
    
    st.divider()
    st.success("🤖 Модель: 2.0 Flash (No SDK)")

# --- 5. ГЛАВНЫЙ ЭКРАН ---
tab1, tab2 = st.tabs(["📄 Документ / Фото", "🔗 Ссылка"])

with tab1:
    up = st.file_uploader("Загрузите договор", type=["pdf", "docx", "jpg", "png"])

with tab2:
    url_input = st.text_input("Вставьте ссылку на оферту")

if st.button("🚀 НАЧАТЬ АУДИТ", type="primary", use_container_width=True):
    txt_to_analyze = ""
    is_image = False
    
    if up:
        if up.type.startswith("image"):
            txt_to_analyze, is_image = up.getvalue(), True
        else:
            txt_to_analyze = extract_text(up)
    elif url_input:
        with st.spinner("Читаю сайт..."):
            txt_to_analyze = extract_from_url(url_input)

    if txt_to_analyze:
        with st.spinner(f"Анализирую для: {audience}..."):
            prompts = {
                "Гражданин": "Найди скрытые риски и штрафы. Пиши просто.",
                "Предприниматель": "Фокус на сроки, ответственность и штрафы. Score 0-100.",
                "Юрист": f"Анализ по праву {jurisdiction}. Поиск коллизий и лазеек."
            }
            full_p = f"Role: Senior Lawyer. Audience: {audience}. Jurisdiction: {jurisdiction}. {prompts[audience]} Format: SCORE: X/100, ### 🔴 РИСКИ, ### 🟡 СОВЕТЫ, ### 🟢 ПЛАН ДЕЙСТВИЙ (списком)."
            
            st.session_state.res = call_gemini(full_p, txt_to_analyze, is_img=is_image)
    else:
        st.error("Нет данных для анализа.")

# --- 6. ВЫВОД ---
if "res" in st.session_state:
    res = st.session_state.res
    left, right = st.columns([2, 1])
    
    with left:
        st.subheader("📊 Анализ")
        sections = res.split("###")
        for s in sections:
            if "🔴" in s: st.error(s)
            elif "🟡" in s: st.warning(s)
            elif "🟢" in s: st.success(s)
            else: st.markdown(s)

    with right:
        st.subheader("✅ Чек-лист")
        steps = re.findall(r"-\s*(.*?)(?:\n|$)", res)
        for i, step in enumerate(steps[:10]):
            st.checkbox(step.strip(), key=f"ch_{i}")
