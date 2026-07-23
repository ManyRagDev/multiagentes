"""Fixtures compartilhadas para testes."""
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_mock_completion(content: dict | str) -> MagicMock:
    """Cria um mock de resposta da API OpenAI."""
    if isinstance(content, dict):
        content = json.dumps(content, ensure_ascii=False)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_response.usage = MagicMock()
    mock_response.usage.total_tokens = 100
    return mock_response


@pytest.fixture
def mock_openai(mocker):
    """Fixture que intercepta chamadas a API OpenAI no BaseAgent.

    Patcha `OpenAI.chat.completions.create` para retornar um mock
    com content customizavel.
    """
    mock = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_make_mock_completion("{}"),
    )
    return mock


@pytest.fixture
def mock_openai_response(mocker):
    """Fixture que retorna um callable para criar respostas mock.

    Uso:
        resultado = skill_plano(objetivo="X")
    """
    def _configure(response_content: dict | str):
        return_value = _make_mock_completion(response_content)
        mocker.patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=return_value,
        )
    return _configure
