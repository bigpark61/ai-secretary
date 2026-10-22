from fastapi import HTTPException

from app.repository import (
    FirestoreConfigurationError,
    FirestoreRepository,
    create_firestore_client,
)


def get_repository() -> FirestoreRepository:
    try:
        return FirestoreRepository(create_firestore_client())
    except FirestoreConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
