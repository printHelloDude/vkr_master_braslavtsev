"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 1.0.2 — Добавлено количество партии в ТЗ, авто-QC, обновление загрузки
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

def init_session_state():
    """Инициализация хранилища данных в памяти."""
    if 'tech_specs' not in st.session_state:
        st.session_state.tech_specs = []
    if 'orders' not in st.session_state:
        st.session_state.orders = []
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
    if 'selected_ts' not in st.session_state:
        st.session_state.selected_ts = None
    if 'qc_order' not in st.session_state:
        st.session_state.qc_order = None

# ============================================================================
# === 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============================================
# ============================================================================

def get_next_id(items: List) -> int:
    """Получить следующий ID."""
    if not items:
        return 1
    return max(item.get('id', 0) for item in items) + 1

def calculate_defect_rate(defects: int, total: int) -> float:
    """[R-PR-3] Расчет процента брака."""
    if total <= 0:
        return 0.0
    return round((defects / total) * 100, 2)

def recalc_dates(priority: str) -> Dict[str, str]:
    """[R-PL-2] Пересчет дат по приоритету."""
    now = datetime.now()
    offsets = {"Высокий": 2, "Средний": 5, "Низкий": 10}
    offset = offsets.get(priority, 5)
    start = now + timedelta(days=offset)
    end = start + timedelta(days=14)
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }

def calculate_workshop_load(orders: List) -> float:
    """Рассчитать загруженность цеха на основе прошедших QC заказов."""
    total_qty = sum(order.get('qty', 0) for order in orders if order.get('qc_status') == 'passed')
    # Номинальная мощность цеха - 500 изделий
    capacity = 500
    return min((total_qty / capacity) * 100, 100) if capacity > 0 else 0

# ============================================================================
# === 3. СТРАНИЦЫ ПРИЛОЖЕНИЯ =================================================
# ============================================================================

def login_page():
    """[R-SY-1] Страница входа."""
    st.title("🔐 Вход в систему")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Логин", placeholder="admin / planner / tech / sewer / qc")
        if st.button("Войти", type="primary", use_container_width=True):
            if username.strip():
                st.session_state.authenticated = True
                st.session_state.current_user = username.strip()
                st.session_state.last_activity = datetime.now()
                st.rerun()
            else:
                st.error("Введите логин")
    
    with col2:
        if st.button("Войти как гость", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.current_user = "Гость"
            st.session_state.last_activity = datetime.now()
            st.rerun()

def design_page():
    """Контекст: Конструирование [R-DE-1..7]."""
    st.title("📐 Конструирование")
    
    tab1, tab2 = st.tabs(["📋 Реестр ТЗ", "➕ Создать ТЗ"])
    
    with tab1:
        st.subheader("Технические задания")
        if not st.session_state.tech_specs:
            st.info("⚠️ Нет технических заданий. Создайте первое.")
        else:
            for ts in st.session_state.tech_specs:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{ts['article']}**")
                        st.caption(ts['name'])
                    with col2:
                        status_emoji = {"draft": "📝", "approved": "✅", "archived": "📦"}.get(ts['status'], "📄")
                        st.markdown(f"{status_emoji} **Статус:** {ts['status']}")
                        st.caption(f"Версия: v{ts.get('version', 1)}")
                    with col3:
                        if st.button("📄 Открыть", key=f"open_{ts['id']}", use_container_width=True):
                            st.session_state.selected_ts = ts
                        if ts['status'] != 'approved':
                            if st.button("✅ Утвердить", key=f"app_{ts['id']}", use_container_width=True):
                                ts['status'] = 'approved'
                                st.success(f"ТЗ {ts['article']} утверждено")
                                st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_{ts['id']}", use_container_width=True):
                            ts['status'] = 'archived'
                            st.success("ТЗ архивировано")
                            st.rerun()
    
    with tab2:
        st.subheader("➕ Создать техническое задание")
        with st.form("create_ts", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                article = st.text_input("Артикул *", placeholder="T-001")
                name = st.text_input("Наименование *", placeholder="Худи")
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки"])
            
            # [НОВОЕ] Количество в партии
            batch_qty = st.number_input("Количество в партии (шт)", min_value=50, value=100, step=10)
            
            if st.form_submit_button("💾 Создать", type="primary", use_container_width=True):
                if not article or not name:
                    st.error("Артикул и наименование обязательны")
                else:
                    new_ts = {
                        "id": get_next_id(st.session_state.tech_specs),
                        "article": article,
                        "name": name,
                        "season": season,
                        "category": category,
                        "status": "draft",
                        "version": 1,
                        "batch_qty": batch_qty,  # [НОВОЕ] Сохраняем количество партии
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "patterns": []
                    }
                    st.session_state.tech_specs.append(new_ts)
                    st.success(f"✅ ТЗ {article} создано!")
                    st.rerun()

    # Детали ТЗ
    if st.session_state.selected_ts:
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts['article']} — {ts['name']}")
        
        if ts['status'] == 'approved':
            st.error("🔒 Утвержденное ТЗ. Редактирование заблокировано.")
        
        # [R-DE-1] Загрузка лекал
        st.subheader("📎 Загрузка лекал")
        with st.form("upload_pattern", clear_on_submit=True):
            file = st.file_uploader("Файл (DXF/PDF)", type=['pdf', 'dxf'])
            if st.form_submit_button("Загрузить", use_container_width=True):
                if file:
                    if file.size > 50 * 1024 * 1024:
                        st.error("Файл > 50 МБ")
                    else:
                        ts['patterns'].append({
                            "filename": file.name,
                            "size": file.size,
                            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success("✅ Лекало загружено")
                        st.rerun()
                else:
                    st.error("Выберите файл")
        
        if ts['patterns']:
            st.write("**Загруженные лекала:**")
            for p in ts['patterns']:
                st.caption(f"📄 {p['filename']} ({p['size'] / 1024:.1f} KB)")

def planning_page():
    """Контекст: Планирование [R-PL-1..7]."""
    st.title("📅 Планирование")
    
    # [R-PL-1] Только утвержденные ТЗ
    approved_ts = [ts for ts in st.session_state.tech_specs if ts['status'] == 'approved']
    
    tab1, tab2 = st.tabs(["📋 План производства", "➕ Добавить заказ"])
    
    with tab1:
        st.subheader("Календарный план")
        if not st.session_state.orders:
            st.info("Нет заказов в плане")
        else:
            # [R-PL-3] Визуализация загрузки - считаем только прошедшие QC заказы
            load_percent = calculate_workshop_load(st.session_state.orders)
            st.metric("Загрузка цеха (прошедшие QC)", f"{load_percent:.1f}%", 
                     delta=f"{sum(o.get('qty', 0) for o in st.session_state.orders if o.get('qc_status') == 'passed')}/500 ед.")
            st.progress(load_percent / 100)
            
            for order in st.session_state.orders:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order['article']}**")
                        st.caption(f"Приоритет: {order['priority']} | Партия: {order.get('qty', 0)} шт.")
                    with col2:
                        st.caption(f"Начало: {order['start_date']}")
                        st.caption(f"Конец: {order['end_date']}")
                    with col3:
                        qc_status = order.get('qc_status', 'pending')
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        elif qc_status == 'failed':
                            st.error("❌ Брак")
                        else:
                            st.warning("⏳ Ожидает QC")
                        
                        if st.button("📝 Изменить", key=f"prio_{order['id']}"):
                            new_prio = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"], 
                                                  key=f"sel_{order['id']}")
                            dates = recalc_dates(new_prio)
                            order['priority'] = new_prio
                            order['start_date'] = dates['start_date']
                            order['end_date'] = dates['end_date']
                            st.success("План пересчитан")
                            st.rerun()

    with tab2:
        if not approved_ts:
            st.warning("⚠️ Нет утвержденных ТЗ")
        else:
            st.info("✅ Доступны только утвержденные ТЗ")
            with st.form("add_order", clear_on_submit=True):
                ts_options = {f"{ts['article']} - {ts['name']}": ts for ts in approved_ts}
                selected = st.selectbox("Выберите ТЗ", list(ts_options.keys()))
                priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                
                # Количество берется из ТЗ (но можно изменить)
                selected_ts = ts_options[selected]
                qty = st.number_input("Количество в заказе", min_value=50, 
                                     value=selected_ts.get('batch_qty', 100))
                
                if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                    ts = ts_options[selected]
                    dates = recalc_dates(priority)
                    new_order = {
                        "id": get_next_id(st.session_state.orders),
                        "tech_spec_id": ts['id'],
                        "article": ts['article'],
                        "priority": priority,
                        "qty": qty,  # Количество из формы
                        "start_date": dates['start_date'],
                        "end_date": dates['end_date'],
                        "status": "planned",
                        "qc_status": "pending",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.orders.append(new_order)
                    st.success("✅ Заказ добавлен в план")
                    st.rerun()

def production_page():
    """Контекст: Производство [R-PR-1..8]."""
    st.title("🏭 Производство")
    tab1, tab2 = st.tabs(["🧵 Пошив", "🔍 Контроль качества"])

    with tab1:
        st.info("📌 Пошив доступен только после QC")
        
        # Показываем только заказы, прошедшие QC
        passed_qc_orders = [o for o in st.session_state.orders if o.get('qc_status') == 'passed']
        
        if not passed_qc_orders:
            st.info("Нет заказов, прошедших QC")
        else:
            for order in passed_qc_orders:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 2])
                    with col1:
                        st.markdown(f"**{order['article']}**")
                        st.caption(f"Заказ #{order['id']} | Партия: {order.get('qty', 0)} шт.")
                    with col2:
                        st.success("✅ QC пройден")
                    with col3:
                        if st.button("🧵 Пошив", key=f"sew_{order['id']}", use_container_width=True):
                            qty = st.number_input("Выполнено", min_value=1, value=10, 
                                                key=f"qty_{order['id']}")
                            st.success(f"✅ Записано: {qty} шт.")
                            st.rerun()

    with tab2:
        st.subheader("🔍 Контроль качества [R-PR-2, R-PR-3, R-PR-8]")
        
        # [ИЗМЕНЕНО] Показываем только заказы, ожидающие QC
        pending_orders = [o for o in st.session_state.orders if o.get('qc_status') == 'pending']
        
        if not pending_orders:
            st.info("Нет заказов на контроль качества")
        else:
            for order in pending_orders:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{order['article']}** (Заказ #{order['id']})")
                        st.caption(f"Партия: {order.get('qty', 0)} шт.")
                    with col2:
                        if st.button("🔍 Проверить", key=f"qc_{order['id']}"):
                            st.session_state.qc_order = order
                            st.rerun()
        
        # Форма QC
        if st.session_state.qc_order:
            order = st.session_state.qc_order
            st.subheader(f"🔍 QC: {order['article']}")
            
            with st.form("qc_form", clear_on_submit=True):
                # [ИЗМЕНЕНО] Показываем количество из заказа (read-only)
                st.info(f"📦 Количество в партии: **{order.get('qty', 0)} шт.**")
                
                defects = st.number_input("Обнаружено дефектов", min_value=0, 
                                         max_value=order.get('qty', 0), value=0)
                
                # [R-PR-3] Авто расчет % брака
                rate = calculate_defect_rate(defects, order.get('qty', 1))
                st.info(f"📊 Брак: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    # [R-PR-8] Алерт при браке > 5%
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        st.error(f"🚨 БРАК >5%! Технологу отправлен сигнал")
                    else:
                        order['qc_status'] = 'passed'
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    order['defect_rate'] = rate
                    st.session_state.qc_order = None
                    st.rerun()

def main():
    """Главная функция."""
    st.set_page_config(page_title="Легпром Управление", layout="wide")
    init_session_state()
    
    # Проверка таймаута [R-SY-2]
    if st.session_state.authenticated and st.session_state.last_activity:
        inactive = datetime.now() - st.session_state.last_activity
        if inactive > timedelta(minutes=30):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.warning("⏰ Сессия завершена")
            st.rerun()
        st.session_state.last_activity = datetime.now()

    if not st.session_state.authenticated:
        login_page()
        return

    # Сайдбар
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.markdown("---")
        page = st.radio("Навигация", 
                       ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
                       label_visibility="collapsed")
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        st.caption("Версия: 1.0.2 (In-Memory)")

    # Роутинг
    if page == "🏠 Главная":
        st.title("🏭 Система управления предприятием")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        st.markdown("---")
        st.info("✅ Прототип готов к работе")
        st.markdown("""
        ### Реализованные функции:
        - **Конструирование**: Создание ТЗ с количеством партии, загрузка лекал, утверждение
        - **Планирование**: Добавление заказов, приоритеты, пересчет дат, загрузка цеха
        - **Производство**: Контроль качества (авто-количество), пошив, учет брака
        """)
    elif page == "📐 Конструирование":
        design_page()
    elif page == "📅 Планирование":
        planning_page()
    elif page == "🏭 Производство":
        production_page()

if __name__ == "__main__":
    main()
