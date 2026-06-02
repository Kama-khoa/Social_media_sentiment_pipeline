from unittest.mock import MagicMock

from nlp import gemini_gateway


def test_gateway_routes_to_next_model_after_rate_limit(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = [
        RuntimeError("429 resource exhausted"),
        MagicMock(text="fallback result"),
    ]
    monkeypatch.setattr(gemini_gateway._RateLimiter, "wait", lambda self, model_name: None)

    gateway = gemini_gateway.GeminiGateway(client=client)

    assert gateway.generate("prompt") == "fallback result"
    assert gateway.last_model == gateway._available_models[1]
    assert client.models.generate_content.call_count == 2


def test_gateway_waits_before_each_request(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value.text = "ok"
    waits = []
    monkeypatch.setattr(gemini_gateway._RateLimiter, "wait", lambda self, model_name: waits.append(model_name))

    gateway = gemini_gateway.GeminiGateway(client=client)
    gateway.generate("first")
    gateway.generate("second")

    assert waits == [gateway._available_models[0], gateway._available_models[0]]
