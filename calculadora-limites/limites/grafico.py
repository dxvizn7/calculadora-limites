"""Plotagem de f(x) ao redor do ponto a, destacando (a, L)."""
import numpy as np
import sympy as sp

from .parser import x
from .solver import Resultado, txt_ponto

CORES = {
    "fundo": "#1b1b1b",
    "figura": "#242424",
    "texto": "#cccccc",
    "borda": "#555555",
    "curva": "#3b8ed0",
    "x_a": "#f39c12",
    "y_L": "#2ecc71",
    "ponto": "#e74c3c",
}


def aplicar_estilo(fig, ax):
    fig.patch.set_facecolor(CORES["figura"])
    ax.set_facecolor(CORES["fundo"])
    ax.tick_params(colors=CORES["texto"])
    for s in ax.spines.values():
        s.set_color(CORES["borda"])


def _amostrar(expr, a):
    f = sp.lambdify(x, expr, modules="numpy")
    if a.is_finite:
        ac = float(sp.N(a))
        xs = np.linspace(ac - 4, ac + 4, 4001)
        xs = xs[np.abs(xs - ac) > 1e-9]
    else:
        ac = None
        xs = np.linspace(1, 60, 4000) if a == sp.oo else np.linspace(-60, -1, 4000)

    with np.errstate(all="ignore"):
        ys = f(xs)
    ys = np.asarray(ys, dtype=complex if np.iscomplexobj(ys) else float)
    if np.iscomplexobj(ys):
        ys = np.where(np.abs(ys.imag) < 1e-12, ys.real, np.nan)
    ys = np.broadcast_to(ys, xs.shape).astype(float).copy()
    ys[~np.isfinite(ys)] = np.nan
    return xs, ys, ac


def _limites_y(ys, L):
    validos = ys[np.isfinite(ys)]
    if validos.size == 0:
        lo, hi = -1.0, 1.0
    else:
        lo, hi = np.percentile(validos, [3, 97])
    if L is not None:
        lo, hi = min(lo, L), max(hi, L)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    m = 0.15 * (hi - lo)
    return lo - m, hi + m


def plotar(fig, ax, expr, a, res: Resultado):
    """Desenha f(x), as retas tracejadas x = a e y = L e o ponto (a, L)."""
    ax.clear()
    aplicar_estilo(fig, ax)

    xs, ys, ac = _amostrar(expr, a)
    L = float(sp.N(res.numerico)) if res.numerico is not None else None

    y0, y1 = _limites_y(ys, L)
    # quebra a curva em saltos/assíntotas para não ligar ramos diferentes
    salto = np.abs(np.diff(ys)) > (y1 - y0)
    ys[1:][salto] = np.nan
    if ac is not None:  # não ligar a curva por cima de x = a
        ys[np.argmin(np.abs(xs - ac))] = np.nan

    ax.plot(xs, ys, color=CORES["curva"], lw=2.2, label="f(x)")

    if ac is not None:
        ax.axvline(ac, ls="--", color=CORES["x_a"], lw=1.3, label=f"x → {txt_ponto(a)}")
    if L is not None:
        ax.axhline(L, ls="--", color=CORES["y_L"], lw=1.3, label=f"f(x) → L = {L:.4g}")
        if ac is not None:
            ax.plot([ac], [L], "o", ms=11, mew=2.2, mec=CORES["ponto"], zorder=5,
                    mfc=CORES["curva"] if res.continuo else "none",
                    label="(a, L): contínua" if res.continuo else "(a, L): f(a) ≠ L ou indefinida")
            # setas de aproximação dos dois lados
            for lado in (-1, 1):
                xi = ac + lado * 1.2
                with np.errstate(all="ignore"):
                    yi = float(sp.N(expr.subs(x, xi))) if expr.subs(x, xi).is_real else None
                if yi is not None and y0 < yi < y1:
                    ax.annotate("", xy=(ac + lado * 0.25, L), xytext=(xi, yi),
                                arrowprops=dict(arrowstyle="->", color=CORES["texto"],
                                                lw=1, ls=":"))

    ax.set_ylim(y0, y1)
    ax.set_title(f"lim x → {txt_ponto(a)} f(x) = {res.texto.split('   ')[0]}", color="#eeeeee")
    ax.set_xlabel("x", color=CORES["texto"])
    ax.set_ylabel("f(x)", color=CORES["texto"])
    ax.grid(True, alpha=0.25)
    ax.legend(facecolor="#2a2a2a", edgecolor="#444444", labelcolor="#dddddd", fontsize=9,
              loc="best")
