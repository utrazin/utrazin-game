"""Simulacao simples da economia proposta (cidade + arena). So para conferir ordem de grandeza."""
import math

# Armas (tier, preco, dps base). DPS base da pistola atual: 25 dano x 4 tiros/s = 100.
ARMAS = [("Pistola", 0, 100), ("Escopeta", 2000, 190), ("Rifle", 8000, 360),
         ("Rifle de precisao", 28000, 650), ("Lanca-plasma", 90000, 1200)]
UP_BASE, UP_RATE, UP_BONUS = 300, 1.17, 0.10     # bancada: custo = 150 x 1,15^n, +10% dano por nivel
HP_COMUM, HP_RATE = 60, 1.14                       # vida do zumbi comum no nivel L: 60 x 1,14^(L-1)
KILL_BASE, KILL_RATE = 6, 1.11                     # creditos por zumbi comum: 6 x 1,11^(L-1)
def ameaca(L): return 160 * (1 + 0.22 * (L - 1))   # orcamento do diretor por corrida (pontos)
CUSTO_MEDIO = 1.7                                  # pontos por inimigo (mistura comum/corredor/tanque)
VIDA_MEDIA = 1.9                                   # vida media da mistura em "zumbis comuns"

creditos, arma, up, linhas = 0, 0, 0, []
L, corridas = 1, 0
while L <= 25 and corridas < 400:
    dps = ARMAS[arma][2] * (1 + UP_BONUS * up)
    hp = HP_COMUM * HP_RATE ** (L - 1)
    ttk = hp * VIDA_MEDIA / dps
    abates = ameaca(L) / CUSTO_MEDIO
    tempo_combate = abates * ttk / 0.55            # 55% do tempo atirando
    ganho = abates * VIDA_MEDIA * KILL_BASE * KILL_RATE ** (L - 1) + 120 * L
    creditos += ganho; corridas += 1
    # compra: proxima arma se der, senao nivel de bancada
    comprou = []
    while True:
        if arma + 1 < len(ARMAS) and creditos >= ARMAS[arma + 1][1] and up >= 3:
            creditos -= ARMAS[arma + 1][1]; arma += 1; up = 0; comprou.append(ARMAS[arma][0])
        elif creditos >= UP_BASE * UP_RATE ** (up + 4 * arma):
            creditos -= UP_BASE * UP_RATE ** (up + 4 * arma); up += 1; comprou.append(f"bancada {up}")
        else:
            break
    linhas.append((corridas, L, ARMAS[arma][0], up, round(ttk, 2), round(tempo_combate / 60, 1), round(ganho), ", ".join(comprou)))
    if ttk < 0.9 and tempo_combate < 8 * 60:   # passa de nivel quando mata rapido
        L += 1
print("corrida | nivel | arma | bancada | seg p/ matar | min de combate | ganho | comprou")
for l in linhas:
    print(" | ".join(map(str, l)))
