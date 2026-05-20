"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 3.1.3 STABLE — Восстановлен контроль брака, архивация заказов
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

def init_session_state():
    """Инициализация хранилища данных в памяти."""
    defaults = {
        'tech_specs': [],
        'orders': [],
        'authenticated': False,
        'current_user': None,
        'last_activity': datetime.now(),
        'selected_ts': None,
        'editing_order_id': None,
        'qc_order': None,
        'notifications': [],
        'selected_production_order': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

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
                        st.markdown(f"**{ts.get('article', 'N/A')}**")
                        st.caption(ts.get('name', ''))
                    with col2:
                        status_emoji = {"draft": "📝", "approved": "✅", "archived": "📦"}.get(ts.get('status', 'draft'), "📄")
                        st.markdown(f"{status_emoji} **Статус:** {ts.get('status', 'draft')}")
                        st.caption(f"Версия: v{ts.get('version', 1)}")
                    with col3:
                        if st.button("📄 Открыть", key=f"open_{ts.get('id')}", use_container_width=True):
                            st.session_state.selected_ts = ts
                        if ts.get('status') != 'approved':
                            if st.button("✅ Утвердить", key=f"app_{ts.get('id')}", use_container_width=True):
                                ts['status'] = 'approved'
                                st.success(f"ТЗ {ts.get('article')} утверждено")
                                st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_{ts.get('id')}", use_container_width=True):
                            ts['status'] = 'archived'
                            st.success("ТЗ архивировано")
                            st.rerun()
    
    # ДЕТАЛИ ТЗ
    if st.session_state.get('selected_ts'):
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts.get('article', 'N/A')} — {ts.get('name', '')}")
        
        if ts.get('status') == 'approved':
            st.error("🔒 Утвержденное ТЗ. Редактирование заблокировано.")
        
        st.subheader("📄 Документация ТЗ")
        if ts.get('status') != 'approved':
            with st.form("upload_ts_doc", clear_on_submit=True):
                doc_type = st.selectbox("Тип документа", ["Техническое задание (ТЗ)", "Лекала"])
                file = st.file_uploader("Файл (DXF/PDF)", type=['pdf', 'dxf'])
                if st.form_submit_button("Загрузить", use_container_width=True):
                    if file:
                        if file.size > 50 * 1024 * 1024:
                            st.error("Файл > 50 МБ")
                        else:
                            if 'documents' not in ts:
                                ts['documents'] = []
                            ts['documents'].append({
                                "type": doc_type,
                                "filename": file.name,
                                "data": file.getvalue(),
                                "size": file.size,
                                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            st.success(f"✅ {doc_type} загружен")
                            st.rerun()
                    else:
                        st.error("Выберите файл")
        else:
            st.info("📌 Загрузка документов заблокирована (ТЗ утверждено)")
        
        if ts.get('documents'):
            st.write("**Загруженные документы:**")
            for i, doc in enumerate(ts['documents']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"📄 {doc.get('type', 'Document')} — {doc.get('filename', 'unknown')} ({doc.get('size', 0) / 1024:.1f} KB)")
                with col2:
                    st.download_button(
                        label="⬇️ Скачать",
                        data=doc.get('data', b''),
                        file_name=doc.get('filename', 'file.pdf'),
                        mime="application/pdf",
                        key=f"dl_{ts.get('id')}_{i}",
                        use_container_width=True
                    )
        
        if st.button("← Закрыть карточку", key=f"close_{ts.get('id')}"):
            st.session_state.selected_ts = None
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
                        "documents": []
                    }
                    st.session_state.tech_specs.append(new_ts)
                    st.success(f"✅ ТЗ {article} создан!")
                    st.rerun()

def planning_page():
    """Контекст: Планирование [R-PL-1..7]."""
    st.title("📅 Планирование")
    
    approved_ts = [ts for ts in st.session_state.tech_specs if ts.get('status') == 'approved']
    
    tab1, tab2 = st.tabs(["📋 План производства", "➕ Добавить заказ"])
    
    with tab1:
        st.subheader("Календарный план")
        if not st.session_state.orders:
            st.info("Нет заказов в плане")
        else:
            st.metric("Загрузка цеха", f"{min(len(st.session_state.orders) * 15, 100)}%")
            
            for order in st.session_state.orders:
                if order.get('status') == 'archived':
                    continue
                    
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order.get('article', 'N/A')}**")
                        st.caption(f"Приоритет: {order.get('priority', 'Средний')}")
                        st.info(f"📦 **{order.get('qty', 0)} шт.** в партии")
                    with col2:
                        st.caption(f"Начало: {order.get('start_date', 'N/A')}")
                        st.caption(f"Конец: {order.get('end_date', 'N/A')}")
                    with col3:
                        qc_status = order.get('qc_status', 'pending')
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        else:
                            st.warning("⏳ Ожидает QC")
                        
                        if st.button("📝 Изменить", key=f"edit_btn_{order.get('id')}", use_container_width=True):
                            st.session_state.editing_order_id = order.get('id')
                            st.rerun()
    
    if st.session_state.editing_order_id is not None:
        order_to_edit = None
        for order in st.session_state.orders:
            if order.get('id') == st.session_state.editing_order_id:
                order_to_edit = order
                break
        
        if order_to_edit:
            st.subheader(f"📝 Изменение заказа: {order_to_edit.get('article', 'N/A')}")
            
            with st.form("edit_order_form", clear_on_submit=False):
                priorities = ["Высокий", "Средний", "Низкий"]
                current_priority = order_to_edit.get('priority', 'Средний')
                current_idx = priorities.index(current_priority) if current_priority in priorities else 1
                new_priority = st.selectbox("Новый приоритет", priorities, index=current_idx)
                
                current_start = order_to_edit.get('start_date', datetime.now().strftime("%Y-%m-%d"))
                current_end = order_to_edit.get('end_date', (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"))
                
                try:
                    start_date_val = datetime.strptime(current_start, "%Y-%m-%d")
                    end_date_val = datetime.strptime(current_end, "%Y-%m-%d")
                except:
                    start_date_val = datetime.now()
                    end_date_val = datetime.now() + timedelta(days=14)
                
                new_start = st.date_input("Дата начала", value=start_date_val)
                new_end = st.date_input("Дата окончания", value=end_date_val)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Сохранить", type="primary", use_container_width=True):
                        order_to_edit['priority'] = new_priority
                        order_to_edit['start_date'] = new_start.strftime("%Y-%m-%d")
                        order_to_edit['end_date'] = new_end.strftime("%Y-%m-%d")
                        st.success("✅ Изменения сохранены!")
                        st.session_state.editing_order_id = None
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                        st.session_state.editing_order_id = None
                        st.rerun()

    with tab2:
        if not approved_ts:
            st.warning("⚠️ Нет утвержденных ТЗ")
        else:
            st.info("✅ Доступны только утвержденные ТЗ")
            with st.form("add_order", clear_on_submit=True):
                ts_options = {f"{ts.get('article')} - {ts.get('name')}": ts for ts in approved_ts}
                selected = st.selectbox("Выберите ТЗ", list(ts_options.keys()))
                priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                qty = st.number_input("Количество", min_value=50, value=100)
                
                start_date = st.date_input("Дата начала производства", 
                                          value=datetime.now() + timedelta(days=7))
                end_date = st.date_input("Дата окончания производства",
                                        value=datetime.now() + timedelta(days=21))
                
                if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                    ts = ts_options[selected]
                    new_order = {
                        "id": get_next_id(st.session_state.orders),
                        "tech_spec_id": ts.get('id'),
                        "article": ts.get('article'),
                        "priority": priority,
                        "qty": qty,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
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
        
        active_orders = [o for o in st.session_state.orders if o.get('status') != 'archived']
        
        if not active_orders:
            st.info("Нет активных заказов.")
        else:
            for order in active_orders:
                article = order.get('article', 'N/A')
                order_id = order.get('id', 0)
                qty = order.get('qty', 0)
                qc_status = order.get('qc_status', 'pending')
                defect_rate = order.get('defect_rate', 0.0)
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 2])
                    with col1:
                        st.markdown(f"**{article}**")
                        st.caption(f"Заказ #{order_id} | Партия: {qty} шт.")
                        
                        # ИНДИКАТОР БРАКА — ВОССТАНОВЛЕНО
                        if qc_status == 'passed':
                            if defect_rate > 0:
                                if defect_rate > 5.0:
                                    st.error(f"🚨 Брак: **{defect_rate}%** (ПРЕВЫШЕНИЕ!)")
                                else:
                                    st.success(f"✅ Брак: {defect_rate}% (норма)")
                            else:
                                st.success("✅ Брак: 0% (идеально)")
                    
                    with col2:
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        else:
                            st.warning("🚫 QC не пройден")
                    
                    with col3:
                        disabled = qc_status != 'passed'
                        if st.button("✅ Закрыть заказ", key=f"sew_{order_id}", 
                                   disabled=disabled, use_container_width=True):
                            st.session_state.selected_production_order = order
                            st.rerun()
    
    # ФОРМА ЗАКРЫТИЯ ЗАКАЗА
    if st.session_state.get('selected_production_order'):
        order = st.session_state.selected_production_order
        st.subheader(f"✅ Закрытие заказа: {order.get('article', 'N/A')}")
        
        with st.form("sewing_form", clear_on_submit=True):
            sewn_qty = st.number_input("Фактически выполнено (шт)", min_value=1, value=order.get('qty', 10))
            worker = st.text_input("Швея", value=st.session_state.current_user)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Закрыть заказ", type="primary", use_container_width=True):
                    if 'sewing_records' not in order:
                        order['sewing_records'] = []
                    order['sewing_records'].append({
                        "qty": sewn_qty,
                        "worker": worker,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    order['status'] = 'archived'
                    order['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.success(f"✅ Заказ закрыт! Выполнено: {sewn_qty} шт. (швея: {worker})")
                    st.session_state.selected_production_order = None
                    st.rerun()
            with col2:
                if st.form_submit_button("❌ Отмена", use_container_width=True):
                    st.session_state.selected_production_order = None
                    st.rerun()

    with tab2:
        st.subheader("🔍 Контроль качества [R-PR-2, R-PR-3, R-PR-8]")
        
        planned_orders = [o for o in st.session_state.orders if o.get('status') == 'planned']
        
        for order in planned_orders:
            article = order.get('article', 'N/A')
            order_id = order.get('id', 0)
            order_qty = order.get('qty', 100)
            
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{article}** (Заказ #{order_id})")
                    st.caption(f"Партия: {order_qty} шт.")
                with col2:
                    if st.button("🔍 Проверить", key=f"qc_{order_id}"):
                        st.session_state.qc_order = order
                        st.rerun()
        
        if st.session_state.get('qc_order'):
            order = st.session_state.qc_order
            article = order.get('article', 'N/A')
            order_qty = order.get('qty', 100)
            
            st.subheader(f"🔍 QC: {article}")
            
            with st.form("qc_form", clear_on_submit=True):
                total = st.number_input("Всего изделий", min_value=1, value=order_qty)
                defects = st.number_input("Обнаружено дефектов", min_value=0, value=0)
                
                rate = calculate_defect_rate(defects, total)
                
                if rate > 5.0:
                    st.error(f"🚨 КРИТИЧЕСКИЙ БРАК: **{rate}%** (порог 5%)")
                elif rate > 3.0:
                    st.warning(f"⚠️ Повышенный брак: **{rate}%**")
                else:
                    st.success(f"✅ Брак в норме: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        st.error(f"🚨 БРАК >5%! Технологу отправлен сигнал")
                        st.session_state.notifications.append({
                            "msg": f"🚨 БРАК {rate}% в заказе {article}!",
                            "time": datetime.now().strftime("%H:%M"),
                            "level": "error"
                        })
                    else:
                        order['qc_status'] = 'passed'
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    order['defect_rate'] = rate
                    st.session_state.qc_order = None
                    st.rerun()

def main_dashboard():
    """Главная страница с дашбордом."""
    st.title("🏭 Система управления предприятием")
    st.success(f"Добро пожаловать, {st.session_state.current_user}!")
    st.markdown("---")
    
    st.subheader("📊 Оперативная сводка")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_orders = len(st.session_state.orders)
    approved_ts = len([ts for ts in st.session_state.tech_specs if ts.get('status') == 'approved'])
    active_orders = len([o for o in st.session_state.orders if o.get('status') != 'archived'])
    archived_orders = len([o for o in st.session_state.orders if o.get('status') == 'archived'])
    
    with col1:
        st.metric("📋 Всего ТЗ", approved_ts, delta=f"из {len(st.session_state.tech_specs)}")
    with col2:
        st.metric("📅 Активных заказов", active_orders)
    with col3:
        st.metric("📦 Завершено", archived_orders)
    with col4:
        st.metric("⏳ Ожидает QC", len([o for o in st.session_state.orders if o.get('qc_status') == 'pending']))
    
    st.markdown("---")
    
    if active_orders > 0:
        capacity = min(active_orders * 15, 100)
        st.progress(capacity / 100)
        st.caption(f"Текущая загрузка: {capacity}%")
    else:
        st.info("📌 Нет активных заказов")
    
    if st.session_state.notifications:
        st.markdown("---")
        st.subheader("🔔 Последние уведомления")
        for n in st.session_state.notifications[-5:]:
            if n.get('level') == 'error':
                st.error(f"🕐 {n.get('time')} - {n.get('msg')}", icon="🚨")
            else:
                st.info(f"🕐 {n.get('time')} - {n.get('msg')}", icon="ℹ️")

def main():
    """Главная функция."""
    st.set_page_config(page_title="Легпром Управление", layout="wide")
    init_session_state()
    
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
        st.caption("Версия: 3.1.3 STABLE")

    if page == "🏠 Главная":
        main_dashboard()
    elif page == "📐 Конструирование":
        design_page()
    elif page == "📅 Планирование":
        planning_page()
    elif page == "🏭 Производство":
        production_page()

if __name__ == "__main__":
    main()
