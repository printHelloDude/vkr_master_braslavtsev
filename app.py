"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.2.0 (Skeleton)
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
# TODO: Реализовать полноценную аутентификацию с сессиями
# TODO: Добавить таймаут сессии 30 минут (Требование R-SY-2)

def check_authentication():
    """
    Заглушка проверки аутентификации.
    В текущей версии всегда возвращает True.
    """
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Аутентификация пользователя")
            username = st.text_input("Логин", key="login_username")
            password = st.text_input("Пароль", type="password", key="login_password")
            
            if st.button("Войти", type="primary"):
                # [STUB_MARKER] Здесь будет проверка учетных данных
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.rerun()
        
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
    """
    Основная функция приложения.
    Реализует навигацию по ограниченным контекстам (Раздел 2 ВКР).
    """
    
    # Проверка аутентификации (Требование R-SY-1)
    if not check_authentication():
        return
    
    # Заголовок приложения
    st.title("Система управления деятельностью предприятия")
    st.markdown("---")
    
    # Боковая панель с навигацией
    with st.sidebar:
        st.markdown(f"**Пользователь:** {st.session_state.get('current_user', 'Гость')}")
        st.markdown("---")
        
        # Навигация по ограниченным контекстам
        st.navigation([
    st.Page("pages/Design.py", title="Конструирование", icon="📐"),
    st.Page("pages/Planning.py", title="Планирование", icon="📅"),
    st.Page("pages/Production.py", title="Производство", icon="🏭"),
        ])
        
        st.markdown("---")
        if st.button("Выйти", use_container_width=True):
            logout()
        
        # Системная информация (Требование R-SY-5)
        st.markdown("---")
        st.caption(f"Версия прототипа: 0.2.0")
        st.caption(f"Время сессии: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
