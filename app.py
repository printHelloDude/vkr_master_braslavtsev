"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 3.2.0 FINAL — Восстановлен функционал версий, убрано лишнее
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

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
        'qc_order': None,
        'notifications': [],
        'selected_production_order': None,
        'show_archived': False
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

def create_new_version(ts: Dict, created_by: str) -> int:
    """[R-DE-5] Создать новую версию ТЗ."""
    if 'versions' not in ts:
        ts['versions'] = []
    
    current_version = ts.get('version', 1)
    new_version_num = current_version + 1
    
    # Сохраняем текущую версию в историю
    version_record = {
        'version': current_version,
        'status': ts.get('status', 'draft'),
        'created_at': ts.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        'created_by': created_by,
        'documents': ts.get('documents', []).copy()
    }
    ts['versions'].append(version_record)
    
    # Храним только последние 5 версий [R-DE-5]
    if len(ts['versions']) > 5:
        ts['versions'] = ts['versions'][-5:]
    
    # Создаем новую версию
    ts['version'] = new_version_num
    ts['status'] = 'draft'
    ts['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts['documents'] = []
    
    return new_version_num

def rollback_version(ts: Dict, version_num: int) -> bool:
    """[R-DE-5] Откатиться к указанной версии."""
    if 'versions' not in ts or not ts['versions']:
        return False
    
    # Ищем версию
    target_version = None
    for v in ts['versions']:
        if v['version'] == version_num:
            target_version = v
            break
    
    if not target_version:
        return False
    
    # Восстанавливаем версию
    ts['status'] = target_version['status']
    ts['created_at'] = target_version['created_at']
    ts['documents'] = target_version['documents'].copy()
    ts['version'] = version_num
    
    return True

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
    
    # Фильтр по статусу [R-DE-3]
    status_filter = st.selectbox(
        "Статус",
        ["Все", "draft", "approved", "archived"],
        format_func=lambda x: {"Все": "Все", "draft": "📝 Черновик", "approved": "✅ Утверждено", "archived": "📦 Архив"}.get(x, x)
    )
    
    tab1, tab2 = st.tabs(["📋 Реестр ТЗ", "➕ Создать ТЗ"])
    
    with tab1:
        st.subheader("Технические задания")
        
        # Фильтрация
        filtered_specs = st.session_state.tech_specs
        if status_filter != "Все":
            filtered_specs = [ts for ts in filtered_specs if ts.get('status') == status_filter]
        
        if not filtered_specs:
            st.info("⚠️ Нет технических заданий. Создайте первое.")
        else:
            for ts in filtered_specs:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{ts.get('article', 'N/A')}**")
                        st.caption(ts.get('name', ''))
                    with col2:
                        status_emoji = {"draft": "📝", "approved": "✅", "archived": "📦"}.get(ts.get('status', 'draft'), "📄")
                        st.markdown(f"{status_emoji} **Статус:** {ts.get('status', 'draft')}")
                        st.caption(f"Версия: v{ts.get('version', 1)}")
                        
                        # [R-DE-3] Проверка времени согласования
                        if ts.get('status') == 'approved' and ts.get('approved_at'):
                            try:
                                approved_date = datetime.strptime(ts['approved_at'], "%Y-%m-%d")
                                days_since = (datetime.now() - approved_date).days
                                if days_since > 2:
                                    st.warning(f"⏳ Согласование >2 дней")
                            except:
                                pass
                    with col3:
                        if st.button("📄 Открыть", key=f"open_{ts.get('id')}", use_container_width=True):
                            st.session_state.selected_ts = ts
                            st.rerun()
                        if ts.get('status') != 'approved':
                            if st.button("✅ Утвердить", key=f"app_{ts.get('id')}", use_container_width=True):
                                ts['status'] = 'approved'
                                ts['approved_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                st.success(f"ТЗ {ts.get('article')} утверждено")
                                st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_{ts.get('id')}", use_container_width=True):
                            ts['status'] = 'archived'
                            st.success("ТЗ архивировано")
                            st.rerun()
    
    # ДЕТАЛИ ТЗ — показ карточки с версиями и документами
    if st.session_state.get('selected_ts'):
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts.get('article', 'N/A')} — {ts.get('name', '')}")
        
        # [R-DE-4] Блокировка после утверждения
        if ts.get('status') == 'approved':
            st.error("🔒 Утвержденное ТЗ. Для изменений создайте новую версию.")
            
            # Кнопка создания новой версии
            if st.button("📄 Создать новую версию", type="primary"):
                new_ver = create_new_version(ts, st.session_state.current_user)
                st.success(f"✅ Создана версия v{new_ver}")
                st.rerun()
        else:
            # Кнопка отката к предыдущей версии [R-DE-5]
            if 'versions' in ts and ts['versions']:
                st.markdown("### 📚 История версий")
                version_options = {f"v{v['version']} ({v['status']})": v['version'] for v in ts['versions']}
                selected_version = st.selectbox("Откатиться к версии:", list(version_options.keys()))
                if st.button("🔄 Откатиться"):
                    if rollback_version(ts, version_options[selected_version]):
                        st.success(f"✅ Откат к версии {version_options[selected_version]} выполнен")
                        st.rerun()
                    else:
                        st.error("❌ Ошибка отката")
        
        # [R-DE-1] Загрузка документов ТЗ
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
        
        # Отображение загруженных документов с возможностью скачивания
        if ts.get('documents'):
            st.write("**Загруженные документы:**")
            for i, doc in enumerate(ts['documents']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"📄 {doc.get('type', 'Document')} — {doc.get('filename', 'unknown')} ({doc.get('size', 0) / 1024:.1f} KB)")
                with col2:
                    st.download_button(
                        label="⬇️",
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
                        "documents": [],
                        "versions": []
                    }
                    st.session_state.tech_specs.append(new_ts)
                    st.success(f"✅ ТЗ {article} создан! Версия v1")
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
    
    # ИНДИКАТОР ЗАГРУЗКИ
    st.metric("Загрузка цеха", f"{current_load} / {MAX_SHOP_CAPACITY} ед. ({capacity_pct:.1f}%)")
    
    if capacity_pct >= 100:
        st.error(f"🚨 ЦЕХ ПОЛНОСТЬЮ ЗАГРУЖЕН!")
        st.progress(1.0)
    elif capacity_pct >= WARNING_CAPACITY_THRESHOLD * 100:
        st.warning(f"⚠️ ВЫСОКАЯ ЗАГРУЗКА! Осталось: {available_capacity} ед.")
        st.progress(capacity_pct / 100)
    else:
        st.success(f"✅ Доступно: {available_capacity} ед.")
        st.progress(capacity_pct / 100)
    
    tab1, tab2 = st.tabs(["📋 План производства", "➕ Добавить заказ"])
    
    with tab1:
        st.subheader("Календарный план")
        
        if not st.session_state.orders:
            st.info("Нет заказов в плане")
        else:
            for order in st.session_state.orders:
                if order.get('status') == 'archived':
                    continue
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order.get('article', 'N/A')}**")
                        st.caption(f"Приоритет: {order.get('priority', 'Средний')}")
                        st.info(f"📦 **{order.get('qty', 0)} шт.**")
                    with col2:
                        st.caption(f"Начало: {order.get('start_date', 'N/A')}")
                        st.caption(f"Конец: {order.get('end_date', 'N/A')}")
                    with col3:
                        qc_status = order.get('qc_status', 'pending')
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        elif qc_status == 'failed':
                            st.error("❌ Брак")
                        else:
                            st.warning("⏳ Ожидает QC")
                        
                        # Кнопка изменения приоритета [R-PL-2]
                        if st.button("📝 Изменить", key=f"prio_{order.get('id')}", use_container_width=True):
                            new_prio = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"], key=f"sel_{order.get('id')}")
                            dates = recalc_dates(new_prio)
                            order['priority'] = new_prio
                            order['start_date'] = dates['start_date']
                            order['end_date'] = dates['end_date']
                            st.success("План пересчитан")
                            # [R-PL-4] Уведомление
                            st.session_state.notifications.append({
                                "msg": f"Изменен приоритет заказа {order.get('article')}",
                                "time": datetime.now().strftime("%H:%M"),
                                "level": "info"
                            })
                            st.rerun()
    
    with tab2:
        if not approved_ts:
            st.warning("⚠️ Нет утвержденных ТЗ")
        else:
            if available_capacity <= 0:
                st.error("🚨 НЕВОЗМОЖНО ДОБАВИТЬ ЗАКАЗ! Цех полностью загружен")
            else:
                st.info(f"✅ Доступно: {available_capacity} из {MAX_SHOP_CAPACITY} ед.")
                
                with st.form("add_order", clear_on_submit=True):
                    ts_options = {f"{ts.get('article')} - {ts.get('name')}": ts for ts in approved_ts}
                    selected = st.selectbox("Выберите ТЗ", list(ts_options.keys()))
                    priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                    
                    max_qty = min(available_capacity, 500)
                    qty = st.number_input("Количество в партии", min_value=50, max_value=max_qty, value=min(100, max_qty))
                    
                    start_date = st.date_input("Дата начала", value=datetime.now() + timedelta(days=7))
                    end_date = st.date_input("Дата окончания", value=datetime.now() + timedelta(days=21))
                    
                    if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                        if not is_capacity_available(qty):
                            st.error(f"❌ НЕДОСТАТОЧНО МОЩНОСТИ! Доступно: {available_capacity} ед.")
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
                            st.success(f"✅ Заказ добавлен! Осталось: {get_available_capacity()} ед.")
                            st.rerun()

def production_page():
    """Контекст: Производство [R-PR-1..8]."""
    st.title("🏭 Производство")
    
    tab1, tab2, tab3 = st.tabs(["🧵 Пошив", "🔍 Контроль качества", "📦 Архив"])
    
    with tab1:
        st.info("📌 Пошив доступен только после QC")
        
        if not st.session_state.orders:
            st.info("Нет заказов.")
        else:
            for order in st.session_state.orders:
                if order.get('status') == 'archived':
                    continue
                
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
                        if qc_status == 'passed' and defect_rate > 0:
                            if defect_rate > 5.0:
                                st.error(f"🚨 Брак: **{defect_rate}%**")
                            else:
                                st.success(f"✅ Брак: {defect_rate}%")
                    with col2:
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        elif qc_status == 'failed':
                            st.error("❌ Брак")
                        else:
                            st.warning("🚫 QC не пройден")
                    with col3:
                        disabled = qc_status != 'passed'
                        if st.button("✅ Закрыть заказ", key=f"sew_{order_id}", disabled=disabled, use_container_width=True):
                            st.session_state.selected_production_order = order
                            st.rerun()
        
        # ФОРМА ЗАКРЫТИЯ ЗАКАЗА
        if st.session_state.get('selected_production_order'):
            order = st.session_state.selected_production_order
            st.subheader(f"✅ Закрытие заказа: {order.get('article', 'N/A')}")
            
            with st.form("sewing_form", clear_on_submit=True):
                sewn_qty = st.number_input("Выполнено (шт)", min_value=1, value=order.get('qty', 10))
                worker = st.text_input("Швея", value=st.session_state.current_user)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Закрыть", type="primary", use_container_width=True):
                        if 'sewing_records' not in order:
                            order['sewing_records'] = []
                        order['sewing_records'].append({
                            "qty": sewn_qty,
                            "worker": worker,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        order['status'] = 'archived'
                        order['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success(f"✅ Закрыт! Выполнено: {sewn_qty} шт.")
                        st.info(f"📊 Освобождено: {order.get('qty', 0)} ед. Доступно: {get_available_capacity()} ед.")
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
            order_qty = order.get('qty', 100)
            
            st.subheader(f"🔍 QC: {article}")
            
            with st.form("qc_form", clear_on_submit=True):
                total = st.number_input("Всего изделий", min_value=1, value=order_qty)
                defects = st.number_input("Дефектов", min_value=0, value=0)
                
                rate = calculate_defect_rate(defects, total)
                
                if rate > 5.0:
                    st.error(f"🚨 КРИТИЧЕСКИЙ БРАК: **{rate}%**")
                elif rate > 3.0:
                    st.warning(f"⚠️ Повышенный брак: **{rate}%**")
                else:
                    st.success(f"✅ Норма: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        st.error("🚨 БРАК >5%! Сигнал технологу")
                        st.session_state.notifications.append({
                            "msg": f"🚨 БРАК {rate}% в заказе {article}!",
                            "time": datetime.now().strftime("%H:%M"),
                            "level": "error"
                        })
                    else:
                        order['qc_status'] = 'passed'
                        st.success("✅ Допущено к пошиву")
                    
                    order['defect_rate'] = rate
                    st.session_state.qc_order = None
                    st.rerun()
    
    # ВКЛАДКА АРХИВ
    with tab3:
        st.subheader("📦 Архив завершенных заказов")
        
        archived_orders = [o for o in st.session_state.orders if o.get('status') == 'archived']
        
        if not archived_orders:
            st.info("📌 Нет завершенных заказов")
        else:
            st.success(f"✅ Найдено {len(archived_orders)} заказов")
            
            for order in archived_orders:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order.get('article', 'N/A')}**")
                        st.caption(f"Заказ #{order.get('id')} | {order.get('qty', 0)} шт.")
                    with col2:
                        st.caption(f"Завершен: {order.get('completed_at', 'N/A')}")
                        st.caption(f"Брак: {order.get('defect_rate', 0.0)}%")
                    with col3:
                        if order.get('sewing_records'):
                            for record in order['sewing_records']:
                                st.success(f"✅ {record.get('qty')} шт. ({record.get('worker', 'N/A')})")

def main_dashboard():
    """Главная страница с дашбордом."""
    st.title("🏭 Система управления предприятием")
    st.success(f"Добро пожаловать, {st.session_state.current_user}!")
    st.markdown("---")
    
    st.subheader("📊 Оперативная сводка")
    
    col1, col2, col3, col4 = st.columns(4)
    
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
    
    st.subheader("🏭 Загрузка мощностей")
    
    if capacity_pct >= 100:
        st.error("🚨 ЦЕХ ПОЛНОСТЬЮ ЗАГРУЖЕН!")
        st.progress(1.0)
    elif capacity_pct >= WARNING_CAPACITY_THRESHOLD * 100:
        st.warning(f"⚠️ Высокая загрузка! Осталось: {get_available_capacity()} ед.")
        st.progress(capacity_pct / 100)
    else:
        st.success(f"✅ Доступно: {get_available_capacity()} из {MAX_SHOP_CAPACITY} ед.")
        st.progress(capacity_pct / 100)
    
    if st.session_state.notifications:
        st.markdown("---")
        st.subheader("🔔 Уведомления")
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
        st.caption("Версия: 3.2.0 FINAL")
    
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
