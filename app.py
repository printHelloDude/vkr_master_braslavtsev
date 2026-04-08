"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.4.1
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime


# =============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# =============================================================================
st.set_page_config(
    page_title="СУП Легкой Промышленности",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# УПРАВЛЕНИЕ СОСТОЯНИЕМ (SESSION STATE)
# =============================================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None


# =============================================================================
# ФУНКЦИИ АУТЕНТИФИКАЦИИ
# =============================================================================
def login():
    """Форма входа в систему."""
    st.markdown("## 🔐 Вход в систему")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Логин", key="login_username")
        password = st.text_input("Пароль", type="password", key="login_password")
        
        col_btn1, col_btn2, _ = st.columns([1, 1, 1])
        with col_btn1:
            if st.button("Войти", type="primary", use_container_width=True):
                if username and password:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Введите логин и пароль")
        
        with col_btn2:
            if st.button("Войти как гость", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.current_user = "Гость"
                st.rerun()


def logout():
    """Выход из системы."""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()


# =============================================================================
# СТРАНИЦЫ ПРИЛОЖЕНИЯ
# =============================================================================
def page_home():
    """Главная страница."""
    st.title("🏭 Система управления деятельностью предприятия")
    st.markdown("---")
    
    st.markdown("""
    ### Добро пожаловать!
    
    Это прототип системы управления для предприятия легкой промышленности.
    
    #### Доступные разделы:
    - **📐 Конструирование** — управление техническими пакетами и лекалами
    - **📅 Планирование** — календарное планирование производства
    - **🏭 Производство** — учет выполнения операций и контроль качества
    
    ---
    **Версия:** 0.4.1 | **Дата:** 2026
    """)


def page_design():
    """Страница: Конструирование."""
    st.title("📐 Конструирование")
    st.markdown("---")
    st.info("Раздел находится в разработке")


def page_planning():
    """Страница: Планирование."""
    st.title("📅 Планирование")
    st.markdown("---")
    st.info("Раздел находится в разработке")


def page_production():
    """Страница: Производство."""
    st.title("🏭 Производство")
    st.markdown("---")
    st.info("Раздел находится в разработке")


# =============================================================================
# ОСНОВНАЯ ЛОГИКА ПРИЛОЖЕНИЯ
# =============================================================================
def main():
    """Основная функция приложения."""
    
    # Проверка аутентификации
    if not st.session_state.authenticated:
        login()
        return
    
    # Боковая панель
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.markdown("---")
        
        # Навигация
        page = st.radio(
            "Навигация",
            ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.button("🚪 Выйти", on_click=logout, use_container_width=True)
    
    # Отображение страниц
    if page == "🏠 Главная":
        page_home()
    elif page == "📐 Конструирование":
        page_design()
    elif page == "📅 Планирование":
        page_planning()
    elif page == "🏭 Производство":
        page_production()


if __name__ == "__main__":
    main()
