import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
import io
import base64

# --- 1. CONFIG & STYLES ---
st.set_page_config(page_title="LegalAI Enterprise Max", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 10px; background-color: #28a745; color: white; }
    .main-header { font-size: 2.5rem; color: #FF4B4B; text-align: center; margin-bottom: 1rem; font-weight: 800; }
    
    /* Блоки рисков */
    .risk-card { 
        background-color: #ffffff; 
        border-left: 6px solid #ff4b4b; 
        padding: 20px; 
        border-radius: 8px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .loss-text { color: #d63031; font-weight: bold; font-size: 1.1rem; }
    .score-container {
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 25px; border-radius: 15px; text-align: center;
        border: 2px solid #dee2e6; margin-bottom: 25px;
    }
    .disclaimer { font-size: 0.8rem; color: #7f8c8d; padding: 15px; background: #fff3f3; border-radius: 10px; border: 1px solid #fab1a0; }
    </style>
    """, unsafe_allow_html=True)

TARGET_MODEL = "gemini-2.5-flash-lite"
DISCLAIMER_TEXT = "⚠️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ: Данный инструмент использует ИИ. Результаты носят ознакомительный характер, не являются юридической консультацией и могут содержать ошибки. Всегда проверяйте документы у лицензированного адвоката."

# --- 2. CORE ENGINE ---
def call_gemini(prompt, content, is_image=False):
    api_key = st.secrets.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/{TARGET_MODEL}:generateContent?key={api_key}"
    
    if is_image:
        img_b64 = base64.b64encode(content).decode('utf-8')
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}]}]}
    else:
        payload = {"contents": [{"parts": [{"text": f"{prompt}\n\nДОКУМЕНТ ДЛЯ АНАЛИЗА:\n{content}"}]}]}

    try:
        r = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=90)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        st.error(f"Ошибка ИИ: {e}")
        return None

# --- 3. HELPERS ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    p = doc.add_paragraph(); p.add_run(DISCLAIMER_TEXT).italic = True
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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🛠️ Конфигуратор")
    role = st.radio("Ваша роль:", ["Предприниматель", "Юрист", "Физическое лицо"])
    loc = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "Международное право"])
    detail = st.select_slider("Глубина анализа:", options=["Кратко", "Стандарт", "Максимум"])
    
    st.divider()
    st.markdown(f'<div class="disclaimer">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)
    
    if st.button("🗑️ Очистить историю"):
        st.session_state.clear()
        st.rerun()

# --- 5. MAIN UI ---
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Max</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🚀 УМНЫЙ АУДИТ", "🔍 СРАВНЕНИЕ", "📋 ПРОТОКОЛЫ И ПИСЬМА"])

with tab1:
    c1, c2 = st.columns([1, 1.3])
    with c1:
        dtype = st.selectbox("Что проверяем?", [
            "Договор оказания услуг", "Договор Поставки", "Аренда (Жилая/Коммерческая)", 
            "NDA / Конфиденциальность", "Займ / Инвестиции", "Подряд / Стройка / IT",
            "Страховой полис", "Купля-продажа (Недвижимость/Авто)", "Кредитный договор",
            "Трудовой договор", "Обучение / Онлайн-курсы", "Другое"
        ])
        src = st.radio("Способ загрузки:", ["Файл/Скан", "Текст", "Ссылка"], horizontal=True)
        
        input_data, is_img = None, False
        if src == "Файл/Скан":
            f = st.file_uploader("Загрузите документ (PDF, DOCX, JPG, PNG)", type=["pdf", "docx", "png", "jpg"])
            if f:
                if f.type.startswith("image"): input_data, is_img = f.getvalue(), True
                else: input_data = extract_text(f.getvalue(), f.name)
        elif src == "Ссылка":
            url = st.text_input("Вставьте ссылку:")
            if url: input_data = BeautifulSoup(requests.get(url).text, 'html.parser').get_text()[:30000]
        else: input_data = st.text_area("Вставьте текст здесь:", height=250)

        if st.button("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ"):
            if input_data:
                with c2:
                    with st.spinner("Работаю: считаю риски, ищу ловушки, оцениваю потери..."):
                        prompt = f"""Ты - ведущий эксперт по управлению рисками и юрист. 
                        Твоя цель: защитить интересы стороны '{role}' в стране {loc}. 
                        Тип документа: {dtype}. Глубина проработки: {detail}.

                        СТРОГИЙ ПЛАН ОТВЕТА:
                        1. 📊 LEGAL SAFETY SCORE: Дай оценку документа от 0 до 100%. Объясни почему.
                        2. 🔴 КРИТИЧЕСКИЕ РИСКИ: Найди пункты, которые 'убивают' интересы юзера.
                        3. 💸 ПОТЕРИ ДЛЯ БИЗНЕСА/ЛИЧНОСТИ: Для каждого риска рассчитай или опиши потенциальный финансовый и репутационный ущерб.
                        4. ⚠️ СКРЫТЫЕ ЛОВУШКИ: Проверь автопродление, скрытые пени, подсудность, условия расторжения.
                        5. ⚖️ ССЫЛКИ НА ЗАКОН: Укажи, каким статьям ГК или законам противоречат пункты (если есть).
                        6. 🎯 ТОП-3 ВОПРОСА ДЛЯ ПЕРЕГОВОРОВ: Сформулируй вопросы, которые заставят контрагента понервничать.
                        7. ✅ ИТОГОВАЯ РЕКОМЕНДАЦИЯ: Подписывать, править или бежать."""
                        
                        res = call_gemini(prompt, input_data, is_img)
                        if res: st.session_state.audit_max = res

    if "audit_max" in st.session_state:
        with c2:
            st.markdown('<div class="score-container"><h3>Результаты Enterprise-анализа</h3></div>', unsafe_allow_html=True)
            for part in st.session_state.audit_max.split('\n'):
                if "🔴" in part or "💸" in part or "⚠️" in part:
                    st.markdown(f'<div class="risk-card">{part}</div>', unsafe_allow_html=True)
                else: st.markdown(part)
            
            st.download_button("📥 Скачать фирменный Word-отчет", create_docx(st.session_state.audit_max, f"Аудит: {dtype}"), "Legal_Enterprise_Report.docx")

with tab2:
    st.subheader("🔍 Сравнение редакций")
    col_a, col_b = st.columns(2)
    fa = col_a.file_uploader("Версия А (Ваша)", type=["pdf", "docx"], key="fa")
    fb = col_b.file_uploader("Версия Б (Контрагента)", type=["pdf", "docx"], key="fb")
    if st.button("⚖️ НАЙТИ ОТЛИЧИЯ") and fa and fb:
        with st.spinner("Сравниваю..."):
            txt_a, txt_b = extract_text(fa.getvalue(), fa.name), extract_text(fb.getvalue(), fb.name)
            res = call_gemini("Проведи сравнительный анализ. Составь таблицу изменений: что изменилось и чьи интересы теперь пострадали.", f"Версия А: {txt_a}\n\nВерсия Б: {txt_b}")
            if res: st.markdown(res)

with tab3:
    st.subheader("✍️ Протоколы и письма")
    if "audit_max" in st.session_state:
        st.success("💡 Найдено решение: я могу составить документы на основе вашего аудита.")
        if st.button("📋 СГЕНЕРИРОВАТЬ ПРОТОКОЛ РАЗНОГЛАСИЙ"):
            with st.spinner("Формирую таблицу правок..."):
                res = call_gemini("Преврати результаты аудита в таблицу Протокола разногласий: 1. Пункт контрагента. 2. Наша редакция. 3. Обоснование через финансовые потери.", st.session_state.audit_max)
                if res: 
                    st.markdown(res)
                    st.download_button("📥 Скачать Протокол", create_docx(res, "Протокол разногласий"), "Protocol.docx")
    
    st.divider()
    manual_context = st.text_area("Или напишите задачу вручную (например: 'Напиши досудебную претензию по этому договору'):")
    if st.button("✉️ СОЗДАТЬ ПИСЬМО/ПРЕТЕНЗИЮ"):
        if manual_context:
            res = call_gemini("Напиши официальный документ на основе контекста.", manual_context)
            if res: st.markdown(res)
    
