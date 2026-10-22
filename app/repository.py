from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Any


class FirestoreConfigurationError(RuntimeError):
    """Raised when Firestore credentials are missing or invalid."""


def _read_service_account_json() -> dict[str, Any]:
    configured_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if configured_json:
        try:
            parsed = json.loads(configured_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    env_file = Path(os.getenv("ENV_FILE", Path.cwd() / ".env"))
    if env_file.is_file():
        contents = env_file.read_text(encoding="utf-8-sig")
        assignment = "FIREBASE_SERVICE_ACCOUNT_JSON="
        for line in contents.splitlines():
            if line.strip().startswith(assignment):
                start = contents.index(line) + line.index(assignment) + len(assignment)
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(contents[start:].lstrip())
                except json.JSONDecodeError as exc:
                    raise FirestoreConfigurationError(
                        "FIREBASE_SERVICE_ACCOUNT_JSON in .env must contain valid JSON."
                    ) from exc
                if isinstance(parsed, dict):
                    return parsed
                break

    raise FirestoreConfigurationError(
        "Set FIREBASE_SERVICE_ACCOUNT_JSON to valid JSON or "
        "FIREBASE_SERVICE_ACCOUNT_PATH to a service-account file."
    )


@lru_cache(maxsize=1)
def create_firestore_client() -> Any:
    import firebase_admin
    from firebase_admin import credentials, firestore

    try:
        app = firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if service_account_json:
            try:
                service_account_info = _read_service_account_json()
            except FirestoreConfigurationError:
                raise
            credential = credentials.Certificate(service_account_info)
        elif service_account_path or application_credentials:
            credential = credentials.Certificate(
                service_account_path or application_credentials
            )
        else:
            raise FirestoreConfigurationError(
                "Set FIREBASE_SERVICE_ACCOUNT_JSON or "
                "FIREBASE_SERVICE_ACCOUNT_PATH to connect to Firestore."
            )

        app = firebase_admin.initialize_app(credential)

    return firestore.client(app=app)


class FirestoreRepository:
    def __init__(self, client: Any):
        self.client = client

    def list_data(self) -> list[dict[str, Any]]:
        records = [
            {"id": document.id, **document.to_dict()}
            for document in self.client.collection("data").stream()
        ]
        return sorted(
            records,
            key=lambda record: (
                record.get("source_record_id") is None,
                record.get("source_record_id") or 0,
                record["id"],
            ),
        )

    def get_data(self, record_id: str) -> dict[str, Any] | None:
        document = self.client.collection("data").document(record_id).get()
        if not document.exists:
            return None
        return {"id": document.id, **document.to_dict()}

    def create_data(self, record: dict[str, Any]) -> dict[str, Any]:
        collection = self.client.collection("data")
        record_id = record.pop("id", None)
        document = collection.document(record_id) if record_id else collection.document()
        if record_id and document.get().exists:
            raise ValueError(f"Data record '{record_id}' already exists.")
        now = _now()
        document.set({**record, "created_at": now, "updated_at": now})
        return {"id": document.id, **record, "created_at": now, "updated_at": now}

    def update_data(
        self, record_id: str, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        document = self.client.collection("data").document(record_id)
        if not document.get().exists:
            return None
        updated = {**record, "updated_at": _now()}
        document.update(updated)
        return self.get_data(record_id)

    def delete_data(self, record_id: str) -> bool:
        document = self.client.collection("data").document(record_id)
        if not document.get().exists:
            return False
        document.delete()
        return True

    def upsert_data(self, records: list[dict[str, Any]]) -> int:
        for offset in range(0, len(records), 400):
            batch = self.client.batch()
            for record in records[offset : offset + 400]:
                item = dict(record)
                record_id = item.pop("id")
                document = self.client.collection("data").document(record_id)
                now = _now()
                item["updated_at"] = now
                if not document.get().exists:
                    item["created_at"] = now
                batch.set(document, item, merge=True)
            batch.commit()
        return len(records)

    def list_conversations(self) -> list[dict[str, Any]]:
        conversations = [
            {"id": document.id, **document.to_dict()}
            for document in self.client.collection("conversations").stream()
        ]
        return sorted(
            conversations,
            key=lambda conversation: conversation.get("updated_at", ""),
            reverse=True,
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        document = self.client.collection("conversations").document(conversation_id).get()
        if not document.exists:
            return None
        return {"id": document.id, **document.to_dict()}

    def save_conversation(
        self,
        messages: list[dict[str, str]],
        conversation_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        collection = self.client.collection("conversations")
        document = (
            collection.document(conversation_id)
            if conversation_id
            else collection.document()
        )
        existing = document.get()
        now = _now()
        first_user_message = next(
            (message["content"] for message in messages if message["role"] == "user"),
            "새 대화",
        )
        data = {
            "title": title or first_user_message[:120],
            "messages": messages,
            "updated_at": now,
        }
        if not existing.exists:
            data["created_at"] = now
        document.set(data, merge=True)
        return {"id": document.id, **data}

    def delete_conversation(self, conversation_id: str) -> bool:
        document = self.client.collection("conversations").document(conversation_id)
        if not document.get().exists:
            return False
        document.delete()
        return True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
