"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 4.0.0 — ПЕРЕРАБОТАНА СИСТЕМА ВЕРСИЙ (правильная логика)
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

MAX_SHOP_CAPACITY = 500
WARNING_CAPACITY_THRESHOLD = 0.8

def init_session_state():
    """Инициализация хранилища с ПРАВИЛЬНОЙ структурой версий."""
    defaults = {
        'tech_specs': [],           # Реестр технических заданий (изделий)
        'versions': [],             # ВСЕ версии (каждая версия = ТЗ + набор документов)
        'orders': [],
        'authenticated': False,
        'current_user': None,
        'last_activity': datetime.now(),
        'selected_ts': None,        # Выбранное ТЗ (изделие)
        'selected_version': None,   # Выбранная версия для просмотра/редактирования
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
    if not items:
        return 1
    return max(item.get('id', 0) for item in items) + 1

def get_next_version_number(ts_id: int) -> int:
    """Получить следующий номер версии для ТЗ."""
    ts_versions = [v for v in st.session_state.versions if v.get('tech_spec_id') == ts_id]
    if not ts_versions:
        return 1
    return max(v.get('version_number', 0) for v in ts_versions) + 1

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
    """Рассчитать текущую загрузку цеха."""
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

def create_new_version(ts_id: int, created_by: str, base_version_id: Optional[int] = None) -> int:
    """
    Создать НОВУЮ версию ТЗ.
    Если base_version_id указан — копируем документы из этой версии.
    Возвращает ID новой версии.
    """
    version_number = get_next_version_number(ts_id)
    
    new_version = {
        'id': get_next_id(st.session_state.versions),
        'tech_spec_id': ts_id,
        'version_number': version_number,
        'status': 'draft',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'created_by': created_by,
        'approved_at': None,
        'documents': [],  # Список документов (ТЗ + лекала)
        'changes_description': ''  # Описание изменений
    }
    
    # Если есть базовая версия — копируем документы
    if base_version_id:
        base_version = next((v for v in st.session_state.versions if v.get('id') == base_version_id), None)
        if base_version:
            # Копируем документы (глубокое копирование)
            for doc in base_version.get('documents', []):
                new_version['documents'].append({
                    'id': get_next_id(new_version['documents']),
                    'type': doc.get('type'),
                    'filename': doc.get('filename'),
                    'data': doc.get('data'),
                    'size': doc.get('size'),
                    'uploaded_at': doc.get('uploaded_at')
                })
            new_version['changes_description'] = f"Копия версии {base_version.get('version_number')}"
    
    st.session_state.versions.append(new_version)
    return new_version['id']

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
    """
    Контекст: Конструирование [R-DE-1..7].
    ПРАВИЛЬНАЯ ЛОГИКА ВЕРСИЙ:
    - ТЗ (изделие) → список версий
    - Каждая версия = ТЗ документ + набор лекал
    - Утвержденную версию нельзя менять
    - Новая версия = копия + изменения
    """
    st.title("📐 Конструирование")
    
    tab1, tab2 = st.tabs(["📋 Реестр изделий (ТЗ)", "➕ Создать новое ТЗ"])
    
    # === TAB 1: РЕЕСТР ИЗДЕЛИЙ ===
    with tab1:
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
                        # Показываем последнюю версию
                        ts_versions = [v for v in st.session_state.versions 
                                      if v.get('tech_spec_id') == ts.get('id')]
                        if ts_versions:
                            last_ver = max(ts_versions, key=lambda x: x.get('version_number', 0))
                            status_emoji = {"draft": "📝", "approved": "✅", "archived": "📦"}.get(last_ver.get('status'), "📄")
                            st.markdown(f"{status_emoji} **Последняя версия:** v{last_ver.get('version_number')} ({last_ver.get('status')})")
                            st.caption(f"Всего версий: {len(ts_versions)}")
                    with col3:
                        if st.button("📄 Открыть", key=f"open_ts_{ts.get('id')}", use_container_width=True):
                            st.session_state.selected_ts = ts
                            st.session_state.selected_version = None
                            st.rerun()
                        if st.button("➕ Новая версия", key=f"new_ver_{ts.get('id')}", use_container_width=True):
                            # Создаем новую версию на основе последней
                            ts_versions = sorted([v for v in st.session_state.versions 
                                                 if v.get('tech_spec_id') == ts.get('id')], 
                                                key=lambda x: x.get('version_number', 0))
                            base_id = ts_versions[-1].get('id') if ts_versions else None
                            new_ver_id = create_new_version(ts.get('id'), st.session_state.current_user, base_id)
                            st.success(f"✅ Создана версия v{get_next_version_number(ts.get('id')) - 1}")
                            st.rerun()
    
    # === ДЕТАЛИ ТЗ И ВЕРСИЙ ===
    if st.session_state.get('selected_ts'):
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts.get('article')} — {ts.get('name')}")
        
        # Показываем все версии этого ТЗ
        ts_versions = sorted([v for v in st.session_state.versions 
                             if v.get('tech_spec_id') == ts.get('id')], 
                            key=lambda x: x.get('version_number', 0), reverse=True)
        
        st.markdown("### 📚 Версии")
        
        # Кнопка создания новой версии
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Создать версию", use_container_width=True):
                base_id = ts_versions[0].get('id') if ts_versions else None
                new_ver_id = create_new_version(ts.get('id'), st.session_state.current_user, base_id)
                st.success("✅ Новая версия создана!")
                st.rerun()
        
        for ver in ts_versions:
            with st.container(border=True):
                ver_col1, ver_col2, ver_col3 = st.columns([2, 3, 2])
                with ver_col1:
                    status_emoji = {"draft": "📝", "approved": "✅", "archived": "📦"}.get(ver.get('status'), "📄")
                    st.markdown(f"**{status_emoji} Версия v{ver.get('version_number')}**")
                    st.caption(f"Создана: {ver.get('created_at')}")
                    st.caption(f"Автор: {ver.get('created_by')}")
                    if ver.get('approved_at'):
                        st.caption(f"Утверждена: {ver.get('approved_at')}")
                
                with ver_col2:
                    docs = ver.get('documents', [])
                    st.markdown(f"**Документы ({len(docs)}):**")
                    for doc in docs:
                        doc_type = "📄 ТЗ" if doc.get('type') == 'tech_spec' else "✂️ Лекало"
                        st.caption(f"{doc_type}: {doc.get('filename', 'N/A')} ({doc.get('size', 0) / 1024:.1f} KB)")
                
                with ver_col3:
                    if ver.get('status') == 'draft':
                        if st.button("✅ Утвердить", key=f"approve_ver_{ver.get('id')}", use_container_width=True):
                            ver['status'] = 'approved'
                            ver['approved_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            st.success(f"✅ Версия v{ver.get('version_number')} утверждена!")
                            st.rerun()
                        if st.button("✏️ Редактировать", key=f"edit_ver_{ver.get('id')}", use_container_width=True):
                            st.session_state.selected_version = ver
                            st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_ver_{ver.get('id')}", use_container_width=True):
                            st.session_state.versions.remove(ver)
                            st.success("Версия удалена")
                            st.rerun()
                    elif ver.get('status') == 'approved':
                        st.info("🔒 Утверждена")
                        if st.button("👁️ Просмотр", key=f"view_ver_{ver.get('id')}", use_container_width=True):
                            st.session_state.selected_version = ver
                            st.rerun()
        
        # === РЕДАКТИРОВАНИЕ ВЕРСИИ ===
        if st.session_state.get('selected_version'):
            ver = st.session_state.selected_version
            if ver.get('status') != 'draft':
                st.error("🔒 Нельзя редактировать утвержденную версию! Создайте новую.")
                if st.button("← Закрыть"):
                    st.session_state.selected_version = None
                    st.rerun()
            else:
                st.markdown(f"### ✏️ Редактирование версии v{ver.get('version_number')}")
                
                # Загрузка документов
                with st.form("upload_doc_form", clear_on_submit=True):
                    doc_type = st.selectbox("Тип документа", ["tech_spec", "pattern"], 
                                           format_func=lambda x: "📄 Техническое задание" if x == "tech_spec" else "✂️ Лекало")
                    file = st.file_uploader("Файл (DXF/PDF, макс. 50MB)", type=['pdf', 'dxf'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("📎 Добавить документ", use_container_width=True):
                            if file:
                                if file.size > 50 * 1024 * 1024:
                                    st.error("Файл больше 50MB!")
                                else:
                                    ver['documents'].append({
                                        'id': get_next_id(ver['documents']),
                                        'type': doc_type,
                                        'filename': file.name,
                                        'data': file.getvalue(),
                                        'size': file.size,
                                        'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                    st.success("✅ Документ добавлен!")
                                    st.rerun()
                            else:
                                st.error("Выберите файл!")
                    with col2:
                        if st.form_submit_button("← Закрыть редактор", use_container_width=True):
                            st.session_state.selected_version = None
                            st.rerun()
                
                # Список документов с возможностью удаления
                if ver.get('documents'):
                    st.markdown("**Документы в версии:**")
                    for i, doc in enumerate(ver['documents']):
                        doc_col1, doc_col2 = st.columns([4, 1])
                        with doc_col1:
                            doc_type = "📄 ТЗ" if doc.get('type') == 'tech_spec' else "✂️ Лекало"
                            st.caption(f"{doc_type}: {doc.get('filename')} ({doc.get('size', 0) / 1024:.1f} KB)")
                        with doc_col2:
                            if st.button("🗑️", key=f"del_doc_{ver.get('id')}_{i}"):
                                ver['documents'].pop(i)
                                st.success("Документ удален")
                                st.rerun()
    
    # === TAB 2: СОЗДАНИЕ НОВОГО ТЗ ===
    with tab2:
        st.subheader("➕ Создать новое техническое задание")
        with st.form("create_ts_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                article = st.text_input("Артикул *", placeholder="T-001")
                name = st.text_input("Наименование *", placeholder="Худи")
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки"])
            
            if st.form_submit_button("💾 Создать ТЗ", type="primary", use_container_width=True):
                if not article or not name:
                    st.error("Артикул и наименование обязательны!")
                else:
                    new_ts = {
                        'id': get_next_id(st.session_state.tech_specs),
                        'article': article,
                        'name': name,
                        'season': season,
                        'category': category,
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.tech_specs.append(new_ts)
                    
                    # Автоматически создаем первую версию
                    create_new_version(new_ts['id'], st.session_state.current_user, None)
                    
                    st.success(f"✅ ТЗ {article} создано! Версия v1 готова.")
                    st.rerun()

def planning_page():
    """Контекст: Планирование [R-PL-1..7]."""
    st.title("📅 Планирование")
    approved_ts = [ts for ts in st.session_state.tech_specs 
                   if any(v.get('status') == 'approved' for v in st.session_state.versions 
                         if v.get('tech_spec_id') == ts.get('id'))]
    
    current_load = calculate_current_load()
    capacity_pct = get_capacity_percentage()
    available_capacity = get_available_capacity()
    
    if st.session_state.editing_order_id is not None:
        order_to_edit = next((o for o in st.session_state.orders 
                             if o.get('id') == st.session_state.editing_order_id), None)
        if order_to_edit:
            st.subheader(f"📝 Изменение заказа: {order_to_edit.get('article')}")
            with st.form("edit_order_form", clear_on_submit=False):
                priorities = ["Высокий", "Средний", "Низкий"]
                current_idx = priorities.index(order_to_edit.get('priority', 'Средний'))
                new_priority = st.selectbox("Новый приоритет", priorities, index=current_idx)
                
                try:
                    start_date_val = datetime.strptime(order_to_edit.get('start_date'), "%Y-%m-%d")
                    end_date_val = datetime.strptime(order_to_edit.get('end_date'), "%Y-%m-%d")
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
            st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 План производства", "➕ Добавить заказ"])
    
    with tab1:
        st.subheader("Календарный план")
        st.metric("Загрузка цеха", f"{current_load} / {MAX_SHOP_CAPACITY} ед. ({capacity_pct:.1f}%)")
        
        if capacity_pct >= 100:
            st.error("🚨 ЦЕХ ПОЛНОСТЬЮ ЗАГРУЖЕН!")
            st.progress(1.0)
        elif capacity_pct >= WARNING_CAPACITY_THRESHOLD * 100:
            st.warning(f"⚠️ ВЫСОКАЯ ЗАГРУЗКА! Осталось: {available_capacity} ед.")
            st.progress(capacity_pct / 100)
        else:
            st.success(f"✅ Доступно: {available_capacity} ед.")
            st.progress(capacity_pct / 100)
        
        if not st.session_state.orders:
            st.info("Нет заказов в плане")
        else:
            for order in st.session_state.orders:
                if order.get('status') == 'archived':
                    continue
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{order.get('article')}**")
                        st.caption(f"Приоритет: {order.get('priority')}")
                        st.info(f"📦 **{order.get('qty')} шт.** | Версия: v{order.get('version_number', 'N/A')}")
                    with col2:
                        st.caption(f"Начало: {order.get('start_date')}")
                        st.caption(f"Конец: {order.get('end_date')}")
                    with col3:
                        qc_status = order.get('qc_status', 'pending')
                        if qc_status == 'passed':
                            st.success("✅ QC пройден")
                        else:
                            st.warning("⏳ Ожидает QC")
                        if st.button("📝 Изменить", key=f"prio_{order.get('id')}", use_container_width=True):
                            st.session_state.editing_order_id = order.get('id')
                            st.rerun()
    
    with tab2:
        if not approved_ts:
            st.warning("⚠️ Нет утвержденных ТЗ")
        else:
            if available_capacity <= 0:
                st.error("🚨 НЕВОЗМОЖНО ДОБАВИТЬ ЗАКАЗ! Цех загружен")
            else:
                st.info(f"✅ Доступно: {available_capacity} из {MAX_SHOP_CAPACITY} ед.")
                with st.form("add_order_form", clear_on_submit=True):
                    # Выбор ТЗ и версии
                    ts_options = {}
                    for ts in approved_ts:
                        approved_versions = [v for v in st.session_state.versions 
                                            if v.get('tech_spec_id') == ts.get('id') and v.get('status') == 'approved']
                        for ver in approved_versions:
                            key = f"{ts.get('article')} - {ts.get('name')} (v{ver.get('version_number')})"
                            ts_options[key] = {'ts': ts, 'version': ver}
                    
                    selected_key = st.selectbox("Выберите ТЗ и версию", list(ts_options.keys()))
                    selected = ts_options[selected_key]
                    
                    priority = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
                    max_qty = min(available_capacity, 500)
                    qty = st.number_input("Количество", min_value=50, max_value=max_qty, value=min(100, max_qty))
                    
                    start_date = st.date_input("Дата начала", value=datetime.now() + timedelta(days=7))
                    end_date = st.date_input("Дата окончания", value=datetime.now() + timedelta(days=21))
                    
                    if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                        if not is_capacity_available(qty):
                            st.error(f"❌ Недостаточно мощности! Доступно: {available_capacity} ед.")
                        else:
                            new_order = {
                                'id': get_next_id(st.session_state.orders),
                                'tech_spec_id': selected['ts'].get('id'),
                                'version_id': selected['version'].get('id'),
                                'article': selected['ts'].get('article'),
                                'version_number': selected['version'].get('version_number'),
                                'priority': priority,
                                'qty': qty,
                                'start_date': start_date.strftime("%Y-%m-%d"),
                                'end_date': end_date.strftime("%Y-%m-%d"),
                                'status': 'planned',
                                'qc_status': 'pending',
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                        st.caption(f"Заказ #{order_id} | Партия: {qty} шт. | Версия: v{order.get('version_number', 'N/A')}")
                        if qc_status == 'passed' and defect_rate > 0:
                            if defect_rate > 5.0:
                                st.error(f"🚨 Брак: **{defect_rate}%**")
                            else:
                                st.success(f"✅ Брак: {defect_rate}%")
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
        
        if st.session_state.get('selected_production_order'):
            order = st.session_state.selected_production_order
            st.subheader(f"✅ Закрытие заказа: {order.get('article')}")
            with st.form("sewing_form", clear_on_submit=True):
                sewn_qty = st.number_input("Выполнено (шт)", min_value=1, value=order.get('qty', 10))
                worker = st.text_input("Швея", value=st.session_state.current_user)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Закрыть заказ", type="primary", use_container_width=True):
                        if 'sewing_records' not in order:
                            order['sewing_records'] = []
                        order['sewing_records'].append({
                            'qty': sewn_qty,
                            'worker': worker,
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        order['status'] = 'archived'
                        order['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success(f"✅ Заказ закрыт! Выполнено: {sewn_qty} шт.")
                        st.info(f"📊 Освобождено: {order.get('qty')} ед. Доступно: {get_available_capacity()} ед.")
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
                    st.markdown(f"**{article}** (Заказ #{order_id}) | Версия: v{order.get('version_number', 'N/A')}")
                    st.caption(f"Партия: {order_qty} шт.")
                with col2:
                    if st.button("🔍 Проверить", key=f"qc_{order_id}"):
                        st.session_state.qc_order = order
                        st.rerun()
        
        if st.session_state.get('qc_order'):
            order = st.session_state.qc_order
            article = order.get('article', 'N/A')
            order_qty = order.get('qty', 100)
            
            st.subheader(f"🔍 QC: {article} (v{order.get('version_number', 'N/A')})")
            with st.form("qc_form", clear_on_submit=True):
                total = st.number_input("Всего изделий", min_value=1, value=order_qty)
                defects = st.number_input("Дефектов", min_value=0, value=0)
                
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
                        st.error(f"🚨 БРАК >5%! Сигнал технологу!")
                        st.session_state.notifications.append({
                            'msg': f"🚨 БРАК {rate}% в заказе {article}!",
                            'time': datetime.now().strftime("%H:%M"),
                            'level': 'error'
                        })
                    else:
                        order['qc_status'] = 'passed'
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    order['defect_rate'] = rate
                    st.session_state.qc_order = None
                    st.rerun()
    
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
                        st.markdown(f"**{order.get('article')}**")
                        st.caption(f"Заказ #{order.get('id')} | v{order.get('version_number', 'N/A')} | {order.get('qty')} шт.")
                    with col2:
                        st.caption(f"Завершен: {order.get('completed_at', 'N/A')}")
                        st.caption(f"Брак: {order.get('defect_rate', 0.0)}%")
                    with col3:
                        if order.get('sewing_records'):
                            for record in order['sewing_records']:
                                st.success(f"✅ {record.get('qty')} шт. ({record.get('worker')})")
                                st.caption(f"🕐 {record.get('date')}")

def main_dashboard():
    """Главная страница."""
    st.title("🏭 Система управления предприятием")
    st.success(f"Добро пожаловать, {st.session_state.current_user}!")
    st.markdown("---")
    
    st.subheader("📊 Оперативная сводка")
    col1, col2, col3, col4 = st.columns(4)
    
    total_orders = len([o for o in st.session_state.orders if o.get('status') != 'archived'])
    approved_ts = len([ts for ts in st.session_state.tech_specs 
                      if any(v.get('status') == 'approved' for v in st.session_state.versions 
                            if v.get('tech_spec_id') == ts.get('id'))])
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
        st.error("🚨 ЦЕХ ЗАГРУЖЕН!")
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
        st.caption("Версия: 4.0.0 (ПРАВИЛЬНЫЕ ВЕРСИИ)")
    
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
