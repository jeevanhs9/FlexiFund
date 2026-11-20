"""Authenticated financial-assistant chat and per-account conversation history."""

from __future__ import annotations

from uuid import UUID, uuid4

from flask import Blueprint, request
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import authenticated_blueprint, authenticated_user_id, authorize_body_user_id
from app.database import session_scope
from app.models import AssistantMessage
from app.routes.helpers import error_response, parse_json_body, success_response
from app.schemas import AssistantChatCreate
from app.services.ai_assistant import add_explanation, build_verified_response


assistant_bp = authenticated_blueprint(
    Blueprint("assistant", __name__, url_prefix="/api/assistant")
)
HISTORY_LIMIT = 40
MEMORY_LIMIT = 8


def _normalize_conversation_id(value: str | None) -> tuple[str | None, object | None]:
    if value is None:
        return None, None
    try:
        return str(UUID(value)), None
    except (ValueError, TypeError, AttributeError):
        return None, error_response("conversation_id must be a valid UUID.", 400)


def _serialize(message: AssistantMessage) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "message": message.message,
        "timestamp": message.created_at.isoformat(),
    }


@assistant_bp.post("/chat")
def chat():
    body, error = parse_json_body(AssistantChatCreate)
    if error:
        return error_response(error)
    user_id = authenticated_user_id()
    user_id_error = authorize_body_user_id(body.user_id)
    if user_id_error:
        return user_id_error

    conversation_id, conversation_error = _normalize_conversation_id(body.conversation_id)
    if conversation_error:
        return conversation_error
    conversation_id = conversation_id or str(uuid4())

    try:
        with session_scope() as database_session:
            foreign_owner = database_session.scalar(
                select(AssistantMessage.user_id)
                .where(AssistantMessage.conversation_id == conversation_id)
                .limit(1)
            )
            if foreign_owner is not None and foreign_owner != user_id:
                return error_response("Conversation was not found.", 404)
            recent_rows = database_session.scalars(
                select(AssistantMessage)
                .where(
                    AssistantMessage.user_id == user_id,
                    AssistantMessage.conversation_id == conversation_id,
                )
                .order_by(AssistantMessage.id.desc())
                .limit(MEMORY_LIMIT)
            ).all()
            recent_history = [
                {"role": row.role, "content": row.message[:800]}
                for row in reversed(recent_rows)
            ]

        with session_scope() as database_session:
            verified = build_verified_response(
                database_session,
                user_id=user_id,
                question=body.question,
            )
        result = add_explanation(verified, history=recent_history)

        with session_scope() as database_session:
            database_session.add_all(
                [
                    AssistantMessage(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        role="user",
                        message=body.question,
                    ),
                    AssistantMessage(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        role="assistant",
                        message=result["stored_message"],
                    ),
                ]
            )
            database_session.flush()
            latest_rows = database_session.scalars(
                select(AssistantMessage)
                .where(
                    AssistantMessage.user_id == user_id,
                    AssistantMessage.conversation_id == conversation_id,
                )
                .order_by(AssistantMessage.id.desc())
                .limit(2)
            ).all()
            messages = [_serialize(row) for row in reversed(latest_rows)]
    except SQLAlchemyError:
        return error_response("Assistant history is temporarily unavailable.", 503)

    result.pop("stored_message", None)
    return success_response(
        {
            "conversation_id": conversation_id,
            "intent": result["intent"],
            "factual_calculation": result["factual_calculation"],
            "factual_answer": result["factual_answer"],
            "ai_explanation": result["ai_explanation"],
            "answer": result["answer"],
            "explanation_source": result["explanation_source"],
            "ai_status": result["ai_status"],
            "messages": messages,
        }
    )


@assistant_bp.get("/history")
def get_history():
    user_id = authenticated_user_id()
    conversation_id, error = _normalize_conversation_id(request.args.get("conversation_id"))
    if error:
        return error
    try:
        with session_scope() as database_session:
            if conversation_id:
                owner = database_session.scalar(
                    select(AssistantMessage.user_id)
                    .where(AssistantMessage.conversation_id == conversation_id)
                    .limit(1)
                )
                if owner is not None and owner != user_id:
                    return error_response("Conversation was not found.", 404)
            else:
                conversation_id = database_session.scalar(
                    select(AssistantMessage.conversation_id)
                    .where(AssistantMessage.user_id == user_id)
                    .order_by(AssistantMessage.id.desc())
                    .limit(1)
                )
            if conversation_id is None:
                return success_response({"conversation_id": None, "messages": []})
            rows = database_session.scalars(
                select(AssistantMessage)
                .where(
                    AssistantMessage.user_id == user_id,
                    AssistantMessage.conversation_id == conversation_id,
                )
                .order_by(AssistantMessage.id.desc())
                .limit(HISTORY_LIMIT)
            ).all()
            messages = [_serialize(row) for row in reversed(rows)]
    except SQLAlchemyError:
        return error_response("Assistant history is temporarily unavailable.", 503)
    return success_response({"conversation_id": conversation_id, "messages": messages})


@assistant_bp.delete("/history")
def clear_history():
    user_id = authenticated_user_id()
    conversation_id, error = _normalize_conversation_id(request.args.get("conversation_id"))
    if error:
        return error
    try:
        with session_scope() as database_session:
            query = delete(AssistantMessage).where(AssistantMessage.user_id == user_id)
            if conversation_id:
                owner = database_session.scalar(
                    select(AssistantMessage.user_id)
                    .where(AssistantMessage.conversation_id == conversation_id)
                    .limit(1)
                )
                if owner is not None and owner != user_id:
                    return error_response("Conversation was not found.", 404)
                query = query.where(AssistantMessage.conversation_id == conversation_id)
            result = database_session.execute(query)
            deleted_count = result.rowcount or 0
    except SQLAlchemyError:
        return error_response("Assistant history could not be cleared.", 503)
    return success_response({"deleted_messages": deleted_count})
