"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.3.0 (Single File)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.

[STUB_MARKER] - обозначает заглушку для последующей реализации
[IMPLEMENTED] - обозначает реализованный функционал
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
    
    # Боковая панель с навигацией
    with st.sidebar:
        st.markdown(f"**Пользователь:** {st.session_state.get('current_user', 'Гость')}")
        st.markdown("---")
        
        # Навигация по ограниченным контекстам (Раздел 2 ВКР)
        context = st.radio(
            "Разделы системы:",
            ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.button("Выйти", use_container_width=True, on_click=logout)
        st.caption("Версия прототипа: 0.3.0")
    
    # ========================================================================
    # КОНТЕКСТ: ГЛАВНАЯ
    # ========================================================================
    if context == "🏠 Главная":
        st.title("🏭 Система управления деятельностью предприятия")
        st.markdown("---")
        
        st.markdown("""
        ### Добро пожаловать в прототип системы!
        
        **Назначение системы:** автоматизация управления деятельностью малого предприятия легкой промышленности.
        
        #### 📋 Доступные разделы:
        
        1. **📐 Конструирование**
           - Загрузка технических пакетов и лекал
           - Управление версиями документации
           - Согласование конструкторской документации
        
        2. **📅 Планирование**
           - Формирование календарного плана производства
           - Управление приоритетами заказов
           - Контроль загрузки производственных мощностей
        
        3. **🏭 Производство**
           - Учет выполнения операций
           - Фиксация брака и дефектов
           - Контроль качества продукции
        
        #### ℹ️ Техническая информация:
        
        - **Версия прототипа:** 0.3.0
        - **Направление:** 27.04.03 «Системный анализ и управление»
        - **Разработчик:** Браславцев Б.Э.
        """)
        
        st.markdown("---")
        st.info("💡 **Подсказка:** Некоторые функции находятся в разработке и обозначены как [STUB_MARKER].")
    
    # ========================================================================
    # КОНТЕКСТ: КОНСТРУИРОВАНИЕ (Требования R-DE-1...R-DE-7)
    # ========================================================================
    elif context == "📐 Конструирование":
        st.title("📐 Контекст: Конструирование")
        st.markdown("---")
        
        st.subheader("Загрузка технического пакета")
        
        # [STUB_MARKER] Заглушка для R-DE-1, R-DE-2
        st.info("""
        **[STUB_MARKER] Функционал загрузки лекал находится в разработке.**
        
        Планируемая функциональность:
        - Загрузка файлов в форматах DXF, PDF (макс. 50 МБ)
        - Автоматическая фиксация даты и времени версии
        - Хранение истории версий (мин. 5 предыдущих)
        - Блокировка редактирования утвержденных документов
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(label="Артикул модели", placeholder="M-000", key="design_article")
            st.text_input(label="Наименование", placeholder="Худи Базовое", key="design_name")
        with col2:
            st.selectbox(label="Сезон", options=["Весна-Лето", "Осень-Зима"], key="design_season")
            st.selectbox(label="Категория", options=["Верхняя одежда", "Брюки", "Футболки"], key="design_category")
        
        st.file_uploader(label="Загрузить лекала (DXF/PDF)", type=["dxf", "pdf"], key="design_files", disabled=True)
        
        st.markdown("---")
        st.subheader("Согласование технического задания")
        
        # [STUB_MARKER] Заглушка для R-DE-3, R-DE-4, R-DE-6
        st.info("[STUB_MARKER] Функционал согласования находится в разработке.", icon="ℹ️")
        st.text_area(label="Комментарии к техническому пакету", key="design_comments", disabled=True)
        st.button(label="Отправить на согласование", disabled=True, type="primary")
    
    # ========================================================================
    # КОНТЕКСТ: ПЛАНИРОВАНИЕ (Требования R-PL-1...R-PL-7)
    # ========================================================================
    elif context == "📅 Планирование":
        st.title("📅 Контекст: Планирование")
        st.markdown("---")
        
        st.subheader("Календарный план производства")
        
        # [STUB_MARKER] Заглушка для R-PL-1, R-PL-3
        st.info("""
        **[STUB_MARKER] Функционал календарного планирования находится в разработке.**
        
        Планируемая функциональность:
        - Формирование календарного плана на основе заказов
        - Отображение загрузки цеха в процентах
        - Автоматический пересчет дат при изменении приоритета
        - Уведомления об изменении плана (в течение 30 минут)
        - Экспорт плана в формат PDF
        """)
        
        # Таблица-заглушка для демонстрации структуры данных
        mock_plan = pd.DataFrame({
            "Заказ": ["PO-001", "PO-002", "PO-003"],
            "Модель": ["Худи Базовое", "Футболка Classic", "Брюки Карго"],
            "Приоритет": ["Высокий", "Средний", "Низкий"],
            "Плановая дата начала": [
                datetime.now().strftime("%d.%m.%Y"),
                (datetime.now() + timedelta(days=2)).strftime("%d.%m.%Y"),
                (datetime.now() + timedelta(days=5)).strftime("%d.%m.%Y")
            ],
            "Загрузка цеха": ["75%", "60%", "45%"]
        })
        st.dataframe(data=mock_plan, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Изменение приоритета заказа")
        
        # [STUB_MARKER] Заглушка для R-PL-2, R-PL-4
        st.info("[STUB_MARKER] Функционал изменения приоритета находится в разработке.", icon="ℹ️")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox(label="Выберите заказ", options=["PO-001", "PO-002", "PO-003"], key="planning_order", disabled=True)
        with col2:
            st.selectbox(label="Новый приоритет", options=["Высокий", "Средний", "Низкий"], key="planning_priority", disabled=True)
        st.button(label="Пересчитать план", disabled=True, type="primary")
    
    # ========================================================================
    # КОНТЕКСТ: ПРОИЗВОДСТВО (Требования R-PR-1, R-PR-2, R-PR-3, R-PR-4, R-PR-7, R-PR-8)
    # ========================================================================
    elif context == "🏭 Производство":
        st.title("🏭 Контекст: Производство")
        st.markdown("---")
        
        # [IMPLEMENTED] УЧЕТ БРАКА (Требования R-PR-2, R-PR-3, R-PR-8)
        st.subheader("Учет брака в партии")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            total_items = st.number_input(
                label="Всего изделий в партии",
                min_value=1,
                value=100,
                help="Общее количество изделий в производственной партии",
                key="prod_total"
            )
        with col2:
            defect_items = st.number_input(
                label="Количество брака (шт)",
                min_value=0,
                value=0,
                help="Количество изделий с дефектами",
                key="prod_defect"
            )
        with col3:
            # [IMPLEMENTED] Автоматический расчет процента брака (Требование R-PR-3)
            if total_items > 0:
                defect_percent = (defect_items / total_items) * 100
                st.metric(
                    label="Процент брака",
                    value=f"{defect_percent:.2f}%",
                    delta=None
                )
        
        # [IMPLEMENTED] Сигнал Технологи при браке > 5% (Требование R-PR-8)
        if total_items > 0 and 'defect_percent' in locals() and defect_percent > 5:
            st.error(
                body="⚠️ ВНИМАНИЕ ТЕХНОЛОГУ: Брак превысил 5%! Требуется немедленное вмешательство.",
                icon="🚨"
            )
        elif total_items > 0 and 'defect_percent' in locals():
            st.success(
                body="✅ Партия в норме. Уровень брака в допустимых пределах.",
                icon="✅"
            )
        
        st.markdown("---")
        
        # [IMPLEMENTED] ОТМЕТКА СТАТУСА ОПЕРАЦИИ (Требование R-PR-1, R-PR-7)
        st.subheader("Статус производственной операции")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            operation_status = st.radio(
                label="Статус выполнения операции",
                options=["В работе", "Выполнено", "На проверке ОТК"],
                horizontal=True,
                key="prod_status"
            )
        with col2:
            quantity_completed = st.number_input(
                label="Количество изделий",
                min_value=0,
                value=0,
                key="prod_qty"
            )
        
        # [IMPLEMENTED] Сохранение записи (Требование R-PR-7: время ≤ 1 сек)
        if st.button("Сохранить статус операции", type="primary"):
            # [STUB_MARKER] Здесь будет запись в базу данных
            # TODO: Реализовать сохранение в PostgreSQL/Google Sheets
            st.session_state.last_save_time = datetime.now()
            st.toast(body="Статус операции сохранен", icon="✅")
        
        st.markdown("---")
        
        # [STUB_MARKER] ИСТОРИЯ ОПЕРАЦИЙ (Требование R-PR-6)
        st.subheader("История операций")
        st.info(
            body="[STUB_MARKER] Функционал истории операций находится в разработке. "
            "Здесь будет отображаться журнал выполненных операций с возможностью экспорта и фильтрации.",
            icon="ℹ️"
        )
        
        # [STUB_MARKER] Таблица-заглушка для демонстрации структуры данных
        mock_data = pd.DataFrame({
            "Дата": [datetime.now().strftime("%d.%m.%Y")] * 3,
            "Операция": ["Раскрой", "Пошив", "Контроль качества"],
            "Исполнитель": ["Иванов А.А.", "Петрова Б.Б.", "Сидоров В.В."],
            "Статус": ["Выполнено", "В работе", "Ожидает"],
            "Количество": [100, 85, 0]
        })
        st.dataframe(data=mock_data, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
