'type') and data.type.startswith("image")
                    
                    if is_image:
                        prompt = (
                            f"Ты ведущий юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. "
                            "Структура ответа: 1. Jurisdiction, 2. Verdict (%), 3. Таблица рисков, 4. Рекомендации."
                        )
                        response = model.generate_content([prompt, Image.open(data)])
                    else:
                        # Получаем текст из файла или из текстового поля
                        if hasattr(data, 'getvalue'):
                            text = extract_text(data.getvalue(), data.name)
                        else:
                            text = data
                            
                        if not text or "Ошибка" in text:
                            st.error("Не удалось извлечь текст из файла. Попробуйте загрузить его как фото.")
                            st.stop()

                        full_prompt = f"Ты профессиональный юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}.\n\nТЕКСТ:\n{text}"
                        response = model.generate_content(full_prompt)

                    st.session_state.rep1 = response.text
                except Exception as e:
                    st.error(f"Ошибка анализа: {e}")

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button(
            "📥 Скачать отчёт (.docx)",
            save_to_docx(st.session_state.rep1, "Legal_Audit"),
            file_name="Legal_Audit.docx",
            key="dl1"
        )

# ==================================================
# TAB 2 — СРАВНЕНИЕ
# ==================================================
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        a = st.file_uploader("Документ A", type=["pdf", "docx"], key="ua")
    with c2:
        b = st.file_uploader("Документ B", type=["pdf", "docx"], key="ub")

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if not a or not b:
            st.warning("Загрузите оба документа.")
        else:
            with st.spinner("Сравнение документов..."):
                try:
                    txt_a = extract_text(a.getvalue(), a.name)
                    txt_b = extract_text(b.getvalue(), b.name)

                    full_prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Сравни документы. Ответ в таблице: Пункт | Было | Стало | Юридический риск.\n\nДОК А:\n{txt_a}\n\nДОК Б:\n{txt_b}"
                    res = model.generate_content(full_prompt)
                    st.session_state.rep2 = res.text
                except Exception as e:
                    st.error(f"Ошибка сравнения: {e}")

    if "rep2" in st.session_state:
        st.markdown(st.session_state.rep2)

# ==================================================
# TAB 3 — ОТВЕТ
# ==================================================
with tab3:
    mode3 = st.radio("Источник претензии", ["Файл / Фото", "Текст"], horizontal=True, key="mode3")
    claim = (
        st.file_uploader("Документ контрагента", type=["pdf", "docx", "jpg", "png"], key="up3")
        if mode3 == "Файл / Фото"
        else st.text_area("Текст претензии", height=250, key="txt3")
    )
    goal = st.text_area("Цель ответа", placeholder="Например: Отклонить претензию.")

    if st.button("✍️ Сформировать ответ", type="primary", use_container_width=True):
        if not claim:
            st.warning("Добавьте претензию.")
        else:
            with st.spinner("Формируется официальный ответ..."):
                try:
                    is_img3 = hasattr(claim, 'type') and claim.type.startswith("image")
                    if is_img3:
                        response = model.generate_content([f"Напиши официальный юридический ответ. Цель: {goal}", Image.open(claim)])
                    else:
                        text3 = extract_text(claim.getvalue(), claim.name) if hasattr(claim, 'getvalue') else claim
                        response = model.generate_content(f"Напиши официальный ответ. Цель: {goal}\n\nПРЕТЕНЗИЯ:\n{text3}")
                    st.session_state.rep3 = response.text
                except Exception as e:
                    st.error(f"Ошибка генерации: {e}")

    if "rep3" in st.session_state:
        st.markdown(st.session_state.rep3)
        st.download_button(
            "📥 Скачать письмо (.docx)",
            save_to_docx(st.session_state.rep3, "Official_Response"),
            file_name="Official_Response.docx",
            key="dl3"
)
            st.title("🛡️ LegalAI Control")

    depth = st.select_slider(
        "Глубина анализа",
        options=["Базовая", "Стандартная", "Глубокая"],
        value="Стандартная"
    )

    jurisdiction = st.selectbox(
        "Юрисдикция",
        ["Россия / СНГ", "ЕС", "США", "Международная"]
    )

    st.caption("Модель: Gemini 1.5 Flash")

    if st.button("🗑️ Сбросить всё"):
        st.session_state.clear()
        st.rerun()

# ==================================================
# 5. TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(
    ["🚀 АНАЛИЗ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТ КОНТРАГЕНТУ"]
)

# ==================================================
# TAB 1 — АНАЛИЗ
# ==================================================
with tab1:
    mode = st.radio("Источник данных", ["Файл / Фото", "Текст"], horizontal=True)

    data = (
        st.file_uploader("Загрузите документ", type=["pdf", "docx", "jpg", "png", "jpeg"])
        if mode == "Файл / Фото"
        else st.text_area("Вставьте текст договора", height=300)
    )

    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if not data:
            st.warning("Добавьте документ или текст.")
            st.stop()

        with st.spinner("⚖️ Проводится юридический анализ..."):
            if mode == "Файл / Фото" and data.type and data.type.startswith("image"):
                prompt = (
                    f"Ты ведущий юрист.\n"
                    f"Юрисдикция: {jurisdiction}\n"
                    f"Глубина анализа: {depth}\n\n"
                    "Структура ответа:\n"
                    "1. Jurisdiction\n"
                    "2. Verdict (%)\n"
                    "3. Таблица рисков\n"
                    "4. Рекомендации"
                )
                response = model.generate_content([prompt, Image.open(data)])
            else:
                text = extract_text(data.getvalue(), data.name) if mode == "Файл / Фото" else data
                if not text:
                    st.error("Этот файл анализируется только как изображение.")
                    st.stop()

                full_prompt = f"""Ты профессиональный юрист.
Юрисдикция: {jurisdiction}
Глубина анализа: {depth}

====================
ТЕКСТ ДОКУМЕНТА:
====================
{text}
"""
                response = model.generate_content(full_prompt)

            st.session_state.rep1 = response.text

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button(
            "📥 Скачать отчёт (.docx)",
            save_to_docx(st.session_state.rep1, "Legal_Audit"),
            file_name="Legal_Audit.docx"
        )

# ==================================================
# TAB 2 — СРАВНЕНИЕ
# ==================================================
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        a = st.file_uploader("Документ A", type=["pdf", "docx"])
    with c2:
        b = st.file_uploader("Документ B", type=["pdf", "docx"])

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if not a or not b:
            st.warning("Загрузите оба документа.")
            st.stop()

        with st.spinner("Сравнение документов..."):
            txt_a = extract_text(a.getvalue(), a.name)
            txt_b = extract_text(b.getvalue(), b.name)

            full_prompt = f"""Ты юрист.
Юрисдикция: {jurisdiction}

Сравни документы.
Ответ в таблице:
Пункт | Было | Стало | Юридический риск

===== ДОКУМЕНТ A =====
{txt_a}

===== ДОКУМЕНТ B =====
{txt_b}
"""
            res = model.generate_content(full_prompt)
            st.session_state.rep2 = res.text

    if "rep2" in st.session_state:
        st.markdown(st.session_state.rep2)

# ==================================================
# TAB 3 — ОТВЕТ
# ==================================================
with tab3:
    mode = st.radio("Источник претензии", ["Файл / Фото", "Текст"], horizontal=True)

    claim = (
        st.file_uploader("Документ контрагента", type=["pdf", "docx", "jpg", "png"])
        if mode == "Файл / Фото"
        else st.text_area("Текст претензии", height=250)
    )

    goal = st.text_area(
        "Цель ответа",
        placeholder="Например: Отклонить претензию, сославшись на пункт 4.1 договора."
    )

    if st.button("✍️ Сформировать ответ", type="primary", use_container_width=True):
        if not claim:
            st.warning("Добавьте претензию.")
            st.stop()

        with st.spinner("Формируется официальный ответ..."):
            if mode == "Файл / Фото" and claim.type and claim.type.startswith("image"):
                response = model.generate_content(
                    [f"Напиши официальный юридический ответ. Цель: {goal}", Image.open(claim)]
                )
            else:
                text = extract_text(claim.getvalue(), claim.name) if mode == "Файл / Фото" else claim

                full_prompt = f"""Напиши официальный юридический ответ.

Цель:
{goal}

====================
ТЕКСТ ПРЕТЕНЗИИ:
====================
{text}
"""
                response = model.generate_content(full_prompt)

            st.session_state.rep3 = response.text

    if "rep3" in st.session_state:
        st.markdown(st.session_state.rep3)
        st.download_button(
            "📥 Скачать письмо (.docx)",
            save_to_docx(st.session_state.rep3, "Official_Response"),
            file_name="Official_Response.docx"
        )
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import re

# ==================================================
# 1. КОНФИГУРАЦИЯ
# ==================================================
st.set_page_config(
    page_title="LegalAI Enterprise Pro",
    page_icon="⚖️",
    layout="wide"
)

st.error(
    "⚠️ ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР: "
    "Результаты сформированы ИИ и не являются юридическим заключением. "
    "Обязательно проверьте документ у лицензированного юриста."
)

# ==================================================
# 2. GEMINI INIT (FIXED 404)
# ==================================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.warning("⚙️ Добавьте GOOGLE_API_KEY в Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Прямое имя модели без префиксов для устранения ошибки 404
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.2,
        "top_p": 0.9,
        "max_output_tokens": 4096
    }
)

# ==================================================
# 3. UTILITIES
# ==================================================
@st.cache_data(show_spinner=False, max_entries=10)
def extract_text(file_bytes: bytes, filename: str):
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return "".join(p.extract_text() or "" for p in reader.pages)[:30000]
        if name.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)[:30000]
        if name.endswith((".txt", ".md")):
            return file_bytes.decode("utf-8", errors="ignore")[:30000]
        return None
    except Exception as e:
        return f"Ошибка извлечения текста: {e}"

def clean_markdown(text: str) -> str:
    return re.sub(r'[*_#>`]', '', text)

def save_to_docx(content: str, title: str):
    doc = Document()
    doc.add_heading(title, 0)
    p = doc.add_paragraph()
    run = p.add_run("Сформировано LegalAI Enterprise. Требуется проверка юриста.")
    run.bold = True
    for line in clean_markdown(content).split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==================================================
# 4. SIDEBAR
# ==================================================
with st.sidebar:
    st.title("🛡️ LegalAI Control")
    depth = st.select_slider(
        "Глубина анализа",
        options=["Базовая", "Стандартная", "Глубокая"],
        value="Стандартная"
    )
    jurisdiction = st.selectbox(
        "Юрисдикция",
        ["Россия / СНГ", "ЕС", "США", "Международная"]
    )
    st.caption("Модель: Gemini 1.5 Flash")
    if st.button("🗑️ Сбросить всё"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

# ==================================================
# 5. TABS
# ==================================================
tab1, tab2, tab3 = st.tabs(
    ["🚀 АНАЛИЗ РИСКОВ", "🔍 СРАВНЕНИЕ", "✉️ ОТВЕТ КОНТРАГЕНТУ"]
)

# ==================================================
# TAB 1 — АНАЛИЗ
# ==================================================
with tab1:
    mode1 = st.radio("Источник данных", ["Файл / Фото", "Текст"], horizontal=True, key="m1")
    data1 = (
        st.file_uploader("Загрузите документ", type=["pdf", "docx", "jpg", "png", "jpeg"], key="up1")
        if mode1 == "Файл / Фото"
        else st.text_area("Вставьте текст договора", height=300, key="tx1")
    )

    if st.button("🔍 Запустить аудит", type="primary", use_container_width=True):
        if not data1:
            st.warning("Добавьте документ или текст.")
        else:
            with st.spinner("⚖️ Проводится юридический анализ..."):
                try:
                    is_img = hasattr(data1, 'type') and data1.type.startswith("image")
                    if is_img:
                        prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}. Структура: Jurisdiction, Verdict (%), Таблица рисков, Рекомендации."
                        response = model.generate_content([prompt, Image.open(data1)])
                    else:
                        text = extract_text(data1.getvalue(), data1.name) if hasattr(data1, 'getvalue') else data1
                        full_prompt = f"Ты юрист. Юрисдикция: {jurisdiction}. Глубина: {depth}.\n\nТЕКСТ:\n{text}"
                        response = model.generate_content(full_prompt)
                    st.session_state.rep1 = response.text
                except Exception as e:
                    st.error(f"Ошибка анализа: {e}")

    if "rep1" in st.session_state:
        st.markdown(st.session_state.rep1)
        st.download_button("📥 Скачать отчёт", save_to_docx(st.session_state.rep1, "Audit"), file_name="Audit.docx")

# ==================================================
# TAB 2 — СРАВНЕНИЕ
# ==================================================
with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        a = st.file_uploader("Документ A", type=["pdf", "docx"], key="ua")
    with col_b:
        b = st.file_uploader("Документ B", type=["pdf", "docx"], key="ub")

    if st.button("⚖️ Найти отличия", use_container_width=True):
        if a and b:
            with st.spinner("Сравнение..."):
                try:
                    t_a = extract_text(a.getvalue(), a.name)
                    t_b = extract_text(b.getvalue(), b.name)
                    prompt = f"Сравни. Таблица: Пункт | Было | Стало | Риск.\n\nА:\n{t_a}\n\nБ:\n{t_b}"
                    st.session_state.rep2 = model.generate_content(prompt).text
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if "rep2" in st.session_state:
        st.markdown(st.session_state.rep2)

# ==================================================
# TAB 3 — ОТВЕТ
# ==================================================
with tab3:
    mode3 = st.radio("Источник", ["Файл / Фото", "Текст"], horizontal=True, key="m3")
    claim = (
        st.file_uploader("Претензия", type=["pdf", "docx", "jpg", "png"], key="up3")
        if mode3 == "Файл / Фото"
        else st.text_area("Текст претензии", height=200, key="tx3")
    )
    goal = st.text_area("Цель ответа", key="goal3")

    if st.button("✍️ Создать ответ", type="primary", use_container_width=True):
        if claim:
            with st.spinner("Формирование..."):
                try:
                    if hasattr(claim, 'type') and claim.type.startswith("image"):
                        res = model.generate_content([f"Ответ. Цель: {goal}", Image.open(claim)])
                    else:
                        txt = extract_text(claim.getvalue(), claim.name) if hasattr(claim, 'getvalue') else claim
                        res = model.generate_content(f"Напиши ответ. Цель: {goal}\n\nТекст:\n{txt}")
                    st.session_state.rep3 = res.text
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if "rep3" in st.session_state:
        st.markdown(st.session_state.rep3)
        st.download_button("📥 Скачать ответ", save_to_docx(st.session_state.rep3, "Letter"), file_name="Letter.docx")
