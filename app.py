"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 3.2.0 FINAL — Полная версия с фильтрами и Google Sheets
Автор: Браславцев Б.Э.
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

# ============================================================================
# === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ========================================
# ============================================================================

MAX_SHOP_CAPACITY = 500  # Максимальная загрузка цеха в единицах
WARNING_CAPACITY_THRESHOLD = 0.8  # Порог предупреждения (80%)
TIMEOUT_MINUTES = 30  # Таймаут сессии

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
        'selected_production_order': None,
        'dal': None,
        'fallback_mode': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# === 2. GOOGLE SHEETS & DAL (DATA ACCESS LAYER) =============================
# ============================================================================

@st.cache_resource
def get_gspread_client():
    """Инициализация клиента Google Sheets."""
    try:
        if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
            creds_dict = st.secrets.google_service_account
        else:
            creds_dict = {
                "type": "service_account",
                "project_id": "vkr-master-492811",
                "private_key_id": "0e3fe0bbebc8d3914f7f7c46b9cb9c20beb08d36",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDi/bhOcaODruEu\nfFUcfkisNJ/BECpeVYclprHzseaJgMJKCSYChiipFJXoQYdk+qB28WTH+j9OmB1y\nrAZxA84FSbOXp21r9uwl2TI2SC8HMrT92yuw65ThV82o0c/DFv89sXBbW1Bl9YXx\nQKP4szDwN9nImpE+AFhTFJ7cOszzHxJdYQ5I/CoMR4cTitfll7ed+6eN53AMDtkT\nfVIvPigWNeQA4FcP5Kiw+Fmmb3SlnvXJ5yrbW5v6Y48bev4wwRryFrRSKAkK8UsN\nOfHmZAcdvBtZdeq0hiHZPv5fQEoH7ZzNg+kYdILWQO9lfXwF4krkWRclXR4M/rgB\n7uQ2/PNtAgMBAAECggEAD+B/S71XGpbY2U+JBH0wyBrGMdLXo9GHqnKGb+05mtSO\nwm7xYavQnEL8WUp8FewR3T/1NKekVfL93E98A9uoRWZqUWk8lhinW95dTL6vy2kY\nj8kMvUs9FqX1lKFYTuUE5WPL4Bf6/6a0v7MtxO+DtMmzSfzFu/h6NRV0JyNVwouA\nG+FLo+PAGNrzw5fuXaHv44IE9AY5vOh8xIDVHHWx0WrUMoVZWjESq9tqvhsTv0YM\nq/iICwD5p5cmVGJ/4b+qGA1TxstKFqTLjD3aSqKu5ZDCYOGodeiUF72lRWji0wAx\n/bXscntk4/ELVGMphf3TCwxAc5sg58SAwlZsQAPiAQKBgQDztpta7unu+zOT6P7/\nGVmymXX05sqmT/M9CGb5ZMhCiUGHKMiozFg11omS39AGACR2wQyT2JuTRLXSOO1i\nJyRwpngmA/fkCQJWymmSqpRPWsFMKns+FZdDFUeqvxh9qPs8toVhw7sDq56BpJTh\nVCUyh/GwNJc2ql645g9K0HvwfQKBgQDub0tP4Qe7esreP8jx8/zt7aFfNz35XUSe\ncfqOjf1dVb39Yg75yztPutGXVUO9l/mbEX+rz8LmuTU5yJgYALux2hIYQEvLOLE\n2Gd2cECqWDh3hlIqonMAs8kHgPwAbRMoXD+jAhSsU9pQ21ozbPjnnTmi0No0EXUT\nuaEhTl7xsQKBgQDFx56CCDs+Xwu3cDFoUmlRoGpyic1RdLaABE6U++3s2TideEKH\ngfXgEy/oSsul4v20hewwG2v98pffd6Vlr0BKTz5YE4Zbv9fvGSreBKKBV7RgnGUR\nuDHeFenoLlawu67P0YujEFW3n9HtgeP0jPX28Q35omRIz7A5OzKT02eRfQKBgQDr\nMXEynCDKeDeAv55xvGD0OYECsTU6sxuqx3eGAt23oYpFVOK82BHrdbak9oBZln2q\nzroHOmtgt7SfCRWuJ5MWhrCBJN7MMBSIY4a7N8MxxM/+ZsrKL3ANc0qLUlpB+VX6\na/SB0N2flx80vwrcy1NC9L4TsrxqvAWmrWcZuXrCIQKBgFchibaNsjcRU8yZR2JK\nbRjCLIRjZ9pzqJ094UI4AriUi2SqWqLBXNdzo5hF7eg0IrK9UQkwlV5n2GFwXTlQ\nTVsE6PNzcMjdARoTjWVh+B0Gm/b8COHRzRiR5k3dLjkAw6/NZQcnw1Q1kMunbJKl\n//kPhJjzl6h3VO2gH3ATE8eM\n-----END PRIVATE KEY-----\n",
                "client_email": "vkr-crud-bot@vkr-master-492811.iam.gserviceaccount.com",
                "client_id": "108493844494936286424",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/vkr-crud-bot%40vkr-master-492811.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }
        
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Ошибка авторизации Google Sheets: {e}")
        return None

class SheetDAL:
    """Data Access Layer для работы с Google Sheets."""
    
    def __init__(self):
        self.client = get_gspread_client()
        self.sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "12jwDv0K-6qC8vAMO6TaNpgpbhgLhlHX5D8Kb768BwQs")
        self.sheet = None
        self.use_fallback = False
        
        if self.client:
            try:
                self.sheet = self.client.open_by_key(self.sheet_id)
                self._init_database()
            except Exception as e:
                st.warning(f"⚠️ Режим offline. Данные сохраняются локально. Ошибка: {e}")
                self.use_fallback = True
        else:
            st.warning("⚠️ Режим offline. Данные сохраняются локально.")
            self.use_fallback = True
    
    def _init_database(self):
        """Инициализация листов с заголовками."""
        if not self.sheet:
            return
        
        sheets_config = {
            'TechSpecs': ['id', 'article', 'name', 'season', 'category', 'status', 'created_at', 'updated_at', 'current_version'],
            'Versions': ['id', 'tech_spec_id', 'version', 'status', 'created_at', 'created_by'],
            'Patterns': ['id', 'version_id', 'filename', 'file_url', 'file_size', 'uploaded_at', 'status'],
            'Comments': ['id', 'version_id', 'author', 'text', 'created_at', 'status'],
            'Orders': ['id', 'tech_spec_id', 'article', 'priority', 'qty', 'start_date', 'end_date', 'status', 'qc_status', 'created_at'],
            'Operations': ['id', 'order_id', 'worker', 'qty', 'status', 'created_at'],
            'Batches': ['id', 'order_id', 'defects', 'total', 'rate', 'alert_sent', 'created_at']
        }
        
        for sheet_name, headers in sheets_config.items():
            try:
                worksheet = self.sheet.worksheet(sheet_name)
                if worksheet.row_count < 2:
                    worksheet.insert_row(headers, 1)
            except gspread.WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                worksheet.insert_row(headers, 1)
    
    def get_tech_specs(self, status_filter=None):
        """Получить ТЗ с фильтрацией."""
        if self.use_fallback:
            specs = st.session_state.tech_specs
        else:
            try:
                ws = self.sheet.worksheet('TechSpecs')
                data = ws.get_all_records()
                specs = [dict(r) for r in data]
            except:
                specs = st.session_state.tech_specs
        
        if status_filter:
            return [s for s in specs if s.get('status') == status_filter]
        return [s for s in specs if s.get('status') != 'archived']
    
    def get_orders(self, status_filter=None):
        """Получить заказы с фильтрацией."""
        if self.use_fallback:
            orders = st.session_state.orders
        else:
            try:
                ws = self.sheet.worksheet('Orders')
                data = ws.get_all_records()
                orders = [dict(r) for r in data]
            except:
                orders = st.session_state.orders
        
        if status_filter:
            return [o for o in orders if o.get('status') == status_filter]
        return [o for o in orders if o.get('status') != 'archived']
    
    def create_tech_spec(self, article, name, season, category, created_by):
        """Создать ТЗ."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_ts = {
            "id": str(len(st.session_state.tech_specs) + 1),
            "article": article,
            "name": name,
            "season": season,
            "category": category,
            "status": "draft",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "documents": []
        }
        st.session_state.tech_specs.append(new_ts)
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('TechSpecs')
                ws.append_row([new_ts['id'], article, name, season, category, 'draft', now, now, 1])
            except:
                pass
        
        return new_ts['id']
    
    def approve_tech_spec(self, ts_id):
        """Утвердить ТЗ."""
        for ts in st.session_state.tech_specs:
            if str(ts.get('id')) == str(ts_id):
                ts['status'] = 'approved'
                ts['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('TechSpecs')
                cell = ws.find(str(ts_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 6, 'approved')
            except:
                pass
    
    def archive_tech_spec(self, ts_id):
        """Архивировать ТЗ."""
        for ts in st.session_state.tech_specs:
            if str(ts.get('id')) == str(ts_id):
                ts['status'] = 'archived'
                break
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('TechSpecs')
                cell = ws.find(str(ts_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 6, 'archived')
            except:
                pass
    
    def create_order(self, tech_spec_id, article, priority, qty, start_date, end_date):
        """Создать заказ."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_order = {
            "id": str(len(st.session_state.orders) + 1),
            "tech_spec_id": str(tech_spec_id),
            "article": article,
            "priority": priority,
            "qty": qty,
            "start_date": start_date,
            "end_date": end_date,
            "status": "planned",
            "qc_status": "pending",
            "created_at": now,
            "defect_rate": 0.0,
            "sewing_records": []
        }
        st.session_state.orders.append(new_order)
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('Orders')
                ws.append_row([new_order['id'], tech_spec_id, article, priority, qty, start_date, end_date, 'planned', 'pending', now])
            except:
                pass
        
        return new_order['id']
    
    def update_order_priority(self, order_id, new_priority, new_start, new_end):
        """Обновить приоритет и даты заказа."""
        for order in st.session_state.orders:
            if str(order.get('id')) == str(order_id):
                order['priority'] = new_priority
                order['start_date'] = new_start
                order['end_date'] = new_end
                break
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('Orders')
                cell = ws.find(str(order_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 4, new_priority)
                    ws.update_cell(cell.row, 6, new_start)
                    ws.update_cell(cell.row, 7, new_end)
            except:
                pass
    
    def update_order_qc(self, order_id, qc_status, defect_rate=0.0):
        """Обновить статус QC заказа."""
        for order in st.session_state.orders:
            if str(order.get('id')) == str(order_id):
                order['qc_status'] = qc_status
                order['defect_rate'] = defect_rate
                break
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('Orders')
                cell = ws.find(str(order_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 9, qc_status)
            except:
                pass
    
    def archive_order(self, order_id):
        """Архивировать заказ."""
        for order in st.session_state.orders:
            if str(order.get('id')) == str(order_id):
                order['status'] = 'archived'
                order['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        if not self.use_fallback and self.sheet:
            try:
                ws = self.sheet.worksheet('Orders')
                cell = ws.find(str(order_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 8, 'archived')
            except:
                pass

# ============================================================================
# === 3. DOMAIN LOGIC & VALIDATION ===========================================
# ============================================================================

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
    """Проверить доступность мощности."""
    current_load = calculate_current_load()
    return (current_load + qty) <= MAX_SHOP_CAPACITY

def get_available_capacity() -> int:
    """Получить доступную мощность."""
    current_load = calculate_current_load()
    return max(0, MAX_SHOP_CAPACITY - current_load)

# ============================================================================
# === 4. STREAMLIT PAGES (UI) ================================================
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

def design_page(dal):
    """Контекст: Конструирование [R-DE-1..7]."""
    st.title("📐 Конструирование")
    tab1, tab2 = st.tabs(["📋 Реестр ТЗ", "➕ Создать ТЗ"])
    
    with tab1:
        st.subheader("Технические задания")
        
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Статус", ["Все", "draft", "approved", "archived"])
        
        specs = dal.get_tech_specs()
        
        if status_filter != "Все":
            specs = [s for s in specs if s.get('status') == status_filter]
        
        if not specs:
            st.info("⚠️ Нет технических заданий. Создайте первое.")
        else:
            for ts in specs:
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
                                dal.approve_tech_spec(ts.get('id'))
                                st.success(f"ТЗ {ts.get('article')} утверждено")
                                st.rerun()
                        if st.button("🗑️ Удалить", key=f"del_{ts.get('id')}", use_container_width=True):
                            dal.archive_tech_spec(ts.get('id'))
                            st.success("ТЗ архивировано")
                            st.rerun()
    
    # Детали ТЗ
    if st.session_state.get('selected_ts'):
        ts = st.session_state.selected_ts
        st.markdown("---")
        st.subheader(f"📦 {ts.get('article', 'N/A')} — {ts.get('name', '')}")
        
        # [R-DE-4] Блокировка после утверждения
        if ts.get('status') == 'approved':
            st.error("🔒 Утвержденное ТЗ. Редактирование заблокировано.")
        
        # [R-DE-1] Загрузка документов
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
        
        # Отображение документов
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
                    dal.create_tech_spec(article, name, season, category, st.session_state.current_user)
                    st.success(f"✅ ТЗ {article} создан!")
                    st.rerun()

def planning_page(dal):
    """Контекст: Планирование [R-PL-1..7]."""
    st.title("📅 Планирование")
    
    # Расчет загрузки
    current_load = calculate_current_load()
    capacity_pct = get_capacity_percentage()
    available_capacity = get_available_capacity()
    
    # Форма редактирования
    if st.session_state.editing_order_id is not None:
        order_to_edit = None
        for order in st.session_state.orders:
            if str(order.get('id')) == str(st.session_state.editing_order_id):
                order_to_edit = order
                break
        
        if order_to_edit:
            st.subheader(f"📝 Изменение заказа: {order_to_edit.get('article', 'N/A')}")
            
            with st.form("edit_order_form", clear_on_submit=False):
                priorities = ["Высокий", "Средний", "Низкий"]
                current_priority = order_to_edit.get('priority', 'Средний')
                current_idx = priorities.index(current_priority) if current_priority in priorities else 1
                new_priority = st.selectbox("Новый приоритет", priorities, index=current_idx)
                
                try:
                    start_date_val = datetime.strptime(order_to_edit.get('start_date', datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
                    end_date_val = datetime.strptime(order_to_edit.get('end_date', (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")), "%Y-%m-%d")
                except:
                    start_date_val = datetime.now()
                    end_date_val = datetime.now() + timedelta(days=14)
                
                new_start = st.date_input("Дата начала", value=start_date_val)
                new_end = st.date_input("Дата окончания", value=end_date_val)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Сохранить", type="primary", use_container_width=True):
                        dal.update_order_priority(
                            order_to_edit.get('id'),
                            new_priority,
                            new_start.strftime("%Y-%m-%d"),
                            new_end.strftime("%Y-%m-%d")
                        )
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
        
        # [R-PL-3] Индикатор загрузки
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
        
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Статус заказа", ["Все", "planned", "archived"], key="plan_filter_status")
        with col2:
            filter_priority = st.selectbox("Приоритет", ["Все", "Высокий", "Средний", "Низкий"], key="plan_filter_priority")
        
        orders = dal.get_orders()
        
        # Применение фильтров
        if filter_status != "Все":
            orders = [o for o in orders if o.get('status') == filter_status]
        if filter_priority != "Все":
            orders = [o for o in orders if o.get('priority') == filter_priority]
        
        if not orders:
            st.info("Нет заказов в плане")
        else:
            for order in orders:
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
                        if st.button("📝 Изменить", key=f"prio_{order.get('id')}", use_container_width=True):
                            st.session_state.editing_order_id = order.get('id')
                            st.rerun()
    
    with tab2:
        # [R-PL-1] Только утвержденные ТЗ
        approved_ts = [ts for ts in dal.get_tech_specs() if ts.get('status') == 'approved']
        
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
                            dal.create_order(
                                ts.get('id'),
                                ts.get('article'),
                                priority,
                                qty,
                                start_date.strftime("%Y-%m-%d"),
                                end_date.strftime("%Y-%m-%d")
                            )
                            st.success(f"✅ Заказ добавлен! Осталось: {get_available_capacity()} ед.")
                            st.rerun()

def production_page(dal):
    """Контекст: Производство [R-PR-1..8]."""
    st.title("🏭 Производство")
    tab1, tab2, tab3 = st.tabs(["🧵 Пошив", "🔍 Контроль качества", "📦 Архив"])
    
    with tab1:
        st.info("📌 Пошив доступен только после QC")
        
        # Фильтр
        show_completed = st.checkbox("Показать завершенные", value=False)
        
        orders = dal.get_orders()
        
        for order in orders:
            if order.get('status') == 'archived' and not show_completed:
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
                    else:
                        st.warning("🚫 QC не пройден")
                with col3:
                    # [R-PR-5] Блокировка без QC
                    disabled = qc_status != 'passed'
                    if st.button("✅ Закрыть заказ", key=f"sew_{order_id}", disabled=disabled, use_container_width=True):
                        st.session_state.selected_production_order = order
                        st.rerun()
    
    # Форма закрытия заказа
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
                    dal.archive_order(order.get('id'))
                    st.success(f"✅ Заказ закрыт! Выполнено: {sewn_qty} шт.")
                    st.info(f"📊 Освобождено: {order.get('qty', 0)} ед. Доступно: {get_available_capacity()} ед.")
                    st.session_state.selected_production_order = None
                    st.rerun()
            with col2:
                if st.form_submit_button("❌ Отмена", use_container_width=True):
                    st.session_state.selected_production_order = None
                    st.rerun()
    
    with tab2:
        st.subheader("🔍 Контроль качества [R-PR-2, R-PR-3, R-PR-8]")
        
        planned_orders = [o for o in dal.get_orders() if o.get('status') == 'planned']
        
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
                defects = st.number_input("Дефектов", min_value=0, value=0)
                
                rate = calculate_defect_rate(defects, total)
                
                if rate > 5.0:
                    st.error(f"🚨 КРИТИЧЕСКИЙ БРАК: **{rate}%**")
                elif rate > 3.0:
                    st.warning(f"⚠️ Повышенный брак: **{rate}%**")
                else:
                    st.success(f"✅ Брак в норме: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    # [R-PR-8] Алерт при браке > 5%
                    if rate > 5.0:
                        dal.update_order_qc(order.get('id'), 'failed', rate)
                        st.error("🚨 БРАК >5%! Технологу отправлен сигнал")
                        st.session_state.notifications.append({
                            "msg": f"🚨 БРАК {rate}% в заказе {article}!",
                            "time": datetime.now().strftime("%H:%M"),
                            "level": "error"
                        })
                    else:
                        dal.update_order_qc(order.get('id'), 'passed', rate)
                        st.success("✅ Норма. Допущено к пошиву")
                    
                    st.session_state.qc_order = None
                    st.rerun()
    
    with tab3:
        st.subheader("📦 Архив завершенных заказов")
        
        archived_orders = [o for o in dal.get_orders() if o.get('status') == 'archived']
        
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
                                st.success(f"✅ {record.get('qty')} шт.")
                                st.caption(f"🕐 {record.get('date', 'N/A')}")

def main_dashboard(dal):
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

# ============================================================================
# === 5. MAIN APP LOOP =======================================================
# ============================================================================

def check_session_timeout():
    """[R-SY-2] Проверка таймаута сессии."""
    if st.session_state.authenticated and st.session_state.last_activity:
        inactive = datetime.now() - st.session_state.last_activity
        if inactive > timedelta(minutes=TIMEOUT_MINUTES):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.warning("⏰ Сессия завершена")
            st.rerun()
        st.session_state.last_activity = datetime.now()

def main():
    """Главная функция."""
    st.set_page_config(page_title="Легпром Управление", layout="wide")
    init_session_state()
    
    # Инициализация DAL
    if st.session_state.dal is None:
        st.session_state.dal = SheetDAL()
    
    check_session_timeout()
    
    if not st.session_state.authenticated:
        login_page()
        return
    
    dal = st.session_state.dal
    
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.markdown("---")
        page = st.radio(
            "Навигация",
            ["🏠 Главная", "📐 Конструирование", "📅 Планирование", "🏭 Производство"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        st.caption("Версия: 3.2.0 FINAL")
    
    if page == "🏠 Главная":
        main_dashboard(dal)
    elif page == "📐 Конструирование":
        design_page(dal)
    elif page == "📅 Планирование":
        planning_page(dal)
    elif page == "🏭 Производство":
        production_page(dal)

if __name__ == "__main__":
    main()
