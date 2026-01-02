import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. НАСТРОЙКА И МОДЕЛЬ ---
st.set_page_config(page_title="LegalAI Ultimate 2026", page_icon="🛡️", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Используем проверенную модель 2.5
    model = genai.GenerativeModel('models/gemini-2.5-flash') 
else:
    st.error("Ключ API не найден в Secrets!")
    st.stop()

# --- 2. ФУНКЦИИ ЧТЕНИЯ ---
def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages])
        elif file.name.endswith(".docx"):
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        return file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Ошибка чтения: {e}")
        return ""

# --- 3. ИНТЕРФЕЙС И МАРКЕТИНГ ---
st.title("🛡️ LegalAI Ultimate 2026")
st.subheader("Профессиональный аудит на базе Gemini 2.5")

# Визуальные карточки преимуществ
m1, m2, m3 = st.columns(3)
with m1:
    st.info("🔍 **Мгновенный Аудит**\n\nПоиск ловушек и кабальных условий за 10 секунд.")
with m2:
    st.success("⚖️ **Протокол правок**\n\nГотовые формулировки для замены пунктов по ГК РФ.")
with m3:
    st.warning("🔍 **Сравнение версий**\n\nПроверка правок на новые скрытые условия.")

st.markdown("---")

tab1, tab2 = st.tabs(["🧐 Глубокий аудит и OCR", "🔍 Сравнение двух редакций"])

# ВКЛАДКА 1: АУДИТ
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.write("### 📁 Шаг 1: Загрузка")
        cat = st.selectbox("Тип договора:", ["Банковский", "Кредитный", "Аренда", "Трудовой", "Услуги/IT"])
        file = st.file_uploader("Загрузите файл или фото страницы", type=["pdf", "docx", "jpg", "png", "jpeg"])
        analyze_btn = st.button("🚀 Запустить экспертизу")

    with c2:
        st.write("### 📝 Шаг 2: Заключение")
        if analyze_btn:
            if file:
                with st.spinner("Gemini 2.5 анализирует документ..."):
                    try:
                        if file.type in ["image/jpeg", "image/png"]:
                            img = Image.open(file)
                            prompt = [f"Ты юрист. Категория: {cat}. Найди 5 рисков в этом скане и напиши протокол правок.", img]
                        else:
                            text = extract_text(file)
                            # Ограничение текста для стабильности Free Tier
                            prompt = f"""Ты ведущий юрист РФ. Категория: {cat}. 
                            Проведи аудит текста: {text[:18000]}. 
                            1. Дай вердикт (🔴 Опасно / 🟡 Внимательно / 🟢 Безопасно). 
                            2. Объясни суть договора простыми словами.
                            3. Найди 5 рисков со ссылками на ГК РФ. 
                            4. Составь таблицу правок (Как есть | Риск | Предлагаемая редакция)."""
                        
                        res = model.generate_content(prompt)
                        st.success("Готово!")
                        st.markdown(res.text)
                        st.download_button("📥 Скачать отчет", res.text, file_name="legal_audit.txt")
                    except Exception as e:
                        st.error(f"Ошибка ИИ: {e}")
            else:
                st.warning("Загрузите документ!")

# ВКЛАДКА 2: СРАВНЕНИЕ
with tab2:
    st.write("### 🔍 Проверка изменений")
    st.write("Сравните две версии, чтобы убедиться, что ваши правки внесены.")
    col_a, col_b = st.columns(2)
    f_old = col_a.file_uploader("Старый файл", type=["pdf", "docx"], key="old")
    f_new = col_b.file_uploader("Новый файл", type=["pdf", "docx"], key="new")
    
    if st.button("🔎 Найти отличия"):
        if f_old and f_new:
            with st.spinner("Сравниваю..."):
                try:
                    t_old, t_new = extract_text(f_old), extract_text(f_new)
                    diff_prompt = f"Сравни два договора. Найди изменения. \n1: {t_old[:9000]} \n2: {t_new[:9000]}"
                    res = model.generate_content(diff_prompt)
                    st.info("Результат сравнения:")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Ошибка: {e}")

st.markdown("---")
st.caption("LegalAI Ultimate 2026. Работает на базе Gemini 2.5 Flash.")
    
