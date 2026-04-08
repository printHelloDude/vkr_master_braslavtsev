"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.2.1 (Skeleton)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.
[STUB_MARKER] - обозначает заглушку для последующей реализации
[IMPLEMENTED] - обозначает реализованный функционал
"""
import streamlit as st
from datetime import datetime

# ============================================================================
# НАСТРОЙКИ СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="СУП Легкой Промышленности",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# [STUB_MARKER] КОМПОНЕНТ АУТЕНТИФИКАЦИИ (Требование R-SY-1)
# ============================================================================
def check_authentication():
    """Заглушка проверки аутентификации."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Аутентификация пользователя")
            username = st.text_input("Логин", key="login_username")
            password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", type="primary"):
                if username:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Введите логин")
        return False
    return True

def logout():
    """Завершение сеанса пользователя"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================
def main():
    """Основная функция приложения."""
    # Проверка аутентификации (Требование R-SY-1)
    if not check_authentication():
        return
    
    # Заголовок приложения
    st.title("Система управления деятельностью предприятия")
    st.markdown("---")

    # Боковая панель с навигацией
    with st.sidebar:
        # Навигация по страницам
        st.navigation([
            st.Page("pages/Main.py", title="Главная", icon="🏠"),
            st.Page("pages/Design.py", title="Конструирование", icon="📐"),
            st.Page("pages/Planning.py", title="Планирование", icon="📅"),
            st.Page("pages/Production.py", title="Производство", icon="🏭"),
        ])
        
        st.markdown("  ")
        st.markdown(f"**Пользователь:** {st.session_state.get('current_user', 'Гость')}")
        
        # Пустое пространство
        st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True)
        
        # Кнопка выхода
        st.button("Выйти", use_container_width=True, on_click=logout)
        
        st.markdown("  ")
        st.caption("Версия прототипа: 0.2.1")

if __name__ == "__main__":
    main()
