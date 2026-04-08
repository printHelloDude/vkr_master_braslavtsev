"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.5.0 (Single File / Mono-Page)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.

Инструкция по запуску:
1. Установите библиотеку: pip install streamlit
2. Запустите: streamlit run app.py
"""

import streamlit as st
from datetime import datetime


# =============================================================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
# =============================================================================
st.set_page_config(
    page_title="СУП Легкой Промышленности",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# 2. УПРАВЛЕНИЕ СОСТОЯНИЕМ (SESSION STATE)
# =============================================================================
def init_session_state():
    """Инициализация переменных сессии."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Главная"

init_session_state()


# =============================================================================
# 3. ФУНКЦИИ АУТЕНТИФИКАЦИИ
# =============================================================================
def login_page():
    """Страница входа в систему."""
    st.title("🔐 Вход в систему")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Введите учетные данные")
        username = st.text_input("Логин", key="login_user", placeholder="user")
        password = st.text_input("Пароль", type="password", key="login_pass", placeholder="••••")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Войти", type="primary", use_container_width=True):
                if username:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Введите логин")
        
        with col_btn2:
            if st.button("Войти как гость", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.current_user = "Гость"
                st.rerun()


def logout():
    """Выход из системы."""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.page = "🏠 Главная"
    st.rerun()


# =============================================================================
# 4. СТРАНИЦЫ КОНТЕКСТОВ
# =============================================================================
def page_home():
    """Главная страница."""
    st.title("🏭 Система управления деятельностью предприятия")
    st.markdown("---")
    
    st.success(f"Добро пожаловать, {st.session_state.current_user}!")
    
    st.markdown("""
    ### О прототипе
    
    Это система для управления процессами малого швейного предприятия.
    Выберите раздел в меню слева для перехода к функционалу.
    
    **Доступные разделы:**
    - 📐 **Конструирование** — загрузка лекал, ТЗ, комментарии.
    - 📅 **Планирование** — календарные планы, приоритеты.
    - 🏭 **Производство** — учет брака, операций.
    """)


def page_design():
    """Контекст: Конструирование."""
    st.title("📐 Конструирование")
    st.markdown("---")
    
    st.subheader("Создание новой модели")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Артикул модели", placeholder="M-001")
        st.text_input("Наименование", placeholder="Худи Базовое")
    
    with col2:
        st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима"])
        st.selectbox("Категория", ["Верхняя одежда", "Брюки"])
        
    st.markdown("---")
    st.subheader("Загрузка лекал (DXF/PDF)")
    uploaded_files = st.file_uploader("Загрузить файлы", type=["dxf", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"Загружено файлов: {len(uploaded_files)}")
        for file in uploaded_files:
            st.caption(f"📄 {file.name} ({file.size} bytes)")
    
    if st.button("Сохранить модель", type="primary"):
        st.toast("Модель сохранена (демо)", icon="✅")


def page_planning():
    """Контекст: Планирование."""
    st.title("📅 Планирование")
    st.markdown("---")
    st.info("Раздел в разработке. Здесь будет календарный план производства.")


def page_production():
    """Контекст: Производство."""
    st.title("🏭 Производство")
    st.markdown("---")
    st.info("Раздел в разработке. Здесь будет учет операций и брака.")


# =============================================================================
# 5. ОСНОВНАЯ ЛОГИКА (MAIN)
# =============================================================================
def main():
    """Главная функция приложения."""
    
    # Если не авторизован — показываем экран входа
    if not st.session_state.authenticated:
        login_page()
        return

    # Если авторизован — показываем интерфейс
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.markdown("---")
        
        # Навигация
        st.session_state.page = st.radio(
            "Навигация",
            ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
            index=["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"].index(st.session_state.page),
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            logout()

    # Рендеринг выбранной страницы
    if st.session_state.page == "🏠 Главная":
        page_home()
    elif st.session_state.page == "📐 Конструирование":
        page_design()
    elif st.session_state.page == "📅 Планирование":
        page_planning()
    elif st.session_state.page == "🏭 Производство":
        page_production()


if __name__ == "__main__":
    main()
