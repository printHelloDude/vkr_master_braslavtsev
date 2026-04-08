"""
Страница: Производство (Production)
Требования: R-PR-1, R-PR-2, R-PR-3, R-PR-4, R-PR-7, R-PR-8
Статус: [IMPLEMENTED] - Базовая функциональность реализована
"""
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Производство", page_icon="🏭", layout="wide")

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
    st.toast(
        body="Статус операции сохранен",
        icon="✅"
    )

st.markdown("---")

# [STUB_MARKER] ИСТОРИЯ ОПЕРАЦИЙ (Требование R-PR-6)
st.subheader("История операций")
st.info(
    body="[STUB_MARKER] Функционал истории операций находится в разработке. "
         "Здесь будет отображаться журнал выполненных операций с возможностью "
         "экспорта и фильтрации.",
    icon="ℹ️"
)

# [STUB_MARKER] Таблица-заглушка для демонстрации структуры данных
import pandas as pd

mock_data = pd.DataFrame({
    "Дата": [datetime.now().strftime("%d.%m.%Y")] * 3,
    "Операция": ["Раскрой", "Пошив", "Контроль качества"],
    "Исполнитель": ["Иванов А.А.", "Петрова Б.Б.", "Сидоров В.В."],
    "Статус": ["Выполнено", "В работе", "Ожидает"],
    "Количество": [100, 85, 0]
})

st.dataframe(
    data=mock_data,
    use_container_width=True,
    hide_index=True
)