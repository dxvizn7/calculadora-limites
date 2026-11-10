"""Núcleo de cálculo de limites (sem dependência de interface gráfica)."""
from .parser import parse_funcao, parse_ponto, x
from .solver import FORMA_NOME, Resultado, resolver

__all__ = ["parse_funcao", "parse_ponto", "x", "resolver", "Resultado", "FORMA_NOME"]
