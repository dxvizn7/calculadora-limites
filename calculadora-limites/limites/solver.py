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
    return sp.pretty(_empilhar(e), use_unicode=True)


def rotulo(texto: str, e) -> str:
    """Escreve 'texto' ao lado da expressão 2D, alinhado na linha da fração."""
    from sympy.printing.pretty.pretty import PrettyPrinter
    forma = PrettyPrinter({"use_unicode": True})._print(_empilhar(sp.sympify(e)))
    linhas = str(forma).split("\n")
    base = forma.baseline if 0 <= forma.baseline < len(linhas) else len(linhas) // 2
    pad = " " * len(texto)
    return "\n".join((texto if i == base else pad) + l for i, l in enumerate(linhas))


def txt_ponto(a) -> str:
    """Ponto a escrito com símbolos (∞, −∞, π, e)."""
    if a == sp.oo:
        return "+∞"
    if a == -sp.oo:
        return "−∞"
    return _bonito(str(a))


def _bonito(txt: str) -> str:
    txt = re.sub(r"\bE\b", "e", txt)
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


def _tratar_c_sobre_zero(expr, a, d, add):
    esq, dir_ = lim(expr, a, "-"), lim(expr, a, "+")
    add("2) Limites laterais",
        f"lim x→a⁻ f(x) = {fmt(esq)}\nlim x→a⁺ f(x) = {fmt(dir_)}")
    if d == "-":
        r = esq
    elif d == "+":
        r = dir_
    elif esq == dir_:
        r = esq
        add("3) Conclusão", "Os laterais são iguais: o limite bilateral é esse valor.")
    else:
        r = NAO_EXISTE
        add("3) Conclusão", "Os laterais são diferentes: o limite bilateral não existe.")
    return r, "Análise de c/0 pelos limites laterais"


def _tratar_zero_zero(expr, a, d, add):
    # 1º: fatoração (divisão de polinômios)
    simpl = sp.factor(sp.cancel(sp.together(expr)))
    if simpl != expr and _resolvido(simpl, a):
        add("2) Fatoração e cancelamento do fator comum", pretty(simpl))
        add("3) Substituição direta na expressão simplificada", rotulo("= ", _subs(simpl, a)))
        return lim(simpl, a, d), "Fatoração (cancelamento do fator comum)"

    # 2º: racionalização (multiplicar pelo conjugado)
    if _tem_raiz(expr):
        num, den = sp.fraction(sp.together(expr))
        alvo_num = _tem_raiz(num)
        c = _conjugado(num if alvo_num else den)
        if c is not None:
            novo = sp.cancel(sp.expand(num * c) / sp.expand(den * c))
            add("2) Racionalização: multiplicar numerador e denominador pelo conjugado",
                f"conjugado:\n{pretty(c)}\n\nnova expressão:\n{pretty(novo)}")
            if _resolvido(novo, a):
                add("3) Substituição direta", rotulo("= ", _subs(novo, a)))
                return lim(novo, a, d), "Racionalização com o conjugado"

    # 3º: limites fundamentais
    if expr.has(sp.sin, sp.cos, sp.tan):
        add("2) Limite fundamental trigonométrico",
            "lim u→0  sen(u)/u = 1\n(e consequências: tg(u)/u → 1, (1 − cos u)/u² → 1/2)")
        r = lim(expr, a, d)
        add("3) Aplicando o limite fundamental", f"= {fmt(r)}")
        return r, "Limite fundamental trigonométrico"

    if expr.has(sp.exp) or expr.has(sp.log) or any(p.exp.has(x) for p in expr.atoms(sp.Pow)):
        add("2) Limite fundamental exponencial",
            "lim u→0  (eᵘ − 1)/u = 1     lim u→0  (aᵘ − 1)/u = ln a\nlim u→0  ln(1 + u)/u = 1")
        r = lim(expr, a, d)
        add("3) Aplicando o limite fundamental", f"= {fmt(r)}")
        return r, "Limite fundamental exponencial"

    # 4º: L'Hôpital como último recurso
    return _lhopital(expr, a, d, add, "2"), "Regra de L'Hôpital"


def _lhopital(expr, a, d, add, prefixo):
    e = expr
    for k in range(1, 5):
        n_, d_ = sp.fraction(sp.together(e))
        e = sp.simplify(sp.diff(n_, x) / sp.diff(d_, x))
        add(f"{prefixo}.{k}) L'Hôpital ({k}ª derivação: f'/g')", pretty(e))
        if identificar(e, a, d) not in ("INF/INF", "0/0"):
            break
    return lim(e, a, d)


def _tratar_inf_sobre_inf(expr, a, d, add):
    num, den = sp.fraction(sp.together(expr))
    try:
        P, Q = sp.Poly(num, x), sp.Poly(den, x)
        tn = P.LC() * x ** P.degree()
        td = Q.LC() * x ** Q.degree()
        q = sp.simplify(tn / td)
        add("2) Colocar em evidência o termo de maior grau",
            rotulo("numerador   ~ ", tn) + "\n" + rotulo("denominador ~ ", td) + "\n\n" + rotulo("quociente   ~ ", q))
        r = lim(q, a)
        add("3) Limite do quociente", f"= {fmt(r)}")
        return r, "Termo de maior grau (numerador e denominador)"
    except (sp.PolynomialError, sp.GeneratorsNeeded):
        pass
    return _lhopital(expr, a, d, add, "2"), "Regra de L'Hôpital"


def _tratar_inf_menos_inf(expr, a, d, add):
    A, B = expr.args
    novo = sp.simplify((A ** 2 - B ** 2) / (A - B))
    add("2) Multiplicar e dividir pelo conjugado",
        f"(A + B)·(A − B)/(A − B) = (A² − B²)/(A − B)\n\n{pretty(novo)}")
    forma2 = identificar(novo, a, d)
    if forma2 == "INF/INF":
        r, _ = _tratar_inf_sobre_inf(novo, a, d, add)
    else:
        r = lim(novo, a, d)
        add("3) Limite da nova expressão", f"= {fmt(r)}")
    return r, "Multiplicação pelo conjugado"


def _tratar_um_elevado_inf(expr, a, d, add):
    base, ex = expr.args
    g = lim(sp.simplify(ex * (base - 1)), a, d)
    add("2) Limite fundamental exponencial",
        "Se base → 1 e expoente → ∞:\nlim baseᵉˣᵖ = e^( lim (base − 1)·expoente )")
    add("3) Expoente", f"lim (base − 1)·expoente = {fmt(g)}")
    r = sp.exp(g) if isinstance(g, sp.Expr) else g
    add("4) Resultado", f"e^({g}) = {fmt(r)}")
    return r, "Limite fundamental exponencial (forma 1^∞)"


def _tratar_inf_elevado_zero(expr, a, d, add):
    base, ex = expr.args
    g = lim(sp.simplify(ex * sp.log(base)), a, d)
    add("2) Reescrever como exponencial",
        "baseᵉˣᵖ = e^( expoente·ln(base) )")
    add("3) Expoente", f"lim expoente·ln(base) = {fmt(g)}")
    r = sp.exp(g) if isinstance(g, sp.Expr) else g
    return r, "Forma exponencial e^(expoente·ln base) (forma ∞^0)"


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------
def resolver(expr: sp.Expr, a: sp.Expr, d: Optional[str] = None) -> Resultado:
    """Resolve lim x→a f(x) mostrando o passo a passo do fluxograma."""
    passos: List[Tuple[str, str]] = []

    def add(titulo, corpo=""):
        passos.append((titulo, corpo))

    if not a.is_finite:
        d = None

    forma = identificar(expr, a, d)
    add("Função", pretty(expr))
    add("Ponto e direção", f"x → {txt_ponto(a)}  ({DIR_TXT[d]})")

    if a.is_finite:
        num, den = sp.fraction(sp.together(expr))
        if den != 1:
            add("1) Substituição direta",
                rotulo(f"numerador   em x = {txt_ponto(a)}: ", _subs(num, a)) + "\n"
                + rotulo(f"denominador em x = {txt_ponto(a)}: ", _subs(den, a)))
        else:
            add("1) Substituição direta", rotulo(f"f({txt_ponto(a)}) = ", _subs(expr, a)))
    else:
        add("1) Comportamento no infinito", "Analisar para onde vão os termos quando x → " + txt_ponto(a))
    add("Forma identificada", FORMA_NOME[forma])

    if forma == "DIRETA":
        r = _subs(expr, a) if a.is_finite else lim(expr, a)
        add("2) Conclusão", "Não há indeterminação: o limite é o próprio valor da expressão.")
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
        add("2) Cálculo simbólico direto (SymPy)", fmt(r))
        metodo = "Cálculo simbólico direto (SymPy)"

    continuo = False
    if a.is_finite and isinstance(r, sp.Expr) and r.is_finite:
        fa = _subs(expr, a)
        continuo = bool(fa.is_real and fa.is_finite and sp.simplify(fa - r) == 0)
        if forma != "DIRETA":
            add("Continuidade",
                "f(a) existe e é igual ao limite → contínua em a" if continuo
                else "f(a) não está definida (ou ≠ L) → descontinuidade em a")

    add("Resultado", (pretty(r) + "\n\n" if isinstance(r, sp.Expr) and r.is_finite and not r.is_Integer else "") + fmt(r))
    add("Método utilizado", metodo)
    return Resultado(forma=forma, valor=r, metodo=metodo, passos=passos, continuo=continuo)
