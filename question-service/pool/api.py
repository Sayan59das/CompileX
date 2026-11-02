"""The HTTP routes of the question pool. Thin on purpose: every decision is made in QuestionService.

    GET  /api/question?topic=&difficulty=&player_id=      a question for one player or a lobby (repeat player_id, or comma separated)
    GET  /api/question/prefetch?...                       the same, for fetching the next question in the background (it also
                                                          counts as served, so the player never gets it twice)
    GET  /api/pool/status                                 sizes per topic and difficulty, counted from the database
    POST /api/submit                                      grade the outputs a player's program produced against the hidden tests
    GET  /internal/questions/{id}/tests                   the hidden tests, for the backend's code runner (needs X-Internal-Token)

Nothing here calls a model, the verifier or a generator.
"""

import hmac
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .service import NoQuestion, QuestionService

DIFFICULTIES = ("easy", "medium", "hard")


class SubmitRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    results: List[str]


def players_from(values: Optional[List[str]]) -> list[str]:
    """['1,2', '3'] -> ['1', '2', '3']"""
    return [p.strip() for value in values or [] for p in value.split(",") if p.strip()]


def build_router(service: QuestionService, internal_token: Optional[str] = None) -> APIRouter:
    router = APIRouter()

    def serve(topic: str, difficulty: str, player_id: Optional[List[str]], prefetch: bool) -> dict:
        level = difficulty.strip().lower()
        if level not in DIFFICULTIES:
            raise HTTPException(status_code=400, detail="difficulty must be 'easy', 'medium' or 'hard'")
        players = players_from(player_id)
        if not players:
            raise HTTPException(status_code=400, detail="player_id is required")
        try:
            question = service.get_question(topic, level, players)
        except NoQuestion as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        question["prefetched"] = prefetch
        return question

    @router.get("/api/question")
    def get_question(topic: str, difficulty: str, player_id: Optional[List[str]] = Query(default=None)):
        return serve(topic, difficulty, player_id, False)

    @router.get("/api/question/prefetch")
    def prefetch_question(topic: str, difficulty: str, player_id: Optional[List[str]] = Query(default=None)):
        return serve(topic, difficulty, player_id, True)

    @router.get("/api/pool/status")
    def pool_status():
        return service.status()

    @router.post("/api/submit")
    def submit(body: SubmitRequest):
        try:
            return service.grade(body.question_id, body.results)
        except NoQuestion as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.get("/internal/questions/{question_id}/tests")
    def hidden_tests(question_id: str, x_internal_token: Optional[str] = Header(default=None)):
        if not internal_token:
            raise HTTPException(status_code=403, detail="the internal endpoints are disabled (INTERNAL_TOKEN is not set)")
        if not x_internal_token or not hmac.compare_digest(x_internal_token, internal_token):
            raise HTTPException(status_code=403, detail="bad token")
        tests = service.tests(question_id)
        if tests is None:
            raise HTTPException(status_code=404, detail=f"unknown question {question_id}")
        return {"question_id": question_id, "tests": tests}

    return router
