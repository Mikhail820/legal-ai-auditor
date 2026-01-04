import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
import io
import base64

# --- 1. НАСТРОЙКИ СТИЛЕЙ ---
st.set_page_config(page_title="LegalAI Enterprise Max", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; background-color: #FF4B4B; color: white; border: none; }
    .stDownloadButton>button { width: 100%; border-radius: 10px; background-color: #28a745; color: white; }
    .main-header { font-size: 2.5rem; color: #FF4B4B; text-align: center; margin-bottom: 1.5rem; font-weight: 800; }
    .risk-card { 
        background-color: #ffffff; border-left: 6px solid #ff4b4b; padding: 20px; 
        border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    .score-container {
        background: #f0f2f6; padding: 20px; border-radius: 15px; text-align: center;
        border: 2px solid #dee2e6; margin-bottom: 20px;
    }
    .disclaimer { font-size: 0.8rem; color: #7f8c8d; padding: 15px; background: #fff3f3; border-radius: 10px; border: 1px solid #fab1a0; }
    </style>
    """, unsafe_allow_html=True)

TARGET_MODEL = "gemini-2.5-flash-lite"
DISCLAIMER_TEXT = "⚠️ ВНИМАНИЕ: Анализ выполнен ИИ. Не является юридической консультацией. Проконсультируйтесь с юристом."

# --- 2. ДВИЖОК ИИ ---
def call_gemini(prompt, content, is_image=False):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"
    
    if is_image:
        img_b64 = base64.b64encode(content).decode('utf-8')
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    else:
        payload = {"contents": [{"parts": [{"text": f"{prompt}\n\nДОКУМЕНТ:\n{content}"}]}]}

    try:
        # Увеличили таймаут до 120 секунд для сложных протоколов
        r = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=120)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        st.error(f"Ошибка ИИ: Проверьте интернет или размер документа. ({e})")
        return None

# --- 3. ИНСТРУМЕНТЫ ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(DISCLAIMER_TEXT).italic = True
    doc.add_paragraph("-" * 40)
    for line in text.replace('*', '').split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            return " ".join([p.extract_text() for p in PdfReader(io.BytesIO(file_bytes)).pages if p.extract_text()])
        elif filename.lower().endswith(".docx"):
            return "\n".join([p.text for p in Document(io.BytesIO(file_bytes)).paragraphs])
    except: return "Ошибка чтения."
    return ""

# --- 4. БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Конфигурация")
    role = st.radio("Кто вы:", ["Предприниматель", "Юрист", "Физическое лицо"])
    loc = st.selectbox("Страна:", ["РФ", "Казахстан", "Узбекистан", "Международное право"])
    detail = st.select_slider("Глубина анализа:", options=["Кратко", "Стандарт", "Максимум"])
    st.divider()
    st.markdown(f'<div class="disclaimer">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

# --- 5. ОСНОВНОЙ ИНТЕРФЕЙС ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Max</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🚀 УМНЫЙ АУДИТ", "🔍 СРАВНЕНИЕ", "📋 ПРОТОКОЛЫ И ПИСЬМА"])

with tab1:
    c1, c2 = st.columns([1, 1.3])
    with c1:
        dtype = st.selectbox("Тип документа:", [
            "Договор услуг", "Договор Поставки", "Аренда (Жилая/Коммерц)", 
            "NDA / Конфиденциальность", "Займ / Инвестиции", "Подряд / Стройка / IT",
            "Страховой полис", "Купля-продажа (Дом/Авто)", "Кредит / Рассрочка",
            "Трудовой договор", "Обучение / Онлайн-курсы", "Другое"
        ])
        src = st.radio("Загрузка:", ["Файл/Скан", "Текст", "Ссылка"], horizontal=True)
        
        input_data, is_img = None, False
        if src == "Файл/Скан":
            f = st.file_uploader("Загрузите (PDF, DOCX, JPG, PNG)", type=["pdf", "docx", "png", "jpg"])
            if f:
                if f.type.startswith("image"): input_data, is_img = f.getvalue(), True
                else: input_data = extract_text(f.getvalue(), f.name)
        elif src == "Ссылка":
            url = st.text_input("Вставьте URL:")
            if url: input_data = BeautifulSoup(requests.get(url).text, 'html.parser').get_text()[:30000]
        else: input_data = st.text_area("Вставьте текст:", height=250)

        if st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ"):
            if input_data:
                with c2:
                    with st.spinner("Анализирую риски и потери..."):
                        p = f"""Ты эксперт по рискам. Роль: {role}. Страна: {loc}. Тип: {dtype}. Детальность: {detail}.
                        ОТВЕТЬ ПО ПЛАНУ:
                        1. LEGAL SCORE: Безопасность от 0 до 100%.
                        2. 🔴 КРИТИЧЕСКИЕ РИСКИ: Найди опасные пункты.
                        3. 💸 ПОТЕРИ: Оцени финансовый ущерб для {role}.
                        4. ⚠️ ЛОВУШКИ: Скрытые штрафы, автопродление, суды.
                        5. ⚖️ ЗАКОН: Ссылки на статьи ГК или законы.
                        6. 🎯 ВОПРОСЫ: 3 вопроса для переговоров.
                        7. ✅ ИТОГ: Подписывать или нет."""
                        res = call_gemini(p, input_data, is_img)
                        if res: st.session_state.audit_max = res

    if "audit_max" in st.session_state:
        with c2:
            st.markdown('<div class="score-container"><h3>📊 Результаты анализа</h3></div>', unsafe_allow_html=True)
            for part in st.session_state.audit_max.split('\n'):
                if any(x in part for x in ["🔴", "💸", "⚠️"]):
                    st.markdown(f'<div class="risk-card">{part}</div>', unsafe_allow_html=True)
                else: st.markdown(part)
            st.download_button("📥 Скачать Word отчет", create_docx(st.session_state.audit_max, f"Анализ {dtype}"), "Legal_Report.docx")

with tab2:
    st.subheader("🔍 Сравнение версий")
    col_a, col_b = st.columns(2)
    fa = col_a.file_uploader("Версия А", type=["pdf", "docx"], key="fa")
    fb = col_b.file_uploader("Версия Б", type=["pdf", "docx"], key="fb")
    if st.button("⚖️ НАЙТИ РАЗНИЦУ") and fa and fb:
        with st.spinner("Сравниваю..."):
            res = call_gemini("Найди отличия и составь таблицу изменений.", f"А: {extract_text(fa.getvalue(), fa.name)}\nБ: {extract_text(fb.getvalue(), fb.name)}")
            if res: st.markdown(res)

with tab3:
    st.subheader("✍️ Протоколы и письма")
    if "audit_max" in st.session_state:
        st.info("💡 Можно создать протокол на базе текущего аудита.")
        if st.button("📋 СГЕНЕРИРОВАТЬ ПРОТОКОЛ РАЗНОГЛАСИЙ"):
            with st.spinner("Создаю таблицу правок..."):
                res = call_gemini("На основе аудита сделай таблицу Протокола: Пункт контрагента - Наша редакция - Почему это важно (потери).", st.session_state.audit_max)
                if res: 
                    st.session_state.prot_res = res
                    st.markdown(res)
                    st.download_button("📥 Скачать Протокол", create_docx(res, "Протокол разногласий"), "Protocol.docx")
    st.divider()
    manual = st.text_area("Или напишите задачу вручную (напр. 'Напиши претензию'):")
    if st.button("✉️ СОЗДАТЬ ДОКУМЕНТ"):
        if manual:
            res = call_gemini("Напиши официальный документ.", manual)
            if res: st.markdown(res)
