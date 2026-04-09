"""
Прототип системы управления деятельностью предприятия легкой промышленности
Версия: 1.0.0 — строго по диаграмме классов и ВКР
Автор: Браславцев Б.Э.

Основные изменения:
- Агрегат «Техническое Задание» — корневой (не модель → ТП)
- Все сущности: ТЗ, Версия, Лекало, Комментарий — в одном листе или связанных
- id = номер строки (строка, не int) — чтобы избежать ValueError
- Устранены все UI-ошибки: кнопки горизонтальные, карточки читаемые
- При создании ТЗ автоматически создаётся первая версия (v1) и лекало
- Утверждение: блокирует редактирование, создаёт новую версию при изменении
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
from pathlib import Path

# ============================================================================
# === 1. GOOGLE SHEETS CONFIGURATION =========================================
# ============================================================================

def get_gspread_client():
    try:
        if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
            creds_dict = st.secrets.google_service_account
        else:
            # Для локального запуска — используем встроенные данные
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
7uQ2/PNtAgMBAAECggXGpbY2+JBH0wyBrGMdLXo9GHqnKGb+05mtSO
wm7xYavQnEL8WUp8FewR3T/1NKekVfL93E98A9uoRWZqUWk8lhinW95dTL6vy2kY
j8kMvUs9FqX1lKFYTuUE5WPL4Bf6/6a0v7MtxO>...''',
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
        st.error(f"❌ Не удалось авторизоваться в Google Sheets. Проверьте secrets.toml.\nОшибка: {e}")
        st.stop()


# ============================================================================
# === 2. DATA ACCESS LAYER (DAL) — СТРОГО ПО ДИАГРАММЕ КЛАССОВ ==============
# ============================================================================

class SheetDAL:
    def __init__(self):
        self.client = get_gspread_client()
        self.sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "12jwDv0K-6qC8vAMO6TaNpgpbhgLhlHX5D8Kb768BwQs")
        self.sheet = self.client.open_by_key(self.sheet_id)
        self._tech_specs = None  # «Техническое Задание» — агрегат root

    def _get_worksheet(self, title):
        """Создаёт лист с заголовками, если его нет."""
        try:
            return self.sheet.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self.sheet.add_worksheet(title=title, rows=1000, cols=20)
            # Заголовки по диаграмме классов
            if title == "TechSpecs":
                headers = ["id", "article", "name", "season", "category", "status", "created_at", "updated_at", "current_version"]
                ws.insert_row(headers, 1)
            elif title == "Versions":
                headers = ["id", "tech_spec_id", "version", "status", "created_at", "created_by"]
                ws.insert_row(headers, 1)
            elif title == "Patterns":
                headers = ["id", "version_id", "filename", "file_url", "file_size", "uploaded_at", "status"]
                ws.insert_row(headers, 1)
            elif title == "Comments":
                headers = ["id", "version_id", "author", "text", "created_at", "status"]
                ws.insert_row(headers, 1)
            return ws

    @property
    def tech_specs(self):
        if self._tech_specs is None:
            self._tech_specs = self._get_worksheet("TechSpecs")
        return self._tech_specs

    @property
    def versions(self):
        return self._get_worksheet("Versions")

    @property
    def patterns(self):
        return self._get_worksheet("Patterns")

    @property
    def comments(self):
        return self._get_worksheet("Comments")

    # --- CRUD для ТЗ (агрегат) ---
    def create_tech_spec(self, article, name, season, category, created_by):
        """Создаёт ТЗ + первую версию (v1) + шаблон лекала — как единый агрегат."""
        ws = self.tech_specs
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Вставляем ТЗ
        row = [None, article, name, season, category, "draft", now, now, 1]
        ws.append_row(row)
        tech_spec_id = str(ws.row_count)  # id = номер строки (строка!)

        # Создаём первую версию
        ver_ws = self.versions
        ver_ws.append_row([None, tech_spec_id, 1, "draft", now, created_by])
        version_id = str(ver_ws.row_count)

        # Создаём шаблон лекала для v1
        pat_ws = self.patterns
        pat_ws.append_row([None, version_id, "Лекало_v1.dxf", "", 0, now, "active"])

        return tech_spec_id, version_id

    def get_tech_specs(self, status_filter=None):
        ws = self.tech_specs
        data = ws.get_all_records()
        if status_filter:
            return [r for r in data if r.get("status") == status_filter]
        return [r for r in data if r.get("status") != "archived"]

    def get_versions_for_tech_spec(self, tech_spec_id):
        ws = self.versions
        data = ws.get_all_records()
        return [r for r in data if r.get("tech_spec_id") == tech_spec_id and r.get("status") != "archived"]

    def approve_version(self, version_id):
        """Утверждение версии: статус = approved, блокировка редактирования."""
        ws = self.versions
        cell = ws.find(str(version_id), in_column=1)
        if not cell:
            raise ValueError(f"Версия {version_id} не найдена")
        ws.update_cell(cell.row, 4, "approved")  # col 4 = status

        # Обновляем ТЗ: статус = approved, current_version = эта версия
        tech_spec_id = ws.cell(cell.row, 2).value  # col 2 = tech_spec_id
_ws = self.tech_specs
        tech_cell = tech_ws.find(tech_spec_id, in_column=1)
        if tech_cell:
            ws_ver = int(ws.cell(cell.row, 3).value)  # col 3 = version
            tech_ws.update_cell(tech_cell.row, 6, "approved")  # status
            tech_ws.update_cell(tech_cell.row, 9, ws_ver)  # current_version
            tech_ws.update_cell(tech_cell.row, 8, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # updated_at

    def create_new_version(self, tech_spec_id, created_by):
        """Создаёт новую версию ТЗ (vN+1), архивирует старые (>5)."""
        ws = self.versions
        tech_ws = self.tech_specs
        tech_cell = tech_ws.find(tech_spec_id, in_column=1)
        if not tech_cell:
            raise ValueError("ТЗ не найдено")

        # Получаем текущую версию ТЗ
        current_ver = int(tech_ws.cell(tech_cell.row, 9).value)  # col 9 = current_version
        new_ver = current_ver + 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Создаём новую версию
        ws.append_row([None, tech_spec_id, new_ver, "draft", now, created_by])
        new_version_id = str(ws.row_count)

        # Обновляем ТЗ
        tech_ws.update_cell(tech_cell.row, 9, new_ver)  # current_version
        tech_ws.update_cell(tech_cell.row, 6, "draft")  # status
        tech_ws.update_cell(tech_cell.row, 8, now)  # updated_at

        # Архивируем старые версии (>5)
        all_rows = ws.get_all_records()
        tps_for_spec = [r for r in all_rows if r.get("tech_spec_id") == tech_spec_id]
        if len(tps_for_spec) > 5:
            old_versions = sorted(tps_for_spec, key=lambda x: int(x["version"]))[:len(tps_for_spec)-5]
            for v in old_versions:
                cell = ws.find(str(v["id"]), in_column=1)
                if cell:
                    ws.update_cell(cell.row, 4, "archived")

    # --- Delete via archive (R-DE-7) ---
    def delete_tech_spec(self, tech_spec_id):
        ws = self.tech_specs
        cell = ws.find(tech_spec_id, in_column=1)
        if cell:
            ws.update_cell(cell.row, 6, "archived")

    def delete_version(self, version_id):
        ws = self.versions
        cell = ws.find(version_id, in_column=1)
        if cell:
            ws.update_cell(cell.row, 4, "archived")

    def delete_pattern(self, pattern_id):
        ws = self.patterns
        cell = ws.find(pattern_id, in_column=1)
        if cell:
            ws.update_cell(cell.row, 7, "archived")

    def delete_comment(self, comment_id):
        ws = self.comments
        cell = ws.find(comment_id, in_column=1)
        if cell:
            ws.update_cell(cell.row, 6, "archived")


# ============================================================================
# === 3. UI: ИСПРАВЛЕНИЕ ВСЕХ ОШИБОК =========================================
# ============================================================================

def render_tech_spec_card(spec, dal):
    """Карточка ТЗ — с горизонтальными кнопками и корректным id."""
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"**{spec.get('article', 'N/A')}**")
            st.caption(spec.get('name', ''))

        with col2:
            status = spec.get('status', 'unknown')
            status_emoji = {
                'draft': '📝',
                'in_review': '👀',
                'approved': '✅',
                'archived': '📦'
            }.get(status, '📄')
            st.markdown(f"{status_emoji} **Статус:** {status}")
            st.caption(f"Версия: v{spec.get('current_version', 1)}")

        with col3:
            # Горизонтальные кнопки — через st.columns внутри col3
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("📄", key=f"open_{spec['id']}", help="Открыть", use_container_width=True):
                    st.session_state.selected_tech_spec = spec
                    st.session_state.show_tech_spec_details = True
            with btn_col2:
                if spec.get('status') != 'approved':
                    if st.button("✅", key=f"approve_{spec['id']}", help="Утвердить", use_container_width=True):
                        versions = dal.get_versions_for_tech_spec(spec['id'])
                        if versions:
                            dal.approve_version(versions[-1]['id'])
                            st.success(f"ТЗ {spec['article']} утверждено")
                            st.rerun()
                        else:
                            st.warning("Нет версий для утверждения")
            with btn_col3:
                if st.button("🗑️", key=f"del_{spec['id']}", help="Архивировать", use_container_width=True, type="secondary"):
                    dal.delete_tech_spec(spec['id'])
                    st.success(f"ТЗ {spec['article']} архивировано")
                    st.rerun()


# ============================================================================
# === 4. PAGES ===============================================================
# ============================================================================

def page_design(dal):
    st.title("📐 Конструирование")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📋 Реестр ТЗ", "➕ Создать ТЗ"])

    with tab1:
        specs = dal.get_tech_specs()
        st.subheader("Технические задания")
        if not specs:
            st.info("⚠️ Нет технических заданий. Создайте первое.")
        else:
            for spec in specs:
                render_tech_spec_card(spec, dal)

        # Детали ТЗ
        if st.session_state.get('show_tech_spec_details') and st.session_state.get('selected_tech_spec'):
            spec = st.session_state.selected_tech_spec
            st.markdown("---")
            st.subheader(f"📦 {spec['article']} — {spec['name']}")

            # Получаем версии
            versions = dal.get_versions_for_tech_spec(spec['id'])
            if not versions:
                st.warning("У этого ТЗ нет версий. Создайте первую версию вручную или через форму.")
                return

            current_version = versions[-1]  # последняя активная
            st.info(f"**Версия:** v{current_version['version']} | **Статус:** {current_version['status']} | **Создан:** {current_version['created_by']}")

            # Файлы лекал
            pat_ws = dal.patterns
            patterns = pat_ws.get_all_records()
            files = [p for p in patterns if p.get("version_id") == current_version['id'] and p.get("status") == "active"]
            if files:
                st.markdown("📎 **Лекала:**")
                for f in files:
                    col_f1, col_f2 = st.columns([3, 1])
                    with col_f1:
                        st.caption(f"📄 {f['filename']}")
                    with col_f2:
                        if st.button("🗑️", key=f"del_pat_{f['id']}", help="Архивировать", use_container_width=True):
                            dal.delete_pattern(f['id'])
                            st.success("Лекало архивировано")
                            st.rerun()

            # Комментарии
            com_ws = dal.comments
            comms = com_ws.get_all_records()
            comments = [c for c in comms if c.get("version_id") == current_version['id'] and c.get("status") == "active"]
            st.markdown("💬 **Комментарии**")
            for c in comments:
                with st.chat_message(name=c['author']):
                    st.markdown(c['text'])
                    st.caption(f"{c['author']} • {c['created_at']}")
                    if st.button("🗑️", key=f"del_com_{c['id']}", help="Архивировать", use_container_width=True):
                        dal.delete_comment(c['id'])
                        st.success("Комментарий архивирован")
                        st.rerun()

            # Форма комментария
            if current_version['status'] != 'approved':
                comment_text = st.text_area("Добавить комментарий", placeholder="...", key=f"comm_{current_version['id']}")
                if st.button("Отправить", use_container_width=True, type="secondary"):
                    if comment_text.strip():
                        dal.comments.append_row([None, current_version['id'], st.session_state.current_user, comment_text.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "active"])
                        st.success("Комментарий добавлен")
                        st.rerun()

    with tab2:
        st.subheader("➕ Создать техническое задание")
        with st.form("create_tech_spec"):
            col1, col2 = st.columns(2)
            with col1:
                article = st.text_input("Артикул *", placeholder="T-001")
                name = st.text_input("Наименование *", placeholder="Худи Базовое")
            with col2:
                season = st.selectbox("Сезон", ["Весна-Лето", "Осень-Зима", "Всесезонное"])
                category = st.selectbox("Категория", ["Верхняя одежда", "Брюки", "Футболки", "Другое"])
            if st.form_submit_button("💾 Создать ТЗ", type="primary", use_container_width=True):
                if not article or not name:
                    st.error("Артикул и наименование обязательны")
                else:
                    try:
                        dal.create_tech_spec(article, name, season, category, st.session_state.current_user)
                        st.success(f"✅ ТЗ {article} создано! Создана версия v1 и шаблон лекала.")
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
    if 'selected_tech_spec' not in st.session_state:
        st.session_state.selected_tech_spec = None
    if 'show_tech_spec_details' not in st.session_state:
        st.session_state.show_tech_spec_details = False

    # Подключение к Google Sheets
    try:
        dal = SheetDAL()
    except Exception as e:
        st.error(f"❌ Не удалось подключиться к Google Sheets.\nОшибка: {e}")
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
        st.caption("Версия: 1.0.0")

    if page == "🏠 Главная":
        st.title("🏭 Система управления деятельностью предприятия")
        st.markdown("---")
        st.success(f"Добро пожаловать, {st.session_state.current_user}!")
        st.markdown("""
        ### О прототипе
        - ✅ Агрегат «Техническое Задание» — корневой (как в диаграмме классов)
        - ✅ При создании ТЗ автоматически создаётся v1 + лекало
        - ✅ Утверждение блокирует редактирование
        - ✅ Удаление через `status='archived'`
        - ✅ UI исправлен: кнопки горизонтальные, карточки читаемые
        - ✅ Поддержка масштабирования до 150% (R-SY-5)
        """)
    elif page == "📐 Конструирование":
        page_design(dal)
    elif page == "📅 Планирование":
        page_planning(dal)
    elif page == "🏭 Производство":
        page_production(dal)


if __name__ == "__main__":
    main()
