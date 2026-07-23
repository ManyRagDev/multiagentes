"""Testes end-to-end para as skills do sistema multiagentes."""

import json
import pytest
from pathlib import Path

from src.skills import skill_plano, skill_auditoria, skill_implementar
from src.schemas import Plan


class TestSkillPlano:
    """Testes para a skill /plano."""

    def test_plano_simples(self, mocker):
        """Testa geração de plano simples."""
        # Mock da API para não gastar tokens
        mock_response = mocker.Mock()
        mock_response.choices = [mocker.Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "objetivo": "Adicionar teste",
            "pre_condicoes": ["Framework instalado"],
            "passos": [
                {
                    "id": 1,
                    "descricao": "Criar arquivo de teste",
                    "depende_de": [],
                    "riscos": [],
                    "rollback": None
                }
            ],
            "pos_condicoes": ["Teste criado"]
        }, ensure_ascii=False)
        mock_response.usage = mocker.Mock()
        mock_response.usage.total_tokens = 100

        mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)

        resultado = skill_plano(objetivo="Adicionar teste")

        assert resultado["sucesso"] is True
        assert "plano" in resultado
        assert resultado["plano"]["objetivo"] == "Adicionar teste"

    def test_plano_com_contexto(self, mocker):
        """Testa geração de plano com contexto adicional."""
        mock_response = mocker.Mock()
        mock_response.choices = [mocker.Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "objetivo": "Adicionar teste",
            "pre_condicoes": [],
            "passos": [],
            "pos_condicoes": []
        }, ensure_ascii=False)
        mock_response.usage = mocker.Mock()
        mock_response.usage.total_tokens = 100

        mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)

        resultado = skill_plano(
            objetivo="Adicionar teste",
            contexto="Projeto Django"
        )

        assert resultado["sucesso"] is True

    def test_plano_com_erro_na_api(self, mocker):
        """Testa tratamento de erro na API."""
        mocker.patch("openai.resources.chat.completions.Completions.create", side_effect=Exception("API Error"))

        resultado = skill_plano(objetivo="Adicionar teste")

        assert resultado["sucesso"] is False
        assert "erro" in resultado


class TestSkillAuditoria:
    """Testes para a skill /auditoria."""

    def test_auditoria_arquivo_inexistente(self):
        """Testa auditoria de caminho inexistente."""
        resultado = skill_auditoria(caminho_codigo="/caminho/inexistente")

        assert resultado["sucesso"] is False
        assert "não encontrado" in resultado["erro"].lower()

    def test_auditoria_codigo_simples(self, mocker, tmp_path):
        """Testa auditoria de código simples."""
        # Criar arquivo de teste
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def process(items):
    for i in range(len(items) + 1):
        print(items[i])
""")

        # Mock das respostas da API
        def mock_create(*args, **kwargs):
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            mock_response = mocker.Mock()

            if "bug_hunter" in prompt or "BugHunter" in str(args):
                mock_response.choices[0].message.content = json.dumps([{
                    "tipo": "bug",
                    "arquivo": "test.py",
                    "linha": 4,
                    "titulo": "Off-by-one error",
                    "descricao": "Loop acessa items[i] onde i pode ser len(items)",
                    "severidade": "high",
                    "evidencia": "for i in range(len(items) + 1):"
                }], ensure_ascii=False)
            elif "bug_refuter" in prompt:
                mock_response.choices[0].message.content = json.dumps([{
                    "finding": {
                        "tipo": "bug",
                        "arquivo": "test.py",
                        "linha": 4,
                        "titulo": "Off-by-one error",
                        "descricao": "Loop acessa items[i]",
                        "severidade": "high",
                        "evidencia": "..."
                    },
                    "confirmado": True,
                    "refutacao": None
                }], ensure_ascii=False)
            elif "completeness" in prompt:
                mock_response.choices[0].message.content = json.dumps({
                    "cobertura_arquivos": {
                        "total_arquivos": 1,
                        "arquivos_analisados": ["test.py"],
                        "arquivos_ignorados": [],
                        "arquivos_relevantes_nao_analisados": []
                    },
                    "cobertura_dimensoes": {
                        "bugs": "completa",
                        "security": "nao_analisada",
                        "performance": "nao_analisada"
                    },
                    "faltando": [],
                    "conclusao": {
                        "completa": True,
                        "justificativa": "Dimensão bugs analisada completamente"
                    }
                }, ensure_ascii=False)
            else:
                mock_response.choices[0].message.content = "[]"

            mock_response.usage = mocker.Mock()
            mock_response.usage.total_tokens = 100
            return mock_response

        mocker.patch("openai.resources.chat.completions.Completions.create", side_effect=mock_create)

        resultado = skill_auditoria(
            caminho_codigo=str(tmp_path),
            dimensoes=["bugs"]
        )

        assert resultado["sucesso"] is True
        assert "findings" in resultado


class TestSkillImplementar:
    """Testes para a skill /implementar."""

    def test_implementar_plano_simples(self, mocker):
        """Testa implementação de plano simples."""
        plano = Plan(
            objetivo="Criar função hello",
            pre_condicoes=[],
            passos=[
                {
                    "id": 1,
                    "descricao": "Criar arquivo hello.py",
                    "depende_de": [],
                    "riscos": [],
                    "rollback": None
                }
            ],
            pos_condicoes=["Arquivo criado"]
        )

        # Mock das respostas da API
        def mock_create(*args, **kwargs):
            prompt = kwargs.get("messages", [{}])[0].get("content", "")
            mock_response = mocker.Mock()

            if "generator" in str(args) or "CodeGen" in str(args):
                mock_response.choices[0].message.content = json.dumps({
                    "arquivos": [
                        {
                            "caminho": "hello.py",
                            "conteudo": "def hello():\n    return 'Hello World'\n",
                            "passo_implementado": 1
                        }
                    ],
                    "resumo": "Função hello criada",
                    "proximos_passos": []
                }, ensure_ascii=False)
            elif "verifier" in str(args) or "CodeVerifier" in str(args):
                mock_response.choices[0].message.content = json.dumps({
                    "aprovado": True,
                    "arquivos_verificados": [
                        {
                            "caminho": "hello.py",
                            "passo_correspondente": 1,
                            "correspondencia": "completa",
                            "problemas": []
                        }
                    ],
                    "passos_faltando": [],
                    "problemas_codigo": [],
                    "sugestoes": []
                }, ensure_ascii=False)

            mock_response.usage = mocker.Mock()
            mock_response.usage.total_tokens = 100
            return mock_response

        mocker.patch("openai.resources.chat.completions.Completions.create", side_effect=mock_create)

        resultado = skill_implementar(plano=plano)

        assert resultado["sucesso"] is True
        assert "arquivos" in resultado
        assert len(resultado["arquivos"]) == 1

    def test_implementar_com_output_dir(self, mocker, tmp_path):
        """Testa implementação salvando arquivos."""
        plano = Plan(
            objetivo="Criar arquivo",
            pre_condicoes=[],
            passos=[{
                "id": 1,
                "descricao": "Criar test.py",
                "depende_de": [],
                "riscos": [],
                "rollback": None
            }],
            pos_condicoes=[]
        )

        def mock_create(*args, **kwargs):
            mock_response = mocker.Mock()
            mock_response.choices[0].message.content = json.dumps({
                "arquivos": [{"caminho": "test.py", "conteudo": "# test", "passo_implementado": 1}],
                "resumo": "Arquivo criado",
                "proximos_passos": []
            }, ensure_ascii=False)
            mock_response.usage = mocker.Mock()
            mock_response.usage.total_tokens = 100
            return mock_response

        mocker.patch("openai.resources.chat.completions.Completions.create", side_effect=mock_create)

        resultado = skill_implementar(plano=plano, output_dir=str(tmp_path))

        assert resultado["sucesso"] is True
        assert (tmp_path / "test.py").exists()


class TestWorkflows:
    """Testes para workflows compostos."""

    def test_planejar_e_implementar_workflow(self, mocker):
        """Testa workflow completo de planejar e implementar."""
        # Simula o fluxo completo
        # 1. /plano gera plano
        # 2. /implementar usa o plano

        pass  # Implementação completa seria muito longa para este exemplo


# Fixtures
@pytest.fixture
def mock_openai(mocker):
    """Fixture para mockar a API OpenAI."""
    def mock_create(*args, **kwargs):
        mock_response = mocker.Mock()
        mock_response.choices = [mocker.Mock()]
        mock_response.choices[0].message.content = "{}"
        mock_response.usage = mocker.Mock()
        mock_response.usage.total_tokens = 50
        return mock_response

    return mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_create())
