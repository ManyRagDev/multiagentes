"""Classificador determinístico de complexidade e risco de tarefas."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TaskTier(str, Enum):
    """Níveis de tier para roteamento."""
    LOCAL = "local"           # Qwen local - tarefas mecânicas/baixo risco
    MEDIUM = "medium"         # API intermediária - complexidade moderada
    STRONG = "strong"         # API forte - alto risco/crítico


@dataclass
class TaskClassification:
    """Resultado da classificação de uma tarefa."""
    tier: TaskTier
    risk_score: int = 0
    complexity_score: int = 0
    reasons: List[str] = field(default_factory=list)
    
    @property
    def is_local_safe(self) -> bool:
        """Indica se é seguro executar localmente."""
        return self.tier == TaskTier.LOCAL
    
    @property
    def requires_strong_model(self) -> bool:
        """Indica se requer modelo forte obrigatoriamente."""
        return self.tier == TaskTier.STRONG


class TaskClassifier:
    """
    Classificador determinístico de tarefas.
    
    Usa regras heurísticas para determinar o tier apropriado
    baseado em risco, complexidade e contexto da tarefa.
    """
    
    # Pesos de risco por tipo de operação
    RISK_WEIGHTS = {
        "auth": 5,
        "authentication": 5,
        "password": 5,
        "token": 4,
        "refresh_token": 5,
        "jwt": 4,
        "oauth": 5,
        "payment": 5,
        "stripe": 5,
        "billing": 5,
        "webhook": 4,
        "database": 3,
        "migration": 4,
        "schema": 3,
        "security": 5,
        "encryption": 5,
        "permission": 4,
        "api_public": 3,
        "endpoint": 2,
        "infraestrutura": 4,
        "infrastructure": 4,
        "config": 2,
        "deploy": 3,
        "ci/cd": 3,
    }
    
    # Palavras-chave que indicam alta complexidade
    COMPLEXITY_INDICATORS = [
        "refatorar", "refactor", "migrar", "migrate",
        "arquitetura", "architecture", "redesenhar", "redesign",
        "otimizar", "optimize", "debug", "investigar", "investigate",
        "ambíguo", "ambiguous", "complexo", "complex",
        "paginação", "pagination", "cache", "rate limit",
        "concorrência", "concurrency", "async", "websocket",
        "middleware", "interceptor", "pipeline",
        "integração", "integration", "terceiros", "third-party",
        "multi-arquivo", "multi-file", "cross-module",
    ]
    
    def __init__(self, config: Optional[dict] = None):
        """
        Inicializa o classificador.
        
        Args:
            config: Configuração customizada (opcional)
        """
        self.config = config or {}
        self.max_files_for_local = self.config.get("max_files_for_local", 3)
        self.local_risk_threshold = self.config.get("local_risk_threshold", 3)
        self.medium_risk_threshold = self.config.get("medium_risk_threshold", 6)
    
    def classify(
        self,
        objective: str,
        files: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        context: Optional[dict] = None
    ) -> TaskClassification:
        """
        Classifica uma tarefa para determinar o tier apropriado.
        
        Args:
            objective: Descrição do objetivo da tarefa
            files: Lista de arquivos afetados
            constraints: Lista de restrições/requisitos
            context: Contexto adicional (opcional)
            
        Returns:
            TaskClassification com tier e scores
        """
        files = files or []
        constraints = constraints or []
        context = context or {}
        
        risk_score = self._calculate_risk(objective, files, constraints)
        complexity_score = self._calculate_complexity(objective, files, constraints)
        reasons = []
        
        # Determinar tier baseado nos scores
        if risk_score >= self.medium_risk_threshold:
            tier = TaskTier.STRONG
            reasons.append(f"Alto risco detectado (score={risk_score})")
        elif complexity_score >= 5 or len(files) > self.max_files_for_local:
            tier = TaskTier.MEDIUM
            reasons.append(f"Complexidade moderada ou muitos arquivos (complexity={complexity_score}, files={len(files)})")
        elif risk_score <= self.local_risk_threshold and len(files) <= self.max_files_for_local:
            tier = TaskTier.LOCAL
            reasons.append(f"Baixo risco e poucos arquivos (risk={risk_score}, files={len(files)})")
        else:
            tier = TaskTier.MEDIUM
            reasons.append(f"Risco/complexidade intermediários (risk={risk_score}, complexity={complexity_score})")
        
        # Adicionar razões detalhadas
        if any(kw in objective.lower() for kw in ["auth", "security", "payment"]):
            reasons.append("Operação sensível detectada no objetivo")
        if len(files) > self.max_files_for_local:
            reasons.append(f"Muitos arquivos ({len(files)} > {self.max_files_for_local})")
        
        return TaskClassification(
            tier=tier,
            risk_score=risk_score,
            complexity_score=complexity_score,
            reasons=reasons
        )
    
    def _calculate_risk(
        self,
        objective: str,
        files: List[str],
        constraints: List[str]
    ) -> int:
        """Calcula score de risco baseado em palavras-chave e contexto."""
        score = 0
        text = f"{objective} {' '.join(files)} {' '.join(constraints)}".lower()
        
        for keyword, weight in self.RISK_WEIGHTS.items():
            if keyword in text:
                score += weight
        
        # Arquivos de configuração/infra têm risco inerente
        infra_patterns = ["docker", "k8s", "terraform", ".env", "config/", "infra/"]
        for pattern in infra_patterns:
            if any(pattern in f.lower() for f in files):
                score += 3
        
        return min(score, 10)  # Cap em 10
    
    def _calculate_complexity(
        self,
        objective: str,
        files: List[str],
        constraints: List[str]
    ) -> int:
        """Calcula score de complexidade baseado em indicadores."""
        score = 0
        text = f"{objective} {' '.join(constraints)}".lower()
        
        # Complexidade por número de arquivos
        score += min(len(files), 5)
        
        # Indicadores textuais de complexidade
        for indicator in self.COMPLEXITY_INDICATORS:
            if indicator in text:
                score += 2
        
        # Muitas constraints indicam complexidade
        if len(constraints) > 5:
            score += 2
        
        return min(score, 10)  # Cap em 10
