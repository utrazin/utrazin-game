"""Construções com interior da L01 (A-070): regras da skill enterable-interior e posição no mapa (sem a Unreal)."""
import json
import math
from pathlib import Path

import pytest

import l01_interiors as I
import l01_user_dressing as U

REPO = Path(__file__).resolve().parents[2]
LAYOUT = REPO / "assets" / "work" / "levels" / "L01" / "l01_layout_v3.json"

pytestmark = pytest.mark.skipif(not Path(I.INTERIORS).exists() or not Path(I.PLACEMENT).exists() or not LAYOUT.exists(),
                                reason="interiores ainda não gerados")


@pytest.fixture(scope="module")
def data():
    L = json.loads(LAYOUT.read_text(encoding="utf-8"))
    return L, I.load_json(I.INTERIORS), I.load_json(I.PLACEMENT)


def test_portas_pe_direito_e_conteudo(data):
    _, B, _ = data
    for key, b in B["buildings"].items():
        assert b["doors"], key
        assert all(d["width_m"] >= 1.0 for d in b["doors"]), key
        assert b["h_m"] >= 2.6, key
        assert len(b["furniture"]) >= 2, key
        assert b["pickups"] or b["chests"] or b.get("absorb_pickups"), f"{key}: nada para pegar dentro"
        assert b["lights"], key


def test_todas_posicionadas_fora_da_estrada_e_sem_encavalar(data):
    L, B, PL = data
    C = U.Clearance(L)
    pls = PL["placements"]
    assert set(pls) == set(B["buildings"])
    for key, pl in pls.items():
        assert I.rect_clear(C, pl["x"], pl["y"], pl["yaw"], B["buildings"][key]), key
        assert pl["desnivel_m"] <= 1.3, key
    keys = list(pls)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = math.hypot(pls[a]["x"] - pls[b]["x"], pls[a]["y"] - pls[b]["y"])
            assert d > (pls[a]["radius_cm"] + pls[b]["radius_cm"]) * 0.6, (a, b)


def test_sem_aprovacao_o_plano_nao_troca_nada(data, monkeypatch):
    L, B, PL = data
    monkeypatch.delenv("JR_INTERIORS", raising=False)
    if I.enabled():
        pytest.skip("interiores já aprovados neste PC")
    P = U.plan_v3(L)
    assert "CON_PostoLoja" in [p["name"] for p in P["place"]] and P["interiors"] == []


def test_plano_troca_modelos_e_leva_baus_para_dentro(data, monkeypatch):
    L, B, PL = data
    monkeypatch.setenv("JR_INTERIORS", "1")
    P = U.plan_v3(L)
    names = [p["name"] for p in P["place"]]
    assert "CON_PostoLoja" not in names and "CON_Cabana" not in names and "CON_Conteiner" not in names
    assert names.count("CON_CasaVila") == 0
    assert {i["key"] for i in P["interiors"]} == set(B["buildings"])
    assert P["chests"]["Bau_Pistola_Posto"]["interior"] == "Escritorio"
    assert P["chests"]["Bau_Vila_Municao"]["interior"] == "CasaSobrevivente"
    assert P["pickups"]["Pickup_Medkit_Posto"]["interior"] == "PostoLoja"
    assert P["registry"].find_overlaps() == []
