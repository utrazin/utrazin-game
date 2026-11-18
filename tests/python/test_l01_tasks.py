"""Tarefas da L01 (A-064): tabela de tools/unreal/l01_tasks.py contra o layout v3 (sem a Unreal)."""
import json
from pathlib import Path

import pytest

import l01_tasks as T

REPO = Path(__file__).resolve().parents[2]
LAYOUT = REPO / "assets" / "work" / "levels" / "L01" / "l01_layout_v3.json"

pytestmark = pytest.mark.skipif(not LAYOUT.exists(), reason="layout v3 ausente")


@pytest.fixture(scope="module")
def layout():
    return json.loads(LAYOUT.read_text(encoding="utf-8"))


def test_todo_gatilho_tem_tarefa_e_todo_alvo_existe(layout):
    assert T.validate(layout) == []


def test_primeiras_tarefas_apontam_para_o_que_o_jogador_faz_primeiro():
    assert T.TASKS["Historia_Z0_Queda"][1] == "Pickup_Graveto"
    assert T.TASKS["Historia_Z0_Chave"][1] == "Bau_ChaveBuggy"
    assert T.TASKS["Historia_Z0_Buggy"][1] == "Buggy_Fase"


def test_pontos_tem_raio_de_chegada():
    for label, t in T.TASKS.items():
        if t and t[0] == "poi":
            assert t[2] >= 1000, label
