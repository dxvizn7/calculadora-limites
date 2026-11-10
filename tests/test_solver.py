import matplotlib

matplotlib.use("Agg")

import pytest
import sympy as sp
from matplotlib.figure import Figure

from limites import parse_funcao, parse_ponto, resolver
from limites.grafico import plotar
from limites.solver import NAO_EXISTE

# (função, ponto, direção, forma esperada, limite esperado, trecho do método)
CASOS = [
    ("x^2 + 3x", "2", None, "DIRETA", sp.Integer(10), "Substituição"),
    ("1/x", "0", None, "C/0", NAO_EXISTE, "laterais"),
    ("1/x", "0", "+", "C/0", sp.oo, "laterais"),
    ("1/x", "0", "-", "C/0", -sp.oo, "laterais"),
    ("1/x^2", "0", None, "C/0", sp.oo, "laterais"),
    ("(x^2 - 1)/(x - 1)", "1", None, "0/0", sp.Integer(2), "Fatoração"),
    ("(x^2 - 5x + 6)/(x - 2)", "2", None, "0/0", sp.Integer(-1), "Fatoração"),
    ("(sqrt(x + 1) - 1)/x", "0", None, "0/0", sp.Rational(1, 2), "conjugado"),
    ("(x - 4)/(sqrt(x) - 2)", "4", None, "0/0", sp.Integer(4), "conjugado"),
    ("(x^3 - 3x + 2)/(x^2 - 2x + 1)", "1", None, "0/0", sp.Integer(3), "Briot-Ruffini"),
    ("(x^2 - 1)/(x - 1)^2", "1", "+", "0/0", sp.oo, "laterais"),
    ("sen(x)/x", "0", None, "0/0", sp.Integer(1), "trigonométrico"),
    ("sin(3x)/x", "0", None, "0/0", sp.Integer(3), "trigonométrico"),
    ("(1 - cos(x))/x^2", "0", None, "0/0", sp.Rational(1, 2), "trigonométrico"),
    ("(exp(x) - 1)/x", "0", None, "0/0", sp.Integer(1), "exponencial"),
    ("(3x^2 + 1)/(2x^2 - x)", "oo", None, "INF/INF", sp.Rational(3, 2), "maior grau"),
    ("(x^3 + 1)/(x^2 + 1)", "-oo", None, "INF/INF", -sp.oo, "maior grau"),
    ("(2x + 1)/(x^2 + 1)", "oo", None, "INF/INF", sp.Integer(0), "maior grau"),
    ("ln(x)/x", "oo", None, "INF/INF", sp.Integer(0), "L'Hôpital"),
    ("sqrt(x^2 + x) - x", "oo", None, "INF-INF", sp.Rational(1, 2), "conjugado"),
    ("(1 + 1/x)^x", "oo", None, "1^INF", sp.E, "exponencial"),
    ("(1 + 2/x)^(3x)", "oo", None, "1^INF", sp.exp(6), "exponencial"),
    ("(1 + x)^(1/x)", "0", None, "1^INF", sp.E, "exponencial"),
    ("x^(1/x)", "oo", None, "INF^0", sp.Integer(1), "exponencial"),
]


@pytest.mark.parametrize("f, a, d, forma, esperado, metodo", CASOS)
def test_limites_do_fluxograma(f, a, d, forma, esperado, metodo):
    res = resolver(parse_funcao(f), parse_ponto(a), d)
    assert res.forma == forma
    if isinstance(esperado, str):
        assert res.valor == esperado
    else:
        assert sp.simplify(res.valor - esperado) == 0 if esperado.is_finite else res.valor == esperado
    if metodo:
        assert metodo.lower() in res.metodo.lower()
    assert res.passos[-1][0] == "Método utilizado"


def test_continuidade():
    assert resolver(parse_funcao("x^2"), parse_ponto("3")).continuo is True
    assert resolver(parse_funcao("(x^2 - 1)/(x - 1)"), parse_ponto("1")).continuo is False


@pytest.mark.parametrize("texto, esperado", [
    ("oo", sp.oo), ("+oo", sp.oo), ("-oo", -sp.oo), ("∞", sp.oo), ("1/2", sp.Rational(1, 2)), ("pi", sp.pi),
])
def test_parse_ponto(texto, esperado):
    assert parse_ponto(texto) == esperado


@pytest.mark.parametrize("texto", ["f(x) = x^2", "f(x)=x^2", "y = x^2", "x^2"])
def test_parse_aceita_prefixo(texto):
    assert parse_funcao(texto) == parse_funcao("x**2")


def test_passo_a_passo_mostra_ruffini():
    res = resolver(parse_funcao("(x^2 - 1)/(x - 1)"), parse_ponto("1"))
    texto = "\n".join(c for _, c in res.passos)
    assert "│" in texto and "(x - 1)⋅(x + 1)" in texto and "1 + 1 = 2" in texto


@pytest.mark.parametrize("texto", ["", "x + y", "   "])
def test_parse_funcao_invalida(texto):
    with pytest.raises(ValueError):
        parse_funcao(texto)


@pytest.mark.parametrize("f, a, d", [(c[0], c[1], c[2]) for c in CASOS])
def test_grafico_nao_quebra(f, a, d):
    expr, ponto = parse_funcao(f), parse_ponto(a)
    fig = Figure()
    ax = fig.add_subplot(111)
    plotar(fig, ax, expr, ponto, resolver(expr, ponto, d))
