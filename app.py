import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io

# ==================================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ И МОДЕЛИ
# ==================================================
st.set_page_config(page_title="LegalAI Enterprise", page_icon="⚖️", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Ошибка: GOOGLE_API_KEY не найден в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

SYSTEM_PROMPT = """
Ты — профессиональный корпоративный юрист. Твоя задача:
1. Анализировать документы на наличие скрытых юридических рисков.
2. Сравнивать версии договоров, выделяя изменения.
3. Составлять официальные ответы на претензии.
Пиши четко, структурировано, используй таблицы для сравнения и списки для рисков.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# ==================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==================================================
def extract_text(file) -> str:
    fname = file.name.lower()
    try:
        if fname.endswith(".pdf"):
            pdf = PdfReader(io.BytesIO(file.getvalue()))
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text
        elif fname.endswith(".docx"):
            doc = Document(io.BytesIO(file.getvalue()))
            return "\n".join([p.text for p in doc.paragraphs])
        elif fname.endswith(".txt"):
            return file.getvalue().decode("utf-8")
        return ""
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"

def create_docx(text: str):
    doc = Document()
    doc.add_heading("Юридический отчет LegalAI", 0)
    for line in text.split('\n'):
        clean_line = line.replace('**', '').replace('###', '').replace('##', '').strip()
        if clean_line:
            doc.add_paragraph(clean_line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 3. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ==================================================
st.title("⚖️ LegalAI Enterprise Pro")
st.caption("Автоматизированный юридический аудит и работа с контрагентами")

with st.sidebar:
    st.header("Настройки")
    jurisdiction = st.selectbox("Юрисдикция", ["РФ", "Казахстан", "Беларусь", "Международное право"])
    depth = st.select_slider("Глубина анализа", ["Базовая", "Стандартная", "Детальная"])
    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🔍 Анализ договора", "🔄 Сравнение версий", "✉️ Ответ на претензию"])

# --- ВКЛАДКА 1: АНАЛИЗ ---
with tab1:
    st.subheader("Поиск юридических рисков")
    up_file = st.file_uploader("Загрузите файл (PDF, DOCX) или Фото договора", type=["pdf", "docx", "png", "jpg", "jpeg"], key="audit_up")
    
    if st.button("Запустить аудит", type="primary"):
        if up_file:
            with st.spinner("Юрист ИИ изучает документ..."):
                try:
                    if up_file.type.startswith("image"):
                        response = model.generate_content([f"Проведи юридический аудит документа на фото. Юрисдикция: {jurisdiction}", Image.open(up_file)])
                    else:
                        text_content = extract_text(up_file)
                        prompt = f"Проведи детальный анализ рисков договора. Юрисдикция: {jurisdiction}. Глубина: {depth}.\n\nТекст:\n{text_content}"
                        response = model.generate_content(prompt)
                    st.session_state.audit_result = response.text
                except Exception as e:
                    st.error(f"Ошибка анализа: {e}")
        else:
            st.warning("Пожалуйста, загрузите документ.")

    if "audit_result" in st.session_state:
        st.markdown(st.session_state.audit_result)
        st.download_button("📥 Скачать отчет (.docx)", create_docx(st.session_state.audit_result), "Legal_Audit.docx")

# --- ВКЛАДКА 2: СРАВНЕНИЕ ---
with tab2:
    st.subheader("Сравнение правок контрагента")
    c1, c2 = st.columns(2)
    with c1: f1 = st.file_uploader("Ваша версия (Оригинал)", type=["pdf", "docx"], key="orig")
    with c2: f2 = st.file_uploader("Версия контрагента", type=["pdf", "docx"], key="mod")
    
    if st.button("Найти отличия"):
        if f1 and f2:
            with st.spinner("Сравниваем условия..."):
                t1, t2 = extract_text(f1), extract_text(f2)
                diff_prompt = "Сравни два текста. Составь таблицу: что изменилось и какой в этом риск для нас."
                response = model.generate_content(f"{diff_prompt}\n\nТекст 1:\n{t1}\n\nТекст 2:\n{t2}")
                st.session_state.diff_result = response.text
        else:
            st.warning("Загрузите оба файла для сравнения.")

    if "diff_result" in st.session_state:
        st.markdown(st.session_state.diff_result)

# --- ВКЛАДКА 3: ОТВЕТ ---
with tab3:
    st.subheader("Генератор официальных ответов")
    claim_text = st.text_area("Вставьте текст претензии или письма", height=200)
    strategy = st.radio("Стратегия ответа", ["Мирная (согласие)", "Защитная (отказ)", "Встречные требования"], horizontal=True)
    
    if st.button("Создать черновик ответа"):
        if claim_text:
            with st.spinner("Подготовка юридического ответа..."):
                prompt = f"Напиши официальный ответ на претензию. Стратегия: {strategy}. Юрисдикция: {jurisdiction}.\n\nТекст претензии:\n{claim_text}"
                response = model.generate_content(prompt)
                st.session_state.reply_result = response.text
        else:
            st.warning("Введите текст претензии.")

    if "reply_result" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state.reply_result)
        st.download_button("📥 Скачать ответ (.docx)", create_docx(st.session_state.reply_result), "Legal_Reply.docx")

st.divider()
st.info("⚠️ Дисклеймер: Ответы сформированы нейросетью и не являются юридическим заключением. Проверьте результат у юриста.")
```
