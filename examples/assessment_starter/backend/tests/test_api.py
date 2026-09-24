import pytest
from fastapi.testclient import TestClient

from assessment_starter.core.config import Settings
from assessment_starter.fixtures import make_model
from assessment_starter.main import create_app


def test_health_and_answer() -> None:
    model = make_model()
    with TestClient(create_app(model=model)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/api/v1/ask", json={"question": "Hello"})
    assert response.status_code == 200
    assert "offline answer" in response.json()["answer"]
    assert model.chat_calls == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": " "},
        {"question": 3},
        {"question": "x" * 4001},
        {"question": "ok", "provider": "unexpected"},
    ],
)
def test_invalid_request_never_invokes_model(body: dict[str, object]) -> None:
    model = make_model()
    with TestClient(create_app(model=model)) as client:
        assert client.post("/api/v1/ask", json=body).status_code == 422
    assert model.chat_calls == 0


def test_explicit_settings_and_separate_instances() -> None:
    first = create_app(Settings("Custom"))
    second = create_app()
    assert first.title == "Custom"
    assert second.title == "Assessment starter"
    with pytest.raises(ValueError):
        Settings(" ")
