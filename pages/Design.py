"""
Страница: Конструирование (Design)
Требования: R-DE-1...R-DE-7
"""
import streamlit as st

st.set_page_config(page_title="Конструирование", page_icon="📐", layout="wide")

st.title("📐 Контекст: Конструирование")
st.markdown("---")

st.subheader("Загрузка технического пакета")

# [STUB_MARKER] Заглушка для R-DE-1, R-DE-2
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