"""Ledger de custos e tokens por provider para tracking e fallback."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import json
from pathlib import Path


@dataclass
class ProviderUsage:
    """Uso acumulado de um provider."""
    tokens_input: int = 0
    tokens_output: int = 0
    total_cost: float = 0.0
    requests: int = 0
    last_used: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output
    
    def to_dict(self) -> dict:
        return {
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "total_cost": self.total_cost,
            "requests": self.requests,
            "last_used": self.last_used,
        }


class CostLedger:
    """
    Registro central de custos e uso de tokens.
    
    Permite tracking por provider e detecção de limites
    para fallback automático quando créditos esgotam.
    """
    
    # Custos aproximados por 1M tokens (USD) - atualizar conforme seus planos
    DEFAULT_COSTS = {
        "local-qwen": {"input": 0.0, "output": 0.0},  # Grátis
        "glm": {"input": 2.0, "output": 8.0},         # GLM-5.2 pricing
        "deepseek": {"input": 0.5, "output": 1.5},     # DeepSeek pricing
        "groq": {"input": 0.0, "output": 0.0},         # Free tier
    }
    
    def __init__(
        self,
        persist_path: Optional[str] = None,
        budgets: Optional[Dict[str, float]] = None
    ):
        """
        Inicializa o ledger.
        
        Args:
            persist_path: Caminho para salvar/carregar estado (JSON)
            budgets: Limites de custo por provider (USD). None = sem limite
        """
        self.persist_path = Path(persist_path) if persist_path else None
        self.budgets = budgets or {}
        self.usage: Dict[str, ProviderUsage] = {}
        
        if self.persist_path and self.persist_path.exists():
            self._load()
    
    def record(
        self,
        provider: str,
        tokens_input: int,
        tokens_output: int
    ) -> None:
        """
        Registra uso de tokens para um provider.
        
        Args:
            provider: Nome do provider
            tokens_input: Tokens de input consumidos
            tokens_output: Tokens de output gerados
        """
        if provider not in self.usage:
            self.usage[provider] = ProviderUsage()
        
        usage = self.usage[provider]
        usage.tokens_input += tokens_input
        usage.tokens_output += tokens_output
        usage.requests += 1
        usage.last_used = datetime.now().isoformat()
        
        # Calcular custo
        costs = self.DEFAULT_COSTS.get(provider, {"input": 0, "output": 0})
        cost = (tokens_input * costs["input"] + tokens_output * costs["output"]) / 1_000_000
        usage.total_cost += cost
        
        self._save()
    
    def get_usage(self, provider: str) -> ProviderUsage:
        """Retorna uso acumulado de um provider."""
        return self.usage.get(provider, ProviderUsage())
    
    def is_within_budget(self, provider: str) -> bool:
        """
        Verifica se o provider está dentro do orçamento.
        
        Returns:
            True se dentro do budget ou se não há budget definido
        """
        if provider not in self.budgets:
            return True  # Sem budget = sem limite
        
        usage = self.get_usage(provider)
        return usage.total_cost < self.budgets[provider]
    
    def get_exceeded_providers(self) -> list[str]:
        """Retorna lista de providers que excederam o budget."""
        exceeded = []
        for provider, budget in self.budgets.items():
            usage = self.get_usage(provider)
            if usage.total_cost >= budget:
                exceeded.append(provider)
        return exceeded
    
    def get_total_cost(self) -> float:
        """Retorna custo total acumulado."""
        return sum(u.total_cost for u in self.usage.values())
    
    def get_summary(self) -> Dict[str, dict]:
        """Retorna resumo de uso por provider."""
        return {
            provider: usage.to_dict()
            for provider, usage in self.usage.items()
        }
    
    def reset(self, provider: Optional[str] = None) -> None:
        """
        Reseta contadores.
        
        Args:
            provider: Se especificado, reseta apenas esse provider.
                     Se None, reseta todos.
        """
        if provider:
            self.usage.pop(provider, None)
        else:
            self.usage.clear()
        self._save()
    
    def _save(self) -> None:
        """Persiste estado em disco."""
        if not self.persist_path:
            return
        
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "usage": {k: v.to_dict() for k, v in self.usage.items()},
            "budgets": self.budgets,
        }
        with open(self.persist_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _load(self) -> None:
        """Carrega estado do disco."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for provider, usage_data in data.get("usage", {}).items():
                self.usage[provider] = ProviderUsage(**usage_data)
            
            self.budgets = data.get("budgets", {})
        except Exception:
            pass  # Se falhar, começa do zero
