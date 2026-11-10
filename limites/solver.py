"""
Resolução de limites seguindo o fluxograma "Resumo de Limites".

x -> a (a real):
    f(a) = L          -> substituição direta
    f(a) = c/0        -> analisar os limites laterais
    f(a) = 0/0        -> fatorar / racionalizar (conjugado) / limites fundamentais
x -> ±oo:
    ±oo/±oo           -> termo de maior grau ou L'Hôpital
    oo - oo           -> multiplicar pelo conjugado
    1^oo ou oo^0      -> limites fundamentais exponenciais
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import sympy as sp

from .parser import x

FORMA_NOME = {
    "DIRETA": "Substituição direta (sem indeterminação)",
    "C/0": "c/0 com c ≠ 0",
    "0/0": "Indeterminação 0/0",
    "INF/INF": "Indeterminação ∞/∞",
    "INF-INF": "Indeterminação ∞ − ∞",
    "1^INF": "Indeterminação 1^∞",
    "INF^0": "Indeterminação ∞^0",
    "OUTRA": "Outro caso (cálculo simbólico direto)",
}

DIR_TXT = {None: "bilateral", "+": "pela direita (a⁺)", "-": "pela esquerda (a⁻)"}

NAO_EXISTE = "não existe (limites laterais diferentes)"

Valor = Union[sp.Expr, str]


@dataclass
class Resultado:
    forma: str
    valor: Valor                     # sp.Expr (número, oo, -oo) ou texto
    metodo: str
    passos: List[Tuple[str, str]] = field(default_factory=list)
    continuo: bool = False           # f(a) existe e f(a) = L

    @property
    def numerico(self) -> Optional[sp.Expr]:
        """Valor real finito do limite (ou None se diverge / não existe)."""
        if isinstance(self.valor, sp.Expr) and self.valor.is_real and self.valor.is_finite:
            return self.valor
        return None

    @property
    def texto(self) -> str:
        return fmt(self.valor)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _empilhar(e):
    """Um racional isolado (ex.: 1/2) sai em linha no pretty; troca por símbolos para empilhar."""
    if isinstance(e, sp.Rational) and not e.is_Integer:
        num = sp.Symbol(str(abs(e.p)))
        frac = num / sp.Symbol(str(e.q))
        return -frac if e.p < 0 else frac
    return e


def pretty(e) -> str:
    """Formato 2D (frações empilhadas)."""
    return linha(e)


_NOMES_PT = {sp.sin: sp.Function("sen"), sp.tan: sp.Function("tg"), sp.log: sp.Function("ln")}


def _em_portugues(e):
    """Só para exibição: sin → sen, tan → tg, log → ln."""
    for f, g in _NOMES_PT.items():
        if e.has(f):
            e = e.replace(f, lambda *args, g=g: g(*args))
    return e


def _forma(p):
    from sympy.printing.pretty.pretty import PrettyPrinter
    from sympy.printing.pretty.stringpict import prettyForm, stringPict
    if isinstance(p, (str, stringPict)):
        return p
    if isinstance(p, Fracao):
        return prettyForm(*stringPict.next(_forma(p.n))) / prettyForm(*stringPict.next(_forma(p.d)))
    return PrettyPrinter({"use_unicode": True})._print(_em_portugues(_empilhar(sp.sympify(p))))


def linha(*partes) -> str:
    """Junta textos e expressões 2D lado a lado, alinhados na linha da fração."""
    from sympy.printing.pretty.stringpict import prettyForm, stringPict
    return str(prettyForm(*stringPict.next(*[_forma(p) for p in partes])))


def rotulo(texto: str, e) -> str:
    return linha(texto, e)


class Fracao:
    """Fração só para exibição: numerador em cima, denominador embaixo, sem simplificar."""

    def __init__(self, n, d):
        self.n, self.d = n, d


def frac(n, d):
    return n if d == 1 else Fracao(n, d)


def parenteses(p):
    from sympy.printing.pretty.stringpict import prettyForm
    return prettyForm(*_forma(p).parens())


def vezes(*fatores):
    fatores = [f for f in fatores if f != 1] or [sp.Integer(1)]
    return fatores[0] if len(fatores) == 1 else sp.Mul(*fatores, evaluate=False)


def _simbolo_valor(a):
    """Símbolo que imprime o valor de a, para mostrar a substituição sem calcular."""
    t = _bonito(str(a))
    if not (a.is_Integer and a >= 0) and not a.is_Symbol and a not in (sp.pi, sp.E):
        t = f"({t})"
    return sp.Symbol(t)


def conta_subst(e, a, prefixo="= ") -> str:
    """Mostra  e(a)  com o número no lugar de x  =  valor."""
    v = _subs(e, a)
    trocada = e.xreplace({x: _simbolo_valor(a)})
    if str(trocada) == str(v) or not e.has(x):
        return linha(prefixo, v)
    return linha(prefixo, trocada, " = ", v)


def txt_ponto(a) -> str:
    """Ponto a escrito com símbolos (∞, −∞, π, e)."""
    if a == sp.oo:
        return "+∞"
    if a == -sp.oo:
        return "−∞"
    return _bonito(str(a))


def _bonito(txt: str) -> str:
    txt = re.sub(r"\bE\b", "e", txt)
    txt = re.sub(r"exp\(([^()]*)\)", r"e^(\1)", txt)
    txt = re.sub(r"\blog\(", "ln(", txt)
    txt = re.sub(r"\bsin\(", "sen(", txt)
    txt = re.sub(r"\bpi\b", "π", txt)
    return txt.replace("sqrt", "√").replace("**", "^")


def is_inf(v) -> bool:
    return isinstance(v, sp.Expr) and v in (sp.oo, -sp.oo, sp.zoo)


def _limite_lado(e, a, d):
    try:
        if a.is_finite:
            return sp.limit(e, x, a, dir=d)
        return sp.limit(e, x, a)
    except Exception:
        return sp.nan


def lim(e, a, d=None) -> Valor:
    """
    Limite de e quando x -> a.
    d = '+' (direita), '-' (esquerda) ou None (bilateral).
    No bilateral com a finito, compara os dois lados: se diferirem, devolve NAO_EXISTE.
    """
    if not a.is_finite:
        r = _limite_lado(e, a, None)
        return sp.simplify(r) if not isinstance(r, sp.Limit) else sp.nan
    if d in ("+", "-"):
        r = _limite_lado(e, a, d)
        return sp.simplify(r) if not isinstance(r, sp.Limit) else sp.nan
    esq, dir_ = _limite_lado(e, a, "-"), _limite_lado(e, a, "+")
    if esq == dir_:
        return sp.simplify(esq)
    return NAO_EXISTE


def fmt(r) -> str:
    if isinstance(r, str):
        return r
    if r is None or r is sp.nan or r == sp.nan or isinstance(r, sp.Limit):
        return "não foi possível determinar"
    if r == sp.oo:
        return "+∞ (diverge)"
    if r == -sp.oo:
        return "−∞ (diverge)"
    if r == sp.zoo:
        return "não existe (infinito sem sinal definido)"
    r = sp.simplify(r)
    txt = _bonito(str(r))
    if r.is_real and not r.is_Integer:
        try:
            txt += f"   ≈ {float(r):.6g}"
        except (TypeError, ValueError):
            pass
    return txt


def _tem_raiz(e) -> bool:
    return any(p.exp.is_Rational and not p.exp.is_integer for p in e.atoms(sp.Pow))


def _conjugado(e):
    """Conjugado de uma soma de dois termos: A + B -> A − B (mantendo a raiz positiva)."""
    if e.is_Add and len(e.args) == 2:
        A, B = e.args
        if not _tem_raiz(A):
            A, B = B, A
        return A - B
    return None


def _subs(expr, a):
    try:
        return sp.simplify(expr.subs(x, a))
    except Exception:
        return sp.nan


# ---------------------------------------------------------------------------
# Identificação da forma
# ---------------------------------------------------------------------------
def identificar(expr, a, d=None) -> str:
    """Classifica a forma de f(a) (ou do comportamento em ±∞)."""
    # Para classificar, um lado basta (no bilateral usa a direita).
    dc = d or "+"

    if expr.is_Pow and expr.base.has(x):
        vb, ve = lim(expr.base, a, dc), lim(expr.exp, a, dc)
        if vb == 1 and is_inf(ve):
            return "1^INF"
        if is_inf(vb) and ve == 0:
            return "INF^0"

    if expr.is_Add and len(expr.args) == 2:
        l1, l2 = (lim(t, a, dc) for t in expr.args)
        if is_inf(l1) and is_inf(l2) and l1 != l2:
            return "INF-INF"

    num, den = sp.fraction(sp.together(expr))

    if a.is_finite:
        vn, vd = _subs(num, a), _subs(den, a)
        if vn.is_zero and vd.is_zero:
            return "0/0"
        if vd.is_zero and vn.is_zero is False and vn.is_finite:
            return "C/0"
        v = _subs(expr, a)
        if v.is_real and v.is_finite:
            return "DIRETA"
        return "OUTRA"

    ln_, ld_ = lim(num, a), lim(den, a)
    if is_inf(ln_) and is_inf(ld_):
        return "INF/INF"
    if ln_ == 0 and ld_ == 0:
        return "0/0"
    if isinstance(ln_, sp.Expr) and isinstance(ld_, sp.Expr) and ln_.is_finite and ld_.is_finite \
            and ln_.is_real and ld_.is_real and ld_ != 0:
        return "DIRETA"
    return "OUTRA"


# ---------------------------------------------------------------------------
# Tratamento de cada ramo do fluxograma
# ---------------------------------------------------------------------------
def _resolvido(e, a) -> bool:
    return identificar(e, a) == "DIRETA"


# ---------------------------------------------------------------------------
# Passos numerados
# ---------------------------------------------------------------------------
class Passos(list):
    """Lista de (título, corpo). etapa() numera automaticamente."""

    def __init__(self):
        super().__init__()
        self.n = 0

    def __call__(self, titulo, corpo=""):
        self.append((titulo, corpo))

    def etapa(self, titulo, corpo=""):
        self.n += 1
        self.append((f"{self.n}) {titulo}", corpo))


def _sinal_perto(e, a, lado):
    """Sinal numérico de e logo à esquerda (-1) ou à direita (+1) de a."""
    for h in (1e-6, 1e-4, 1e-2):
        try:
            v = complex(sp.N(e.subs(x, a + lado * h)))
            if abs(v.imag) < 1e-12 and v.real != 0:
                return 1 if v.real > 0 else -1
        except (TypeError, ValueError):
            pass
    return 0


# ---------------------------------------------------------------------------
# c/0
# ---------------------------------------------------------------------------
def _tratar_c_sobre_zero(expr, a, d, add, num=None, den=None):
    if num is None:
        num, den = sp.fraction(sp.together(expr))
    c = _subs(num, a)
    txt = []
    lados = {"-": ("x → a⁻ (valores um pouco menores que a)", -1),
             "+": ("x → a⁺ (valores um pouco maiores que a)", 1)}
    res = {}
    for chave, (desc, lado) in lados.items():
        sd = _sinal_perto(den, a, lado)
        sn = 1 if c > 0 else -1
        zero = "0⁺" if sd > 0 else "0⁻"
        val = sp.oo if sn * sd > 0 else -sp.oo
        res[chave] = val
        txt.append(f"{desc}:\n  numerador → {_bonito(str(c))}   denominador → {zero}\n"
                   f"  {_bonito(str(c))}/{zero} = {'+∞' if val == sp.oo else '−∞'}")
    add.etapa("Analisar o sinal do denominador perto de a (limites laterais)", "\n\n".join(txt))
    esq, dir_ = res["-"], res["+"]
    if d == "-":
        r = esq
    elif d == "+":
        r = dir_
    elif esq == dir_:
        r = esq
        add.etapa("Conclusão", "Os laterais são iguais, então o limite bilateral é esse valor.")
    else:
        r = NAO_EXISTE
        add.etapa("Conclusão", "Os laterais são diferentes (−∞ ≠ +∞): o limite bilateral não existe.")
    return r, "Análise de c/0 pelos limites laterais"


# ---------------------------------------------------------------------------
# 0/0  ->  fatoração
# ---------------------------------------------------------------------------
def _tabela_ruffini(coefs, r):
    """Divide o polinômio de coeficientes 'coefs' por (x − r). Devolve (texto, quociente, resto)."""
    baixo, meio = [coefs[0]], [None]
    for c in coefs[1:]:
        m = baixo[-1] * r
        meio.append(m)
        baixo.append(c + m)
    fmt_n = lambda v: "" if v is None else _bonito(str(v))
    w = max(len(fmt_n(v)) for v in coefs + meio + baixo) + 2
    rt = _bonito(str(r))
    col = lambda vals: "".join(fmt_n(v).rjust(w) for v in vals)
    l1 = f"{' ' * len(rt)} │{col(coefs)}"
    l2 = f"{rt} │{col(meio)}"
    l3 = f"{' ' * len(rt)} ├{'─' * (w * len(coefs))}"
    l4 = f"{' ' * len(rt)} │{col(baixo[:-1])}{('│ ' + fmt_n(baixo[-1])).rjust(w + 1)}"
    return "\n".join([l1, l2, l3, l4]), baixo[:-1], baixo[-1]


def _fatorar_por_raiz(poly_expr, a, nome, add):
    """Divide por (x − a) via Briot-Ruffini enquanto der resto 0. Devolve (multiplicidade, quociente)."""
    P = sp.Poly(poly_expr, x)
    m = 0
    while P.degree() >= 1 and P.eval(a) == 0:
        tabela, q, resto = _tabela_ruffini(P.all_coeffs(), a)
        Q = sp.Poly(q, x)
        add.etapa(f"Briot-Ruffini no {nome}: dividir por (x − {_bonito(str(a))})",
                  f"{tabela}\n\n" + linha(P.as_expr(), " = ", vezes(x - a, Q.as_expr()), "   (resto 0)"))
        P, m = Q, m + 1
    return m, P.as_expr()


def _fatoracao(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    polinomios = num.is_polynomial(x) and den.is_polynomial(x)

    if polinomios and a.is_Rational:
        add.etapa("Por que fatorar?",
                  f"Numerador e denominador valem 0 em x = {_bonito(str(a))}.\n"
                  f"Pelo Teorema do Resto, (x − {_bonito(str(a))}) é fator dos dois.")
        mn, qn = _fatorar_por_raiz(num, a, "numerador", add)
        md, qd = _fatorar_por_raiz(den, a, "denominador", add)
        fn = vezes((x - a) ** mn if mn > 1 else x - a, qn) if mn else num
        fd = vezes((x - a) ** md if md > 1 else x - a, qd) if md else den
        k = min(mn, md)
        resto_n = (x - a) ** (mn - k) * qn
        resto_d = (x - a) ** (md - k) * qd
        simpl = sp.factor(resto_n / resto_d)
        fator = "(x − " + _bonito(str(a)) + ")" + (f"^{k}" if k > 1 else "")
        add.etapa("Reescrever f(x) fatorada e cancelar o fator comum",
                  linha("f(x) = ", frac(fn, fd)) + "\n\n"
                  f"Cancelando {fator} (pode, porque no limite x ≠ {_bonito(str(a))}):\n\n"
                  + linha("f(x) = ", simpl))
    else:
        fn, fd = sp.factor(num), sp.factor(den)
        simpl = sp.factor(sp.cancel(expr))
        add.etapa("Fatorar numerador e denominador",
                  linha("f(x) = ", frac(fn, fd)) + "\n\nCancelando o fator comum:\n\n"
                  + linha("f(x) = ", simpl))

    forma2 = identificar(simpl, a, d)
    if forma2 == "DIRETA":
        add.etapa("Substituição direta na expressão simplificada", conta_subst(simpl, a))
        return lim(simpl, a, d), "Fatoração (Briot-Ruffini) e cancelamento do fator comum"
    if forma2 == "C/0":
        add.etapa("Nova forma após simplificar", "Ficou c/0: analisar os limites laterais.")
        r, _ = _tratar_c_sobre_zero(simpl, a, d, add)
        return r, "Fatoração seguida de análise dos limites laterais"
    return None, None


# ---------------------------------------------------------------------------
# 0/0  ->  racionalização
# ---------------------------------------------------------------------------
def _racionalizacao(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    no_num = _tem_raiz(num)
    alvo = num if no_num else den
    c = _conjugado(alvo)
    if c is None:
        return None, None
    add.etapa("Multiplicar em cima e embaixo pelo conjugado",
              f"O {'numerador' if no_num else 'denominador'} tem raiz; o conjugado de\n"
              + linha("  ", alvo, "   é   ", c) + "\n\n"
              + linha(frac(num, den), " · ", frac(c, c)))
    novo_num = sp.expand(num * c)
    novo_den = sp.expand(den * c)
    if no_num:
        add.etapa("Numerador: produto da soma pela diferença (a + b)(a − b) = a² − b²",
                  linha(vezes(num, c), " = ", novo_num))
        mostrado = frac(novo_num, vezes(den, c))
    else:
        add.etapa("Denominador: produto da soma pela diferença (a + b)(a − b) = a² − b²",
                  linha(vezes(den, c), " = ", novo_den))
        mostrado = frac(vezes(num, c), novo_den)
    novo = sp.cancel(novo_num / (den * c)) if no_num else sp.cancel((num * c) / novo_den)
    add.etapa("Simplificar (cancelar o fator que zerava)",
              linha("f(x) = ", mostrado) + "\n\n" + linha("f(x) = ", novo))
    if identificar(novo, a, d) == "DIRETA":
        add.etapa("Substituição direta", conta_subst(novo, a))
        return lim(novo, a, d), "Racionalização com o conjugado"
    return None, None


# ---------------------------------------------------------------------------
# 0/0  ->  limites fundamentais
# ---------------------------------------------------------------------------
def _fundamental(num, a):
    """Procura no numerador um fator do tipo sen(u), tg(u), eᵘ − 1, ln(1 + u) com u → 0."""
    termos = [num] if not num.is_Mul else list(num.args)
    for t in termos:
        resto = sp.simplify(num / t)
        if isinstance(t, (sp.sin, sp.tan)):
            u = t.args[0]
            if _subs(u, a) == 0:
                nome = "sen" if isinstance(t, sp.sin) else "tg"
                return t, u, resto, f"lim u→0  {nome}(u)/u = 1"
        if t.is_Add and len(t.args) == 2 and -1 in t.args:
            outro = t - (-1)
            if isinstance(outro, sp.exp) and _subs(outro.args[0], a) == 0:
                return t, outro.args[0], resto, "lim u→0  (eᵘ − 1)/u = 1"
        if isinstance(t, sp.log):
            u = sp.expand(t.args[0] - 1)
            if _subs(u, a) == 0:
                return t, u, resto, "lim u→0  ln(1 + u)/u = 1"
    return None


def _lim_fundamentais(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    # 1 − cos(u): multiplicar por (1 + cos u) e usar sen²(u) = 1 − cos²(u)
    if num.is_Add and set(num.args) and any(isinstance(t, sp.cos) or (t.is_Mul and t.has(sp.cos))
                                            for t in num.args) and 1 in num.args:
        cosu = [t for t in num.atoms(sp.cos)][0]
        u = cosu.args[0]
        if sp.simplify(num - (1 - cosu)) == 0 and _subs(u, a) == 0:
            add.etapa("Limite fundamental trigonométrico", "lim u→0  sen(u)/u = 1")
            add.etapa("Multiplicar por (1 + cos u) e usar 1 − cos²(u) = sen²(u)",
                      linha(frac(1 - cosu, den), " · ", frac(1 + cosu, 1 + cosu), " = ",
                            frac(sp.sin(u) ** 2, vezes(den, 1 + cosu))))
            g = sp.simplify(u ** 2 / den)
            add.etapa("Separar no formato do limite fundamental",
                      linha(frac(sp.sin(u) ** 2, vezes(den, 1 + cosu)), " = ",
                            parenteses(frac(sp.sin(u), u)), "² · ", frac(1, 1 + cosu),
                            *([" · ", g] if g != 1 else [])))
            r = lim(sp.simplify(g / (1 + cosu)), a, d)
            add.etapa("Aplicar o limite (sen(u)/u → 1 e cos(u) → 1)",
                      linha("→ 1² · ", frac(1, sp.Symbol("1 + 1")),
                            *([" · ", _subs(g, a)] if g != 1 else []), " = ", r))
            return r, "Limite fundamental trigonométrico (multiplicando por 1 + cos u)"

    achado = _fundamental(num, a)
    if achado is None:
        return None, None
    t, u, resto, regra = achado
    tipo = "trigonométrico" if isinstance(t, (sp.sin, sp.tan)) else "exponencial"
    g = sp.cancel(u * resto / den)
    add.etapa(f"Limite fundamental {tipo}", regra)
    add.etapa("Multiplicar e dividir por u para formar o limite fundamental",
              linha("u = ", u, "   (u → 0 quando x → ", txt_ponto(a), ")") + "\n\n"
              + linha("f(x) = ", frac(t, u), " · ", frac(vezes(u, resto), den)))
    add.etapa("Simplificar a segunda parte", linha(frac(vezes(u, resto), den), " = ", g))
    lg = lim(g, a, d)
    if not (isinstance(lg, sp.Expr) and lg.is_finite):
        return None, None
    r = sp.simplify(lg)
    add.etapa("Aplicar o limite",
              linha(frac(t, u), " → 1      ", frac(vezes(u, resto), den), " → ", lg) + "\n\n"
              + linha("f(x) → 1 · ", lg, " = ", r))
    return r, f"Limite fundamental {tipo}"


def _tratar_zero_zero(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    polinomios = num.is_polynomial(x) and den.is_polynomial(x)
    simpl = sp.factor(sp.cancel(sp.together(expr)))

    tentativas = []
    if polinomios or (simpl != expr and not _tem_raiz(expr)):
        tentativas.append(_fatoracao)
    if _tem_raiz(expr):
        tentativas.append(_racionalizacao)
    if expr.has(sp.sin, sp.cos, sp.tan, sp.exp, sp.log):
        tentativas.append(_lim_fundamentais)

    for metodo in tentativas:
        tam = len(add)
        n = add.n
        r, nome = metodo(expr, a, d, add)
        if nome:
            return r, nome
        del add[tam:]       # descarta as etapas da tentativa que não resolveu
        add.n = n

    return _lhopital(expr, a, d, add), "Regra de L'Hôpital"


# ---------------------------------------------------------------------------
# L'Hôpital
# ---------------------------------------------------------------------------
def _lhopital(expr, a, d, add):
    add.etapa("Regra de L'Hôpital", "Em 0/0 ou ∞/∞:  lim f/g = lim f'/g'  (derivar em cima e embaixo separadamente)")
    e = expr
    for k in range(1, 5):
        n_, d_ = sp.fraction(sp.together(e))
        dn, dd = sp.simplify(sp.diff(n_, x)), sp.simplify(sp.diff(d_, x))
        e = sp.simplify(dn / dd)
        add.etapa(f"{k}ª derivação",
                  linha("f  = ", n_) + "\n" + linha("f' = ", dn) + "\n\n"
                  + linha("g  = ", d_) + "\n" + linha("g' = ", dd) + "\n\n"
                  + linha("f'/g' = ", frac(dn, dd), " = ", e))
        if identificar(e, a, d) not in ("INF/INF", "0/0"):
            break
        add("   ainda indeterminado: derivar de novo", "")
    r = lim(e, a, d)
    if a.is_finite and identificar(e, a, d) == "DIRETA":
        add.etapa("Substituição direta", conta_subst(e, a))
    else:
        add.etapa("Limite da nova expressão", linha("→ ", r if isinstance(r, sp.Expr) else fmt(r)))
    return r


# ---------------------------------------------------------------------------
# ∞/∞
# ---------------------------------------------------------------------------
def _grau(e, a):
    """'Grau' de e no infinito: p tal que e/xᵖ tende a um número não nulo."""
    try:
        P = sp.Poly(e, x)
        return P.degree()
    except (sp.PolynomialError, sp.GeneratorsNeeded):
        pass
    try:
        p = sp.limit(sp.log(sp.Abs(e)) / sp.log(sp.Abs(x)), x, a)
        if p.is_Rational:
            return p
    except Exception:
        pass
    return None


def _dividir_por_potencia(e, p, a):
    """e/xᵖ termo a termo, levando xᵖ para dentro das raízes (x > 0 ou x < 0 conforme a)."""
    s = 1 if a == sp.oo or p.is_even else -1   # √(x^(2p)) = |x|^p
    termos = sp.Add.make_args(sp.expand(e))
    novos = []
    for t in termos:
        raizes = [f for f in sp.Mul.make_args(t) if f.is_Pow and f.exp == sp.Rational(1, 2)]
        if raizes:
            r = raizes[0]
            fora = sp.Mul(*[f for f in sp.Mul.make_args(t) if f is not r])
            novos.append(s * sp.expand(fora) * sp.sqrt(sp.expand(r.base / x ** (2 * p))))
        else:
            novos.append(sp.expand(t / x ** p))
    return sp.Add(*novos)


def _tratar_inf_sobre_inf(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    transcendente = expr.has(sp.exp, sp.log, sp.sin, sp.cos, sp.tan) or \
        any(q.exp.has(x) for q in expr.atoms(sp.Pow))
    pn, pd = (None, None) if transcendente else (_grau(num, a), _grau(den, a))
    if pn is None or pd is None:
        return _lhopital(expr, a, d, add), "Regra de L'Hôpital"

    eh_poli = num.is_polynomial(x) and den.is_polynomial(x)
    if eh_poli:
        en, ed = sp.expand(num / x ** pn), sp.expand(den / x ** pd)
        add.etapa("Colocar em evidência o termo de maior grau",
                  linha("numerador   = ", vezes(x ** pn, en) if pn else num) + "\n\n"
                  + linha("denominador = ", vezes(x ** pd, ed) if pd else den))
        add.etapa("Reescrever f(x)",
                  linha("f(x) = ", frac(vezes(x ** pn, en), vezes(x ** pd, ed)), " = ",
                        *([x ** (pn - pd), " · "] if pn != pd else []), frac(en, ed)))
        ln_, ld_ = sp.Poly(num, x).LC(), sp.Poly(den, x).LC()
        add.etapa("Termos do tipo c/xᵏ tendem a 0 quando x → " + txt_ponto(a),
                  linha(en, "  →  ", ln_) + "\n" + linha(ed, "  →  ", ld_))
        resto = x ** (pn - pd) * ln_ / ld_
    else:
        p = pd
        en, ed = _dividir_por_potencia(num, p, a), _dividir_por_potencia(den, p, a)
        add.etapa(f"Dividir numerador e denominador por x^{p} (maior potência do denominador)",
                  linha("f(x) = ", frac(en, ed)))
        ln_, ld_ = lim(en, a), lim(ed, a)
        add.etapa("Termos do tipo c/xᵏ tendem a 0 quando x → " + txt_ponto(a),
                  linha(en, "  →  ", ln_) + "\n" + linha(ed, "  →  ", ld_))
        resto = ln_ / ld_

    r = lim(sp.sympify(resto), a)
    if eh_poli:
        if pn == pd:
            regra = "graus iguais → razão dos coeficientes"
        elif pn < pd:
            regra = "grau de cima menor → 0"
        else:
            regra = "grau de cima maior → ±∞ (o sinal vem dos coeficientes e de x)"
        add.etapa("Conclusão (" + regra + ")", linha("f(x) → ", resto, "  →  ", r if r.is_finite else fmt(r)))
    else:
        add.etapa("Conclusão", linha("f(x) → ", resto, " = ", r if r.is_finite else fmt(r)))
    return r, "Termo de maior grau (dividir pela maior potência)"


# ---------------------------------------------------------------------------
# ∞ − ∞
# ---------------------------------------------------------------------------
def _tratar_inf_menos_inf(expr, a, d, add):
    A, B = expr.args
    if not _tem_raiz(A):
        A, B = B, A
    if _tem_raiz(expr):
        c = A - B
        add.etapa("Multiplicar e dividir pelo conjugado",
                  linha("f(x) = ", frac(vezes(A + B, c), c)))
        novo_num = sp.expand(A ** 2 - B ** 2)
        diff = sp.Add(sp.expand(A ** 2), -sp.expand(B ** 2), evaluate=False)
        add.etapa("Numerador: (a + b)(a − b) = a² − b²",
                  linha(vezes(A + B, c), " = ", diff, " = ", novo_num))
        novo = frac(novo_num, c)
        add.etapa("Nova expressão (agora ∞/∞)", linha("f(x) = ", novo))
        r, _ = _tratar_inf_sobre_inf(novo_num / c, a, d, add)
        return r, "Multiplicação pelo conjugado + termo de maior grau"
    novo = sp.factor(sp.together(expr))
    add.etapa("Juntar numa fração só (MMC) e simplificar", linha("f(x) = ", novo))
    forma2 = identificar(novo, a, d)
    if forma2 == "INF/INF":
        r, _ = _tratar_inf_sobre_inf(novo, a, d, add)
    else:
        r = lim(novo, a, d)
        add.etapa("Limite da nova expressão", fmt(r))
    return r, "Simplificação algébrica (MMC)"


# ---------------------------------------------------------------------------
# 1^∞  e  ∞^0
# ---------------------------------------------------------------------------
def _tratar_um_elevado_inf(expr, a, d, add):
    base, ex = expr.args
    add.etapa("Limite fundamental exponencial",
              "Se base → 1 e expoente → ∞:\n\n"
              + linha("lim baseᵉˣᵖᵒᵉⁿᵗᵉ = e^", sp.Symbol("lim (base − 1)·expoente")) + "\n\n"
              + "(caso particular: (1 + k/x)ˣ → eᵏ)")
    b1 = sp.simplify(base - 1)
    add.etapa("Calcular base − 1", linha(base, " − 1 = ", b1))
    prod = sp.simplify(ex * b1)
    add.etapa("Multiplicar pelo expoente", linha(vezes(b1, ex), " = ", prod))
    g = lim(prod, a, d)
    add.etapa("Limite do expoente", linha(sp.Symbol("lim (base − 1)·expoente"), " = ",
                                          g if isinstance(g, sp.Expr) else fmt(g)))
    r = sp.exp(g) if isinstance(g, sp.Expr) else g
    add.etapa("Resultado", linha("e^", g, " = ", r) if isinstance(g, sp.Expr) else fmt(r))
    return r, "Limite fundamental exponencial (forma 1^∞)"


def _tratar_inf_elevado_zero(expr, a, d, add):
    base, ex = expr.args
    add.etapa("Reescrever como exponencial",
              linha("baseᵉˣᵖᵒᵉⁿᵗᵉ = e^", sp.Symbol("(expoente · ln(base))")))
    prod = sp.simplify(ex * sp.log(base))
    add.etapa("Expoente", linha("expoente · ln(base) = ", prod))
    forma2 = identificar(prod, a, d)
    if forma2 in ("INF/INF", "0/0"):
        g = _lhopital(prod, a, d, add)
    else:
        g = lim(prod, a, d)
        add.etapa("Limite do expoente", fmt(g))
    r = sp.exp(g) if isinstance(g, sp.Expr) else g
    add.etapa("Resultado", linha("e^", g, " = ", r) if isinstance(g, sp.Expr) else fmt(r))
    return r, "Forma exponencial e^(expoente·ln base) (forma ∞^0)"


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------
def resolver(expr: sp.Expr, a: sp.Expr, d: Optional[str] = None) -> Resultado:
    """Resolve lim x→a f(x) mostrando o passo a passo do fluxograma."""
    add = Passos()

    if not a.is_finite:
        d = None

    forma = identificar(expr, a, d)
    add("Função", linha("f(x) = ", expr))
    add("Ponto e direção", f"x → {txt_ponto(a)}  ({DIR_TXT[d]})")

    if a.is_finite:
        num, den = sp.fraction(sp.together(expr))
        if den != 1 and forma != "DIRETA":
            add.etapa("Substituição direta",
                      "numerador:\n" + conta_subst(num, a, "  ") + "\n\n"
                      "denominador:\n" + conta_subst(den, a, "  "))
        else:
            add.etapa("Substituição direta", conta_subst(expr, a, f"f({txt_ponto(a)}) = "))
    else:
        add.etapa("Comportamento no infinito", "Ver para onde vão os termos quando x → " + txt_ponto(a))
    add("Forma identificada", FORMA_NOME[forma])

    if forma == "DIRETA":
        r = _subs(expr, a) if a.is_finite else lim(expr, a)
        add.etapa("Conclusão", "Não há indeterminação: o limite é o próprio valor da expressão.")
        metodo = "Substituição direta" + (" (f é contínua em a)" if a.is_finite else "")
    elif forma == "C/0":
        r, metodo = _tratar_c_sobre_zero(expr, a, d, add)
    elif forma == "0/0":
        r, metodo = _tratar_zero_zero(expr, a, d, add)
    elif forma == "INF/INF":
        r, metodo = _tratar_inf_sobre_inf(expr, a, d, add)
    elif forma == "INF-INF":
        r, metodo = _tratar_inf_menos_inf(expr, a, d, add)
    elif forma == "1^INF":
        r, metodo = _tratar_um_elevado_inf(expr, a, d, add)
    elif forma == "INF^0":
        r, metodo = _tratar_inf_elevado_zero(expr, a, d, add)
    else:
        r = lim(expr, a, d)
        add.etapa("Cálculo simbólico direto (SymPy)", fmt(r))
        metodo = "Cálculo simbólico direto (SymPy)"

    # conferência: o valor mostrado tem que bater com o SymPy
    if isinstance(r, sp.Expr):
        oficial = lim(expr, a, d)
        if isinstance(oficial, sp.Expr) and oficial is not sp.nan and sp.simplify(oficial - r) != 0 \
                and oficial != r:
            add("Aviso", f"O passo a passo chegou em {fmt(r)}, mas o SymPy dá {fmt(oficial)}. Usando o SymPy.")
            r = oficial

    continuo = False
    if a.is_finite and isinstance(r, sp.Expr) and r.is_finite:
        fa = _subs(expr, a)
        continuo = bool(fa.is_real and fa.is_finite and sp.simplify(fa - r) == 0)
        if forma != "DIRETA":
            add("Continuidade",
                f"f({txt_ponto(a)}) existe e é igual ao limite → contínua em a" if continuo
                else f"f({txt_ponto(a)}) não está definida (ou ≠ L) → descontinuidade em a")

    if isinstance(r, sp.Expr) and r.is_finite:
        corpo = linha(f"lim x→{txt_ponto(a)} f(x) = ", r)
        if not r.is_Integer:
            corpo += "\n\n" + fmt(r)
    else:
        corpo = fmt(r)
    add("Resultado", corpo)
    add("Método utilizado", metodo)
    return Resultado(forma=forma, valor=r, metodo=metodo, passos=list(add), continuo=continuo)
