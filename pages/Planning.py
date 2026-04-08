"""
Страница: Планирование (Planning)
Требования: R-PL-1...R-PL-7
"""
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="Планирование", page_icon="📅", layout="wide")

st.title("📅 Контекст: Планирование")
st.markdown("---")

st.subheader("Календарный план производства")

# [STUB_MARKER] Заглушка для R-PL-1, R-PL-3
st.info("""
**[STUB_MARKER]** Функционал календарного планирования находится в разработке.

Планируемая функциональность:
- Формирование календарного плана на основе заказов
- Отображение загрузки цеха в процентах
- Автоматический пересчет дат при изменении приоритета
- Уведомления об изменении плана (в течение 30 минут)
- Экспорт плана в формат PDF
""")

# Таблица-заглушка
import pandas as pd

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