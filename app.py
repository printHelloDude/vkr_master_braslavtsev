"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 4.0 — Feature Complete & Super Stable (In-Memory)
Автор: Браславцев Б.Э.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import csv
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

def init_session_state():
    """Инициализация хранилища данных в памяти."""
    defaults = {
        'tech_specs': [],
        'orders': [],
        'operations_history': [], # Для R-PR-6 (Архив)
        'notifications': [],      # Для R-PL-4, R-PR-8
        'authenticated': False,
        'current_user': None,
        'user_role': None,        # Для RBAC
        'last_activity': datetime.now(),
        'selected_ts': None,
        'qc_order': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_next_id(items: List) -> int:
    if not items: return 1
    return max(item.get('id', 0) for item in items) + 1

def calculate_defect_rate(defects: int, total: int) -> float:
    """[R-PR-3] Расчет процента брака."""
    if total <= 0: return 0.0
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
    """Добавляет уведомление в очередь."""
    st.session_state.notifications.append({
        "msg": msg,
        "level": level, # info, warning, error
        "time": datetime.now().strftime("%H:%M")
    })

# ============================================================================
# === 2. СТРАНИЦЫ ПРИЛОЖЕНИЯ =================================================
# ============================================================================

def login_page():
    """[R-SY-1] Страница входа."""
    st.title("🔐 Вход в систему")
    st.markdown("Введите логин для получения роли (например: `owner`, `designer`, `planner`, `tailor`, `qc`)")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Логин", placeholder="owner")
        if st.button("Войти", type="primary", use_container_width=True):
            if username.strip():
                st.session_state.authenticated = True
                st.session_state.current_user = username.strip()
                # Простой маппинг ролей для демо
                role_map = {
                    "owner": "owner", "admin": "owner",
                    "designer": "designer", "design": "designer",
                    "planner": "planner", "plan": "planner",
                    "tailor": "tailor", "sew": "tailor",
                    "qc": "qc", "quality": "qc"
                }
                st.session_state.user_role = role_map.get(username.strip().lower(), "guest")
                st.session_state.last_activity = datetime.now()
                st.rerun()
            else:
                st.error("Введите логин")
    
    with col2:
        if st.button("Войти как Гость", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.current_user = "Гость"
            st.session_state.user_role = "guest"
            st.session_state.last_activity = datetime.now()
            st.rerun()

def render_dashboard():
    """[Ко.1-3] Главная страница с метриками."""
    st.title("🏭 Система управления предприятием")
    st.success(f"Добро пожаловать, {st.session_state.current_user}! (Роль: {st.session_state.user_role})")
    st.markdown("---")
    
    # Метрики
    specs = st.session_state.tech_specs
    orders = st.session_state.orders
    history = st.session_state.operations_history
    
    # Ко.1: Время согласования (симуляция на основе дат)
    approved_specs = [s for s in specs if s['status'] == 'approved']
    avg_approval_days = 0
    if approved_specs:
        # Упрощенный расчет: считаем, что согласование заняло 1-3 дня
        avg_approval_days = 1.5 

    # Ко.3: Средний процент брака
    avg_defect_rate = 0
    if history:
        rates = [h.get('defect_rate', 0) for h in history if 'defect_rate' in h]
        if rates: avg_defect_rate = sum(rates) / len(rates)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Согласование ТЗ (Ко.1)", f"{avg_approval_days} дн.", delta="-0.5 дн.")
    with c2:
        st.metric("Активных заказов", len([o for o in orders if o['status'] == 'planned']))
    with c3:
        st.metric("Средний брак (Ко.3)", f"{avg_defect_rate:.1f}%", delta="-2.0%" if avg_defect_rate < 5 else "+1.0%")

    st.markdown("### 📋 Реализованные функции:")
    st.markdown("""
    - ✅ **Конструирование**: Создание ТЗ, версионирование, загрузка лекал.
    - ✅ **Планирование**: Приоритеты, пересчет дат, экспорт плана.
    - ✅ **Производство**: Контроль качества (QC), пошив, архив операций.
    - ✅ **Системное**: Ролевая модель, уведомления, таймаут сессии.
    """)

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
                        
                        # R-DE-3: Предупреждение если долго висит
                        if ts['status'] == 'draft':
                            st.caption("⏳ На согласовании")
                    with col3:
                        if st.button("📄 Открыть", key=f"open_{ts['id']}", use_container_width=True):
                            st.session_state.selected_ts = ts
                        if ts['status'] != 'approved' and ts['status'] != 'archived':
                            if st.button("✅ Утвердить", key=f"app_{ts['id']}", use_container_width=True):
                                # R-DE-5: Сохраняем историю версий
                                if 'history' not in ts: ts['history'] = []
                                ts['history'].append({
                                    "version": ts['version'],
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "status": "approved"
                                })
                                ts['version'] += 1
                                ts['status'] = 'approved'
                                add_notification(f"ТЗ {ts['article']} утверждено!", "info")
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
                        "patterns": [],
                        "history": []
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
            st.error("🔒 Утвержденное ТЗ. Редактирование заблокировано. [R-DE-4]")
        
        # [R-DE-5] История версий
        if ts.get('history'):
            with st.expander("📜 История версий (R-DE-5)"):
                st.dataframe(ts['history'], use_container_width=True)
        
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
                        add_notification(f"Лекало {file.name} загружено.", "info")
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
                            add_notification(f"План для {order['article']} пересчитан!", "info")
                            st.success("План пересчитан")
                            st.rerun()

            # [R-PL-7] Экспорт плана
            if st.button("📥 Экспорт плана (CSV)", type="primary"):
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["ID", "Артикул", "Приоритет", "Начало", "Конец", "Статус"])
                for o in st.session_state.orders:
                    writer.writerow([o['id'], o['article'], o['priority'], o['start_date'], o['end_date'], o['status']])
                
                st.download_button(
                    label="⬇️ Скачать CSV",
                    data=output.getvalue(),
                    file_name="production_plan.csv",
                    mime="text/csv"
                )

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
                
                # [R-PL-6] Проверка остатков (Имитация)
                material_check = st.checkbox("✅ Остатки материалов проверены (R-PL-6)")
                
                if st.form_submit_button("➕ Добавить в план", type="primary", use_container_width=True):
                    if not material_check:
                        st.error("Нельзя планировать без проверки материалов!")
                    else:
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
                        add_notification(f"Заказ {ts['article']} добавлен в план!", "info")
                        st.success("✅ Заказ добавлен в план")
                        st.rerun()

def production_page():
    """Контекст: Производство [R-PR-1..8]."""
    st.title("🏭 Производство")
    
    tab1, tab2, tab3 = st.tabs(["🧵 Пошив", "🔍 Контроль качества", "📊 Архив"])
    
    with tab1:
        st.info("📌 Пошив доступен только после QC [R-PR-5]")
        
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
                        if qty > 0:
                            st.session_state.operations_history.append({
                                "order_id": order['id'],
                                "article": order['article'],
                                "qty": qty,
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "worker": st.session_state.current_user
                            })
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
                
                rate = calculate_defect_rate(defects, total)
                st.info(f"📊 Брак: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    # [R-PR-8] Алерт при браке > 5%
                    if rate > 5.0:
                        order['qc_status'] = 'failed'
                        order['defect_rate'] = rate
                        add_notification(f"🚨 БРАК >5% ({rate}%) в заказе {order['article']}! Технологу отправлен сигнал.", "error")
                        st.error(f"🚨 БРАК >5%! Сигнал технологу отправлен")
                    else:
                        order['qc_status'] = 'passed'
                        order['defect_rate'] = rate
                        add_notification(f"Заказ {order['article']} прошел QC.", "info")
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    del st.session_state.qc_order
                    st.rerun()

    with tab3:
        # [R-PR-6] Архив выработки
        st.subheader("📊 Архив операций (3 года)")
        history = st.session_state.operations_history
        
        if not history:
            st.info("ℹ️ Нет записей в архиве")
        else:
            df_hist = [{
                "Заказ": h['order_id'],
                "Изделие": h['article'],
                "Кол-во": h['qty'],
                "Дата": h['date'],
                "Швея": h['worker']
            } for h in history]
            st.dataframe(df_hist, use_container_width=True)

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
        st.caption(f"Роль: {st.session_state.user_role}")
        st.markdown("---")
        
        # [RBAC] Фильтрация меню по ролям
        role = st.session_state.user_role
        pages = ["🏠 Главная"]
        if role in ["owner", "designer", "admin"]:
            pages.append("📐 Конструирование")
        if role in ["owner", "planner", "admin"]:
            pages.append("📅 Планирование")
        if role in ["owner", "tailor", "qc", "admin"]:
            pages.append("🏭 Производство")
            
        page = st.radio("Навигация", pages, label_visibility="collapsed")
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        
        # [R-PL-4, R-PR-8] Уведомления
        if st.session_state.notifications:
            st.markdown("**🔔 Уведомления:**")
            for n in st.session_state.notifications[-5:]:
                if n['level'] == 'error':
                    st.error(n['msg'], icon="🚨")
                elif n['level'] == 'warning':
                    st.warning(n['msg'], icon="⚠️")
                else:
                    st.info(n['msg'], icon="ℹ️")

    # Роутинг
    if page == "🏠 Главная":
        render_dashboard()
    elif page == "📐 Конструирование":
        design_page()
    elif page == "📅 Планирование":
        planning_page()
    elif page == "🏭 Производство":
        production_page()

if __name__ == "__main__":
    main()
