"""Outside production every WhatsApp send goes to TEST_FORWARD_NUMBER."""
import asyncio

import httpx

from config import settings
from services import whatsapp


def _capture(monkeypatch):
    sent = []

    class FakeResp:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"messages": [{"id": "wamid.X"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            sent.append(json["to"])
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    return sent


def _send_all():
    async def go():
        await whatsapp.send_text("+919999999999", "hi")
        await whatsapp.send_document("+919999999999", "http://x/y.pdf")
        await whatsapp.send_template("+919999999999", "t")
    asyncio.run(go())


def test_staging_redirects_every_send(monkeypatch):
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "test_forward_number", "919010109555")
    sent = _capture(monkeypatch)
    _send_all()
    assert sent == ["+919010109555"] * 3


def test_production_never_redirects(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "test_forward_number", "919010109555")
    sent = _capture(monkeypatch)
    _send_all()
    assert sent == ["+919999999999"] * 3
