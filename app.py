"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 3.1.4 STABLE — Исправлена загрузка цеха (учет по единицам, лимит 500)
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

# Константы
MAX_SHOP_CAPACITY = 500  # Максимальная загрузка цеха в единицах
WARNING_CAPACITY_THRESHOLD = 0.8  # Порог предупреждения (80%)

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

def calculate_current_load() -> int:
    """Рассчитать текущую загрузку цеха (сумма всех активных заказов)."""
    total = 0
    for order in st.session_state.orders:
        # Считаем только активные заказы (не архивные)
        if order.get('status') != 'archived':
            total += order.get('qty', 0)
    return total

def get_capacity_percentage() -> float:
    """Получить процент загрузки цеха."""
    current_load = calculate_current_load()
    return (current_load / MAX_SHOP_CAPACITY) * 100

def is_capacity_available(qty: int = 0) -> bool:
    """Проверить, есть ли место для нового заказа."""
    current_load = calculate_current_load()
    return (current_load + qty) <= MAX_SHOP_CAPACITY

def get_available_capacity() -> int:
    """Получить доступную мощность цеха."""
    current_load = calculate_current_load()
    return max(0, MAX_SHOP_CAPACITY - current_load)

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
                            st.rerun()
                        if ts.get('status') != 'approved':
                            if st.button("✅ Утвердить", key=f"app_{ts.get('id')}", use_container_width=True):
                                ts['status'] = 'approved'
                                st.success(f"ТЗ {ts.get('article')} утверждено")
                                st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_{ts.get('id')}", use_container_width=True):
                            ts['status'] = 'archived'
                            st.success("ТЗ архивировано")
                            st.rerun()
    
    # ДЕТАЛИ ТЗ — показ карточки с документами
    if st.session_state.get('selected_ts'):
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts.get('article', 'N/A')} — {ts.get('name', '')}")
        
        # Блокировка после утверждения
        if ts.get('status') == 'approved':
            st.error("🔒 Утвержденное ТЗ. Редактирование заблокировано.")
        
        # [R-DE-1] Загрузка документов ТЗ (только если не утверждено)
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
                                "data": file.getvalue(),  # Сохраняем для скачивания
                                "size": file.size,
                                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            st.success(f"✅ {doc_type} загружен")
                            st.rerun()
                    else:
                        st.error("Выберите файл")
        else:
            st.info("📌 Загрузка документов заблокирована (ТЗ утверждено)")
        
        # Отображение загруженных документов с возможностью скачивания
        if ts.get('documents'):
            st.write("**Загруженные документы:**")
            for i, doc in enumerate(ts['documents']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"📄 {doc.get('type', 'Document')} — {doc.get('filename', 'unknown')} ({doc.get('size', 0) / 1024:.1f} KB)")
                with col2:
                    # Кнопка скачивания
                    st.download_button(
                        label="⬇️ Скачать",
                        data=doc.get('data', b''),
                        file_name=doc.get('filename', 'file.pdf'),
                        mime="application/pdf",
                        key=f"dl_{ts.get('id')}_{i}",
                        use_container_width=True
                    )
        
        # Кнопка закрытия
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
                        "documents": []  # Отдельно храним документы
                    }
                    st.session_state.tech_specs.append(new_ts)
                    st.success(f"✅ ТЗ {article} создан!")
                    st.rerun()

def planning_page():
    """Контекст: Планирование [R-PL-1..7]."""
    st.title("📅 Планирование")
    
    # [R-PL-1] Только утвержденные ТЗ
    approved_ts = [ts for ts in st.session_state.tech_specs if ts.get('status') == 'approved']
    
    # Расчет загрузки цеха
    current_load = calculate_current_load()
    capacity_pct = get_capacity_percentage()
    available_capacity = get_available_capacity()
    
    tab1, tab2 = st.tabs(["📋 План производства", "➕ Добавить заказ"])
    
    with tab1:
        st.subheader("Календарный план")
        
        # ИНДИКАТОР ЗАГРУЗКИ ЦЕХА — ИСПРАВЛЕНО
        st.metric("Загрузка цеха", f"{current_load} / {MAX_SHOP_CAPACITY} ед. ({capacity_pct:.1f}%)")
        
        # Визуальная индикация загрузки
        if capacity_pct >= 100:
            st.error(f"🚨 ЦЕХ ПОЛНОСТЬЮ ЗАГРУЖЕН! Доступно: 0 ед.")
            st.progress(1.0)
        elif capacity_pct >= WARNING_CAPACITY_THRESHOLD * 100:
            st.warning(f"⚠️ ВЫСОКАЯ ЗАГРУЗКА! Осталось мест: {available_capacity} ед.")
            st.progress(capacity_pct / 100)
        else:
            st.success(f"✅ Доступно для заказов: {available_capacity} ед.")
            st.progress(capacity_pct / 100)
        
        if not st.session_state.orders:
            st.info("Нет заказов в плане")
        else:
            for order in st.session_state.orders:
                # Пропускаем архивные заказы
                if order.get('status') == 'archived':
                    continue
                    
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order.get('article', 'N/A')}**")
                        st.caption(f"Приоритет: {order.get('priority', 'Средний')}")
                        # ИНДИКАТОР КОЛИЧЕСТВА
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
                        
                        # КНОПКА ИЗМЕНИТЬ ПРИОРИТЕТ
                        if st.button("📝 Изменить", key=f"prio_{order.get('id')}", use_container_width=True):
                            new_prio = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"], 
                                                  key=f"sel_{order.get('id')}")
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
            # ПРОВЕРКА ДОСТУПНОЙ МОЩНОСТИ
            if available_capacity <= 0:
                st.error("🚨 НЕВОЗМОЖНО ДОБАВИТЬ ЗАКАЗ! Цех полностью загружен (500/500 ед.)")
                st.info("💡 Сначала закройте выполненные заказы или удалите ненужные.")
            else:
                st.info(f"✅ Доступно для заказов: {available_capacity} из {MAX_SHOP_CAPACITY} ед.")
                
                with st.form("add_order", clear_on_submit=True):
                    ts_options = {f"{ts.get('article')} - {ts.get('name')}": ts for ts in approved_ts}
                    selected = st.selectbox("Выберите ТЗ", list(ts_options.keys()))
                    priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                    
                    # Ограничение по количеству с учетом доступной мощности
                    max_qty = min(available_capacity, 500)  # Не больше 500 за раз
                    qty = st.number_input("Количество в партии", 
                                        min_value=50, 
                                        max_value=max_qty,
                                        value=min(100, max_qty))
                    
                    # Предупреждение если заказ превышает доступную мощность
                    if qty > available_capacity:
                        st.error(f"⚠️ Заказ ({qty} ед.) превышает доступную мощность ({available_capacity} ед.)")
                    
                    # РУЧНОЙ ВВОД ДАТ
                    start_date = st.date_input("Дата начала производства", 
                                              value=datetime.now() + timedelta(days=7))
                    end_date = st.date_input("Дата окончания производства",
                                            value=datetime.now() + timedelta(days=21))
                    
                    if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                        # ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ДОБАВЛЕНИЕМ
                        if not is_capacity_available(qty):
                            st.error(f"❌ НЕДОСТАТОЧНО МОЩНОСТИ! Доступно: {available_capacity} ед., требуется: {qty} ед.")
                            st.info("💡 Закройте выполненные заказы или уменьшите количество.")
                        else:
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
                            st.success(f"✅ Заказ добавлен в план! Осталось мест: {get_available_capacity()} ед.")
                            st.rerun()

def production_page():
    """Контекст: Производство [R-PR-1..8]."""
    st.title("🏭 Производство")
    tab1, tab2 = st.tabs(["🧵 Пошив", "🔍 Контроль качества"])

    with tab1:
        st.info("📌 Пошив доступен только после QC")
        
        if not st.session_state.orders:
            st.info("Нет заказов.")
        else:
            for order in st.session_state.orders:
                # Пропускаем архивные заказы
                if order.get('status') == 'archived':
                    continue
                    
                # БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ДАННЫХ
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
                        # ИНДИКАТОР БРАКА (если QC пройден)
                        if qc_status == 'passed' and defect_rate > 0:
                            if defect_rate > 5.0:
                                st.error(f"🚨 Брак: **{defect_rate}%**")
                            else:
                                st.success(f"✅ Брак: {defect_rate}% (норма)")
                    with col2:
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        else:
                            st.warning("🚫 QC не пройден")
                    with col3:
                        # [R-PR-5] Блокировка без QC
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
                    st.info(f"📊 Освобождено мощности: {order.get('qty', 0)} ед. Доступно: {get_available_capacity()} ед.")
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
        
        # ФОРМА QC
        if st.session_state.get('qc_order'):
            order = st.session_state.qc_order
            article = order.get('article', 'N/A')
            order_qty = order.get('qty', 100)  # БЕРЕМ КОЛИЧЕСТВО ИЗ ЗАКАЗА!
            
            st.subheader(f"🔍 QC: {article}")
            
            with st.form("qc_form", clear_on_submit=True):
                # [ИСПРАВЛЕНО] По умолчанию количество из заказа
                total = st.number_input("Всего изделий", min_value=1, value=order_qty)
                defects = st.number_input("Обнаружено дефектов", min_value=0, value=0)
                
                # [R-PR-3] Авто расчет % брака
                rate = calculate_defect_rate(defects, total)
                
                # Визуальная индикация
                if rate > 5.0:
                    st.error(f"🚨 КРИТИЧЕСКИЙ БРАК: **{rate}%** (порог 5%)")
                elif rate > 3.0:
                    st.warning(f"⚠️ Повышенный брак: **{rate}%**")
                else:
                    st.success(f"✅ Брак в норме: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    # [R-PR-8] Алерт при браке > 5%
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        st.error(f"🚨 БРАК >5%! Технологу отправлен сигнал")
                        # Добавляем уведомление
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
    
    # ДАШБОРД — метрики и статистика
    st.subheader("📊 Оперативная сводка")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Метрики
    total_orders = len([o for o in st.session_state.orders if o.get('status') != 'archived'])
    approved_ts = len([ts for ts in st.session_state.tech_specs if ts.get('status') == 'approved'])
    archived_orders = len([o for o in st.session_state.orders if o.get('status') == 'archived'])
    current_load = calculate_current_load()
    capacity_pct = get_capacity_percentage()
    
    with col1:
        st.metric("📋 Всего ТЗ", approved_ts, delta=f"из {len(st.session_state.tech_specs)}")
    with col2:
        st.metric("📅 Активных заказов", total_orders)
    with col3:
        st.metric("📦 Завершено", archived_orders)
    with col4:
        st.metric("⏳ Загрузка цеха", f"{capacity_pct:.0f}%", delta=f"{current_load}/{MAX_SHOP_CAPACITY} ед.")
    
    st.markdown("---")
    
    # Загрузка цеха — визуализация
    st.subheader("🏭 Загрузка производственных мощностей")
    
    if capacity_pct >= 100:
        st.error("🚨 ЦЕХ ПОЛНОСТЬЮ ЗАГРУЖЕН!")
        st.progress(1.0)
    elif capacity_pct >= WARNING_CAPACITY_THRESHOLD * 100:
        st.warning(f"⚠️ Высокая загрузка! Осталось: {get_available_capacity()} ед.")
        st.progress(capacity_pct / 100)
    else:
        st.success(f"✅ Доступно: {get_available_capacity()} из {MAX_SHOP_CAPACITY} ед.")
        st.progress(capacity_pct / 100)
    
    # Уведомления
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
        st.caption("Версия: 3.1.4 STABLE")

    # Роутинг
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
