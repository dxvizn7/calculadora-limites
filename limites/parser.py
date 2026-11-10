"""Leitura da função f(x) e do ponto de aproximação a."""
import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

x = sp.Symbol("x", real=True)

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

LOCALS = {
    "x": x,
    "e": sp.E,
    "pi": sp.pi,
    "sen": sp.sin,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "tg": sp.tan,
    "ln": sp.log,
    "log": sp.log,
    "exp": sp.exp,
    "sqrt": sp.sqrt,
    "raiz": sp.sqrt,
}


def parse_funcao(texto: str) -> sp.Expr:
    """Converte o texto digitado em expressão SymPy. Aceita x^2, 2x, sen(x), ln(x)..."""
    if not texto or not texto.strip():
        raise ValueError("Digite a função f(x).")
    # aceita "f(x) = ..." ou "y = ..." no começo
    texto = re.sub(r"^\s*(f\s*\(\s*x\s*\)|y)\s*=", "", texto)
    if not texto.strip():
        raise ValueError("Digite a função f(x).")
    expr = parse_expr(texto, local_dict=LOCALS, transformations=TRANSFORMS)
    if not expr.free_symbols <= {x}:
        raise ValueError("A função deve depender apenas de x.")
    return expr


def parse_ponto(texto: str) -> sp.Expr:
    """Converte o ponto a. Aceita números, frações, pi, 'oo', '-oo', '+oo', 'inf', '∞'."""
    t = (texto or "").strip().replace(" ", "").replace("∞", "oo").replace("inf", "oo")
    if not t:
        raise ValueError("Digite o ponto a (número, oo ou -oo).")
    if t in ("oo", "+oo"):
        return sp.oo
    if t == "-oo":
        return -sp.oo
    a = parse_expr(t, local_dict=LOCALS, transformations=TRANSFORMS)
    if a.free_symbols:
        raise ValueError("O ponto a não pode conter x.")
    a = sp.simplify(a)
    if a.is_real is False:
        raise ValueError("O ponto a deve ser um número real.")
    return a
