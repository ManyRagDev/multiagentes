"""TierRouter - Roteamento inteligente por custo, risco e disponibilidade."""

from typing import Dict, List, Optional, Tuple
import logging

from .task_classifier import TaskClassifier, TaskClassification, TaskTier
from .cost_ledger import CostLedger
from src.providers import ProviderRegistry

logger = logging.getLogger(__name__)


class TierRouter:
    """
    Roteador de tarefas por tier (local/medium/strong).
    
    Decide qual provider usar baseado em:
    1. Classificação de risco/complexidade da tarefa
    2. Disponibilidade de budget do provider
    3. Saúde do provider (para local)
    4. Fallback automático quando créditos esgotam
    
    Princípio: "Use o modelo mais barato que resolve com confiança."
    """
    
    # Mapeamento tier -> providers preferidos (em ordem de prioridade)
    TIER_PROVIDERS = {
        TaskTier.LOCAL: ["local-qwen"],
        TaskTier.MEDIUM: ["deepseek", "groq", "local-qwen"],  # fallback para local se API falhar
        TaskTier.STRONG: ["glm", "deepseek"],  # Nunca faz fallback para local em STRONG
    }
    
    def __init__(
        self,
        classifier: Optional[TaskClassifier] = None,
        ledger: Optional[CostLedger] = None,
        config: Optional[dict] = None
    ):
        """
        Inicializa o router.
        
        Args:
            classifier: Classificador de tarefas (usa default se None)
            ledger: Ledger de custos (usa default se None)
            config: Configuração customizada
        """
        self.classifier = classifier or TaskClassifier()
        self.ledger = ledger or CostLedger()
        self.config = config or {}
        
        # Cache de saúde dos providers
        self._provider_health: Dict[str, bool] = {}
    
    def route(
        self,
        objective: str,
        files: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        preferred_provider: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Tuple[str, TaskClassification]:
        """
        Determina o melhor provider para uma tarefa.
        
        Args:
            objective: Descrição do objetivo
            files: Arquivos afetados
            constraints: Restrições/requisitos
            preferred_provider: Provider preferido (override manual)
            context: Contexto adicional
            
        Returns:
            Tuple de (provider_name, classification)
            
        Raises:
            RuntimeError: Se nenhum provider disponível para tarefas STRONG
        """
        # 1. Classificar a tarefa
        classification = self.classifier.classify(
            objective=objective,
            files=files,
            constraints=constraints,
            context=context
        )
        
        logger.info(
            f"Classificação: tier={classification.tier.value}, "
            f"risk={classification.risk_score}, "
            f"complexity={classification.complexity_score}"
        )
        
        # 2. Se há override manual e é compatível com o tier, respeita
        if preferred_provider:
            if self._is_compatible(preferred_provider, classification):
                if self._is_available(preferred_provider):
                    logger.info(f"Usando provider preferido: {preferred_provider}")
                    return preferred_provider, classification
                else:
                    logger.warning(
                        f"Provider preferido '{preferred_provider}' indisponível, "
                        f"usando fallback"
                    )
            else:
                logger.warning(
                    f"Provider preferido '{preferred_provider}' incompatível com "
                    f"tier {classification.tier.value} (risco={classification.risk_score}). "
                    f"Ignorando preferência por segurança."
                )
        
        # 3. Tentar providers do tier em ordem de prioridade
        candidates = self.TIER_PROVIDERS.get(classification.tier, [])
        
        for provider in candidates:
            if self._is_available(provider) and self.ledger.is_within_budget(provider):
                logger.info(f"Provider selecionado: {provider}")
                return provider, classification
        
        # 4. Fallback: se tier MEDIUM e APIs esgotaram, tenta local (com aviso)
        if classification.tier == TaskTier.MEDIUM:
            if self._is_available("local-qwen"):
                logger.warning(
                    "⚠️ APIs de tier MEDIUM esgotadas/indisponíveis. "
                    "Fazendo fallback para local-qwen. "
                    "Qualidade pode ser reduzida."
                )
                return "local-qwen", classification
        
        # 5. Se tier STRONG e nada disponível, BLOQUEIA (não faz fallback inseguro)
        if classification.tier == TaskTier.STRONG:
            raise RuntimeError(
                f"❌ Tarefa de ALTO RISCO (risk={classification.risk_score}) "
                f"requer modelo forte, mas todos os providers STRONG estão "
                f"indisponíveis ou sem budget. NÃO é seguro executar localmente.\n"
                f"Providers tentados: {candidates}\n"
                f"Aguarde recarga de créditos ou use outro provider."
            )
        
        # 6. Último recurso: qualquer provider disponível
        for provider in ProviderRegistry.list_providers():
            if self._is_available(provider):
                logger.warning(f"Usando último recurso: {provider}")
                return provider, classification
        
        raise RuntimeError("Nenhum provider disponível no sistema.")
    
    def _is_available(self, provider_name: str) -> bool:
        """Verifica se um provider está disponível."""
        try:
            provider = ProviderRegistry.get(provider_name)
            
            # Para providers locais, verifica saúde
            if hasattr(provider, 'is_available'):
                available = provider.is_available()
                self._provider_health[provider_name] = available
                return available
            
            # Para APIs remotas, assume disponível (falha será detectada na chamada)
            return True
        except ValueError:
            return False
    
    def _is_compatible(self, provider: str, classification: TaskClassification) -> bool:
        """
        Verifica se um provider é compatível com o tier da tarefa.
        
        Regra: local só é compatível com LOCAL e MEDIUM (nunca STRONG).
        """
        if classification.tier == TaskTier.STRONG and provider == "local-qwen":
            return False
        return True
    
    def get_status(self) -> dict:
        """Retorna status atual do router."""
        return {
            "providers": {
                name: {
                    "available": self._is_available(name),
                    "within_budget": self.ledger.is_within_budget(name),
                    "usage": self.ledger.get_usage(name).to_dict()
                }
                for name in ProviderRegistry.list_providers()
            },
            "exceeded_budgets": self.ledger.get_exceeded_providers(),
            "total_cost": self.ledger.get_total_cost()
        }
