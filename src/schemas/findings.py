"""Schemas para findings de auditoria de código e geração de código."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


class Severity(str, Enum):
    """Níveis de severidade para findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    """Um finding (problema/observação) encontrado em código."""

    tipo: Literal["bug", "security", "performance", "architecture"] = Field(
        ...,
        description="Categoria do finding"
    )
    arquivo: str = Field(..., description="Nome do arquivo")
    linha: int = Field(..., description="Linha (1-indexed)")
    titulo: str = Field(..., description="Título curto e descritivo")
    descricao: str = Field(..., description="Explicação detalhada")
    severidade: Severity = Field(..., description="Nível de severidade")
    evidencia: str = Field(..., description="Snippet do código ou explicação técnica")


class Verdict(BaseModel):
    """Veredito adversarial de um finding."""

    finding: Finding = Field(..., description="O finding original")
    confirmado: bool = Field(..., description="True se bug/vulnerabilidade real")
    refutacao: Optional[str] = Field(
        None,
        description="Por que foi refutado, null se confirmado"
    )


class CodeReport(BaseModel):
    """Report consolidado de auditoria de código."""

    findings: List[Finding] = Field(
        default_factory=list,
        description="Todos os findings encontrados"
    )
    verdicts: List[Verdict] = Field(
        default_factory=list,
        description="Vereditos adversariais"
    )
    resumo: str = Field(..., description="Resumo executivo")


class CoberturaArquivos(BaseModel):
    """Cobertura de arquivos na auditoria."""

    total_arquivos: int = Field(..., description="Total de arquivos no escopo")
    arquivos_analisados: List[str] = Field(
        default_factory=list,
        description="Arquivos que foram analisados"
    )
    arquivos_ignorados: List[str] = Field(
        default_factory=list,
        description="Arquivos ignorados (por opção)"
    )
    arquivos_relevantes_nao_analisados: List[str] = Field(
        default_factory=list,
        description="Arquivos relevantes que não foram analisados (gap)"
    )


class CoberturaDimensoes(BaseModel):
    """Cobertura por dimensão de análise."""

    bugs: Literal["completa", "parcial", "nao_analisada"] = Field(
        ...,
        description="Cobertura da dimensão bugs"
    )
    security: Literal["completa", "parcial", "nao_analisada"] = Field(
        ...,
        description="Cobertura da dimensão security"
    )
    performance: Literal["completa", "parcial", "nao_analisada"] = Field(
        ...,
        description="Cobertura da dimensão performance"
    )


class Falta(BaseModel):
    """Algo que foi deixado de fora na auditoria."""

    categoria: str = Field(..., description="Qual dimensão/categoria")
    descricao: str = Field(..., description="O que foi deixado de fora")
    importancia: Literal["critical", "high", "medium", "low"] = Field(
        ...,
        description="Importância do gap"
    )


class ConclusaoCompleteness(BaseModel):
    """Conclusão sobre completude da auditoria."""

    completa: bool = Field(..., description="True se auditoria é completa")
    justificativa: str = Field(..., description="Justificativa da conclusão")


class CompletenessReport(BaseModel):
    """Report de meta-auditoria (completude)."""

    cobertura_arquivos: CoberturaArquivos = Field(
        ...,
        description="Cobertura por arquivo"
    )
    cobertura_dimensoes: CoberturaDimensoes = Field(
        ...,
        description="Cobertura por dimensão"
    )
    faltando: List[Falta] = Field(
        default_factory=list,
        description="O que foi deixado de fora"
    )
    conclusao: ConclusaoCompleteness = Field(
        ...,
        description="Conclusão sobre completude"
    )


# === Schemas para Listas de Findings e Verdicts ===


class FindingList(BaseModel):
    """Lista de findings."""

    findings: List[Finding] = Field(
        default_factory=list,
        description="Lista de findings encontrados"
    )


class VerdictList(BaseModel):
    """Lista de vereditos adversariais."""

    verdicts: List[Verdict] = Field(
        default_factory=list,
        description="Lista de vereditos adversariais"
    )


# === Schemas para Geração de Código ===


class ArquivoGerado(BaseModel):
    """Arquivo de código gerado."""

    caminho: str = Field(..., description="Caminho do arquivo")
    conteudo: str = Field(..., description="Conteúdo do arquivo")
    passo_implementado: int = Field(..., description="ID do passo implementado")


class CodeOutput(BaseModel):
    """Output do agente CodeGen."""

    arquivos: List[ArquivoGerado] = Field(
        default_factory=list,
        description="Arquivos gerados"
    )
    resumo: str = Field(..., description="O que foi implementado")
    proximos_passos: List[str] = Field(
        default_factory=list,
        description="Próximos passos se restarem"
    )


class ArquivoVerificado(BaseModel):
    """Resultado de verificação de um arquivo."""

    caminho: str = Field(..., description="Caminho do arquivo")
    passo_correspondente: int = Field(..., description="ID do passo")
    correspondencia: Literal["completa", "parcial", "nao_implementado"] = Field(
        ...,
        description="Nível de correspondência com o passo"
    )
    problemas: List[str] = Field(
        default_factory=list,
        description="Problemas encontrados"
    )


class ProblemaCodigo(BaseModel):
    """Problema encontrado no código gerado."""

    tipo: Literal["sintaxe", "logica", "security", "performance"] = Field(
        ...,
        description="Tipo do problema"
    )
    arquivo: str = Field(..., description="Caminho do arquivo")
    descricao: str = Field(..., description="Descrição do problema")


class CodeVerification(BaseModel):
    """Resultado da verificação de código gerado."""

    aprovado: bool = Field(..., description="True se código aprovado")
    arquivos_verificados: List[ArquivoVerificado] = Field(
        default_factory=list,
        description="Arquivos verificados"
    )
    passos_faltando: List[int] = Field(
        default_factory=list,
        description="IDs dos passos não implementados"
    )
    problemas_codigo: List[ProblemaCodigo] = Field(
        default_factory=list,
        description="Problemas encontrados no código"
    )
    sugestoes: List[str] = Field(
        default_factory=list,
        description="Sugestões de melhoria"
    )
