import json
import os
import shutil
import sys
import tempfile

import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database import DatabaseDAO

ADMINS_PATH = os.path.join(os.path.dirname(__file__), "..", "admins.json")
BACKUP_PATH = ADMINS_PATH + ".bak"


@pytest.fixture(autouse=True)
def protect_admins():
    """Backup and restore admins.json so tests don't destroy it."""
    shutil.copy2(ADMINS_PATH, BACKUP_PATH)
    yield
    shutil.move(BACKUP_PATH, ADMINS_PATH)


@pytest.fixture
def db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = tmp.name
    tmp.close()

    # Write test operators to admins.json
    with open(ADMINS_PATH, "w", encoding="utf-8") as f:
        json.dump([{"username": "test_op", "password": "test123", "display_name": "Tester"}], f)

    dao = DatabaseDAO(db_path=db_path)
    dao._sync_operators()
    yield dao

    conn = dao._get_connection()
    conn.close()
    try:
        os.unlink(db_path)
    except PermissionError:
        pass


class TestUsers:
    def test_upsert_and_get_lang(self, db):
        db.upsert_user(telegram_id=1, full_name="Alice", username="@alice", lang="en")
        assert db.get_user_lang(1) == "en"

    def test_upsert_updates_last_seen(self, db):
        db.upsert_user(telegram_id=1, full_name="Alice", username="@alice", lang="en")
        db.upsert_user(telegram_id=1, full_name="Alice Updated", username="@alice", lang="kz")
        assert db.get_user_lang(1) == "kz"

    def test_get_lang_defaults_to_ru(self, db):
        assert db.get_user_lang(999) == "ru"


class TestSessions:
    def test_create_and_get_active(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="danger")
        active = db.get_active_session(telegram_id=1)
        assert active is not None
        assert active["id"] == session_id
        assert active["status"] == "waiting"

    def test_get_active_returns_none_when_closed(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="safe")
        db.update_session_status(session_id, status="closed")
        active = db.get_active_session(telegram_id=1)
        assert active is None

    def test_get_session_by_id(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="notsure")
        found = db.get_session_by_id(session_id)
        assert found is not None
        assert found["urgency"] == "notsure"


class TestBlacklist:
    def test_ban_and_is_banned(self, db):
        db.ban_user(telegram_id=1, full_name="Eve", username="@eve", reason="Spam", banned_by="admin")
        assert db.is_banned(1) is True

    def test_unban(self, db):
        db.ban_user(telegram_id=1, full_name="Eve", username="@eve", reason="Spam", banned_by="admin")
        db.unban_user(1)
        assert db.is_banned(1) is False

    def test_get_blacklist(self, db):
        db.ban_user(telegram_id=1, full_name="Eve", username="@eve", reason="Spam", banned_by="admin")
        bl = db.get_blacklist()
        assert len(bl) == 1
        assert bl[0]["reason"] == "Spam"


class TestMessages:
    def test_add_and_get_messages(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="danger")
        db.add_message(session_id=session_id, sender_type="kid", text="Hello")
        db.add_message(session_id=session_id, sender_type="operator", text="Hi there")
        msgs = db.get_session_messages(session_id)
        assert len(msgs) == 2
        assert msgs[0]["text"] == "Hello"
        assert msgs[0]["is_read"] == 0

    def test_mark_messages_read(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="danger")
        db.add_message(session_id=session_id, sender_type="kid", text="Hello")
        db.mark_messages_read(session_id)
        msgs = db.get_session_messages(session_id)
        assert msgs[0]["is_read"] == 1

    def test_add_message_with_photo(self, db):
        db.upsert_user(telegram_id=1, full_name="Bob", username="@bob", lang="ru")
        session_id = db.create_session(telegram_id=1, urgency="danger")
        db.add_message(session_id=session_id, sender_type="kid", text="See this", photo_id="abc123")
        msgs = db.get_session_messages(session_id)
        assert msgs[0]["photo_id"] == "abc123"


class TestOperators:
    def test_verify_operator_valid(self, db):
        op = db.verify_operator("test_op", "test123")
        assert op is not None
        assert op["display_name"] == "Tester"

    def test_verify_operator_invalid_password(self, db):
        op = db.verify_operator("test_op", "wrong")
        assert op is None

    def test_verify_operator_nonexistent(self, db):
        op = db.verify_operator("nobody", "pwd")
        assert op is None
