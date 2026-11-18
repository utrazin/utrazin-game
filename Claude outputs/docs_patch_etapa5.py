"""Atualiza LEVELS.md (seção v3) e ASSUMPTIONS.md (A-046/A-047). Uso: python3 docs_patch.py <raiz do repo>"""
import os
import re
import sys

ROOT = sys.argv[1]
LEV = os.path.join(ROOT, "docs", "gameplay", "LEVELS.md")
ASM = os.path.join(ROOT, "docs", "decisions", "ASSUMPTIONS.md")

V3 = """## L01 v3 "Vale aberto" (2026-11-15, Etapa 5)

Roteiro e tabela de zonas: [L01_STORYBOARD.md](L01_STORYBOARD.md). Substitui a v2 (corredor fechado).

| Item | Valor gerado |
|---|---|
| Mapa | o mesmo `/Game/Levels/L01_ZombieValley/L01_ZombieValley`; terreno 2 x 2 km em 64 pedaços (grade 4 m) + estrada em 15 trechos (a ponte faz parte da estrada) |
| Zonas | 8, alternando a pé / carro: 0 Acampamento, 1 Estrada do vale, 2 Posto, 3 Floresta, 4 Ponte/colmeia, 5 Fuga da horda, 6 Vila, 7 Saída |
| Estrada principal | ~3,5 km, 12 m de largura, raio mínimo 65 m, rampa máxima 4,6% |
| Rotas alternativas (terra) | Z1 Dunas (com salto) e Z1 Pedras, Z3 Trilha da árvore-mãe (desvio da barricada), Z5 Ribeirinha (com salto), Z7 Serra |
| Limites | morros suaves a partir de ~50 m das rotas, mesas/penhascos longe, serra com penhasco na borda, rio tóxico na ravina (só a ponte cruza), lago tóxico; **4 paredes invisíveis só na borda** (985 m) |
| Portões | árvore caída na ponte (AJRBlockingGate, explosivos), barreiras na entrada da vila; checkpoints de transição no posto, na ponte e na vila |
| Carro | buggy estacionado no acampamento; o jogador começa **a pé** e precisa da chave (baú); E perto do carro para entrar |
| Checkpoints | Start (a pé), Z1_Road, Z2_Posto, Z3_Forest, Z4_Bridge, Z5_Escape, Z6_Village (armas + CarKey; nas zonas a pé o carro renasce estacionado) |
| Diretor de IA | 1 AJRAIDirector + 8 AJRDirectorZone (acampamento e saída seguros; posto, ponte, vila mais densos) |
| Vegetação | **não** espalhada aqui: `veg_hints`/`veg_rules` no layout + `l01_veg_density_v3.png` (R floresta, G esparso, B deserto) para o agente Densidade |

Gerar de novo (Blender 5.2 e Python com Pillow):
```
blender -b --python tools/blender/gen_l01_v3.py -- assets/work/levels/L01
python tools/blender/plot_l01_v3.py assets/work/levels/L01
```
Montar no Editor (depois de compilar o C++): `py tools/unreal/build_l01.py` (usa a v3 se `l01_layout_v3.json`
existir; `build_l01.py v2` força a antiga) e `py tools/unreal/setup_minimap.py` (minimapa v3).
Modelos Quaternius entram por `tools/unreal/quaternius_lib.py` em `/Game/Environment/Quaternius/<Pack>/`.

"""

ROWS = [
    "| A-046 | Mapa L01 v3 | **Vale aberto 2 x 2 km com 8 zonas alternando a pé / carro** (12 a 15 min, nenhum trecho > ~2,5 min), "
    "2 a 3 caminhos nos trechos de carro, limites naturais (morros, penhascos, rio em ravina, lago, mata) e paredes "
    "invisíveis só na borda; saltos só em rotas alternativas, sem buraco fatal na estrada | Usuário rejeitou a v2 "
    "(corredor com paredões, curvas feias, metade/metade); plano aprovado na conversa | Alta | Substitui A-035 "
    "(corredor) e o roteiro da v2; valores em tools/blender/gen_l01_v3.py | pendente (testar) | conversa |",
    "| A-047 | Carro a pé e itens-chave | Jogador começa a pé; o buggy fica no mapa e só liga com o item `CarKey`; "
    "E perto do carro entra (herói some e vai junto); `Fuel` (posto) e `Explosive` (colmeia) são itens-chave no "
    "AJRPlayerController; checkpoints devolvem armas + itens e estacionam o carro do mapa no portão da zona a pé; "
    "Driving/OnFoot alternam nos checkpoints; o resgate não encerra a fase (o portão norte encerra) | Necessário "
    "para alternar carro e a pé sem duplicar carros | Média | Sem sistema de combustível de verdade (só o item "
    "Fuel); a sobrevivente não entra no carro (visual pendente) | pendente (testar) | conversa |",
]


def main():
    s = open(LEV, encoding="utf-8").read()
    if "## L01 v3" not in s:
        i = s.find("## L01 v2")
        s = s[:i] + V3 + s[i:] if i >= 0 else s + "\n" + V3
        open(LEV, "w", encoding="utf-8", newline="").write(s)
        print("LEVELS.md: seção v3 adicionada")
    a = open(ASM, encoding="utf-8").read()
    nums = [int(n) for n in re.findall(r"^\| A-(\d+) \|", a, flags=re.M)]
    nxt = max(nums) + 1
    if "Mapa L01 v3" in a:
        print("ASSUMPTIONS.md: já tem as linhas v3")
        return
    rows = []
    for k, r in enumerate(ROWS):
        rows.append(re.sub(r"^\| A-\d+ \|", f"| A-{nxt + k:03d} |", r))
    lines = a.rstrip("\n").split("\n")
    last = max(i for i, ln in enumerate(lines) if re.match(r"^\| A-\d+ \|", ln))
    lines[last + 1:last + 1] = rows
    open(ASM, "w", encoding="utf-8", newline="").write("\n".join(lines) + "\n")
    print("ASSUMPTIONS.md: linhas", [f"A-{nxt + k:03d}" for k in range(len(rows))])


main()
