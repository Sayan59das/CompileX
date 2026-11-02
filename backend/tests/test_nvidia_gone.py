"""Once NVIDIA says the model is retired (410 Gone), the image analysis stops asking on every question.

Run from the backend folder:  python -m pytest tests/test_nvidia_gone.py -q
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

from app.services.nvidia_image_service import NvidiaImageService


class Gone:
    status_code = 410
    text = "gone"


class FakeClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        FakeClient.calls += 1
        return Gone()


def test_a_410_switches_the_analysis_off_so_later_questions_make_no_call(monkeypatch):
    FakeClient.calls = 0
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    service = NvidiaImageService()
    assert asyncio.run(service.analyze_and_generate_image("Draw a tree")) is None
    assert service.llm_gone is True and FakeClient.calls == 1
    assert asyncio.run(service.analyze_and_generate_image("Another question")) is None
    assert FakeClient.calls == 1          # no second request
