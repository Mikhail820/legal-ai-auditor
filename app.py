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
import time
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------
# 1. Настройки интерфейса
# -------------------
st.set_page_config(
    page_title="LegalAI Enterprise Pro", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные стили
st.markdown("""
<style>
    /* Основные стили */
    .main-header { 
        font-size: 2.5rem; 
        color: #FF4B4B; 
        text-align: center; 
        margin-bottom: 1.5rem; 
        font-weight: 800;
        padding: 20px 0;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stButton>button { 
        width: 100%; 
        border-radius: 10px; 
        font-weight: bold; 
        height: 3.5em; 
        background: linear-gradient(135deg, #FF4B4B 0%, #FF6B6B 100%); 
        color: white; 
        border: none;
        transition: all 0.3s ease;
        margin-top: 10px;
    }
    
    .stButton>button:hover { 
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4);
    }
    
    .stDownloadButton>button { 
        width: 100%; 
        border-radius: 10px; 
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
        color: white; 
        border: none;
    }
    
    /* Карточки рисков */
    .risk-card { 
        background-color: #ffffff; 
        border-left: 6px solid #ff4b4b; 
        padding: 20px; 
        border-radius: 8px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        margin-bottom: 20px; 
        color: #000;
        transition: transform 0.3s ease;
    }
    
    .risk-card:hover {
        transform: translateX(5px);
    }
    
    .score-container { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px; 
        border-radius: 15px; 
        text-align: center; 
        border: none;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .disclaimer { 
        font-size: 0.8rem; 
        color: #7f8c8d; 
        padding: 15px; 
        background: #fff3f3; 
        border-radius: 10px; 
        border: 1px solid #fab1a0;
        margin: 10px 0;
    }
    
    /* Вкладки */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    /* Прогресс бар */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 100%);
    }
    
    /* Боковая панель */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2d3436 0%, #1a1e1f 100%);
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label {
        color: white !important;
    }
    
    /* Улучшенные текстовые области */
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
    }
    
    /* Карточки загрузки файлов */
    .upload-card {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background: #f8f9fa;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Текст дисклеймера
DISCLAIMER_TEXT = """
⚠️ **ВНИМАНИЕ:** 
Анализ выполнен искусственным интеллектом. Не является юридической консультацией. 
Все выводы требуют обязательной проверки у квалифицированного юриста. 
Используйте на свой страх и риск.
"""

# -------------------
# 2. Конфигурация моделей и API
# -------------------
MODEL_POLICY = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

# Получение API ключа
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY")
    if not API_KEY:
        st.error("❌ API ключ не найден в Secrets. Добавьте GOOGLE_API_KEY.")
except:
    API_KEY = None
    st.warning("⚠️ Secrets не настроены. Укажите API ключ вручную.")

# Резервный ввод API ключа
if not API_KEY:
    with st.sidebar:
        API_KEY = st.text_input("🔑 Введите Google API Key:", type="password")
        if API_KEY:
            st.success("✅ Ключ принят")
        else:
            st.warning("Введите API ключ для работы приложения")

# -------------------
# 3. Улучшенная функция вызова Gemini
# -------------------
@st.cache_data(show_spinner=False, max_entries=10)
def call_gemini_safe(prompt: str, content: str, is_image: bool = False, model_override: str = None):
    """
    Безопасный вызов Gemini API с обработкой ошибок и ретраями
    """
    if not API_KEY:
        return "❌ Ошибка: Отсутствует API ключ. Добавьте GOOGLE_API_KEY в Secrets или введите вручную."
    
    if not content or (isinstance(content, str) and not content.strip()):
        return "⚠️ Предупреждение: Пустой документ или текст для анализа."
    
    # Ограничение длины текста для предотвращения перегрузки
    if isinstance(content, str) and len(content) > 100000:
        content = content[:100000] + "\n\n... [текст обрезан из-за большого объема]"
    
    models_to_try = [model_override] if model_override else MODEL_POLICY
    
    for model_idx, model in enumerate(models_to_try):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
            
            # Формирование payload в зависимости от типа контента
            if is_image:
                # Определяем MIME тип по первым байтам
                if content[:3] == b'\xff\xd8\xff':
                    mime_type = "image/jpeg"
                elif content[:8] == b'\x89PNG\r\n\x1a\n':
                    mime_type = "image/png"
                else:
                    mime_type = "image/jpeg"  # fallback
                
                img_b64 = base64.b64encode(content).decode('utf-8')
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topP": 0.8,
                        "topK": 40
                    }
                }
            else:
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{prompt}\n\n=== ДОКУМЕНТ ДЛЯ АНАЛИЗА ===\n{content}\n=== КОНЕЦ ДОКУМЕНТА ==="}]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topP": 0.9,
                        "topK": 50,
                        "maxOutputTokens": 4000
                    }
                }
            
            # Логирование (безопасное)
            logger.info(f"Вызов модели: {model}, длина контента: {len(content) if isinstance(content, str) else 'image'}")
            
            # Вызов API с таймаутом
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    logger.info(f"Успешный ответ от модели {model}")
                    return text
                else:
                    logger.warning(f"Пустой ответ от модели {model}: {result}")
                    continue
            
            elif response.status_code == 429:
                logger.warning(f"Rate limit для модели {model}. Пробуем следующую...")
                time.sleep(1)  # Небольшая задержка перед ретраем
                continue
                
            else:
                error_msg = response.json().get('error', {}).get('message', 'Неизвестная ошибка')
                logger.error(f"Ошибка API ({model}): {response.status_code} - {error_msg}")
                continue
                
        except requests.exceptions.Timeout:
            logger.warning(f"Таймаут для модели {model}")
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка для модели {model}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Неожиданная ошибка для модели {model}: {str(e)}")
            continue
    
    return "⚠️ Все модели временно недоступны. Пожалуйста, попробуйте позже или проверьте:\n1. Доступность API ключа\n2. Интернет-соединение\n3. Лимиты API"

# -------------------
# 4. Инструменты для работы с документами
# -------------------
def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Извлечение текста из различных форматов файлов
    """
    try:
        filename_lower = filename.lower()
        
        if filename_lower.endswith(".pdf"):
            text_parts = []
            try:
                pdf_reader = PdfReader(io.BytesIO(file_bytes))
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            text_parts.append(f"[Страница {page_num + 1}]\n{text}\n")
                    except Exception as e:
                        logger.warning(f"Ошибка чтения страницы {page_num}: {str(e)}")
                        continue
                
                if not text_parts:
                    return "⚠️ Не удалось извлечь текст из PDF. Возможно, документ состоит из сканированных изображений."
                    
                return "\n".join(text_parts)
                
            except Exception as e:
                return f"❌ Ошибка чтения PDF: {str(e)}"
        
        elif filename_lower.endswith(".docx"):
            try:
                doc = Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n".join(paragraphs)
            except Exception as e:
                return f"❌ Ошибка чтения DOCX: {str(e)}"
        
        elif filename_lower.endswith(".txt"):
            try:
                return file_bytes.decode('utf-8', errors='ignore')
            except:
                return file_bytes.decode('cp1251', errors='ignore')
        
        else:
            return "❌ Неподдерживаемый формат файла. Используйте PDF, DOCX или TXT."
            
    except Exception as e:
        logger.error(f"Критическая ошибка при извлечении текста: {str(e)}")
        return f"❌ Не удалось прочитать файл: {str(e)}"

def validate_url(url: str) -> bool:
    """Проверка валидности URL"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def fetch_url_content(url: str) -> str:
    """Безопасное получение контента с веб-страницы"""
    try:
        if not validate_url(url):
            return "❌ Неверный URL. Используйте формат http:// или https://"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=15,
            verify=True,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        # Проверка типа контента
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            return f"⚠️ URL не содержит HTML. Content-Type: {content_type}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Извлекаем основной текст
        text = soup.get_text(separator='\n', strip=True)
        
        # Очистка лишних пробелов и переносов
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not text:
            return "⚠️ Не удалось извлечь текст со страницы"
        
        # Ограничение длины
        if len(text) > 30000:
            text = text[:30000] + "\n\n... [контент обрезан]"
        
        return text
        
    except requests.exceptions.Timeout:
        return "❌ Таймаут при загрузке URL. Проверьте доступность сайта."
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка сети: {str(e)}"
    except Exception as e:
        return f"❌ Неожиданная ошибка: {str(e)}"

def create_docx(text: str, title: str) -> io.BytesIO:
    """
    Создание DOCX документа из текста с форматированием
    """
    try:
        doc = Document()
        
        # Заголовок
        title_para = doc.add_heading(title, 0)
        title_para.alignment = 1  # По центру
        
        # Дата
        from datetime import datetime
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        doc.add_paragraph(f"Дата создания: {date_str}").italic = True
        
        # Дисклеймер
        disclaimer_para = doc.add_paragraph(DISCLAIMER_TEXT)
        disclaimer_para.italic = True
        for run in disclaimer_para.runs:
            run.font.color.rgb = 0xFF0000  # Красный цвет
        
        doc.add_paragraph().add_run().add_break()  # Разделитель
        
        # Обработка текста
        lines = text.split('\n')
        table_data = []
        in_table = False
        
        for line in lines:
            line = line.rstrip()
            
            # Детекция таблицы Markdown
            if '|' in line and not re.match(r'^[\|\s\-:]+$', line.strip()):
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    table_data.append(cells)
                    in_table = True
                continue
            
            # Если собрана таблица, вставляем её
            if in_table and table_data and (not line.strip() or '|' not in line):
                if len(table_data) > 1:  # Минимум 2 строки для таблицы
                    # Определяем количество колонок
                    num_cols = max(len(row) for row in table_data)
                    table = doc.add_table(rows=len(table_data), cols=num_cols)
                    table.style = 'Table Grid'
                    
                    # Заполняем таблицу
                    for i, row in enumerate(table_data):
                        for j, cell_text in enumerate(row):
                            if j < num_cols:
                                cell = table.cell(i, j)
                                cell.text = cell_text
                                # Центрируем заголовки
                                if i == 0:
                                    for paragraph in cell.paragraphs:
                                        paragraph.alignment = 1
                
                table_data = []
                in_table = False
                doc.add_paragraph()  # Отступ после таблицы
            
            # Обработка обычного текста
            if line.strip() and not in_table:
                # Убираем Markdown разметку
                clean_line = re.sub(r'^[#\*\-\+]+|\*\*|\*|__|_|~~', '', line).strip()
                
                if line.startswith('## '):
                    doc.add_heading(clean_line, 2)
                elif line.startswith('# '):
                    doc.add_heading(clean_line, 1)
                elif line.startswith('### '):
                    doc.add_heading(clean_line, 3)
                elif line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
                    doc.add_paragraph(clean_line, style='List Bullet')
                elif re.match(r'^\d+\.', line):
                    doc.add_paragraph(clean_line, style='List Number')
                else:
                    para = doc.add_paragraph(clean_line)
                    
                    # Выделение ключевых фраз
                    if any(keyword in line for keyword in ['риск', 'опасность', 'проблема', '⚠️', '🔴']):
                        for run in para.runs:
                            run.bold = True
                            run.font.color.rgb = 0xFF0000
                    elif any(keyword in line for keyword in ['рекомендация', 'совет', 'решение', '✅', '💡']):
                        for run in para.runs:
                            run.font.color.rgb = 0x008000
        
        # Сохранение в буфер
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        
        logger.info(f"DOCX создан успешно: {title}, размер: {len(buf.getvalue())} байт")
        return buf
        
    except Exception as e:
        logger.error(f"Ошибка создания DOCX: {str(e)}")
        # Возвращаем простой текстовый файл в случае ошибки
        buf = io.BytesIO()
        buf.write(f"Ошибка создания документа: {str(e)}\n\n{text}".encode('utf-8'))
        buf.seek(0)
        return buf

# -------------------
# 5. Боковая панель
# -------------------
with st.sidebar:
    st.markdown("### ⚙️ Конфигурация анализа")
    
    role = st.radio(
        "👤 Анализ для:",
        ["Предприниматель", "Юрист", "Физическое лицо", "Корпоративный клиент"],
        help="Настройка рекомендаций под вашу роль"
    )
    
    loc = st.selectbox(
        "🌍 Юрисдикция:",
        ["Российская Федерация", "Казахстан", "Узбекистан", "Беларусь", "Международное право"],
        index=0
    )
    
    detail = st.select_slider(
        "📊 Уровень детализации:",
        options=["Краткий обзор", "Стандартный", "Детальный анализ", "Максимальный"],
        value="Стандартный",
        help="Влияет на объем и глубину анализа"
    )
    
    st.divider()
    
    st.markdown("### 🎯 Дополнительные параметры")
    
    include_recommendations = st.checkbox("Включить рекомендации", value=True)
    include_alternatives = st.checkbox("Показать альтернативные формулировки", value=False)
    
    st.divider()
    
    # Кэш и сброс
    col_cache1, col_cache2 = st.columns(2)
    with col_cache1:
        if st.button("🗑️ Очистить кэш", use_container_width=True):
            st.cache_data.clear()
            st.success("Кэш очищен!")
            time.sleep(1)
            st.rerun()
    
    with col_cache2:
        if st.button("🔄 Сбросить всё", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Все данные сброшены!")
            time.sleep(1)
            st.rerun()
    
    st.divider()
    
    # Дисклеймер
    with st.expander("⚠️ Важная информация", expanded=True):
        st.markdown(f'<div class="disclaimer">{DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)
    
    # Информация о системе
    st.markdown("---")
    st.markdown("**LegalAI Enterprise Pro v2.0**")
    st.caption("Анализ документов с использованием Google Gemini AI")

# -------------------
# 6. Основной интерфейс
# -------------------
st.markdown('<div class="main-header">⚖️ LegalAI Enterprise Pro</div>', unsafe_allow_html=True)

# Инициализация сессионных переменных
if 'audit_result' n