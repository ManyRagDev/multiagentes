"""
Multiagentes - Sistema multiagentes para perícia/auditoria de código.

Este pacote fornece skills para uso com Claude Code:
- /plano: Gera e valida planos de implementação
- /auditoria: Audita código com verificação adversarial
- /implementar: Implementa código a partir de planos
"""

__version__ = "0.1.0"

try:
    # Quando instalado via pip install -e .
    from skills.plano import skill_plano
    from skills.auditoria import skill_auditoria
    from skills.implementar import skill_implementar
except ImportError:
    # Quando usado localmente
    from src.skills.plano import skill_plano
    from src.skills.auditoria import skill_auditoria
    from src.skills.implementar import skill_implementar

__all__ = [
    "skill_plano",
    "skill_auditoria",
    "skill_implementar",
]


def get_skills():
    """Retorna todas as skills disponíveis."""
    return {
        "plano": skill_plano,
        "auditoria": skill_auditoria,
        "implementar": skill_implementar,
    }
