"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.6.0 (Single File + SQLite + Registry Pattern)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.

Реализованные требования:
- R-SY-1: Обязательная аутентификация
- R-SY-2: Таймаут сессии 30 минут
- R-DE-1: Загрузка DXF/PDF (≤50 МБ)
- R-DE-2: Автофиксация даты/времени версии
- R-DE-4: Блокировка редактирования утвержденного ТП
- R-DE-6: Комментарии к лекалам
"""

import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

# ============================================================================
# === 1. CONFIG & DB LAYER ===================================================
# ============================================================================

# Конфигурация
DB_PATH = "./data/prototype.db"
UPLOADS_DIR = "./data/uploads"
MAX_FILE_SIZE_MB = 50
SESSION_TIMEOUT_MIN = 30

# Инициализация директорий
Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def db_init():
    """Инициализация базы данных SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица моделей (R-DE-1, R-DE-2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            season TEXT,
            category TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_version INTEGER DEFAULT 1
        )
    """)
    
    # Таблица технических пакетов (версионирование)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tech_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (model_id) REFERENCES models(id),
            UNIQUE(model_id, version)
        )
    """)
    
    # Таблица файлов (R-DE-1)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_package_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tech_package_id) REFERENCES tech_packages(id)
        )
    """)
    
    # Таблица комментариев (R-DE-6)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_package_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tech_package_id) REFERENCES tech_packages(id)
        )
    """)
    
    conn.commit()
    conn.close()


def db_get_connection():
    """Получение соединения с БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_get_models(status_filter=None):
    """Получение списка моделей."""
    conn = db_get_connection()
    cursor = conn.cursor()
    
    if status_filter:
        cursor.execute("""
            SELECT m.*, 
                   COUNT(DISTINCT tp.id) as package_count,
                   MAX(tp.created_at) as last_update
            FROM models m
            LEFT JOIN tech_packages tp ON m.id = tp.model_id
            WHERE m.status = ?
            GROUP BY m.id
            ORDER BY m.created_at DESC
        """, (status_filter,))
    else:
        cursor.execute("""
            SELECT m.*, 
                   COUNT(DISTINCT tp.id) as package_count,
                   MAX(tp.created_at) as last_update
            FROM models m
            LEFT JOIN tech_packages tp ON m.id = tp.model_id
            GROUP BY m.id
            ORDER BY m.created_at DESC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def db_save_model(article, name, season, category, created_by):
    """
    Создание модели с техническим пакетом v1.
    R-DE-1, R-DE-2
    """
    conn = db_get_connection()
    cursor = conn.cursor()
    
    try:
        # Создание модели
        cursor.execute("""
            INSERT INTO models (article, name, season, category, status, current_version)
            VALUES (?, ?, ?, ?, 'draft', 1)
        """, (article, name, season, category))
        model_id = cursor.lastrowid
        
        # Создание технического пакета v1
        cursor.execute("""
            INSERT INTO tech_packages (model_id, version, status, created_by)
            VALUES (?, 1, 'draft', ?)
        """, (model_id, created_by))
        package_id = cursor.lastrowid
        
        conn.commit()
        return model_id, package_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def db_get_tech_package(package_id):
    """Получение технического пакета."""
    conn = db_get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tp.*, m.article, m.name 
        FROM tech_packages tp
        JOIN models m ON tp.model_id = m.id
        WHERE tp.id = ?
    """, (package_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def db_approve_package(package_id):
    """
    Утверждение технического пакета.
    R-DE-4: Блокировка редактирования
    """
    conn = db_get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tech_packages 
        SET status = 'approved', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (package_id,))
    
    cursor.execute("""
        UPDATE models 
        SET status = 'approved', updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT model_id FROM tech_packages WHERE id = ?)
    """, (package_id,))
    
    conn.commit()
    conn.close()


def db_create_new_version(model_id, created_by):
    """
    Создание новой версии технического пакета.
    R-DE-2, R-DE-4
    """
    conn = db_get_connection()
    cursor = conn.cursor()
    
    # Получение текущего номера версии
    cursor.execute("""
        SELECT MAX(version) FROM tech_packages WHERE model_id = ?
    """, (model_id,))
    current_version = cursor.fetchone()[0] or 0
    new_version = current_version + 1
    
    # Создание новой версии
    cursor.execute("""
        INSERT INTO tech_packages (model_id, version, status, created_by)
        VALUES (?, ?, 'draft', ?)
    """, (model_id, new_version, created_by))
    package_id = cursor.lastrowid
    
    # Обновление текущей версии модели
    cursor.execute("""
        UPDATE models 
        SET current_version = ?, status = 'draft', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_version, model_id))
    
    conn.commit()
    conn.close()
    return package_id


def db_save_file(package_id, filename, file_path, file_size, mime_type):
    """
    Сохранение метаданных файла.
    R-DE-1
    """
    conn = db_get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (tech_package_id, filename, file_path, file_size, mime_type)
        VALUES (?, ?, ?, ?, ?)
    """, (package_id, filename, file_path, file_size, mime_type))
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def db_get_package_files(package_id):
    """Получение списка файлов пакета."""
    conn = db_get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files 
        WHERE tech_package_id = ?
        ORDER BY uploaded_at DESC
    """, (package_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def db_add_comment(package_id, author, text):
    """
    Добавление комментария.
    R-DE-6
    """
    conn = db_get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (tech_package_id, author, text)
        VALUES (?, ?, ?)
    """, (package_id, author, text))
    comment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return comment_id


def db_get_comments(package_id):
    """Получение комментариев пакета."""
    conn = db_get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM comments 
        WHERE tech_package_id = ?
        ORDER BY created_at DESC
    """, (package_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============================================================================
# === 2. UI COMPONENTS (PATTERNS) ============================================
# ============================================================================

def render_registry(entity_name, columns, rows, actions_callback, show_archived=False):
    """
    Универсальный компонент реестра/архива.
    
    Args:
        entity_name: Название сущности
        columns: Список колонок для отображения
        rows: Список словарей с данными
        actions_callback: Функция для рендеринга кнопок действий
        show_archived: Показывать архивные записи
    """
    st.subheader(f"📋 {entity_name}")
    
    if not rows:
        st.info(f"⚠️ {entity_name} пока пуст. Создайте первую запись.")
        return
    
    # Фильтрация по статусу
    if not show_archived:
        active_rows = [r for r in rows if r.get('status') != 'archived']
    else:
        active_rows = rows
    
    # Отображение в виде карточек
    for row in active_rows:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.markdown(f"**{row.get('article', row.get('id', 'N/A'))}**")
                st.caption(row.get('name', ''))
            
            with col2:
                status = row.get('status', 'unknown')
                status_emoji = {
                    'draft': '📝',
                    'in_review': '👀',
                    'approved': '✅',
                    'archived': '📦'
                }.get(status, '📄')
                st.markdown(f"{status_emoji} **Статус:** {status}")
                st.caption(f"Версия: v{row.get('current_version', 1)}")
            
            with col3:
                created = row.get('created_at', '')
                if created:
                    st.caption(f"Создано: {created[:10]}")
                actions_callback(row)
            
            # Expander с деталями
            with st.expander("📎 Детали и файлы"):
                st.markdown("#### Информация")
                for key, value in row.items():
                    if value and key not in ['id', 'article', 'name', 'status']:
                        st.text(f"{key}: {value}")


# ============================================================================
# === 3. CONTEXT PAGES =======================================================
# ============================================================================

def page_design():
    """
    Контекст: Конструирование.
    R-DE-1, R-DE-2, R-DE-4, R-DE-6
    """
    st.title("📐 Конструирование")
    st.markdown("---")
    
    # Вкладки: Реестр и Создание
    tab1, tab2 = st.tabs(["📋 Реестр моделей", "➕ Создание модели"])
    
    with tab1:
        # Реестр моделей
        models = db_get_models()
        
        def model_actions(model):
            """Кнопки действий для модели."""
            package = db_get_tech_package(model.get('id'))
            
            if st.button("📄 Открыть", key=f"open_{model['id']}"):
                st.session_state.selected_model = model
                st.session_state.show_model_details = True
            
            if model.get('status') != 'approved':
                if st.button("✅ Утвердить", key=f"approve_{model['id']}"):
                    db_approve_package(package['id'])
                    st.success(f"Модель {model['article']} утверждена")
                    st.rerun()
            
            if model.get('status') == 'approved':
                if st.button("🔄 Создать v2", key=f"newver_{model['id']}"):
                    db_create_new_version(model['id'], st.session_state.current_user)
                    st.success("Создана новая версия")
                    st.rerun()
        
        render_registry(
            entity_name="Модели",
            columns=['article', 'name', 'status', 'current_version'],
            rows=models,
            actions_callback=model_actions
        )
        
        # Детали модели (если выбрана)
        if st.session_state.get('show_model_details') and st.session_state.get('selected_model'):
            model = st.session_state.selected_model
            st.markdown("---")
            st.subheader(f"📦 {model['article']} - {model['name']}")
            
            package = db_get_tech_package(model['id'])
            if package:
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Статус:** {package['status']}\n\n**Версия:** v{package['version']}\n\n**Создан:** {package['created_by']}")
                
                with col2:
                    # Загрузка файлов (R-DE-1)
                    if package['status'] != 'approved':
                        uploaded = st.file_uploader(
                            "Загрузить лекала (DXF/PDF, ≤50МБ)",
                            type=['dxf', 'pdf'],
                            key=f"upload_{package['id']}"
                        )
                        
                        if uploaded:
                            if uploaded.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                                st.error(f"Файл превышает {MAX_FILE_SIZE_MB}МБ")
                            else:
                                # Сохранение файла
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                safe_name = f"{model['id']}_v{package['version']}_{timestamp}_{uploaded.name}"
                                file_path = os.path.join(UPLOADS_DIR, safe_name)
                                
                                with open(file_path, "wb") as f:
                                    f.write(uploaded.getvalue())
                                
                                db_save_file(
                                    package['id'],
                                    uploaded.name,
                                    file_path,
                                    uploaded.size,
                                    uploaded.type
                                )
                                st.success("Файл загружен")
                                st.rerun()
                    
                    # Список файлов
                    files = db_get_package_files(package['id'])
                    if files:
                        st.markdown("📎 **Файлы:**")
                        for file in files:
                            st.caption(f"📄 {file['filename']} ({file['file_size'] / 1024:.1f} КБ)")
                            
                            # Кнопка скачивания
                            with open(file['file_path'], 'rb') as f:
                                st.download_button(
                                    label="⬇️ Скачать",
                                    data=f,
                                    file_name=file['filename'],
                                    mime=file['mime_type'],
                                    key=f"dl_{file['id']}"
                                )
                
                # Комментарии (R-DE-6)
                st.markdown("---")
                st.subheader("💬 Комментарии")
                
                comments = db_get_comments(package['id'])
                for comment in comments:
                    with st.chat_message(name=comment['author']):
                        st.markdown(comment['text'])
                        st.caption(f"{comment['author']} • {comment['created_at']}")
                
                # Форма добавления комментария
                if package['status'] != 'approved':
                    comment_text = st.text_area(
                        "Добавить комментарий",
                        key=f"comment_input_{package['id']}"
                    )
                    if st.button("Отправить", key=f"send_comment_{package['id']}"):
                        if comment_text.strip():
                            db_add_comment(package['id'], st.session_state.current_user, comment_text.strip())
                            st.success("Комментарий добавлен")
                            st.rerun()
    
    with tab2:
        # Форма создания модели (R-DE-1, R-DE-2)
        st.subheader("➕ Создание новой модели")
        
        with st.form(key="create_model_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                article = st.text_input("Артикул модели *", placeholder="M-001")
                name = st.text_input("Наименование *", placeholder="Худи Базовое")
            
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима", "Всесезонное"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки", "Другое"])
            
            submitted = st.form_submit_button("💾 Сохранить модель", use_container_width=True, type="primary")
            
            if submitted:
                if not article or not name:
                    st.error("Заполните обязательные поля (артикул и наименование)")
                else:
                    try:
                        model_id, package_id = db_save_model(
                            article, name, season, category, st.session_state.current_user
                        )
                        st.success(f"✅ Модель {article} создана! Технический пакет v1 сформирован автоматически.")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")


def page_planning():
    """Контекст: Планирование (заглушка)."""
    st.title("📅 Планирование")
    st.markdown("---")
    st.info("🚧 Раздел в разработке. Здесь будет календарный план производства.")


def page_production():
    """Контекст: Производство (заглушка)."""
    st.title("🏭 Производство")
    st.markdown("---")
    st.info("🚧 Раздел в разработке. Здесь будет учет операций и брака.")


# ============================================================================
# === 4. AUTH & ROUTER =======================================================
# ============================================================================

def check_session_timeout():
    """R-SY-2: Проверка таймаута сессии."""
    if 'last_activity' in st.session_state:
        inactive_time = datetime.now() - st.session_state.last_activity
        if inactive_time > timedelta(minutes=SESSION_TIMEOUT_MIN):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.last_activity = None
            st.warning("⏰ Сессия завершена из-за неактивности")
            st.stop()
    st.session_state.last_activity = datetime.now()


def login_page():
    """Страница входа (R-SY-1)."""
    st.title("🔐 Вход в систему")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Введите учетные данные")
        
        with st.form(key="login_form"):
            username = st.text_input("Логин", placeholder="user")
            password = st.text_input("Пароль", type="password", placeholder="••••")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("Войти", use_container_width=True, type="primary")
                if submitted:
                    if username:
                        st.session_state.authenticated = True
                        st.session_state.current_user = username
                        st.session_state.last_activity = datetime.now()
                        st.rerun()
                    else:
                        st.error("Введите логин")
            
            with col_btn2:
                if st.form_submit_button("Войти как гость", use_container_width=True):
                    st.session_state.authenticated = True
                    st.session_state.current_user = "Гость"
                    st.session_state.last_activity = datetime.now()
                    st.rerun()


def main():
    """Основная функция приложения."""
    # Инициализация БД
    db_init()
    
    # Инициализация session_state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    if 'show_model_details' not in st.session_state:
        st.session_state.show_model_details = False
    
    # Проверка аутентификации (R-SY-1)
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Проверка таймаута (R-SY-2)
    check_session_timeout()
    
    # Боковая панель с навигацией
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.caption(f"Последняя активность: {st.session_state.last_activity.strftime('%H:%M:%S') if st.session_state.last_activity else 'N/A'}")
        st.markdown("---")
        
        # Навигация (SPA, без перезагрузки)
        page = st.radio(
            "Навигация",
            ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        
        st.markdown("---")
        st.caption("Версия: 0.6.0")
    
    # Рендеринг страниц
    if page == "🏠 Главная":
        st.title("🏭 Система управления деятельностью предприятия")
        st.markdown("---")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        
        st.markdown("""
        ### О прототипе
        
        Это система для управления процессами малого швейного предприятия.
        
        **Реализованные функции:**
        - ✅ Аутентификация с таймаутом сессии
        - ✅ Создание моделей с автоверсионированием
        - ✅ Загрузка лекал (DXF/PDF, ≤50МБ)
        - ✅ Утверждение технических пакетов
        - ✅ Комментарии к лекалам
        - ✅ Блокировка редактирования утвержденных документов
        
        **В разработке:**
        - 🚧 Календарное планирование
        - 🚧 Учет производства и брака
        """)
    
    elif page == "📐 Конструирование":
        page_design()
    
    elif page == "📅 Планирование":
        page_planning()
    
    elif page == "🏭 Производство":
        page_production()


if __name__ == "__main__":
    main()
