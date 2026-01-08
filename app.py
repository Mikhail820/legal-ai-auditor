import streamlit as st
import requests
import json
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
import io
import base64
import re
import time
from urllib.parse import urlparse
import logging
from datetime import datetime, timedelta
import hashlib
import threading
from queue import Queue

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ЛИМИТОВ GOOGLE AI STUDIO FREE TIER ====================
FREE_TIER_CONFIG = {
    "models": {
        # Приоритет: сначала самые "дешевые" по токенам с высокими лимитами
        "gemini-2.5-flash-lite": {
            "priority": 1,  # Самый высокий приоритет (максимальный RPD ~1000)
            "rpm": 15,  # Запросов в минуту
            "tpm": 250000,  # Токенов в минуту
            "price_input": 0.0,
            "price_output": 0.0
        },
        "gemini-2.5-flash": {
            "priority": 2,  # Средний приоритет (RPD ~20-50)
            "rpm": 10,
            "tpm": 250000,
            "price_input": 0.0,
            "price_output": 0.0
        },
        "gemini-2.0-flash-lite": {
            "priority": 3,  # Низкий приоритет (резерв)
            "rpm": 15,
            "tpm": 250000,
            "price_input": 0.0,
            "price_output": 0.0
        }
    },
    "global_limits": {
        "daily_request_limit": 1000,  # Примерный общий лимит на день
        "reset_time_hours": 0  # Полночь по PT (0 часов)
    }
}

# Менеджер лимитов
class RateLimitManager:
    def __init__(self):
        self.requests_log = []
        self.lock = threading.Lock()
        self.daily_requests = 0
        self.last_reset = datetime.utcnow()
        
    def check_daily_limit(self):
        """Проверка дневного лимита запросов"""
        with self.lock:
            # Сброс счетчика в 00:00 PT (8:00 UTC)
            now_utc = datetime.utcnow()
            if now_utc.hour == 8 and now_utc.minute < 5:
                if (now_utc - self.last_reset).days >= 1:
                    self.daily_requests = 0
                    self.last_reset = now_utc
                    logger.info("Счетчик дневных запросов сброшен")
            
            if self.daily_requests >= FREE_TIER_CONFIG["global_limits"]["daily_request_limit"]:
                return False
            self.daily_requests += 1
            return True
    
    def record_request(self, model):
        """Запись запроса для расчета RPM"""
        with self.lock:
            now = time.time()
            self.requests_log.append((now, model))
            # Очистка старых записей (старше 1 минуты)
            self.requests_log = [(t, m) for t, m in self.requests_log if now - t < 60]
            
            # Подсчет RPM для конкретной модели
            model_count = len([(t, m) for t, m in self.requests_log if m == model])
            return model_count < FREE_TIER_CONFIG["models"][model]["rpm"]
    
    def get_wait_time(self, model):
        """Время ожидания при превышении RPM"""
        with self.lock:
            if not self.requests_log:
                return 0
            oldest = min(t for t, m in self.requests_log if m == model)
            return max(0, 60 - (time.time() - oldest))

# Инициализация менеджера лимитов
limit_manager = RateLimitManager()

# ==================== НАСТРОЙКА ИНТЕРФЕЙСА ====================
st.set_page_config(
    page_title="LegalAI Enterprise Pro", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { 
        font-size: 2.5rem; 
        color: #FF4B4B; 
        text-align: center; 
        margin-bottom: 1.5rem; 
        font-weight: 800;
    }
    .limit-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9em;
    }
    .limit-critical {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9em;
    }
    .cache-badge {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        margin-left: 10px;
    }
    .stButton>button:disabled {
        background-color: #6c757d !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== УЛУЧШЕННАЯ ФУНКЦИЯ ВЫЗОВА GEMINI ====================
@st.cache_data(show_spinner=False, max_entries=50, ttl=3600)  # Кэш на 1 час
def call_gemini_with_limits(_prompt_hash, prompt, content, is_image=False, max_retries=3):
    """
    Улучшенная функция вызова с учетом всех лимитов Free Tier
    """
    if not st.secrets.get("GOOGLE_API_KEY"):
        return None, "❌ API ключ не настроен"
    
    # Проверка дневного лимита
    if not limit_manager.check_daily_limit():
        return None, "⚠️ Достигнут дневной лимит запросов. Попробуйте завтра."
    
    # Подготовка моделей в порядке приоритета
    models_priority = sorted(
        FREE_TIER_CONFIG["models"].keys(),
        key=lambda x: FREE_TIER_CONFIG["models"][x]["priority"]
    )
    
    for model in models_priority:
        for retry in range(max_retries):
            try:
                # Проверка RPM для модели
                if not limit_manager.record_request(model):
                    wait_time = limit_manager.get_wait_time(model)
                    if wait_time > 0:
                        logger.warning(f"RPM лимит для {model}. Ждем {wait_time:.1f} сек")
                        time.sleep(wait_time)
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={st.secrets['GOOGLE_API_KEY']}"
                
                # Формирование запроса с оптимизацией
                if is_image:
                    mime_type = "image/jpeg" if content[:3] == b'\xff\xd8\xff' else "image/png"
                    img_b64 = base64.b64encode(content).decode('utf-8')
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt[:1000]},  # Ограничиваем промпт
                                {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                            ]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 1024,  # Ограничиваем вывод
                            "topP": 0.8
                        }
                    }
                else:
                    # Оптимизация текста для экономии токенов
                    if len(content) > 30000:
                        content = content[:15000] + "\n\n... [текст сокращен для Free Tier] ...\n\n" + content[-15000:]
                    
                    payload = {
                        "contents": [{
                            "parts": [{"text": f"{prompt[:500]}\n\nТЕКСТ:\n{content}"}]
                        }],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 2048,  # Лимит вывода
                            "topP": 0.9
                        }
                    }
                
                # Вызов API
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 429:
                    # Обработка Rate Limit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit для {model}. Retry после {retry_after} сек")
                    time.sleep(retry_after)
                    continue
                    
                elif response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        text = result['candidates'][0]['content']['parts'][0]['text']
                        logger.info(f"Успешно: {model}, токены: ~{len(text)//4}")
                        return text, None
                
                else:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown')
                    logger.error(f"Ошибка {model}: {response.status_code} - {error_msg}")
                    break
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут {model}, попытка {retry+1}")
                time.sleep(2 ** retry)  # Exponential backoff
                continue
            except Exception as e:
                logger.error(f"Ошибка {model}: {str(e)}")
                break
        
        # Если модель не сработала, пробуем следующую по приоритету
        logger.info(f"Переход к следующей модели после {model}")
        continue
    
    return None, "⚠️ Все модели недоступны. Проверьте лимиты и попробуйте позже."

# ==================== ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДОКУМЕНТАМИ ====================
@st.cache_data(show_spinner=False, max_entries=100, ttl=1800)
def extract_text_cached(file_bytes, filename):
    """Кэшированное извлечение текста"""
    try:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            return " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return ""
    except:
        return ""

# ==================== ОБНОВЛЕННЫЙ ИНТЕРФЕЙС ====================
# Боковая панель с информацией о лимитах
with st.sidebar:
    st.header("⚙️ Конфигурация")
    
    # Информация о Free Tier
    with st.expander("📊 Лимиты Free Tier", expanded=True):
        st.markdown(f"""
        **Доступные модели:**
        - Gemini 2.5 Flash-Lite (приоритет 1)
        - Gemini 2.5 Flash (приоритет 2)  
        - Gemini 2.0 Flash-Lite (приоритет 3)
        
        **Лимиты:**
        - RPM: 15/мин (Flash-Lite), 10/мин (Flash)
        - TPM: 250,000 токенов
        - RPD: ~1000 запросов/день
        
        **Использовано сегодня:** {limit_manager.daily_requests}/1000
        """)
        
        if limit_manager.daily_requests > 800:
            st.error("⚠️ Достигается дневной лимит!")
        elif limit_manager.daily_requests > 500:
            st.warning("ℹ️ Использовано более 50% лимита")
    
    # Настройки
    role = st.radio("Анализ для:", ["Предприниматель", "Юрист", "Физическое лицо"])
    loc = st.selectbox("Юрисдикция:", ["РФ", "Казахстан", "Узбекистан", "Международная"])
    
    # Оптимизация запросов
    st.subheader("Оптимизация")
    use_cache = st.checkbox("Использовать кэш", value=True, 
                           help="Кэширует результаты на 1 час для экономии запросов")
    optimize_text = st.checkbox("Сокращать длинные тексты", value=True,
                               help="Автоматически сокращает документы >30K символов")
    
    st.divider()
    
    if st.button("🗑️ Очистить кэш", use_container_width=True):
        st.cache_data.clear()
        st.success("Кэш очищен!")
        time.sleep(1)
        st.rerun()

# ==================== ГЛАВНЫЙ ИНТЕРФЕЙС ====================
st.title("⚖️ LegalAI Enterprise Pro")
st.markdown('<div class="limit-warning">⚠️ Работает в режиме Google AI Studio Free Tier. Строгие лимиты: ~1000 запросов/день</div>', unsafe_allow_html=True)

# Вкладки
tab1, tab2, tab3 = st.tabs(["🚀 Анализ", "🔍 Сравнение", "📋 Генерация"])

with tab1:
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("Загрузка документа")
        
        # Выбор типа ввода
        input_type = st.radio("Источник:", ["Файл", "Текст", "URL"], horizontal=True)
        
        input_data, is_image = None, False
        
        if input_type == "Файл":
            file = st.file_uploader("Загрузите документ", type=["pdf", "docx", "txt", "png", "jpg"])
            if file:
                if file.type.startswith("image"):
                    input_data, is_image = file.getvalue(), True
                    st.image(file, width=300)
                else:
                    with st.spinner("Извлекаю текст..."):
                        input_data = extract_text_cached(file.getvalue(), file.name)
                        st.info(f"Извлечено: {len(input_data)} символов")
        
        elif input_type == "Текст":
            input_data = st.text_area("Введите текст:", height=200)
            if input_data:
                st.info(f"Длина: {len(input_data)} символов")
        
        else:  # URL
            url = st.text_input("URL документа:")
            if url:
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    input_data = soup.get_text()[:20000]  # Лимит
                except:
                    st.error("Ошибка загрузки URL")
        
        # Проверка лимитов перед активацией кнопки
        daily_remaining = 1000 - limit_manager.daily_requests
        can_make_request = daily_remaining > 0 and input_data
        
        if daily_remaining <= 50:
            st.markdown(f'<div class="limit-critical">⚠️ Осталось {daily_remaining} запросов сегодня!</div>', unsafe_allow_html=True)
        
        analyze_btn = st.button(
            "🚀 Запустить анализ", 
            disabled=not can_make_request,
            type="primary" if can_make_request else "secondary",
            use_container_width=True
        )
        
        if not can_make_request and daily_remaining <= 0:
            st.error("Дневной лимит исчерпан. Попробуйте завтра.")
    
    with col2:
        st.subheader("Результаты")
        
        if analyze_btn and input_data:
            # Создаем уникальный хеш для кэширования
            prompt_text = f"Анализ для {role} в {loc}"
            content_hash = hashlib.md5(f"{prompt_text}_{input_data[:1000]}".encode()).hexdigest()
            
            # Проверяем кэш если включено
            cache_key = f"analysis_{content_hash}"
            if use_cache and cache_key in st.session_state:
                result = st.session_state[cache_key]
                st.markdown('<div class="cache-badge">Из кэша</div>', unsafe_allow_html=True)
            else:
                with st.spinner(f"Анализирую (осталось {daily_remaining-1} запросов)..."):
                    # Оптимизация промпта для экономии токенов
                    prompt = f"""
                    Роль: {role}. Страна: {loc}. 
                    Выдели: 
                    1. Главные риски (🔴)
                    2. Финансовые аспекты (💸)  
                    3. Проблемные пункты (⚠️)
                    Кратко, по делу. MAX 500 слов.
                    """
                    
                    result, error = call_gemini_with_limits(
                        content_hash, prompt, 
                        input_data[:30000] if optimize_text and len(input_data) > 30000 else input_data,
                        is_image
                    )
                    
                    if error:
                        st.error(error)
                        result = None
                    elif result and use_cache:
                        st.session_state[cache_key] = result
            
            if result:
                # Отображение результата
                lines = result.split('\n')
                for line in lines:
                    if '🔴' in line or '💸' in line or '⚠️' in line:
                        st.markdown(f'<div class="risk-card">{line}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(line)
                
                # Кнопка скачивания
                if st.button("📥 Сохранить отчет", use_container_width=True):
                    doc = Document()
                    doc.add_heading("Анализ документа", 0)
                    doc.add_paragraph(result)
                    bio = io.BytesIO()
                    doc.save(bio)
                    st.download_button(
                        label="Скачать DOCX",
                        data=bio.getvalue(),
                        file_name="analysis.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
        
        elif not analyze_btn:
            st.info("Загрузите документ и нажмите кнопку для анализа")
            st.markdown("""
            **Оптимизация для Free Tier:**
            - Кэширование результатов
            - Автосокращение длинных текстов  
            - Приоритизация моделей
            - Лимит вывода: 2000 токенов
            """)

with tab2:
    st.subheader("Сравнение документов (оптимизировано)")
    
    col_a, col_b = st.columns(2)
    with col_a:
        file_a = st.file_uploader("Документ A", type=["pdf", "docx"], key="fa")
    with col_b:
        file_b = st.file_uploader("Документ B", type=["pdf", "docx"], key="fb")
    
    if st.button("⚖️ Сравнить", disabled=not (file_a and file_b)):
        with st.spinner("Сравниваю..."):
            # Используем кэшированное извлечение
            text_a = extract_text_cached(file_a.getvalue(), file_a.name)[:15000]
            text_b = extract_text_cached(file_b.getvalue(), file_b.name)[:15000]
            
            prompt = "Сравни два документа, выдели только ключевые различия в таблице. Кратко."
            content = f"ДОК А:\n{text_a}\n\nДОК Б:\n{text_b}"
            
            content_hash = hashlib.md5(f"compare_{text_a[:500]}_{text_b[:500]}".encode()).hexdigest()
            result, error = call_gemini_with_limits(content_hash, prompt, content)
            
            if result:
                st.markdown(result)

with tab3:
    st.subheader("Генерация документов")
    
    if 'audit_result' in st.session_state:
        st.info("Используется результат предыдущего анализа")
    
    task = st.text_area("Запрос для генерации:", 
                       placeholder="Например: составь протокол разногласий на основе анализа",
                       height=100)
    
    if st.button("📝 Сгенерировать", disabled=not task):
        with st.spinner("Генерирую..."):
            context = st.session_state.get('audit_result', '')
            prompt = f"{task}. Будь кратким. MAX 300 слов."
            
            content_hash = hashlib.md5(f"generate_{task}_{context[:500]}".encode()).hexdigest()
            result, error = call_gemini_with_limits(content_hash, prompt, context[:10000])
            
            if result:
                st.markdown(result)

# ==================== ФУТЕР С ИНФОРМАЦИЕЙ О ЛИМИТАХ ====================
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.caption(f"📊 Запросов сегодня: {limit_manager.daily_requests}/1000")
with col_info2:
    st.caption("⚡ RPM: 15/мин (Flash-Lite)")
with col_info3:
    st.caption("🔑 Google AI Studio Free Tier")

# Скрипт для автоматического сброса счетчика в 08:00 UTC
if st.button("🔄 Обновить счетчик лимитов (тест)"):
    limit_manager.daily_requests = 0
    limit_manager.last_reset = datetime.utcnow()
    st.success("Счетчик сброшен!")
    time.sleep(1)
    st.rerun()
