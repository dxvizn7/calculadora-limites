# Calculadora de Limites

Aplicativo desktop em Python que calcula limites **passo a passo**, seguindo o fluxograma do *Resumo de Limites* de Cálculo I, e mostra o gráfico da função ao redor do ponto.

- Interface: **CustomTkinter**
- Cálculo simbólico: **SymPy**
- Gráfico embutido: **Matplotlib**

## Instalação

Requer Python 3.9+ com Tkinter (já vem no instalador oficial do Python para Windows).

```bash
git clone https://github.com/dxvizn7/calculadora-limites.git
cd calculadora-limites
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Como usar

| Campo | Exemplos |
|---|---|
| `f(x)` | `(x^2 - 1)/(x - 1)`, `sen(x)/x`, `(1 + 1/x)^x`, `sqrt(x^2 + x) - x`, `ln(x)/x` |
| `x →` | `1`, `0`, `1/2`, `pi`, `oo` (+∞), `-oo` (−∞) |
| Direção | Bilateral, Esquerda (a⁻), Direita (a⁺) |

Aceita `x^2` ou `x**2`, multiplicação implícita (`2x`, `3x^2`) e as funções `sen/sin`, `cos`, `tg/tan`, `ln/log`, `exp`, `sqrt`.
O menu **Exemplos do fluxograma** carrega um caso de cada ramo. **Enter** calcula.

## Fluxograma implementado

**x → a (a real)**

| f(a) | O que o programa faz |
|---|---|
| L ∈ ℝ | Substituição direta: o limite é f(a) |
| c/0 (c ≠ 0) | Calcula os limites laterais e diz se existe, diverge para ±∞ ou não existe |
| 0/0 | Tenta, nesta ordem: fatoração → racionalização (conjugado) → limite fundamental trigonométrico/exponencial → L'Hôpital |

**x → ±∞**

| Forma | O que o programa faz |
|---|---|
| ±∞/±∞ | Termo de maior grau no numerador e denominador; se não for polinômio, L'Hôpital |
| ∞ − ∞ | Multiplica pelo conjugado e recalcula |
| 1^∞ | Limite fundamental exponencial: e^(lim (base − 1)·expoente) |
| ∞^0 | Reescreve como e^(expoente·ln base) |

O painel mostra cada etapa com frações empilhadas, o resultado e o método usado.

## Gráfico

- Curva de f(x) ao redor de `a` (ou em x grande, para ±∞), sem ligar ramos em assíntotas
- Linha tracejada laranja em `x = a` e verde em `y = L`
- Ponto `(a, L)` **preenchido** se f é contínua em `a`, **vazado** se f(a) não existe ou é diferente de L
- Barra do Matplotlib para zoom, arrastar e salvar a imagem

## Estrutura

```
main.py              ponto de entrada
gui/app.py           janela (CustomTkinter)
limites/parser.py    leitura da função e do ponto
limites/solver.py    fluxograma: identifica a forma e resolve passo a passo
limites/grafico.py   plotagem com Matplotlib
tests/               testes com um caso de cada ramo
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitações

O passo a passo usa regras do fluxograma. Quando a expressão não se encaixa em nenhuma (ex.: formas 0·∞), o SymPy calcula o limite direto e o painel informa isso.
