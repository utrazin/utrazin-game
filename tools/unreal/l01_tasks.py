"""Tarefas da Fase 1 (A-064): para onde cada gatilho de história aponta no HUD (item 13 do handoff).

Cada AJRStoryTrigger da L01 ganha um TaskTarget: o painel OBJETIVO mostra a dica do gatilho como tarefa
atual e o marcador, o minimapa e a distância apontam para esse alvo (não mais para um checkpoint distante).
A tarefa termina sozinha no C++ (AJRHUD::IsTaskDone): item pego, baú aberto, portão aberto, sobrevivente solta,
carro com o jogador, ou jogador a menos de TaskReachRadius de um ponto.

A parte de TABELA (TASKS, validate) é Python puro (testável sem a Unreal). apply() roda no editor e é usada
por build_l01.py (mapa novo) e fix_l01_frente1.py (mapa já montado).
"""

# gatilho -> (tipo, nome, raio_cm)
#   "actor": rótulo de um ator já colocado pelo build (item, baú, carro, barricada, resgate)
#   "poi":   cria um TargetPoint no centro do POI (pasta L01/Gameplay/Tarefas); termina ao chegar a raio_cm
#   None:    sem alvo (marcador volta ao objetivo geral)
TASKS = {
    "Historia_Z0_Queda": ("actor", "Pickup_Graveto", 0),
    "Historia_Z0_Chave": ("actor", "Bau_ChaveBuggy", 0),
    "Historia_Z0_Buggy": ("actor", "Buggy_Fase", 0),
    "Historia_Z1_Combustivel": ("actor", "Bomba_Galao", 0),
    "Historia_Z2_Posto": ("actor", "Bomba_Galao", 0),
    "Historia_Z2_Sala": ("actor", "Bau_Pistola_Posto", 0),
    "Historia_Z3_Floresta": ("poi", "Ponte", 2500),
    "Historia_Z3_Barricada": ("actor", "Barricada_Corpos_Z3", 1500),
    "Historia_Z4_Arvore": ("actor", "Bau_Colmeia", 0),
    "Historia_Z4_Lago": ("actor", "Bau_Colmeia", 0),
    "Historia_Z5_Fuga": ("poi", "Vila", 4000),
    "Historia_Z6_Vila": ("actor", "Rescue_Victim01", 0),
    "Historia_Z6_Saida": ("actor", "Rescue_Victim01", 0),
    "Historia_Z7_Fim": None,
}
TASK_FOLDER = "L01/Gameplay/Tarefas"
DEFAULT_REACH_CM = 1500.0
# alvos que o build cria fora das listas do layout (rótulos fixos em build_l01.py)
BUILD_LABELS = {"Buggy_Fase", "Rescue_Victim01"}


def validate(L):
    """Confere a tabela contra o layout v3. Retorna lista de problemas (vazia = ok)."""
    probs = []
    story = {s["label"]: s for s in L["story"]}
    known = {c["label"] for c in L["chests"]} | {p["label"] for p in L["pickups"]}
    known |= {b["label"] for b in L.get("barricades", [])} | {g["label"] for g in L.get("gates", [])} | BUILD_LABELS
    pois = {p["key"] for p in L["pois"]}
    for label in story:
        if label not in TASKS:
            probs.append(f"gatilho sem tarefa na tabela: {label}")
    for label, t in TASKS.items():
        if label not in story:
            probs.append(f"tarefa de gatilho que não existe: {label}")
            continue
        if t is None:
            continue
        kind, name, _ = t
        if kind == "actor" and name not in known:
            probs.append(f"{label}: alvo {name} não existe no layout")
        if kind == "poi" and name not in pois:
            probs.append(f"{label}: POI {name} não existe no layout")
        if not story[label]["objective_hint"]:
            probs.append(f"{label}: tem alvo mas não tem texto (objective_hint)")
    return probs


def apply(L, log=print, warn=print):
    """No editor: liga TaskTarget/TaskReachRadius nos gatilhos do mapa aberto. Pode rodar de novo.
    Retorna {"ligados": n, "faltando": [...]}."""
    import unreal
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {}
    old_points = []
    for a in actors.get_all_level_actors():
        if str(a.get_folder_path()) == TASK_FOLDER:
            old_points.append(a)
        else:
            by_label.setdefault(a.get_actor_label(), a)
    for a in old_points:          # refaz os pontos (o POI pode ter mudado de lugar)
        actors.destroy_actor(a)
    pois = {p["key"]: p for p in L["pois"]}
    out = {"ligados": 0, "faltando": []}
    for s in L["story"]:
        trig = by_label.get(s["label"])
        t = TASKS.get(s["label"])
        if trig is None or not isinstance(trig, unreal.JRStoryTrigger):
            out["faltando"].append(f"gatilho {s['label']}")
            continue
        target, reach = None, DEFAULT_REACH_CM
        if t is not None:
            kind, name, r = t
            if kind == "actor":
                target = by_label.get(name)
            else:
                loc = pois[name]["loc"]
                target = actors.spawn_actor_from_class(unreal.TargetPoint,
                                                       unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])))
                if target is not None:
                    target.set_actor_label(f"Tarefa_{name}")
                    target.set_folder_path(TASK_FOLDER)
                    target.set_editor_property("tags", [unreal.Name("L01Gen")])
            if r:
                reach = float(r)
            if target is None:
                out["faltando"].append(f"alvo {name} de {s['label']}")
        try:
            trig.set_editor_property("task_target", target)
            trig.set_editor_property("task_reach_radius", reach)
            out["ligados"] += 1 if target is not None else 0
        except Exception as exc:  # noqa: BLE001
            warn(f"{s['label']}: TaskTarget (compile o C++ novo): {exc}")
            out["faltando"].append(f"propriedade em {s['label']}")
    log(f"tarefas: {out['ligados']} gatilhos com alvo; faltando: {out['faltando']}")
    return out
