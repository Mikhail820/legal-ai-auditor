import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt
from bs4 import BeautifulSoup
import io
import base64
import re

# -------------------
# 1. Настройки интерфейса
# -------------------
st.set_page_config(page_title="LegalAI Enterprise Pro", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; background-color: #FF4B4B; color: white; border: none; }
.stDownloadButton>button { width: 100%; border-radius: 10px; background-color: #28a745; color: white; }
.main-header { font-size: 2.5rem; color: #FF4B4B; text-align: center; margin-bottom: 1.5rem; font-weight: 800; }
.risk-card { background-color: #ffffff; border-left: 6px solid #ff4b4b; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; color: #000; }
.score-container { background: #f0f2f6; padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #dee2e6; margin-bottom: 20px; }
.disclaimer { font-size: 0.8rem; color: #7f8c8d; padding: 15px; background: #fff3f3; border-radius: 10px; border: 1px solid #fab1a0; }
</style>
""", unsafe_allow_html=True)

DISCLAIMER_TEXT = "⚠️ ВНИМАНИЕ: Анализ выполнен ИИ. Не является юридической консультацией. Обязательно проверьте документ у юриста."

# -------------------
# 2. Модели и API (По твоему списку)
# -------------------
MODEL_POLICY = [
    "gemini-2.5-flash-lite", 
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash"
]

API_KEY = st.secrets.get("GOOGLE_API_KEY")

def call_gemini_safe(prompt, content, is_image=False):
    if not API_KEY:
        return "⚠️ Ошибка: Добавьте GOOGLE_API_KEY в Secrets."
        
    for model in MODEL_POLICY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
            
            if is_image:
                img_b64 = base64.b64encode(content).decode('utf-8')
                payload = {"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":img_b64}}]}]}
            else:
                payload = {"contents":[{"parts":[{"text":f"{prompt}\n\nДОКУМЕНТ:\n{content}"}]}]}
            
            r = requests.post(url, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            continue
    return "⚠️ Модель временно недоступна. Попробуйте позже."

# -------------------
# 3. Инструменты (Word + Извлечение)
# -------------------
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(DISCLAIMER_TEXT).italic = True
    doc.add_paragraph("-" * 40)

    lines = text.split('\n')
    table_data = []
    in_table = False

    for line in lines:
        # Детектор таблиц Markdown (| столбец |)
        if '|' in line and not re.match(r'^[|\s\-:]+$', line.strip()):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                table_data.append(cells)
                in_table = True
            continue
        
        # Если строка не табличная, а таблица в буфере есть — сбрасываем её в Word
        if in_table and table_data:
            num_cols = max(len(row) for row in table_data)
            table = doc.add_table(rows=len(table_data), cols=num_cols)
            table.style = 'Table Grid'
            for i, row in enumerate(table_data):
                for j, cell_text in enumerate(row):
                    if j < num_cols:
                        table.cell(i, j).text = cell_text
            table_data = []
            in_table = False
            doc.add_paragraph() # Отступ

        if line.strip() and not in_table:
            clean_line = line.replace('*', '').replace('#', '').strip()
            p = doc.add_paragraph(clean_line)
            if line.startswith('#'): p.style = 'Heading 2'

    # Финальный сброс таблицы, если текст закончился на ней
    if in_table and table_data:
        num_cols = max(len(row) for row in table_data)
        table = doc.add_table(rows=len(table_data), cols=num_cols)
        table.style = 'Table Grid'
        for i, row in enumerate(table_data):
            for j, cell_text in enumerate(row):
                if j < num_cols: table.cell(i, j).text = cell_text

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def extract_text(file_bytes, filename):
    try:
        if filename.lower().endswith(".pdf"):
            return " ".join([p.extract_text() for p in PdfReader(io.BytesIO(file_bytes)).pages if p.extract_text()])
        elif filename.lower().endswith(".docx"):
            return "\n".join([p.text for p in Document(io.BytesIO(file_bytes)).paragraphs])
    except: return "Ошибка чтения."
    return ""

# -------------------
# 4. Sidebar
# -------------------
with st.sidebar:
    st.header("⚙️ Конфигурация")
    role = st.radio("Анализ для:", ["Предприниматель","Юрист","Физическое лицо"])
    loc = st.selectbox("Юрисдикция:", ["РФ","Казахстан","Узбекистан","Международная"])
    detail = st.select_slider("Детальность:", options=["Кратко","Стандарт","Максимум"])
    st.divider()
    st.markdown(f'<div class="disclaimer">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

# -------------------
# 5. Main Tabs
# -------------------
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Pro</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🚀 УМНЫЙ АУДИТ", "🔍 СРАВНЕНИЕ", "📋 ГЕНЕРАТОР"])

with tab1:
    col1, col2 = st.columns([1, 1.2])
    with col1:
        dtype = st.selectbox("Тип:", ["Договор услуг", "Поставка", "Аренда", "NDA", "Трудовой", "Другое"])
        src = st.radio("Ввод:", ["Файл/Скан", "Текст", "Ссылка"], horizontal=True)

        input_data, is_img = None, False
        if src == "Файл/Скан":
            f = st.file_uploader("Загрузите документ или фото", type=["pdf", "docx", "png", "jpg"])
            if f:
                if f.type.startswith("image"): input_data, is_img = f.getvalue(), True
                else: input_data = extract_text(f.getvalue(), f.name)
        elif src == "Ссылка":
            url = st.text_input("URL:")
            if url: input_data = BeautifulSoup(requests.get(url).text, 'html.parser').get_text()[:25000]
        else:
            input_data = st.text_area("Вставьте текст:", height=200)

        if st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ"):
            if input_data:
                with col2:
                    with st.spinner("Анализирую..."):
                        prompt = f"Роль: {role}. Страна: {loc}. Тип: {dtype}. Глубина: {detail}. Выдели LEGAL SCORE (0-100%), риски 🔴, потери 💸 и ловушки ⚠️."
                        res = call_gemini_safe(prompt, input_data, is_img)
                        if res: st.session_state.audit_result = res

    if "audit_result" in st.session_state:
        with col2:
            st.markdown('<div class="score-container"><h3>📊 Результаты</h3></div>', unsafe_allow_html=True)
            for part in st.session_state.audit_result.split('\n'):
                if any(x in part for x in ["🔴", "💸", "⚠️"]):
                    st.markdown(f'<div class="risk-card">{part}</div>', unsafe_allow_html=True)
                else: st.markdown(part)
            st.download_button("📥 Скачать Word", create_docx(st.session_state.audit_result, "Анализ риска"), "Legal_Report.docx")

with tab2:
    st.subheader("🔍 Сравнение версий")
    ca, cb = st.columns(2)
    fa = ca.file_uploader("Оригинал", type=["pdf", "docx"], key="fa")
    fb = cb.file_uploader("Редакция", type=["pdf", "docx"], key="fb")
    if st.button("⚖️ НАЙТИ РАЗНИЦУ") and fa and fb:
        with st.spinner("Сравниваю..."):
            res = call_gemini_safe("Составь таблицу сравнения: Пункт - Что было - Что стало - Риск.", 
                                   f"А: {extract_text(fa.getvalue(), fa.name)}\nБ: {extract_text(fb.getvalue(), fb.name)}")
            if res:
                st.markdown(res)
                st.download_button("📥 Скачать Сравнение (Word)", create_docx(res, "Сравнение версий"), "Comparison.docx")

with tab3:
    st.subheader("📋 Генерация документов")
    if "audit_result" in st.session_state:
        if st.button("📋 СОЗДАТЬ ПРОТОКОЛ РАЗНОГЛАСИЙ"):
            with st.spinner("Формирую..."):
                res = call_gemini_safe("На основе анализа создай таблицу Протокола разногласий: Пункт - Редакция контрагента - Наша редакция - Обоснование.", st.session_state.audit_result)
                if res:
                    st.markdown(res)
                    st.download_button("📥 Скачать Протокол", create_docx(res, "Протокол"), "Protocol.docx")
    st.divider()
    task = st.text_area("Ваш запрос (напр. 'Напиши мотивированный отказ'):")
    if st.button("✉️ СГЕНЕРИРОВАТЬ"):
        if task:
            res = call_gemini_safe(f"Напиши документ: {task}", st.session_state.get("audit_result", ""))
            st.markdown(res)
            st.download_button("📥 Скачать Ответ", create_docx(res, "Юридический документ"), "Response.docx")
