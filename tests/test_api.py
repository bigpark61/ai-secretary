from fastapi.testclient import TestClient

from app.dependencies import get_repository
from app.main import app
from app.repository import FirestoreConfigurationError, _read_service_account_json


class FakeRepository:
    def __init__(self):
        self.data = {}
        self.conversations = {}

    def list_data(self):
        return list(self.data.values())

    def get_data(self, record_id):
        return self.data.get(record_id)

    def create_data(self, record):
        record_id = record.pop("id", None) or f"record-{len(self.data) + 1}"
        if record_id in self.data:
            raise ValueError(f"Data record '{record_id}' already exists.")
        self.data[record_id] = {"id": record_id, **record}
        return self.data[record_id]

    def update_data(self, record_id, record):
        if record_id not in self.data:
            return None
        self.data[record_id].update(record)
        return self.data[record_id]

    def delete_data(self, record_id):
        return self.data.pop(record_id, None) is not None

    def list_conversations(self):
        return list(self.conversations.values())

    def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    def save_conversation(self, messages, conversation_id=None, title=None):
        conversation_id = conversation_id or f"conversation-{len(self.conversations) + 1}"
        conversation = {
            "id": conversation_id,
            "title": title or messages[0]["content"][:120],
            "messages": messages,
        }
        self.conversations[conversation_id] = conversation
        return conversation

    def delete_conversation(self, conversation_id):
        return self.conversations.pop(conversation_id, None) is not None


def setup_client():
    repository = FakeRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    return TestClient(app), repository


def teardown_function():
    app.dependency_overrides.clear()


def sample_data():
    return {
        "production_volume": 120,
        "defect_rate": 1.5,
        "energy_consumption": 900,
        "energy_efficiency": 0.8,
        "downtime_percentage": 2,
        "maintenance_hours": 4,
        "energy_per_unit": 7.5,
        "source_record_id": 1,
    }


def test_data_crud_and_summary():
    client, _ = setup_client()
    created = client.post("/api/data", json=sample_data())
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert client.post(
        "/api/data",
        json={**sample_data(), "source_record_id": 2},
    ).status_code == 201

    listing = client.get("/api/data")
    assert listing.status_code == 200
    assert listing.json()["count"] == 2
    assert listing.json()["items"][0]["production_volume"] == 120

    summary = client.get("/api/data/summary").json()
    assert summary["count"] == 2
    assert summary["metrics"]["production_volume"]["average"] == 120
    assert summary["trend"]["production_volume"]["direction"] == "유지"

    updated = client.put(
        f"/api/data/{record_id}",
        json={**sample_data(), "production_volume": 150},
    )
    assert updated.status_code == 200
    assert updated.json()["production_volume"] == 150
    assert client.delete(f"/api/data/{record_id}").status_code == 204
    assert client.delete(f"/api/data/{record_id}").status_code == 404


def test_data_validation_and_duplicate_id():
    client, _ = setup_client()
    invalid = client.post("/api/data", json={**sample_data(), "defect_rate": 101})
    assert invalid.status_code == 422
    assert client.post("/api/data", json={**sample_data(), "id": "fixed"}).status_code == 201
    assert client.post("/api/data", json={**sample_data(), "id": "fixed"}).status_code == 409


def test_conversation_save_load_and_delete():
    client, _ = setup_client()
    saved = client.post(
        "/api/conversations",
        json={
            "messages": [
                {"role": "user", "content": "평균 생산량은?"},
                {"role": "assistant", "content": "평균 생산량은 120입니다."},
            ]
        },
    )
    assert saved.status_code == 201
    conversation_id = saved.json()["id"]
    assert client.get("/api/conversations").json()["items"][0]["title"] == "평균 생산량은?"
    assert len(client.get(f"/api/conversations/{conversation_id}").json()["messages"]) == 2
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 204


def test_chat_requires_openai_key(monkeypatch):
    client, _ = setup_client()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/chat", json={"message": "생산량을 알려줘"})
    assert response.status_code == 503


def test_multiline_firebase_json_is_read_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'FIREBASE_SERVICE_ACCOUNT_JSON={\n  "type": "service_account",\n'
        '  "private_key": "line1\\\\nline2"\n}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{")
    monkeypatch.setenv("ENV_FILE", str(env_file))

    assert _read_service_account_json() == {
        "type": "service_account",
        "private_key": "line1\\nline2",
    }


def test_invalid_firebase_json_has_actionable_error(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("FIREBASE_SERVICE_ACCOUNT_JSON={invalid\n", encoding="utf-8")
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{")
    monkeypatch.setenv("ENV_FILE", str(env_file))

    try:
        _read_service_account_json()
    except FirestoreConfigurationError as exc:
        assert "must contain valid JSON" in str(exc)
    else:
        raise AssertionError("Invalid Firebase JSON should raise a configuration error.")


def test_chat_saves_answer_and_context(monkeypatch):
    client, _ = setup_client()
    client.post("/api/data", json=sample_data())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponse:
        class Choice:
            class Message:
                content = "평균 생산량은 120입니다."

            message = Message()

        choices = [Choice()]

    class FakeCompletions:
        def create(self, **_kwargs):
            return FakeResponse()

    class FakeClient:
        class Chat:
            completions = FakeCompletions()

        chat = Chat()

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr("app.main.OpenAI", FakeClient)
    response = client.post("/api/chat", json={"message": "생산량을 알려줘"})
    assert response.status_code == 200
    assert response.json()["answer"] == "평균 생산량은 120입니다."
    assert response.json()["summary"]["count"] == 1
    conversation_id = response.json()["conversation_id"]
    assert len(client.get(f"/api/conversations/{conversation_id}").json()["messages"]) == 2
