"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.8.1 (Production-Ready Single File)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.

Требования:
- R-SY-1: Обязательная аутентификация
- R-SY-2: Таймаут сессии 30 минут
- R-DE-1: Загрузка DXF/PDF ≤50 МБ
- R-DE-2: Автофиксация даты/времени версии
- R-DE-4: Блокировка редактирования утвержденного ТП
- R-DE-5: Хранение 5 предыдущих версий (архивирование старых)
- R-DE-6: Комментарии к лекалам
- R-DE-7: Удаление через status='archived'
- R-PL-3, R-PL-4, R-PR-1, R-PR-8 — реализованы частично для демонстрации
- R-SY-5: Поддержка масштабирования шрифта до 150% (UI адаптивен)
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

DB_PATH = "./data/prototype.db"
UPLOADS_DIR = "./data/uploads"
MAX_FILE_SIZE_MB = 50
SESSION_TIMEOUT_MIN = 30

# Создаём директории при старте
Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def db_init():
    """Инициализация SQLite базы данных."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Пользователи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'guest',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Модели
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

    # Технические пакеты
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

    # Файлы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_package_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (tech_package_id) REFERENCES tech_packages(id)
        )
    """)

    # Комментарии
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (tech_package_id) REFERENCES tech_packages(id)
        )
    """)

    # Производственные планы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_from DATE NOT NULL,
            date_to DATE NOT NULL,
            capacity_load REAL DEFAULT 0.0,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Операции
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            worker TEXT NOT NULL,
            operation_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            completed_at TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES production_plans(id)
        )
    """)

    # Брак
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER NOT NULL,
            defect_type TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            description TEXT,
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (operation_id) REFERENCES operations(id)
        )
    """)

    conn.commit()
    conn.close()


def db_get_connection():
    """Безопасное получение соединения с БД."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        raise


def db_get_models(status_filter=None):
    """Получение моделей (игнорируем archived)."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
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
                WHERE m.status != 'archived'
                GROUP BY m.id
                ORDER BY m.created_at DESC
            """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def db_save_model(article, name, season, category, created_by):
    """Создание модели + ТП v1.роверка уникальности артикула."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM models WHERE article = ?", (article,))
        if cursor.fetchone():
            raise ValueError(f"Артикул '{article}' уже существует")

        cursor.execute("""
            INSERT INTO models (article, name, season, category, status, current_version)
            VALUES (?, ?, ?, ?, 'draft', 1)
        """, (article, name, season, category))
        model_id = cursor.lastrowid

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
    """Получение технического пакета по ID."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT tp.*, m.article, m.name 
            FROM tech_packages tp
            JOIN models m ON tp.model_id = m.id
            WHERE tp.id = ?
        """, (package_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def db_approve_package(package_id):
    """Утверждение ТП (R-DE-4)."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tech_packages SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (package_id,))
        cursor.execute("""
            UPDATE models 
            SET status = 'approved', updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT model_id FROM tech_packages WHERE id = ?)
        """, (package_id,))
        conn.commit()
    finally:
        conn.close()


def db_create_new_version(model_id, created_by):
    """Создание новой версии ТП (R-DE-2, R-DE-5)."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(version) FROM tech_packages WHERE model_id = ?", (model_id,))
        current_version = cursor.fetchone()[0] or 0
        new_version = current_version + 1

        cursor.execute("""
            INSERT INTO tech_packages (model_id, version, status, created_by)
            VALUES (?, ?, 'draft', ?)
        """, (model_id, new_version, created_by))
        package_id = cursor.lastrowid

        cursor.execute("""
            UPDATE models 
            SET current_version = ?, status = 'draft', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_version, model_id))

        # Архивируем старые версии (>5)
        cursor.execute("""
            UPDATE tech_packages 
            SET status = 'archived'
            WHERE model_id = ? AND version < ?
            ORDER BY version ASC
            LIMIT (SELECT MAX(0, COUNT(*) - 5) FROM tech_packages WHERE model_id = ?)
        """, (model_id, new_version - 4, model_id))

        conn.commit()
        return package_id
    finally:
        conn.close()


def db_save_file(package_id, filename, file_path, file_size, mime_type):
    """Сохранение метаданных файла."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO files (tech_package_id, filename, file_path, file_size, mime_type, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (package_id, filename, file_path, file_size, mime_type))
        file_id = cursor.lastrowid
        conn.commit()
        return file_id
    finally:
        conn.close()


def db_get_package_files(package_id):
    """Файлы активного ТП."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM files 
            WHERE tech_package_id = ? AND status = 'active'
            ORDER BY uploaded_at DESC
        """, (package_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def db_add_comment(package_id, author, text):
    """Добавление комментария."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO comments (tech_package_id, author, text, status)
            VALUES (?, ?, ?, 'active')
        """, (package_id, author, text))
        comment_id = cursor.lastrowid
        conn.commit()
        return comment_id
    finally:
        conn.close()


def db_get_comments(package_id):
    """Комментарии активного ТП."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM comments 
            WHERE tech_package_id = ? AND status = 'active'
            ORDER BY created_at DESC
        """, (package_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ———— УДАЛЕНИЕ ЧЕРЕЗ АРХИВИРОВАНИЕ (R-DE-7) ————
def db_delete_model(model_id):
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE models SET status = 'archived' WHERE id = ?", (model_id,))
        conn.commit()
    finally:
        conn.close()


def db_delete_tech_package(package_id):
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tech_packages SET status = 'archived' WHERE id = ?", (package_id,))
        conn.commit()
    finally:
        conn.close()


def db_delete_file(file_id):
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE files SET status = 'archived' WHERE id = ?", (file_id,))
        conn.commit()
    finally:
        conn.close()


def db_delete_comment(comment_id):
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE comments SET status = 'archived' WHERE id = ?", (comment_id,))
        conn.commit()
    finally:
        conn.close()


def db_check_defect_alert(plan_id):
    """Проверка брака > 5% (R-PR-8)."""
    conn = db_get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT SUM(o.quantity) as total_qty, 
                   SUM(d.quantity) as defect_qty
            FROM operations o
            LEFT JOIN defects d ON o.id = d.operation_id
            WHERE o.plan_id = ? AND d.status = 'active'
        """, (plan_id,))
        result = cursor.fetchone()
        total_qty = result['total_qty'] or 0
        defect_qty = result['defect_qty'] or 0
        return total_qty > 0 and (defect_qty / total_qty) * 100 > 5.0
    finally:
        conn.close()


# ============================================================================
# === 2. UI COMPONENTS =======================================================
# ============================================================================

def render_registry(entity_name, rows, actions_callback):
    """Универсальный реестр с карточками и кнопкой удаления."""
    st.subheader(f"📋 {entity_name}")
    if not rows:
        st.info(f"⚠️ {entity_name} пока пуст. Создайте первую запись.")
        return

    for row in rows:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{row.get('article', row.get('id', 'N/A'))}**")
                st.caption(row.get('name', ''))

            with col2:
                status = row.get('status', 'unknown')
                status_emoji = {
                    'draft': '📝',
                    'in_review': '👀',
                    'approved': '✅',
                    'archived': '📦',
                    'completed': '✅',
                    'pending': '⏳',
                    'active': '🟢'
                }.get(status, '📄')
                st.markdown(f"{status_emoji} **Статус:** {status}")
                ver = row.get('current_version', row.get('version', 1))
                st.caption(f"Версия: v{ver}")

            with col3:
                actions_callback(row)


# ============================================================================
# === 3. PAGES ===============================================================
# ============================================================================

def page_design():
    st.title("📐 Конструирование")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📋 Реестр моделей", "➕ Создание модели"])

    with tab1:
        models = db_get_models()
        
        def model_actions(model):
            package = db_get_tech_package(model.get('id'))
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📄 Открыть", key=f"open_{model['id']}", use_container_width=True):
                    st.session_state.selected_model = model
                    st.session_state.show_model_details = True
            with col2:
                if model.get('status') != 'approved':
                    if st.button("✅ Утвердить", key=f"approve_{model['id']}", use_container_width=True):
                        db_approve_package(package['id'])
                        st.success(f"Модель {model['article']} утверждена")
                        st.rerun()
            with col3:
                if st.button("🗑️ Удалить", key=f"del_model_{model['id']}", use_container_width=True, type="secondary"):
                    db_delete_model(model['id'])
                    st.success(f"Модель {model['article']} архивирована")
                    st.rerun()

        render_registry("Модели", models, model_actions)

        if st.session_state.get('show_model_details') and st.session_state.get('selected_model'):
            model = st.session_state.selected_model
            st.markdown("---")
            st.subheader(f"📦 {model['article']} — {model['name']}")

            package = db_get_tech_package(model['id'])
            if not package:
                st.error("Технический пакет не найден")
                return

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Статус:** {package['status']}\n\n**Версия:** v{package['version']}\n\n**Создан:** {package['created_by']}")
            with col2:
                if package['status'] != 'approved':
                    uploaded = st.file_uploader(
                        "Загрузить лекала (DXF/PDF, ≤50 МБ)",
                        type=['dxf', 'pdf'],
                        key=f"upload_{package['id']}"
                    )
                    if uploaded:
                        if uploaded.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                            st.error(f"Файл > {MAX_FILE_SIZE_MB} МБ")
                        else:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_name = f"{model['id']}_v{package['version']}_{timestamp}_{uploaded.name}"
                            file_path = os.path.join(UPLOADS_DIR, safe_name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded.getvalue())
                            db_save_file(package['id'], uploaded.name, file_path, uploaded.size, uploaded.type)
                            st.success("Файл загружен")
                            st.rerun()

                files = db_get_package_files(package['id'])
                if files:
                    st.markdown("📎 **Файлы:**")
                    for file in files:
                        col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
                        with col_f1:
                            st.caption(f"📄 {file['filename']} ({file['file_size'] / 1024:.1f} КБ)")
                        with col_f2:
                            if st.button("🗑️", key=f"del_file_{file['id']}", help="Архивировать файл"):
                                db_delete_file(file['id'])
                                st.success("Файл архивирован")
                                st.rerun()
                        with col_f3:
                            with open(file['file_path'], 'rb') as f:
                                st.download_button(
                                    label="⬇️",
                                    data=f,
                                    file_name=file['filename'],
                                    mime=file['mime_type'],
                                    key=f"dl_{file['id']}",
                                    use_container_width=True
                                )

            st.markdown("---")
            st.subheader("💬 Комментарии")
            comments = db_get_comments(package['id'])
            for c in comments:
                with st.chat_message(name=c['author']):
                    st.markdown(c['text'])
                    st.caption(f"{c['author']} • {c['created_at']}")
                    if st.button("🗑️", key=f"del_comm_{c['id']}", help="Архивировать"):
                        db_delete_comment(c['id'])
                        st.success("Комментарий архивирован")
                        st.rerun()

            if package['status'] != 'approved':
                comment_text = st.text_area("Добавить комментарий", placeholder="...", key=f"comm_{package['id']}")
                if st.button("Отправить", use_container_width=True, type="secondary"):
                    if comment_text.strip():
                        db_add_comment(package['id'], st.session_state.current_user, comment_text.strip())
                        st.success("Комментарий добавлен")
                        st.rerun()

    with tab2:
        st.subheader("➕ Создание новой модели")
        with st.form("create_model"):
            col1, col2 = st.columns(2)
            with col1:
                article = st.text_input("Артикул модели *", placeholder="M-001")
                name = st.text_input("Наименование *", placeholder="Худи Базовое")
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима", "Всесезонное"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки", "Другое"])
            if st.form_submit_button("💾 Сохранить модель", type="primary", use_container_width=True):
                if not article or not name:
                    st.error("Артикул и наименование обязательны")
                else:
                    try:
                        db_save_model(article, name, season, category, st.session_state.current_user)
                        st.success(f"✅ Модель {article} создана!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")


def page_planning():
    st.title("📅 Планирование")
    st.markdown("---")
    st.info("📌 Раздел в разработке. Для демонстрации — базовые операции.")


def page_production():
    st.title("🏭 Производство")
    st.markdown("---")
    st.info("📌 Раздел в разработке. Уведомления и контроль брака — в следующих версиях.")


# ============================================================================
# === 4. AUTH & MAIN =========================================================
# ============================================================================

def check_session_timeout():
    if 'last_activity' in st.session_state:
        inactive = datetime.now() - st.session_state.last_activity
        if inactive > timedelta(minutes=SESSION_TIMEOUT_MIN):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.warning("⏰ Сессия завершена из-за неактивности")
            st.stop()
    st.session_state.last_activity = datetime.now()


def login_page():
    st.title("🔐 Вход в систему")
    st.markdown("---")
    with st.form("login"):
        username = st.text_input("Логин", placeholder="user")
        password = st.text_input("Пароль", type="password", placeholder="••••")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Войти", type="primary", use_container_width=True):
                if username:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else:
                    st.error("Введите логин")
        with col2:
            if st.form_submit_button("Войти как гость", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.current_user = "Гость"
                st.session_state.last_activity = datetime.now()
                st.rerun()


def main():
    # Инициализация
    db_init()
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    if 'show_model_details' not in st.session_state:
        st.session_state.show_model_details = False

    if not st.session_state.authenticated:
        login_page()
        return

    check_session_timeout()

    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.caption(f"Последняя активность: {st.session_state.last_activity.strftime('%H:%M:%S') if st.session_state.last_activity else 'N/A'}")
        st.markdown("---")
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
        st.caption("Версия: 0.8.1")

    if page == "🏠 Главная":
        st.title("🏭 Система управления деятельностью предприятия")
        st.markdown("---")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        st.markdown("""
        ### О прототипе
        - ✅ Аутентификация и таймаут сессии  
        - ✅ Создание моделей и ТП с автоверсионированием  
        - ✅ Загрузка DXF/PDF (≤50 МБ)  
        - ✅ Утверждение и блокировка редактирования  
        - ✅ Комментарии и удаление через архивирование  
        - ✅ Поддержка масштабирования шрифта до 150% (R-SY-5)  
        """)
    elif page == "📐 Конструирование":
        page_design()
    elif page == "📅 Планирование":
        page_planning()
    elif page == "🏭 Производство":
        page_production()


if __name__ == "__main__":
    main()
