import streamlit as st
import pandas as pd
from datetime import datetime

# --- НАСТРОЙКИ СТРАНИЦЫ (R-PR-4: Мобильная адаптивность) ---
st.set_page_config(page_title="СУП Легкой Промышленности", layout="centered")

# --- ЗАГОЛОВОК ---
st.title("🧵 Прототип СУП Легкой Промышленности")
st.markdown("Версия прототипа 0.1 (MVP)")

# --- БОКОВАЯ ПАНЕЛЬ (Навигация по Контекстам из Раздела 4) ---
st.sidebar.header("Навигация")
context = st.sidebar.selectbox(
    "Выберите контекст:",
    ["Главная", "Конструирование (Design)", "Планирование (Planning)", "Производство (Production)"]
)

# --- КОНТЕКСТ: ГЛАВНАЯ ---
if context == "Главная":
    st.info("Добро пожаловать в прототип системы управления.")
    st.write("Выберите контекст в меню слева для начала работы.")

# --- КОНТЕКСТ: КОНСТРУИРОВАНИЕ (Заглушка) ---
elif context == "Конструирование (Design)":
    st.header("📐 Контекст: Конструирование")
    st.write("Здесь будут требования R-DE-1...R-DE-7 (Загрузка лекал, версии ТЗ).")
    st.warning("Функционал в разработке...")

# --- КОНТЕКСТ: ПЛАНИРОВАНИЕ (Заглушка) ---
elif context == "Планирование (Planning)":
    st.header("📅 Контекст: Планирование")
    st.write("Здесь будут требования R-PL-1...R-PL-7 (Календарный план, уведомления).")
    st.warning("Функционал в разработке...")

# --- КОНТЕКСТ: ПРОИЗВОДСТВО (Рабочий код) ---
elif context == "Производство (Production)":
    st.header("🏭 Контекст: Производство")
    
    # Требование R-PR-2: Фиксация дефектов
    st.subheader("Учет брака в партии")
    
    col1, col2 = st.columns(2)
    with col1:
        total_items = st.number_input("Всего изделий в партии", min_value=1, value=100, help="Общее количество")
    with col2:
        defect_items = st.number_input("Количество брака (шт)", min_value=0, value=0, help="Найдено дефектов")
    
    # Требование R-PR-3: Автоматический расчет процента брака
    if total_items > 0:
        defect_percent = (defect_items / total_items) * 100
        st.metric(label="Процент брака", value=f"{defect_percent:.2f}%")
        
        # Требование R-PR-8: Сигнал Технологи при браке > 5%
        if defect_percent > 5:
            st.error("⚠️ ВНИМАНИЕ ТЕХНОЛОГУ! Брак превысил 5%! Требуется вмешательство.")
            st.balloons() # Визуальный эффект для демонстрации
        else:
            st.success("✅ Партия в норме.")
            
    # Требование R-PR-1: Отметка статуса
    st.divider()
    st.subheader("Статус операции")
    status = st.radio("Статус выполнения:", ["В работе", "Выполнено", "На проверке ОТК"])
    if st.button("Сохранить статус"):
        st.toast("Статус сохранен! (Требование R-PR-7)")

# --- ПОДВАЛ (Системная информация) ---
st.sidebar.markdown("---")
st.sidebar.caption(f"Время сессии: {datetime.now().strftime('%H:%M')}")