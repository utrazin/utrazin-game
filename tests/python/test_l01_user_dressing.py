"""Modelos do usuário na L01 v3: plano puro de tools/unreal/l01_user_dressing.py (sem a Unreal)."""
import json
import math
from pathlib import Path

import pytest

import l01_user_dressing as U

REPO = Path(__file__).resolve().parents[2]
LAYOUT = REPO / "assets" / "work" / "levels" / "L01" / "l01_layout_v3.json"

pytestmark = pytest.mark.skipif(not LAYOUT.exists() or not Path(U.PROCESSED).exists(),
                                reason="layout v3 ou tripo_processed.json ausente")


@pytest.fixture(scope="module")
def plan():
    L = json.loads(LAYOUT.read_text(encoding="utf-8"))
    return L, U.plan_v3(L)


def test_catalogo_tem_56_modelos_com_nomes_unicos():
    cat = U.catalog()
    assert len(cat) == 56
    assert all(n.split("_")[0] in {"ZMB", "NPC", "ARM", "ITM", "PRP", "CON", "MRC", "NAT"} for n in cat)


def test_bau_da_chave_dentro_da_barraca_com_folga(plan):
    L, P = plan
    ch = P["chests"]["Bau_ChaveBuggy"]
    tents = [p for p in P["place"] if p["name"] == "CON_Barraca"]
    t = min(tents, key=lambda p: math.hypot(p["x"] - ch["x"], p["y"] - ch["y"]))
    d = U.dims_m("CON_Barraca")
    c, s = math.cos(math.radians(-t["yaw"])), math.sin(math.radians(-t["yaw"]))
    lx = (ch["x"] - t["x"]) * c - (ch["y"] - t["y"]) * s
    ly = (ch["x"] - t["x"]) * s + (ch["y"] - t["y"]) * c
    # baú (1 x 0,72 m) inteiro dentro da barraca, longe da lona de trás e dos lados
    assert lx - 36 > -50 * d[0] + 40
    assert abs(ly) + 50 < 50 * d[1] - 100
    # frente do baú (+Y local do AJRLootChest) virada para a abertura (+X da barraca)
    assert abs(((ch["yaw"] + 90) - t["yaw"] + 180) % 360 - 180) < 1


def test_barraca_bem_maior_que_o_bau():
    assert max(U.dims_m("CON_Barraca")) > 5 * max(U.dims_m("PRP_Bau"))


def test_grupos_de_cenario_longe_das_rotas(plan):
    L, P = plan
    C = U.Clearance(L)
    grupos = [p for p in P["place"] if "Grupos" in p["folder"]]
    assert len(grupos) > 60
    for p in grupos:
        assert C.road_dist(p["x"], p["y"]) > U.radius_cm(p["name"]) + 300, p


def test_portao_da_vila_deixa_vao_a_pe(plan):
    L, P = plan
    pecas = sorted(P["gates"]["Portao_Vila"], key=lambda t: t[1])
    portao, barricada = pecas[0], pecas[1]
    gap = (barricada[1] - 50 * U.dims_m(barricada[0])[1]) - (portao[1] + 50 * U.dims_m(portao[0])[1])
    assert 140 < gap < 220      # a pé passa (cápsula ~85 cm), carro (> 2 m) não


def test_registro_do_plano_sem_sobreposicao(plan):
    L, P = plan
    reg = P["registry"]
    assert reg.find_overlaps() == []
    # peça de blockout trocada por modelo do usuário sai do registro
    ids = {f.id for f in reg.items}
    assert not any(f"{k}[{i}]" in ids for k, i in P["skip"])
    # enfeite recusado por cair em cima de baú/item/peça fica anotado
    assert isinstance(P["placement_rejected"], list)


def test_regras_permitem_bau_na_barraca_e_proibem_enfeite_em_cima():
    reg = U.new_registry()
    reg.add(0, 0, 300, "estrutura", "barraca", force=True)
    assert reg.can_place(50, 0, 120, tag="gameplay")
    assert not reg.can_place(50, 0, 120, tag="cenario")
    assert reg.can_place(50, 0, 120, tag="piso")
