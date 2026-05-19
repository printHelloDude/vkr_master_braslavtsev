"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 1.0.3 — Добавлен контроль брака >5% с алертом технологу
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
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []

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

def add_notification(msg: str, level: str = "info"):
    """Добавить уведомление."""
    st.session_state.notifications.append({
        "msg": msg,
        "level": level,
        "time": datetime.now().strftime("%H:%M")
    })

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
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "patterns": []
                    }
                    st.session_state.tech_specs.append(new_ts)
                    st.success(f"✅ ТЗ {article} создан!")
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
            # [R-PL-3] Визуализация загрузки
            st.metric("Загрузка цеха", f"{min(len(st.session_state.orders) * 15, 100)}%")
            
            for order in st.session_state.orders:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order['article']}**")
                        st.caption(f"Приоритет: {order['priority']}")
                    with col2:
                        st.caption(f"Начало: {order['start_date']}")
                        st.caption(f"Конец: {order['end_date']}")
                    with col3:
                        qc_status = order.get('qc_status', 'pending')
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
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
                qty = st.number_input("Количество", min_value=50, value=100)
                
                if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                    ts = ts_options[selected]
                    dates = recalc_dates(priority)
                    new_order = {
                        "id": get_next_id(st.session_state.orders),
                        "tech_spec_id": ts['id'],
                        "article": ts['article'],
                        "priority": priority,
                        "qty": qty,
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
        
        for order in st.session_state.orders:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.markdown(f"**{order['article']}**")
                    st.caption(f"Заказ #{order['id']}")
                with col2:
                    if order.get('qc_status') == 'passed':
                        st.success("✅ QC пройден")
                    else:
                        st.warning("🚫 QC не пройден")
                with col3:
                    # [R-PR-5] Блокировка без QC
                    disabled = order.get('qc_status') != 'passed'
                    if st.button("🧵 Пошив", key=f"sew_{order['id']}", 
                               disabled=disabled, use_container_width=True):
                        qty = st.number_input("Выполнено", min_value=1, value=10, 
                                            key=f"qty_{order['id']}")
                        st.success(f"✅ Записано: {qty} шт.")
                        st.rerun()

    with tab2:
        st.subheader("🔍 Контроль качества [R-PR-2, R-PR-3, R-PR-8]")
        
        planned_orders = [o for o in st.session_state.orders if o['status'] == 'planned']
        
        for order in planned_orders:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{order['article']}** (Заказ #{order['id']})")
                with col2:
                    if st.button("🔍 Проверить", key=f"qc_{order['id']}"):
                        st.session_state.qc_order = order
                        st.rerun()
        
        if 'qc_order' in st.session_state:
            order = st.session_state.qc_order
            st.subheader(f"🔍 QC: {order['article']}")
            
            with st.form("qc_form", clear_on_submit=True):
                total = st.number_input("Всего изделий", min_value=1, value=100)
                defects = st.number_input("Дефекты", min_value=0, value=0)
                
                # [R-PR-3] Авто расчет % брака
                rate = calculate_defect_rate(defects, total)
                
                # [R-PR-8] Визуальная индикация уровня брака
                if rate > 5.0:
                    st.error(f"🚨 КРИТИЧЕСКИЙ БРАК: **{rate}%** (порог 5%)")
                    st.warning("⚠️ Требуется немедленное вмешательство технолога!")
                elif rate > 3.0:
                    st.warning(f"⚠️ Повышенный брак: **{rate}%** (рекомендуемый порог 3%)")
                else:
                    st.success(f"✅ Брак в норме: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    # [R-PR-8] Алерт при браке > 5%
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        # Сигнал технологу
                        add_notification(
                            f"🚨 БРАК >5%! Заказ {order['article']}: {rate}% брака. Требуется вмешательство технолога!",
                            "error"
                        )
                        st.error(f"🚨 БРАК >5%! Технологу отправлен сигнал")
                        st.warning("Заказ отклонен. Требуется анализ причин брака.")
                    else:
                        order['qc_status'] = 'passed'
                        add_notification(f"Заказ {order['article']} прошел QC (брак {rate}%)", "info")
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    order['defect_rate'] = rate
                    del st.session_state.qc_order
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
        
        # Уведомления [R-PL-4, R-PR-8]
        if st.session_state.notifications:
            st.markdown("**🔔 Уведомления:**")
            for n in st.session_state.notifications[-5:]:
                if n['level'] == 'error':
                    st.error(f"🕐 {n['time']} - {n['msg']}", icon="🚨")
                elif n['level'] == 'warning':
                    st.warning(f"🕐 {n['time']} - {n['msg']}", icon="⚠️")
                else:
                    st.info(f"🕐 {n['time']} - {n['msg']}", icon="ℹ️")
        
        st.caption("Версия: 1.0.3 (In-Memory)")

    # Роутинг
    if page == "🏠 Главная":
        st.title("🏭 Система управления предприятием")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        st.markdown("---")
        st.info("✅ Прототип готов к работе")
        st.markdown("""
        ### Реализованные функции:
        - **Конструирование**: Создание ТЗ, загрузка лекал, утверждение
        - **Планирование**: Добавление заказов, приоритеты, пересчет дат
        - **Производство**: 
          - 🧵 Пошив (после QC)
          - 🔍 Контроль качества с авто-расчетом % брака
          - 🚨 Алерт технологу при браке >5%
        """)
    elif page == "📐 Конструирование":
        design_page()
    elif page == "📅 Планирование":
        planning_page()
    elif page == "🏭 Производство":
        production_page()

if __name__ == "__main__":
    main()
