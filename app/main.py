import json
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI, OpenAIError

from app.analytics import build_summary
from app.dependencies import get_repository
from app.models import (
    ChatRequest,
    ConversationCreate,
    DataRecordCreate,
    DataRecordUpdate,
)
from app.repository import FirestoreRepository


app = FastAPI(
    title="제조 데이터 분석 AI 비서",
    description="Firestore 기반 제조 데이터 관리, 요약 및 AI 질의응답 API",
    version="1.0.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/data", status_code=status.HTTP_201_CREATED)
def create_data(
    payload: DataRecordCreate,
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    try:
        return repository.create_data(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/data")
def list_data(
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    records = repository.list_data()
    return {"items": records, "count": len(records)}


@app.get("/api/data/summary")
def data_summary(
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    return build_summary(repository.list_data())


@app.put("/api/data/{record_id}")
def update_data(
    record_id: str,
    payload: DataRecordUpdate,
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    updated = repository.update_data(
        record_id,
        payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Data record not found.")
    return updated


@app.delete("/api/data/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data(
    record_id: str,
    repository: FirestoreRepository = Depends(get_repository),
) -> None:
    if not repository.delete_data(record_id):
        raise HTTPException(status_code=404, detail="Data record not found.")


@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    return repository.save_conversation(
        [message.model_dump() for message in payload.messages],
        title=payload.title,
    )


@app.get("/api/conversations")
def list_conversations(
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    conversations = repository.list_conversations()
    return {
        "items": [
            {
                "id": conversation["id"],
                "title": conversation.get("title", "새 대화"),
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at"),
            }
            for conversation in conversations
        ],
        "count": len(conversations),
    }


@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@app.delete(
    "/api/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: str,
    repository: FirestoreRepository = Depends(get_repository),
) -> None:
    if not repository.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")


@app.post("/api/chat")
def chat(
    payload: ChatRequest,
    repository: FirestoreRepository = Depends(get_repository),
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI chat is unavailable. Set OPENAI_API_KEY to enable it.",
        )

    conversation = (
        repository.get_conversation(payload.conversation_id)
        if payload.conversation_id
        else None
    )
    if payload.conversation_id and conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = list(conversation.get("messages", [])) if conversation else []
    messages.append({"role": "user", "content": payload.message})
    summary = build_summary(repository.list_data())
    system_message = (
        "당신은 제조 데이터 분석 비서입니다. 제공된 요약을 근거로 한국어로 간결하고 "
        "정확하게 답하세요. 데이터에 없는 사실은 추측하지 마세요. 원본에 날짜가 없으므로 "
        "RecordID 순서 비교를 시간 추세로 표현하지 마세요.\n\n"
        f"[현재 제조 데이터 요약]\n{json.dumps(summary, ensure_ascii=False)}"
    )
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_message},
                *messages,
            ],
            max_tokens=500,
        )
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI provider request failed: {exc}",
        ) from exc

    answer = response.choices[0].message.content
    if not answer:
        raise HTTPException(status_code=502, detail="AI provider returned an empty answer.")
    messages.append({"role": "assistant", "content": answer})
    saved = repository.save_conversation(
        messages,
        conversation_id=payload.conversation_id,
    )
    return {
        "conversation_id": saved["id"],
        "answer": answer,
        "messages": saved["messages"],
        "summary": summary,
    }


web_directory = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=web_directory, html=True), name="web")
