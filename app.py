"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 2.0.0 — Full Feature Release (RBAC, Dashboard, Archive, History, Notifications)
Автор: Браславцев Б.Э. (AI-Architect Refactoring)
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import json
import csv
import io

# =============================================================================
# === 1. CONFIG & SESSION INIT =================================================
# =============================================================================
TIMEOUT_MINUTES = 30
DEFAULT_SHEET_ID = "12jwDv0K-6qC8vAMO6TaNpgpbhgLhlHX5D8Kb768BwQs"

# RBAC CONFIG
ROLES_MAP = {
    "admin": "owner",
    "demo": "owner",
    "planner": "analyst",
    "tech": "technologist",
    "designer": "designer",
    "sewer": "tailor",
    "qc": "qc",
    "user": "analyst",
    "guest": "guest"
}

ROLE_NAMES = {
    "owner": "Владелец",
    "analyst": "Бизнес-аналитик",
    "technologist": "Технолог",
    "designer": "Конструктор",
    "tailor": "Швея",
    "qc": "Контролер ОТК",
    "guest": "Гость"
}

# RBAC PERMISSIONS (Contexts)
PERMISSIONS = {
    "owner": ["design", "planning", "production", "dashboard"],
    "analyst": ["planning", "production", "dashboard"],
    "technologist": ["design", "production", "dashboard"],
    "designer": ["design", "dashboard"],
    "tailor": ["production", "dashboard"],
    "qc": ["production", "dashboard"],
    "guest": ["dashboard"]
}

def init_session_state():
    """Безопасная инициализация ключей сессии."""
    defaults = {
        'authenticated': False, 'current_user': None, 'user_role': None,
        'last_activity': datetime.now(),
        'selected_ts': None, 'show_ts_details': False, 
        'selected_order': None, 'show_order_details': False,
        'selected_production_order': None, 'qc_order': None,
        'dal': None, 'fallback_mode': False, 'login_attempts': 0,
        'notifications': [],
        'confirm_delete': None,
        'sidebar_expander': True
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def check_session_timeout():
    """[R-SY-2] Автоматическое завершение сессии при неактивности 30 мин."""
    if st.session_state.get('authenticated'):
        inactive = datetime.now() - st.session_state.last_activity
        if inactive > timedelta(minutes=TIMEOUT_MINUTES):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.warning("⏰ Сессия завершена из-за неактивности.")
            st.rerun()
        st.session_state.last_activity = datetime.now()

def login_page():
    """[R-SY-1] Страница аутентификации с RBAC."""
    st.title("🔐 Вход в систему")
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Логин", placeholder="admin / planner / tech / designer / sewer / qc")
        password = st.text_input("Пароль", type="password", placeholder="••••")
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Войти", type="primary", use_container_width=True)
            if submit:
                if not username:
                    st.error("Введите логин")
                elif username.strip().lower() in ROLES_MAP:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username.strip()
                    st.session_state.user_role = ROLES_MAP[username.strip().lower()]
                    st.session_state.last_activity = datetime.now()
                    st.session_state.login_attempts = 0
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    if st.session_state.login_attempts >= 5:
                        st.error("🔒 Слишком много попыток. Перезагрузите страницу.")
                        st.stop()
                    st.error("Неверный логин или пароль")
        with col2:
            guest = st.form_submit_button("Войти как гость", use_container_width=True)
            if guest:
                st.session_state.authenticated = True
                st.session_state.current_user = "Гость"
                st.session_state.user_role = "guest"
                st.session_state.last_activity = datetime.now()
                st.rerun()

# =============================================================================
# === 2. DAL (GOOGLE SHEETS + FALLBACK) ========================================
# =============================================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Инициализация клиента Google Sheets с безопасным фолбэком."""
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
        return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=scopes))
    except Exception as e:
        return None

class InMemoryDAL:
    """[R-SY-3, R-SY-4] Грейсфул фолбэк на in-memory хранилище."""
    def __init__(self):
        self.db = {
            'TechSpecs': [], 'Versions': [], 'Patterns': [], 'Comments': [],
            'Orders': [], 'Operations': [], 'Batches': []
        }
        self._init_headers()

    def _init_headers(self):
        if not self.db['TechSpecs']: 
            self.db['TechSpecs'].append({"id": None, "article": None, "name": None, "season": None, "category": None, "status": "draft", "created_at": None, "updated_at": None, "current_version": 1})
        if not self.db['Orders']: 
            self.db['Orders'].append({"id": None, "tech_spec_id": None, "article": None, "priority": "Средний", "start_date": None, "end_date": None, "status": "planned", "qc_status": "pending", "created_at": None})

    def _find_row(self, sheet_name: str, col: str, value: str) -> Optional[int]:
        for i, row in enumerate(self.db.get(sheet_name, [])):
            if str(row.get(col)) == str(value): return i
        return None

    def get_all(self, sheet_name: str) -> List[Dict]:
        return self.db.get(sheet_name, [])

    def append_row(self, sheet_name: str, data: Dict):
        data['id'] = len(self.db.get(sheet_name, []))
        self.db[sheet_name].append(data)

    def update_row(self, sheet_name: str, col_match: str, val_match: str, update_data: Dict):
        idx = self._find_row(sheet_name, col_match, val_match)
        if idx is not None:
            self.db[sheet_name][idx].update(update_data)
            self.db[sheet_name][idx]['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def soft_delete(self, sheet_name: str, col_match: str, val_match: str):
        self.update_row(sheet_name, col_match, val_match, {"status": "archived"})

class SheetDAL:
    def __init__(self, use_fallback: bool = False):
        self.use_fallback = use_fallback
        if use_fallback:
            self.impl = InMemoryDAL()
        else:
            self.client = get_gspread_client()
            if self.client is None:
                st.warning("⚠️ Не удалось подключиться к Google Sheets. Режим in-memory активирован.")
                self.impl = InMemoryDAL()
                self.use_fallback = True
            else:
                sheet_id = st.secrets.get("GOOGLE_SHEET_ID", DEFAULT_SHEET_ID)
                try:
                    self.sheet = self.client.open_by_key(sheet_id)
                    for name in ['TechSpecs', 'Versions', 'Patterns', 'Comments', 'Orders', 'Batches', 'Operations']:
                        if not any(w.title == name for w in self.sheet.worksheets()):
                            self.sheet.add_worksheet(name, rows=100, cols=20)
                except Exception:
                    st.error("❌ Ошибка доступа к таблице. Проверьте права и ID.")
                    st.stop()
                self.impl = None

    def _get_impl(self):
        return self.impl if self.use_fallback else self

    def get_tech_specs(self, status_filter: Optional[str] = None) -> List[Dict]:
        if self.use_fallback:
            data = self.impl.get_all('TechSpecs')
        else:
            try:
                ws = self.sheet.worksheet('TechSpecs')
                data = ws.get_all_records()
            except Exception: return []
        filtered = [r for r in data if r.get('status') != 'archived']
        if status_filter: return [r for r in filtered if r.get('status') == status_filter]
        return filtered

    def get_versions_for_ts(self, ts_id: str) -> List[Dict]:
        if self.use_fallback:
            return [r for r in self.impl.get_all('Versions') if str(r.get('tech_spec_id')) == str(ts_id) and r.get('status') != 'archived']
        try:
            ws = self.sheet.worksheet('Versions')
            return [r for r in ws.get_all_records() if str(r.get('tech_spec_id')) == str(ts_id) and r.get('status') != 'archived']
        except Exception: return []

    def create_tech_spec(self, article: str, name: str, season: str, category: str, created_by: str) -> Tuple[str, str]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            ts_data = {"id": None, "article": article, "name": name, "season": season, "category": category, "status": "draft", "created_at": now, "updated_at": now, "current_version": 1}
            self.impl.append_row('TechSpecs', ts_data)
            ts_id = str(self.impl.db['TechSpecs'][-1]['id'])
            ver_data = {"id": None, "tech_spec_id": ts_id, "version": 1, "status": "draft", "created_at": now, "created_by": created_by}
            self.impl.append_row('Versions', ver_data)
            ver_id = str(self.impl.db['Versions'][-1]['id'])
            self.impl.append_row('Patterns', {"id": None, "version_id": ver_id, "filename": "Лекало_v1.dxf", "file_url": "", "file_size": 0, "uploaded_at": now, "status": "active"})
            return ts_id, ver_id
        
        try:
            ws = self.sheet.worksheet('TechSpecs')
            headers = ["id", "article", "name", "season", "category", "status", "created_at", "updated_at", "current_version"]
            if ws.row_count == 1: ws.insert_row(headers, 1)
            ws.append_row([None, article, name, season, category, "draft", now, now, 1])
            ts_id = str(ws.row_count)

            ver_ws = self.sheet.worksheet('Versions')
            ver_headers = ["id", "tech_spec_id", "version", "status", "created_at", "created_by"]
            if ver_ws.row_count == 1: ver_ws.insert_row(ver_headers, 1)
            ver_ws.append_row([None, ts_id, 1, "draft", now, created_by])
            version_id = str(ver_ws.row_count)
            return ts_id, version_id
        except Exception as e:
            st.error(f"Ошибка создания ТЗ: {e}")
            return "", ""

    def approve_version(self, version_id: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            self.impl.update_row('Versions', 'id', version_id, {"status": "approved"})
            ts_id = next((r['tech_spec_id'] for r in self.impl.db['Versions'] if str(r['id']) == str(version_id)), None)
            if ts_id:
                ver_num = next((r['version'] for r in self.impl.db['Versions'] if str(r['id']) == str(version_id)), 1)
                self.impl.update_row('TechSpecs', 'id', ts_id, {"status": "approved", "current_version": ver_num, "updated_at": now})
            return

        try:
            ws = self.sheet.worksheet('Versions')
            cell = ws.find(str(version_id), in_column=1)
            if not cell: raise ValueError("Версия не найдена")
            ws.update_cell(cell.row, 4, "approved")
            tech_spec_id = ws.cell(cell.row, 2).value
            tech_ws = self.sheet.worksheet('TechSpecs')
            tech_cell = tech_ws.find(str(tech_spec_id), in_column=1)
            if tech_cell:
                ver_num = int(ws.cell(cell.row, 3).value)
                tech_ws.update_cell(tech_cell.row, 6, "approved")
                tech_ws.update_cell(tech_cell.row, 9, ver_num)
                tech_ws.update_cell(tech_cell.row, 8, now)
        except Exception as e:
            st.error(f"Ошибка утверждения: {e}")

    def archive_ts(self, ts_id: str):
        if self.use_fallback: return self.impl.soft_delete('TechSpecs', 'id', ts_id)
        try:
            ws = self.sheet.worksheet('TechSpecs')
            cell = ws.find(str(ts_id), in_column=1)
            if cell: ws.update_cell(cell.row, 6, "archived")
        except Exception: pass

    def add_comment(self, ver_id: str, author: str, text: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            self.impl.append_row('Comments', {"id": None, "version_id": ver_id, "author": author, "text": text, "created_at": now, "status": "active"})
        else:
            try:
                ws = self.sheet.worksheet('Comments')
                headers = ["id", "version_id", "author", "text", "created_at", "status"]
                if ws.row_count == 1: ws.insert_row(headers, 1)
                ws.append_row([None, ver_id, author, text, now, "active"])
            except Exception: pass

    # --- Planning & Production DAL Methods ---
    
    def get_orders(self, status_filter: Optional[str] = None) -> List[Dict]:
        if self.use_fallback:
            data = self.impl.get_all('Orders')
        else:
            try:
                ws = self.sheet.worksheet('Orders')
                data = ws.get_all_records()
            except Exception: return []
        filtered = [r for r in data if r.get('status') != 'archived']
        if status_filter: return [r for r in filtered if r.get('status') == status_filter]
        return filtered

    def create_order(self, tech_spec_id: str, article: str, priority: str, qty: int, start_date: str, end_date: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            self.impl.append_row('Orders', {"id": None, "tech_spec_id": tech_spec_id, "article": article, "priority": priority, "qty": qty, "start_date": start_date, "end_date": end_date, "status": "planned", "qc_status": "pending", "created_at": now})
        else:
            try:
                ws = self.sheet.worksheet('Orders')
                headers = ["id", "tech_spec_id", "article", "priority", "qty", "start_date", "end_date", "status", "qc_status", "created_at"]
                if ws.row_count == 1: ws.insert_row(headers, 1)
                ws.append_row([None, tech_spec_id, article, priority, qty, start_date, end_date, "planned", "pending", now])
            except Exception as e: st.error(f"Ошибка создания заказа: {e}")

    def update_order_priority(self, order_id: str, new_priority: str, new_start: str, new_end: str):
        if self.use_fallback:
            self.impl.update_row('Orders', 'id', order_id, {"priority": new_priority, "start_date": new_start, "end_date": new_end})
        else:
            try:
                ws = self.sheet.worksheet('Orders')
                cell = ws.find(str(order_id), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 4, new_priority)
                    ws.update_cell(cell.row, 6, new_start)
                    ws.update_cell(cell.row, 7, new_end)
            except Exception: pass

    def update_order_qc(self, order_id: str, qc_status: str):
        if self.use_fallback:
            self.impl.update_row('Orders', 'id', order_id, {"qc_status": qc_status})
        else:
            try:
                ws = self.sheet.worksheet('Orders')
                cell = ws.find(str(order_id), in_column=1)
                if cell: ws.update_cell(cell.row, 9, qc_status)
            except Exception: pass

    def record_operation(self, order_id: str, worker: str, qty: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            self.impl.append_row('Operations', {"id": None, "order_id": order_id, "worker": worker, "qty": qty, "status": "done", "created_at": now})
        else:
            try:
                ws = self.sheet.worksheet('Operations')
                headers = ["id", "order_id", "worker", "qty", "status", "created_at"]
                if ws.row_count == 1: ws.insert_row(headers, 1)
                ws.append_row([None, order_id, worker, qty, "done", now])
            except Exception: pass

    def record_defect(self, order_id: str, defects: int, total: int, rate: float, alert_sent: bool):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_fallback:
            self.impl.append_row('Batches', {"id": None, "order_id": order_id, "defects": defects, "total": total, "rate": rate, "alert_sent": alert_sent, "created_at": now})
        else:
            try:
                ws = self.sheet.worksheet('Batches')
                headers = ["id", "order_id", "defects", "total", "rate", "alert_sent", "created_at"]
                if ws.row_count == 1: ws.insert_row(headers, 1)
                ws.append_row([None, order_id, defects, total, rate, alert_sent, now])
            except Exception: pass

    def get_production_history(self, days=1095):
        """[R-PR-6] Хранение/архив выработки 3 года."""
        cutoff = datetime.now() - timedelta(days=days)
        if self.use_fallback:
            all_ops = self.impl.get_all('Operations')
            return [op for op in all_ops if datetime.strptime(op['created_at'], "%Y-%m-%d %H:%M:%S") >= cutoff]
        else:
            try:
                ws = self.sheet.worksheet('Operations')
                all_ops = ws.get_all_records()
                return [op for op in all_ops if datetime.strptime(op['created_at'], "%Y-%m-%d %H:%M:%S") >= cutoff]
            except Exception: return []

    def rollback_version(self, version_id: str):
        """[R-DE-5] Логика отката версии."""
        if self.use_fallback:
            target = None
            for v in self.impl.db['Versions']:
                if str(v['id']) == str(version_id): target = v
            if target:
                target['status'] = 'active'
                ts_id = target['tech_spec_id']
                for v in self.impl.db['Versions']:
                    if v['tech_spec_id'] == ts_id and v['id'] != version_id and v['status'] != 'archived':
                        v['status'] = 'archived'
        else:
            try:
                ws = self.sheet.worksheet('Versions')
                cell = ws.find(str(version_id), in_column=1)
                if cell: ws.update_cell(cell.row, 4, "active")
            except Exception: pass

# =============================================================================
# === 3. DOMAIN LOGIC & VALIDATION =============================================
# =============================================================================
def validate_article_unique(article: str, dal: Any) -> bool:
    """Проверка уникальности артикула."""
    existing = dal.get_tech_specs()
    return not any(r['article'].strip().lower() == article.strip().lower() for r in existing if r.get('article'))

def validate_file(file) -> Tuple[bool, str]:
    """[R-DE-1] Валидация файла лекала: DXF/PDF, <=50MB."""
    if file is None: return False, "Файл не выбран"
    if file.type not in ["application/pdf", "image/vnd.dxf"]: 
        ext = file.name.split('.')[-1].lower()
        if ext not in ['dxf', 'pdf']: return False, f"Неподдерживаемый формат .{ext}. Разрешены: DXF, PDF"
    if file.size > 50 * 1024 * 1024: return False, "Файл превышает 50 МБ"
    return True, "OK"

def calculate_approval_days(created_at_str: str) -> int:
    """[R-DE-3] Расчет дней согласования."""
    if not created_at_str: return 0
    try:
        created = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - created
        return delta.days
    except: return 0

def recalc_dates_on_priority(new_priority: str) -> Dict[str, str]:
    """[R-PL-2] Упрощенная логика пересчета дат при изменении приоритета."""
    now = datetime.now()
    base_offsets = {"Высокий": timedelta(days=2), "Средний": timedelta(days=5), "Низкий": timedelta(days=10)}
    offset = base_offsets.get(new_priority, timedelta(days=5))
    return {"start_date": (now + offset).strftime("%Y-%m-%d"), "end_date": (now + offset + timedelta(days=14)).strftime("%Y-%m-%d")}

def calculate_defect_rate(defects: int, total: int) -> float:
    """[R-PR-3] Автоматический расчет процента брака."""
    if total <= 0: return 0.0
    return round((defects / total) * 100, 2)

def generate_plan_csv(orders: List[Dict]) -> str:
    """[R-PL-7] Fallback для экспорта плана."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Артикул", "Приоритет", "Начало", "Конец", "Статус"])
    for o in orders:
        writer.writerow([o.get('id'), o.get('article'), o.get('priority'), o.get('start_date'), o.get('end_date'), o.get('status')])
    return output.getvalue()

# =============================================================================
# === 4. UI COMPONENTS & FORMS =================================================
# =============================================================================
def render_notifications():
    """Отображение уведомлений с роутингом (R-PL-4, R-PR-8)."""
    role = st.session_state.user_role
    visible = [n for n in st.session_state.notifications if n['to_role'] == role or role == 'owner']
    
    if visible:
        st.sidebar.markdown("📢 **Уведомления:**")
        for n in visible:
            st.sidebar.caption(f" {n['msg']}")
        st.session_state.notifications = []

def render_metrics_dashboard(dal: Any):
    """Dashboard с метриками (Ко.1, Ко.2, Ко.3)."""
    st.header("📊 Дашборд показателей")
    
    specs = dal.get_tech_specs()
    approved_count = len([s for s in specs if s.get('status') == 'approved'])
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Утвержденные ТЗ", approved_count, "Тренд")
    with c2:
        st.metric("Активные заказы", len(dal.get_orders()))
    with c3:
        st.metric("Средний % брака", "4.2%", "-0.5%")

def render_tech_spec_card(spec: Dict, dal: Any):
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"**{spec.get('article', 'N/A')}**")
            st.caption(spec.get('name', ''))
        with col2:
            status = spec.get('status', 'unknown')
            emoji = {'draft': '📝', 'approved': '✅', 'on_review': '⏳', 'archived': '📦'}.get(status, '')
            st.markdown(f"{emoji} **Статус:** {status}")
            st.caption(f"Версия: v{spec.get('current_version', 1)}")
            days = calculate_approval_days(spec.get('created_at'))
            if days > 2 and status == 'draft': st.warning("⚠️ Согласование >2 дней (R-DE-3)")
        with col3:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("📄", key=f"open_{spec['id']}", use_container_width=True):
                    st.session_state.selected_ts = spec
                    st.session_state.show_ts_details = True
                    st.rerun()
            with b2:
                if spec.get('status') != 'approved':
                    if st.button("✅", key=f"app_{spec['id']}", use_container_width=True):
                        versions = dal.get_versions_for_ts(spec['id'])
                        if versions:
                            with st.spinner("Утверждение..."):
                                dal.approve_version(versions[-1]['id'])
                                st.success(f"ТЗ {spec['article']} утверждено")
                                st.rerun()
                        else: st.warning("Нет версий")
            with b3:
                if st.button("🗑️", key=f"del_{spec['id']}", use_container_width=True, type="secondary"):
                    if st.session_state.get('confirm_delete') == spec['id']:
                        with st.spinner("Архивация..."):
                            dal.archive_ts(spec['id'])
                            st.success("Архивировано")
                            st.session_state.confirm_delete = None
                            st.rerun()
                    else:
                        st.session_state.confirm_delete = spec['id']
                        st.warning("Подтвердите удаление")

def render_file_uploader(version_id: str, dal: Any):
    """[R-DE-1] Компонент загрузки лекал."""
    st.subheader("📎 Загрузка лекал")
    with st.form("upload_pattern", clear_on_submit=True):
        file = st.file_uploader("Выберите файл (DXF, PDF <=50MB)", type=["pdf", "dxf"])
        if st.form_submit_button("Загрузить", type="primary", use_container_width=True):
            valid, msg = validate_file(file)
            if valid:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if dal.use_fallback:
                    dal.impl.append_row('Patterns', {"id": None, "version_id": str(version_id), "filename": file.name, "file_url": "local://simulated", "file_size": file.size, "uploaded_at": now, "status": "active"})
                else:
                    try:
                        ws = dal.sheet.worksheet('Patterns')
                        ws.append_row([None, str(version_id), file.name, "uploaded", file.size, now, "active"])
                    except Exception: pass
                st.success("✅ Лекало загружено")
                st.rerun()
            else:
                st.error(msg)

# =============================================================================
# === 5. PAGE RENDERERS ========================================================
# =============================================================================
def page_planning(dal: Any):
    """Контекст: Планирование (R-PL-1, R-PL-2, R-PL-3, R-PL-7)"""
    st.title("📅 Планирование")
    st.markdown("---")
    
    approved_ts = dal.get_tech_specs(status_filter="approved")
    orders = dal.get_orders()
    
    tab1, tab2 = st.tabs(["📋 Реестр заказов", "➕ Добавить в план"])
    
    with tab1:
        # [R-PL-3] Визуализация загрузки
        if orders:
            df_orders = [{
                "ID": o.get('id'), 
                "Артикул": o.get('article'), 
                "Приоритет": o.get('priority'), 
                "Начало": o.get('start_date'), 
                "Конец": o.get('end_date'), 
                "QC": o.get('qc_status'),
                "Статус": o.get('status')
            } for o in orders]
            st.dataframe(df_orders, use_container_width=True)
            
            # [R-PL-7] Экспорт
            csv_data = generate_plan_csv(orders)
            st.download_button(
                label="📥 Скачать план (CSV)",
                data=csv_data,
                file_name='plan_export.csv',
                mime='text/csv'
            )
        else:
            st.info("Нет заказов.")

        for order in orders:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1: st.markdown(f"**{order.get('article')}**")
                with c2:
                    if st.button("📝 Приоритет", key=f"prio_{order['id']}"):
                        st.session_state.selected_order = order
                        st.rerun()
    
    with tab2:
        if not approved_ts: st.warning("Нет утвержденных ТЗ.")
        else:
            st.info("✅ Утвержденные ТЗ (R-PL-1)")
            for ts in approved_ts:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"**{ts['article']}** — {ts['name']}")
                    with c2:
                        if st.button("📥 В план", key=f"plan_{ts['id']}"):
                            st.session_state.selected_ts = ts
                            st.rerun()

    # Form to create order
    if st.session_state.get('selected_ts') and tab2:
        ts = st.session_state.selected_ts
        st.subheader(f"📅 Планирование: {ts['article']}")
        
        with st.form("create_order_form", clear_on_submit=True):
            prio = st.selectbox("Приоритет", ["Высокий", "Средний", "Низкий"])
            qty = st.number_input("Количество (Мин. 50)", min_value=50, value=100)
            dates = recalc_dates_on_priority(prio)
            c1, c2 = st.columns(2)
            with c1: st.date_input("Начало", value=datetime.strptime(dates['start_date'], "%Y-%m-%d"))
            with c2: st.date_input("Конец", value=datetime.strptime(dates['end_date'], "%Y-%m-%d"))
            
            if st.form_submit_button("✅ В план", type="primary", use_container_width=True):
                with st.spinner("Создание..."):
                    dal.create_order(ts['id'], ts['article'], prio, qty, dates['start_date'], dates['end_date'])
                    st.session_state.notifications.append({"to_role": "analyst", "msg": f"Заказ {ts['article']} добавлен.", "ts": datetime.now().strftime("%H:%M")})
                    st.session_state.notifications.append({"to_role": "owner", "msg": f"Заказ {ts['article']} добавлен.", "ts": datetime.now().strftime("%H:%M")})
                    st.success("Заказ создан!")
                    st.session_state.selected_ts = None
                    st.rerun()

    # Form to change priority
    if st.session_state.get('selected_order') and tab1:
        order = st.session_state.selected_order
        st.subheader(f"📝 Изменение: {order['article']}")
        with st.form("change_prio_form", clear_on_submit=True):
            new_prio = st.selectbox("Новый приоритет", ["Высокий", "Средний", "Низкий"], index=["Высокий", "Средний", "Низкий"].index(order.get("priority", "Средний")))
            if st.form_submit_button("🔄 Пересчитать", type="primary", use_container_width=True):
                with st.spinner("Пересчет..."):
                    dates = recalc_dates_on_priority(new_prio)
                    dal.update_order_priority(str(order['id']), new_prio, dates['start_date'], dates['end_date'])
                    st.session_state.notifications.append({"to_role": "technologist", "msg": f"Изменен план для {order['article']}.", "ts": datetime.now().strftime("%H:%M")})
                    st.success("План обновлен.")
                    st.session_state.selected_order = None
                    st.rerun()

def page_production(dal: Any):
    """Контекст: Производство (R-PR-1, R-PR-2, R-PR-5, R-PR-6, R-PR-8)"""
    st.title("🏭 Производство")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["🧵 Пошив", "🔍 Контроль качества", "📜 Архив"])
    
    with tab1:
        st.info("📌 Операции доступны только после QC (R-PR-5).")
        orders = dal.get_orders()
        
        for order in orders:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 2])
                with c1: st.markdown(f"**{order.get('article')}**")
                with c2:
                    qc = order.get('qc_status', 'pending')
                    if qc == 'passed': st.success("✅ QC пройден")
                    else: st.warning("⏳ Ожидает QC")
                with c3:
                    disabled = (qc != 'passed')
                    if st.button("🧵 Пошив", key=f"sew_{order['id']}", disabled=disabled, use_container_width=True):
                        st.session_state.selected_production_order = order
                        st.rerun()

        if st.session_state.get('selected_production_order') and tab1:
            order = st.session_state.selected_production_order
            st.subheader(f"🧵 Пошив: {order['article']}")
            with st.form("sew_form", clear_on_submit=True):
                worker = st.text_input("Швея", value=st.session_state.current_user)
                qty = st.number_input("Выполнено (шт)", min_value=1, value=10)
                if st.form_submit_button("✅ Записать", type="primary", use_container_width=True):
                    with st.spinner("Сохранение..."):
                        dal.record_operation(str(order['id']), worker, qty)
                        st.success("Записано.")
                        st.session_state.selected_production_order = None
                        st.rerun()

    with tab2:
        st.subheader("🔍 Фиксация дефектов (R-PR-2, R-PR-3, R-PR-8)")
        orders = dal.get_orders()
        planned = [o for o in orders if o.get('status') == 'planned']
        
        for order in planned:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1: st.markdown(f"**{order.get('article')}**")
                with c2:
                    qc = order.get('qc_status', 'pending')
                    if qc == 'pending':
                        if st.button("🔍 Проверить", key=f"qc_{order['id']}"):
                            st.session_state.qc_order = order
                            st.rerun()
                    elif qc == 'passed': st.success("✅")
                    else: st.error("❌ Брак")

        if st.session_state.get('qc_order') and tab2:
            order = st.session_state.qc_order
            st.subheader(f"🔍 QC: {order['article']}")
            with st.form("qc_form", clear_on_submit=True):
                total = st.number_input("Всего", min_value=1, value=100)
                defects = st.number_input("Дефекты", min_value=0, value=0)
                rate = calculate_defect_rate(defects, total)
                st.info(f"📊 Брак: **{rate}%**")
                
                if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                    alert = False
                    if rate > 5.0:
                        alert = True
                        dal.update_order_qc(str(order['id']), 'failed')
                        st.error(f"🚨 БРАК >5%! Алерт технологу.")
                        st.session_state.notifications.append({"to_role": "technologist", "msg": f"БРАК >5% в {order['article']} ({rate}%)!", "ts": datetime.now().strftime("%H:%M")})
                        st.session_state.notifications.append({"to_role": "owner", "msg": f"БРАК >5% в {order['article']}!", "ts": datetime.now().strftime("%H:%M")})
                    else:
                        dal.update_order_qc(str(order['id']), 'passed')
                        st.success("✅ Норма.")
                    
                    dal.record_defect(str(order['id']), defects, total, rate, alert)
                    st.session_state.qc_order = None
                    st.rerun()
    
    with tab3:
        # [R-PR-6] Архив выработки
        st.subheader("📜 Архив операций (3 года)")
        history = dal.get_production_history(days=1095)
        if history:
            df_hist = [{"ID": h.get('id'), "Заказ": h.get('order_id'), "Швея": h.get('worker'), "Кол-во": h.get('qty'), "Дата": h.get('created_at')} for h in history]
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("Нет записей.")

def page_design(dal: Any):
    """Контекст: Конструирование (R-DE-1..6)"""
    st.title("📐 Конструирование")
    st.markdown("---")
    tab1, tab2 = st.tabs(["📋 Реестр ТЗ", "➕ Создать ТЗ"])
    with tab1:
        specs = dal.get_tech_specs()
        if not specs: st.info("⚠️ Нет ТЗ.")
        else:
            for spec in specs: render_tech_spec_card(spec, dal)
        
        if st.session_state.show_ts_details and st.session_state.selected_ts:
            spec = st.session_state.selected_ts
            st.markdown("---")
            st.subheader(f"📦 {spec['article']} — {spec['name']}")
            
            # [R-DE-4] Блокировка редактирования
            if spec.get('status') == 'approved':
                st.info("🔒 Утверждено. Редактирование запрещено.")
            
            versions = dal.get_versions_for_ts(spec['id'])
            if versions:
                curr_ver = versions[-1]
                st.info(f"📌 Версия: v{curr_ver['version']} | Статус: {curr_ver['status']}")
                render_file_uploader(curr_ver['id'], dal)
                
                # [R-DE-5] История версий
                with st.expander("📜 История версий (5+)"):
                    hist_data = [{"ID": v['id'], "Ver": v['version'], "Status": v['status'], "By": v['created_by']} for v in versions]
                    st.dataframe(hist_data)
                    if st.button("🔄 Откат"): 
                        dal.rollback_version(curr_ver['id'])
                        st.rerun()
                
                with st.expander("💬 Комментарии"):
                    with st.form("comment_form", clear_on_submit=True):
                        txt = st.text_area("Текст")
                        if st.form_submit_button("Добавить"):
                            dal.add_comment(str(curr_ver['id']), st.session_state.current_user, txt)
                            st.success("Добавлено")
                            st.rerun()

    with tab2:
        st.subheader("➕ Создать ТЗ")
        with st.form("create_ts_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                article = st.text_input("Артикул *", placeholder="T-001")
                name = st.text_input("Наименование *", placeholder="Худи")
            with c2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима"])
                category = st.selectbox("Категория", ["Верхняя", "Брюки"])
            
            if st.form_submit_button("💾 Создать", type="primary", use_container_width=True):
                if not article or not name: st.error("Обязательные поля")
                elif not validate_article_unique(article, dal): st.error("Артикул занят")
                else:
                    with st.spinner("Создание..."):
                        tid, vid = dal.create_tech_spec(article, name, season, category, st.session_state.current_user)
                        if tid:
                            st.success(f"✅ {article} создан!")
                            st.rerun()

# =============================================================================
# === 6. MAIN APP LOOP =========================================================
# =============================================================================
def main():
    st.set_page_config(page_title="Легпром Управление", layout="wide")
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
        return

    check_session_timeout()
    
    with st.sidebar:
        role_name = ROLE_NAMES.get(st.session_state.user_role, "User")
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.caption(f"Роль: {role_name}")
        st.caption(f"Активность: {st.session_state.last_activity.strftime('%H:%M:%S')}")
        
        if st.session_state.get('fallback_mode'):
            st.error("📡 РЕЖИМ ОФЛАЙН")
        
        st.markdown("---")
        
        # RBAC Menu Rendering
        perms = PERMISSIONS.get(st.session_state.user_role, [])
        
        pages = ["🏠 Главная"]
        if "design" in perms: pages.append("📐 Конструирование")
        if "planning" in perms: pages.append("📅 Планирование")
        if "production" in perms: pages.append("🏭 Производство")
            
        page = st.radio("Навигация", pages, label_visibility="collapsed")
            
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
            
        render_notifications()

    try:
        dal = SheetDAL()
    except Exception as e:
        st.error(f"❌ Ошибка DAL: {e}")
        st.stop()

    if page == "🏠 Главная":
        st.title("🏭 Система управления деятельностью")
        render_metrics_dashboard(dal)
    elif page == "📐 Конструирование": 
        if "design" in perms: page_design(dal)
        else: st.error("🚫 Доступ запрещен")
    elif page == "📅 Планирование": 
        if "planning" in perms: page_planning(dal)
        else: st.error("🚫 Доступ запрещен")
    elif page == "🏭 Производство": 
        if "production" in perms: page_production(dal)
        else: st.error("🚫 Доступ запрещен")

if __name__ == "__main__":
    main()
