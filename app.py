"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.3.0 (Единое приложение)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.
[STUB_MARKER] - обозначает заглушку для последующей реализации
[IMPLEMENTED] - обозначает реализованный функционал
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# ============================================================================
# НАСТРОЙКИ СТРАНИЦЫ
# ============================================================================
st.set_page_config(
    page_title="СУ Легкой Промышленности",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ
# ============================================================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Главная"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ============================================================================
# ФУНКЦИИ НАВИГАЦИИ
# ============================================================================
def set_page(page_name):
    st.session_state.current_page = page_name

def logout():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.current_page = "Главная"
    st.rerun()

# ============================================================================
# КОМПОНЕНТ АУТЕНТИФИКАЦИИ
# ============================================================================
def check_authentication():
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

# ============================================================================
# СТРАНИЦА: ГЛАВНАЯ
# ============================================================================
def page_main():
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

---

**Выберите раздел в левом меню для начала работы.**
""")

# ============================================================================
# СТРАНИЦА: КОНСТРУИРОВАНИЕ
# ============================================================================
def page_design():
    st.title("📐 Контекст: Конструирование")
    st.markdown("---")
    
    st.subheader("Загрузка технического пакета")
    
    st.info("""
**[STUB_MARKER]** Функционал загрузки лекал находится в разработке.

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
    st.info("[STUB_MARKER] Функционал согласования находится в разработке.", icon="ℹ️")
    st.text_area(label="Комментарии к техническому пакету", key="design_comments", disabled=True)
    st.button(label="Отправить на согласование", disabled=True, type="primary")

# ============================================================================
# СТРАНИЦА: ПЛАНИРОВАНИЕ
# ============================================================================
def page_planning():
    st.title("📅 Контекст: Планирование")
    st.markdown("---")
    
    st.subheader("Календарный план производства")
    
    st.info("""
**[STUB_MARKER]** Функционал календарного планирования находится в разработке.

Планируемая функциональность:
- Формирование календарного плана на основе заказов
- Отображение загрузки цеха в процентах
- Автоматический пересчет дат при изменении приоритета
- Уведомления об изменении плана (в течение 30 минут)
- Экспорт плана в формат PDF
""")
    
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
    st.info("[STUB_MARKER] Функционал изменения приоритета находится в разработке.", icon="ℹ️")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(label="Выберите заказ", options=["PO-001", "PO-002", "PO-003"], key="planning_order", disabled=True)
    with col2:
        st.selectbox(label="Новый приоритет", options=["Высокий", "Средний", "Низкий"], key="planning_priority", disabled=True)
    
    st.button(label="Пересчитать план", disabled=True, type="primary")

# ============================================================================
# СТРАНИЦА: ПРОИЗВОДСТВО
# ============================================================================
def page_production():
    st.title("🏭 Контекст: Производство")
    st.markdown("---")
    
    # УЧЕТ БРАКА
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
        if total_items > 0:
            defect_percent = (defect_items / total_items) * 100
            st.metric(
                label="Процент брака",
                value=f"{defect_percent:.2f}%",
                delta=None
            )
    
    if total_items > 0 and defect_percent > 5:
        st.error(
            body="ВНИМАНИЕ ТЕХНОЛОГУ: Брак превысил 5%! Требуется немедленное вмешательство.",
            icon="🚨"
        )
    elif total_items > 0:
        st.success(
            body="Партия в норме. Уровень брака в допустимых пределах.",
            icon="✅"
        )
    
    st.markdown("---")
    
    # СТАТУС ОПЕРАЦИИ
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
    
    if st.button("Сохранить статус операции", type="primary"):
        st.session_state.last_save_time = datetime.now()
        st.toast(body="Статус операции сохранен", icon="✅")
    
    st.markdown("---")
    
    # ИСТОРИЯ ОПЕРАЦИЙ
    st.subheader("История операций")
    st.info(
        body="[STUB_MARKER] Функционал истории операций находится в разработке. "
             "Здесь будет отображаться журнал выполненных операций с возможностью "
             "экспорта и фильтрации.",
        icon="ℹ️"
    )
    
    mock_data = pd.DataFrame({
        "Дата": [datetime.now().strftime("%d.%m.%Y")] * 3,
        "Операция": ["Раскрой", "Пошив", "Контроль качества"],
        "Исполнитель": ["Иванов А.А.", "Петрова Б.Б.", "Сидоров В.В."],
        "Статус": ["Выполнено", "В работе", "Ожидает"],
        "Количество": [100, 85, 0]
    })
    
    st.dataframe(data=mock_data, use_container_width=True, hide_index=True)

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================
def main():
    # Проверка аутентификации
    if not check_authentication():
        return
    
    # Сайдбар с навигацией
    with st.sidebar:
        st.markdown(f"**Пользователь:** {st.session_state.get('current_user', 'Гость')}")
        st.markdown("---")
        
        # Кнопки навигации
        st.button("🏠 Главная", use_container_width=True, on_click=set_page, args=("Главная",))
        st.button("📐 Конструирование", use_container_width=True, on_click=set_page, args=("Конструирование",))
        st.button("📅 Планирование", use_container_width=True, on_click=set_page, args=("Планирование",))
        st.button("🏭 Производство", use_container_width=True, on_click=set_page, args=("Производство",))
        
        st.markdown("---")
        st.button("Выйти", use_container_width=True, on_click=logout)
        st.caption("Версия прототипа: 0.3.0")
    
    # Отображение текущей страницы
    current_page = st.session_state.current_page
    
    if current_page == "Главная":
        page_main()
    elif current_page == "Конструирование":
        page_design()
    elif current_page == "Планирование":
        page_planning()
    elif current_page == "Производство":
        page_production()

if __name__ == "__main__":
    main()
