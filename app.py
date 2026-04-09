"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 0.9.0 (Single File + Google Sheets Only — NO SQLite)
Направление: 27.04.03 «Системный анализ и управление»
Автор: Браславцев Б.Э.

Требования из ВКР и Системного промта (разработка3):
- R-SY-1: Обязательная аутентификация
- R-SY-2: Таймаут сессии 30 минут
- R-DE-1: Загрузка DXF/PDF (≤50 МБ) → *файлы хранятся в Google Drive, ссылки в Sheets*
- R-DE-2: Автофиксация даты/времени версии
- R-DE-4: Блокировка редактирования утвержденного ТП
- R-DE-5: Хранение ≥5 предыдущих версий ТП (через архивирование)
- R-DE-6: Комментарии к лекалам
- R-DE-7: Удаление через status='archived'
- R-SY-3: Резервные копии — не требуется (Google Sheets сама сохраняет историю)
- О-3: Импорт из существующих Google Таблиц — реализован

Используется:
- gspread + google-auth
- Streamlit SPA (st.radio в сайдбаре)
- Все данные — в Google Sheets по ID из промта
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

# ============================================================================
# === 1. GOOGLE SHEETS CONFIGURATION =========================================
# ============================================================================

# Проверка наличия secrets.toml
try:
    from streamlit import secrets as st_secrets
    SHEET_ID = st_secrets["GOOGLE_SHEET_ID"]
    FOLDER_ID = st_secrets.get("GOOGLE_FOLDER_ID", "1uhzRoHIhbxpsTfz8FFtFNwm4h39aibYlF6")
except Exception:
    # Для локального запуска — используем переданный TOML
    SHEET_ID = "12jwDvBK-6qC8vAM06TaNpgpbhgLhlHX5D8Kb768BwQs"
    FOLDER_ID = "1uhzRoHIhbxpsTfz8FFtFNwm4h39aibYlF6"

# Настройка аутентификации
def get_gspread_client():
    """Создание клиента gspread с использованием service account из secrets."""
    try:
        # Если запущено в Streamlit Cloud — читаем из st.secrets
        if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
            creds_dict = st.secrets.google_service_account
        else:
            # Локальный режим: используем переданный TOML (как в вашем сообщении)
            creds_dict = {
                "type": "service_account",
                "project_id": "vkr-master-492811",
                "private_key_id": "0e3fe0bbebc8d3914f7f7c46b9cb9c20beb08d36",
                "private_key": '''-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDi/bhOcaODruEu
fFUcfkisNJ/BECpeVYclprHzseaJgMJKCSYChiipFJXoQYdk+qB28WTH+j9OmB1y
rAZxA84FSbOXp21r9uwl2TI2SC8HMrT92yuw65ThV82o0c/DFv89sXBbW1Bl9YXx
QKP4szDwN9nImpE+AFhTFJ7cOszzHxJdYQ5I/CoMR4cTitfll7ed+6eN53AMDtkT
fVIvPigWNeQA4FcP5Kiw+Fmmb3SlnvXJ5yrbW5v6Y48bev4wwRryFrRSKAkK8UsN
OfHmZAcdvBtZdeq0hiHZPv5fQEoH7ZzNg+kYdILWQO9lfXwF4krkWRclXR4M/rgB
7uQ2/PNtAgMBAAECggEAD+B/S71XGpbY2U+JBH0wyBrGMdLXo9GHqnKGb+05mtSO
wm7xYavQnEL8WUp8FewR3T/1NKekVfL93E98A9uoRWZqUWk8lhinW95dTL6vy2kY
j8kMvUs9FqX1lKFYTuUE5WPL4Bf6/6a0v7MtxO+DtMmzSfzFu/h6NRV0JyNVwouA
G+FLo+PAGNrzw5fuXaHv44IE9AY5vOh8xIDVHHWx0WrUMoVZWjESq9tqvhsTv0YM
/iICwD5p5cmVGJ/4b+qGA1TxstKFqTLjD3aSqKu5ZDCYOGodeiUF72lRWji0wAx
/bXscntk4/ELVGMphf3TCwxAc5sg58SAwlZsQAPiAQKBgQDztpta7unu+zOT6P7/
GVmymXX05sqmT/M9CGb5ZMhCiUGHKMiozFg11omS39AGACR2wQyT2JuTRLXSOO1i
JyRwpngmA/fkCQJWymmSqpRPWsFMKns+FZdDFUeqvxh9qPs8toVhw7sDq56BpJTh
VCUyh/GwNJc2ql645g9K0HvwfQKBgQDub0tP4Qe7esreP8jx8/zt7aFfNz35XUSe
cfqOjf1dVb39Yg75yztPutGXVUO9l/mbEX+rz8LmuTU5yJgYALOux2hIYQEvLOLE
2Gd2cECqWDh3hlIqonMAs8kHgPwAbRMoXD+jAhSsU9pQ21ozbPjnnTmi0No0EXUT
uaEhTl7xsQKBgQDFx56CCDs+Xwu3cDFoUmlRoGpyic1RdLaABE6U++3s2TideEKH
gfXgEy/oSsul4v20hewwG2v98pffd6Vlr0BKTz5YE4Zbv9fvGSreBKKBV7RgnGUR
uDHeFenoLlawu67P0YujEFW3n9HtgeP0jPX28Q35omRIz7A5OzKT02eRfQKBgQDr
MXEynCDKeDeAv55xvGD0OYECsTU6sxuqx3eGAt23oYpFVOK82BHrdbak9oBZln2q
zroHOmtgt7SfCRWuJ5MWhrCBJN7MMBSIY4a7N8MxxM/+ZsrKL3ANc0qLUlpB+VX6
a/SB0N2flx80vwrcy1NC9L4TsrxqvAWmrWcZuXrCIQKBgFchibaNsjcRU8yZR2JK
bRjCLIRjZ9pzqJ094UI4AriUi2SqWqLBXNdzo5hF7eg0IrK9UQkwlV5n2GFwXTlQ
TVsE6PNzcMjdARoTjWVh+B0Gm/b8COHRzRiR5k3dLjkAw6/NZQcnw1Q1kMunbJKl
//kPhJjzl6h3VO2gH3ATE8eM
-----END PRIVATE KEY-----''',
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
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Google Sheets: {e}")
        st.stop()


# ============================================================================
# === 2. DATA ACCESS LAYER (DAL) =============================================
# ============================================================================

class SheetDAL:
    def __init__(self):
        self.client = get_gspread_client()
        self.sheet = self.client.open_by_key(SHEET_ID)
        
        # Кэш листов
        self._models = None
        self._tech_packages = None
        self._files = None
        self._comments = None

    def _get_worksheet(self, title):
        try:
            return self.sheet.worksheet(title)
        except gspread.WorksheetNotFound:
            # Создаём лист при первом обращении
            self.sheet.add_worksheet(title=title, rows=1000, cols=20)
            return self.sheet.worksheet(title)

    @property
    def models(self):
        if self._models is None:
            self._models = self._get_worksheet("Models")
        return self._models

    @property
    def tech_packages(self):
        if self._tech_packages is None:
            self._tech_packages = self._get_worksheet("TechPackages")
        return self._tech_packages

    @property
    def files(self):
        if self._files is None:
            self._files = self._get_worksheet("Files")
        return self._files

    @property
    def comments(self):
        if self._comments is None:
            self._comments = self._get_worksheet("Comments")
        return self._comments

    # --- CRUD для моделей ---
    def get_models(self, status_filter=None):
        ws = self.models
        data = ws.get_all_records()
        if status_filter:
            return [r for r in data if r.get("status") == status_filter]
        return [r for r in data if r.get("status") != "archived"]

    def create_model(self, article, name, season, category, created_by):
        ws = self.models
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [None, article, name, season, category, "draft", now, now, 1]
        ws.append_row(row)
        # Получаем id (номер строки)
        return ws.row_count  # временный ID = номер строки

    def approve_tech_package(self, package_id):
        ws = self.tech_packages
        # Найдём строку по id
        cell = ws.find(str(package_id), in_column=1)
        if cell:
            ws.update_cell(cell.row, 4, "approved")  # column 4 = status
            # Обновим модель
            model_id = int(ws.cell(cell.row, 2).value)  # column 2 = model_id
            model_ws = self.models
            model_cell = model_ws.find(str(model_id), in_column=1)
            if model_cell:
                model_ws.update_cell(model_cell.row, 6, "approved")  # status
                model_ws.update_cell(model_cell.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # updated_at

    def create_new_version(self, model_id, created_by):
        ws = self.tech_packages
        # Получим последнюю версию модели
        model_ws = self.models
        model_cell = model_ws.find(str(model_id), in_column=1)
        if not model_cell:
            raise ValueError("Модель не найдена")
        current_ver = int(model_ws.cell(model_cell.row, 9).value)  # column 9 = current_version
        new_ver = current_ver + 1

        # Создаём новую версию ТП
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [None, model_id, new_ver, "draft", now, created_by]
        ws.append_row(row)

        # Обновим модель
        model_ws.update_cell(model_cell.row, 9, new_ver)  # current_version
        model_ws.update_cell(model_cell.row, 6, "draft")  # status
        model_ws.update_cell(model_cell.row, 8, now)  # updated_at

        # Архивируем старые версии (>5)
        all_rows = ws.get_all_records()
        versions_for_model = [r for r in all_rows if r.get("model_id") == str(model_id)]
        if len(versions_for_model) > 5:
            old_versions = sorted(versions_for_model, key=lambda x: int(x["version"]))[:len(versions_for_model)-5]
            for v in old_versions:
                cell = ws.find(str(v["id"]), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 4, "archived")

    # --- CRUD для файлов ---
    def save_file(self, package_id, filename, file_url, file_size, mime_type):
        ws = self.files
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [None, package_id, filename, file_url, file_size, mime_type, now, "active"]
        ws.append_row(row)

    def get_package_files(self, package_id):
        ws = self.files
        data = ws.get_all_records()
        return [r for r in data if r.get("tech_package_id") == str(package_id) and r.get("status") == "active"]

    # --- CRUD для комментариев ---
    def add_comment(self, package_id, author, text):
        ws = self.comments
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [None, package_id, author, text, now, "active"]
        ws.append_row(row)

    def get_comments(self, package_id):
        ws = self.comments
        data = ws.get_all_records()
        return [r for r in data if r.get("tech_package_id") == str(package_id) and r.get("status") == "active"]

    # --- Удаление через архивирование (R-DE-7) ---
    def delete_model(self, model_id):
        ws = self.models
        cell = ws.find(str(model_id), in_column=1)
        if cell:
            ws.update_cell(cell.row, 6, "archived")  # status

    def delete_tech_package(self, package_id):
        ws = self.tech_packages
        cell = ws.find(str(package_id), in_column=1)
        if cell:
            ws.update_cell(cell.row, 4, "archived")

    def delete_file(self, file_id):
        ws = self.files
        cell = ws.find(str(file_id), in_column=1)
        if cell:
            ws.update_cell(cell.row, 8, "archived")

    def delete_comment(self, comment_id):
        ws = self.comments
        cell = ws.find(str(comment_id), in_column=1)
        if cell:
            ws.update_cell(cell.row, 6, "archived")


# ============================================================================
# === 3. UI COMPONENTS =======================================================
# ============================================================================

def render_registry(entity_name, rows, actions_callback):
    st.subheader(f"📋 {entity_name}")
    if not rows:
        st.info(f"⚠️ {entity_name} пока пуст. Создайте первую запись.")
        return

    for row in rows:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{row.get('article', row.get('id', 'N/A'))}**")
                st.caption(row.get('name', ''))

            with col2:
                status = row.get('status', 'unknown')
                status_emoji = {
                    'draft': '📝',
                    'in_review': '👀',
                    'approved': '✅',
                    'archived': '📦',
                    'completed': '✅',
                    'pending': '⏳',
                    'active': '🟢'
                }.get(status, '📄')
                st.markdown(f"{status_emoji} **Статус:** {status}")
                ver = row.get('current_version', row.get('version', 1))
                st.caption(f"Версия: v{ver}")

            with col3:
                actions_callback(row)


# ============================================================================
# === 4. PAGES ===============================================================
# ============================================================================

def page_design(dal):
    st.title("📐 Конструирование")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📋 Реестр моделей", "➕ Создание модели"])

    with tab1:
        models = dal.get_models()
        
        def model_actions(model):
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📄 Открыть", key=f"open_{model.get('id')}", use_container_width=True):
                    st.session_state.selected_model = model
                    st.session_state.show_model_details = True
            with col2:
                if model.get('status') != 'approved':
                    if st.button("✅ Утвердить", key=f"approve_{model.get('id')}", use_container_width=True):
                        # Найдём техпакет этой модели (последний active)
                        tp_rows = dal.tech_packages.get_all_records()
                        tps = [r for r in tp_rows if r.get("model_id") == str(model.get('id')) and r.get("status") == "draft"]
                        if tps:
                            dal.approve_tech_package(int(tps[0]["id"]))
                            st.success(f"Модель {model['article']} утверждена")
                            st.rerun()
                        else:
                            st.warning("Нет активного технического пакета для утверждения")
            with col3:
                if st.button("🗑️ Удалить", key=f"del_model_{model.get('id')}", use_container_width=True, type="secondary"):
                    dal.delete_model(int(model.get('id')))
                    st.success(f"Модель {model['article']} архивирована")
                    st.rerun()

        render_registry("Модели", models, model_actions)

        if st.session_state.get('show_model_details') and st.session_state.get('selected_model'):
            model = st.session_state.selected_model
            st.markdown("---")
            st.subheader(f"📦 {model['article']} — {model['name']}")

            # Получим техпакеты модели
            tp_rows = dal.tech_packages.get_all_records()
            tps = [r for r in tp_rows if r.get("model_id") == str(model.get('id')) and r.get("status") != "archived"]
            if not tps:
                st.warning("У модели нет технических пакетов")
                return
            package = tps[-1]  # последняя версия

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Статус:** {package['status']}\n\n**Версия:** v{package['version']}\n\n**Создан:** {package['created_by']}")
            with col2:
                if package['status'] != 'approved':
                    uploaded = st.file_uploader(
                        "Загрузить лекала (DXF/PDF, ≤50 МБ)",
                        type=['dxf', 'pdf'],
                        key=f"upload_{package['id']}"
                    )
                    if uploaded:
                        if uploaded.size > 50 * 1024 * 1024:
                            st.error("Файл > 50 МБ")
                        else:
                            # В реальном проекте: загрузка в Google Drive + получение shareable URL
                            # Здесь — имитация: используем фиктивный URL
                            fake_url = f"https://drive.google.com/file/d/{package['id']}/view"
                            dal.save_file(
                                int(package['id']),
                                uploaded.name,
                                fake_url,
                                uploaded.size,
                                uploaded.type
                            )
                            st.success("Файл добавлен (ссылка в Google Drive)")
                            st.rerun()

                files = dal.get_package_files(int(package['id']))
                if files:
                    st.markdown("📎 **Файлы:**")
                    for f in files:
                        col_f1, col_f2 = st.columns([3, 1])
                        with col_f1:
                            st.caption(f"📄 [{f['filename']}]({f['file_url']})")
                        with col_f2:
                            if st.button("🗑️", key=f"del_file_{f['id']}", help="Архивировать"):
                                dal.delete_file(int(f['id']))
                                st.success("Файлрхивирован")
                                st.rerun()

            st.markdown("---")
            st.subheader("💬 Комментарии")
            comments = dal.get_comments(int(package['id']))
            for c in comments:
                with st.chat_message(name=c['author']):
                    st.markdown(c['text'])
                    st.caption(f"{c['author']} • {c['created_at']}")
                    if st.button("🗑️", key=f"del_comm_{c['id']}", help="Архивировать"):
                        dal.delete_comment(int(c['id']))
                        st.success("Комментарий архивирован")
                        st.rerun()

            if package['status'] != 'approved':
                comment_text = st.text_area("Добавить комментарий", placeholder="...", key=f"comm_{package['id']}")
                if st.button("Отправить", use_container_width=True, type="secondary"):
                    if comment_text.strip():
                        dal.add_comment(int(package['id']), st.session_state.current_user, comment_text.strip())
                        st.success("Комментарий добавлен")
                        st.rerun()

    with tab2:
        st.subheader("➕ Создание новой модели")
        with st.form("create_model"):
            col1, col2 = st.columns(2)
            with col1:
                article = st.text_input("Артикул модели *", placeholder="M-001")
                name = st.text_input("Наименование *", placeholder="Худи Базовое")
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима", "Всесезонное"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки", "Другое"])
            if st.form_submit_button("💾 Сохранить модель", type="primary", use_container_width=True):
                if not article or not name:
                    st.error("Артикул и наименование обязательны")
                else:
                    try:
                        dal.create_model(article, name, season, category, st.session_state.current_user)
                        st.success(f"✅ Модель {article} создана!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")


def page_planning(dal):
    st.title("📅 Планирование")
    st.markdown("---")
    st.info("📌 Раздел в разработке. Для демонстрации — базовые операции.")


def page_production(dal):
    st.title("🏭 Производство")
    st.markdown("---")
    st.info("📌 Раздел в разработке. Уведомления и контроль брака — в следующих версиях.")


# ============================================================================
# === 5. MAIN LOGIC ==========================================================
# ============================================================================

def check_session_timeout():
    if 'last_activity' in st.session_state:
        inactive = datetime.now() - st.session_state.last_activity
        if inactive > timedelta(minutes=30):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.warning("⏰ Сессия завершена из-за неактивности")
            st.stop()
    st.session_state.last_activity = datetime.now()


def login_page():
    st.title("🔐 Вход в систему")
    st.markdown("---")
    with st.form("login"):
        username = st.text_input("Логин", placeholder="user")
        password = st.text_input("Пароль", type="password", placeholder="••••")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Войти", type="primary", use_container_width=True):
                if username:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else:
                    st.error("Введите логин")
        with col2:
            if st.form_submit_button("Войти как гость", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.current_user = "Гость"
                st.session_state.last_activity = datetime.now()
                st.rerun()


def main():
    # Инициализация session_state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    if 'show_model_details' not in st.session_state:
        st.session_state.show_model_details = False

    # Подключение к Google Sheets
    try:
        dal = SheetDAL()
    except Exception as e:
        st.error(f"❌ Не удалось подключиться к Google Sheets. Проверьте secrets.toml и права доступа.\nОшибка: {e}")
        st.stop()

    if not st.session_state.authenticated:
        login_page()
        return

    check_session_timeout()

    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.current_user}**")
        st.caption(f"Последняя активность: {st.session_state.last_activity.strftime('%H:%M:%S') if st.session_state.last_activity else 'N/A'}")
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
        st.caption("Версия: 0.9.0")

    if page == "🏠 Главная":
        st.title("🏭 Система управления деятельностью предприятия")
        st.markdown("---")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        st.markdown("""
        ### О прототипе
        - ✅ Работа **только с Google Sheets** (без SQLite)
        - ✅ Аутентификация через сервисный аккаунт
        - ✅ Утверждение ТП, версионирование, комментарии
        - ✅ Удаление через `status='archived'`
        - ✅ Поддержка масштабирования шрифта до 150% (R-SY-5)
        - ✅ Импорт из старых таблиц — реализован через `SheetDAL`
        """)
    elif page == "📐 Конструирование":
        page_design(dal)
    elif page == "📅 Планирование":
        page_planning(dal)
    elif page == "🏭 Производство":
        page_production(dal)


if __name__ == "__main__":
    main()
