"""Janela principal da Calculadora de Limites (CustomTkinter + Matplotlib)."""
import threading
from tkinter import messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from limites import parse_funcao, parse_ponto, resolver
from limites.grafico import aplicar_estilo, plotar
from limites.solver import txt_ponto

DIRECOES = {"Bilateral": None, "Esquerda (a⁻)": "-", "Direita (a⁺)": "+"}

EXEMPLOS = {
    "f(a) = L  ·  x² + 3x,  x→2": ("x^2 + 3x", "2"),
    "c/0  ·  1/x,  x→0": ("1/x", "0"),
    "c/0  ·  1/x²,  x→0": ("1/x^2", "0"),
    "0/0 fatorar  ·  (x²−1)/(x−1),  x→1": ("(x^2 - 1)/(x - 1)", "1"),
    "0/0 conjugado  ·  (√(x+1)−1)/x,  x→0": ("(sqrt(x + 1) - 1)/x", "0"),
    "0/0 trigonométrico  ·  sen(x)/x,  x→0": ("sen(x)/x", "0"),
    "0/0 exponencial  ·  (eˣ−1)/x,  x→0": ("(exp(x) - 1)/x", "0"),
    "∞/∞  ·  (3x²+1)/(2x²−x),  x→∞": ("(3x^2 + 1)/(2x^2 - x)", "oo"),
    "∞/∞ L'Hôpital  ·  ln(x)/x,  x→∞": ("ln(x)/x", "oo"),
    "∞−∞  ·  √(x²+x) − x,  x→∞": ("sqrt(x^2 + x) - x", "oo"),
    "1^∞  ·  (1+1/x)^x,  x→∞": ("(1 + 1/x)^x", "oo"),
    "1^∞  ·  (1+2/x)^(3x),  x→∞": ("(1 + 2/x)^(3x)", "oo"),
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Calculadora de Limites")
        self.geometry("1360x820")
        self.minsize(1050, 650)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._montar_entrada()
        self._montar_passos()
        self._montar_grafico()
        self._montar_resultado()
        self.bind("<Return>", lambda _e: self.calcular())

    # ------------------------------------------------------------------ layout
    def _montar_entrada(self):
        p = ctk.CTkFrame(self, corner_radius=14)
        p.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))
        p.grid_columnconfigure(1, weight=1)

        negrito = ctk.CTkFont(size=15, weight="bold")
        ctk.CTkLabel(p, text="f(x) =", font=negrito).grid(row=0, column=0, padx=(16, 6), pady=(14, 6))
        self.ent_f = ctk.CTkEntry(p, height=36, font=ctk.CTkFont(size=14),
                                  placeholder_text="ex: (x^2 - 1)/(x - 1),  sen(x)/x,  (1 + 1/x)^x")
        self.ent_f.grid(row=0, column=1, sticky="ew", padx=6, pady=(14, 6))

        ctk.CTkLabel(p, text="x →", font=negrito).grid(row=0, column=2, padx=(14, 6), pady=(14, 6))
        self.ent_a = ctk.CTkEntry(p, width=110, height=36, font=ctk.CTkFont(size=14),
                                  placeholder_text="1 · oo · -oo")
        self.ent_a.grid(row=0, column=3, padx=6, pady=(14, 6))

        self.seg = ctk.CTkSegmentedButton(p, values=list(DIRECOES))
        self.seg.set("Bilateral")
        self.seg.grid(row=0, column=4, padx=10, pady=(14, 6))

        self.btn = ctk.CTkButton(p, text="Calcular", width=130, height=36,
                                 font=negrito, command=self.calcular)
        self.btn.grid(row=0, column=5, padx=(6, 16), pady=(14, 6))

        menu = ctk.CTkOptionMenu(p, values=list(EXEMPLOS), command=self._carregar_exemplo, width=330)
        menu.set("Exemplos do fluxograma…")
        menu.grid(row=1, column=0, columnspan=2, padx=16, pady=(4, 14), sticky="w")

        dica = "Use x^2 ou x**2 · sen, cos, tg, ln, exp, sqrt · pi, e · oo = +∞, -oo = −∞ · Enter calcula"
        ctk.CTkLabel(p, text=dica, text_color="gray60").grid(
            row=1, column=2, columnspan=4, padx=16, pady=(4, 14), sticky="e")

    def _montar_passos(self):
        f = ctk.CTkFrame(self, corner_radius=14)
        f.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=8)
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f, text="Passo a passo", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 0))
        self.txt = ctk.CTkTextbox(f, width=500, font=("Consolas", 13), wrap="none")
        self.txt.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.txt.tag_config("titulo", foreground="#5dade2")

    def _montar_grafico(self):
        f = ctk.CTkFrame(self, corner_radius=14)
        f.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=8)
        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        aplicar_estilo(self.fig, self.ax)
        self.canvas = FigureCanvasTkAgg(self.fig, master=f)
        bar = NavigationToolbar2Tk(self.canvas, f, pack_toolbar=False)
        bar.update()
        bar.pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True, padx=6, pady=6)

    def _montar_resultado(self):
        f = ctk.CTkFrame(self, corner_radius=14)
        f.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 16))
        self.lbl_res = ctk.CTkLabel(f, text="Resultado: —", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_res.pack(anchor="w", padx=16, pady=(10, 0))
        self.lbl_met = ctk.CTkLabel(f, text="Digite a função e o ponto, depois clique em Calcular.",
                                    text_color="gray70")
        self.lbl_met.pack(anchor="w", padx=16, pady=(0, 10))

    # ------------------------------------------------------------------ ações
    def _carregar_exemplo(self, escolha):
        funcao, ponto = EXEMPLOS[escolha]
        self.ent_f.delete(0, "end")
        self.ent_f.insert(0, funcao)
        self.ent_a.delete(0, "end")
        self.ent_a.insert(0, ponto)
        self.seg.set("Bilateral")
        self.calcular()

    def calcular(self):
        try:
            expr = parse_funcao(self.ent_f.get())
            a = parse_ponto(self.ent_a.get())
        except Exception as exc:
            messagebox.showerror("Entrada inválida", str(exc))
            return
        d = DIRECOES[self.seg.get()]

        self.btn.configure(state="disabled", text="Calculando…")
        self.lbl_met.configure(text="Calculando…")

        def trabalho():  # SymPy fora da thread da interface para a janela não travar
            try:
                res = resolver(expr, a, d)
                self.after(0, lambda: self._mostrar(expr, a, res))
            except Exception as exc:
                self.after(0, lambda e=exc: self._erro(e))

        threading.Thread(target=trabalho, daemon=True).start()

    def _erro(self, exc):
        self.btn.configure(state="normal", text="Calcular")
        self.lbl_met.configure(text="")
        messagebox.showerror("Erro", f"Não foi possível calcular:\n{exc}")

    def _mostrar(self, expr, a, res):
        self.btn.configure(state="normal", text="Calcular")

        self.txt.delete("1.0", "end")
        for titulo, corpo in res.passos:
            self.txt.insert("end", f"▸ {titulo}\n", "titulo")
            self.txt.insert("end", f"{corpo}\n\n")

        self.lbl_res.configure(text=f"lim x→{txt_ponto(a)} f(x) = {res.texto}")
        self.lbl_met.configure(text=f"Método: {res.metodo}")

        try:
            plotar(self.fig, self.ax, expr, a, res)
        except Exception as exc:
            self.ax.clear()
            aplicar_estilo(self.fig, self.ax)
            self.ax.text(0.5, 0.5, f"Não foi possível plotar:\n{exc}", ha="center", va="center",
                         color="#dddddd", transform=self.ax.transAxes)
        self.canvas.draw_idle()
