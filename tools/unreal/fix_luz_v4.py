"""[A-088] Luz da cidade e da arena (itens 1, 9 e 13 do handoff de 23/11).

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/fix_luz_v4.py"
  (ou só um mapa: ... fix_luz_v4.py cidade   /   ... fix_luz_v4.py arena)

Causa encontrada:
  - As lâmpadas da cidade (postes e a luz da praça) foram criadas pelo Python com intensity 5000/9000 sem dizer a
    unidade. Ator criado pelo editor usa a unidade padrão do projeto (candelas): 5000 cd é umas 100 vezes uma
    lâmpada de rua, com o sol do céu alienígena em 5 lux e exposição fixa. Resultado: chão, NPCs e herói brancos.
  - As lâmpadas da arena são criadas no C++ (AJRArenaGenerator::AddLight) sem unidade = "Unitless": 4500 unitless
    dá menos de 15 cd. Com o sol do entardecer a 7 graus de altura, quase nada chega no chão: arena preta.
  - O relatório do céu nunca era gravado quando dress_remap_v3 chamava o setup_alien_sky (erros sumiam).

O que este script faz em cada mapa:
  1. céu alienígena com ajuste por mapa (altura do sol, luz do céu, exposição) por cima do preset "dusk";
  2. toda PointLight/SpotLight do mapa passa a usar CANDELAS com valor medido para a exposição fixa;
  3. luzes direcionais e SkyLights repetidas são desligadas (fica 1 de cada);
  4. relatório completo em reports/fix_luz_v4.json (antes e depois de cada luz).
Ajuste fino: mude MAP_TUNING / LAMP_CD abaixo e rode de novo. Mais claro: exposure_bias +0.5; mais escuro: -0.5.
"""
import importlib.util
import json
import os
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EAL = unreal.EditorAssetLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

CITY_MAP = "/Game/Levels/Remap/L_Cidade"
ARENA_MAP = "/Game/Levels/Remap/L_Arena_F1"
PRESET = "dusk"

# Por cima do preset "dusk" do setup_alien_sky (mesmos nomes de campo).
# Sol a 7 graus (o "dusk" do L01) deixa a luz rasante: chão escuro e sombras compridas. Na cidade e na arena o sol
# sobe para o fim de tarde, continua laranja.
MAP_TUNING = {
    CITY_MAP: {"sun_el": 24.0, "sun_lux": 4.0, "skylight": 0.9, "exposure_bias": 0.0},
    ARENA_MAP: {"sun_el": 30.0, "sun_lux": 5.5, "skylight": 1.5, "exposure_bias": 0.6},
}
# Lâmpadas em candelas (cd). Referência: o sol do "dusk" dá ~2 lux no chão; um poste a 4,7 m com 40 cd dá ~1,8 lux
# embaixo dele (uma poça de luz visível, sem estourar).
LAMP_CD = {"poste": 40.0, "praca": 60.0, "default": 35.0}
MAX_CD = 120.0  # nenhuma lâmpada pontual acima disso
SKIP_LABEL_PREFIXES = ("Ceu", "Sky")

R = {"maps": {}, "warnings": [], "errors": []}


def log(m):
    unreal.log(f"[luz_v4] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[luz_v4] {m}")


def load_sky_module():
    spec = importlib.util.spec_from_file_location("setup_alien_sky", os.path.join(HERE, "setup_alien_sky.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Recriar material existente derruba a Unreal (assert !IsRooted): material que já existe só é carregado.
    base_mb = mod.MB

    class _Keep:
        def __init__(self, m):
            self.m = m

        def finish(self):
            return self.m

        def __getattr__(self, _name):
            return lambda *a, **k: self

    def safe_mb(path, *args, **kwargs):
        if EAL.does_asset_exist(path):
            return _Keep(EAL.load_asset(path))
        return base_mb(path, *args, **kwargs)

    mod.MB = safe_mb
    return mod


def light_comp(a):
    for cls in (unreal.PointLightComponent, unreal.SpotLightComponent, unreal.RectLightComponent):
        c = a.get_component_by_class(cls)
        if c is not None:
            return c
    return None


def lamp_kind(a, c):
    label = a.get_actor_label().lower()
    if "praca" in label or "monumento" in label:
        return "praca"
    try:
        z = a.get_actor_location().z
        loc = a.get_actor_location()
        if abs(loc.x) < 50 and abs(loc.y) < 50 and z > 800:
            return "praca"
    except Exception:  # noqa: BLE001
        pass
    return "poste"


def fix_local_lights(info):
    out = []
    for a in ACTORS.get_all_level_actors():
        if not isinstance(a, (unreal.PointLight, unreal.SpotLight, unreal.RectLight)):
            continue
        if a.get_actor_label().startswith(SKIP_LABEL_PREFIXES):
            continue
        c = light_comp(a)
        if c is None:
            continue
        before = {"units": str(c.get_editor_property("intensity_units")), "intensity": c.get_editor_property("intensity")}
        kind = lamp_kind(a, c)
        cd = min(LAMP_CD.get(kind, LAMP_CD["default"]), MAX_CD)
        c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        c.set_editor_property("intensity", cd)
        # lâmpada de rua sem sombra própria custa caro e quase não aparece; mantém desligado
        c.set_editor_property("cast_shadows", False)
        out.append({"label": a.get_actor_label(), "kind": kind, "before": before, "after_cd": cd})
    info["local_lights"] = len(out)
    info["local_lights_detail"] = out[:30]
    log(f"{len(out)} lâmpadas em candelas")


def dedupe(info):
    suns = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)]
    skys = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.SkyLight)]
    info["directional_lights"] = [a.get_actor_label() for a in suns]
    info["sky_lights"] = [a.get_actor_label() for a in skys]
    main_sun = None
    for a in suns:
        c = a.get_component_by_class(unreal.DirectionalLightComponent)
        if c and c.get_editor_property("atmosphere_sun_light") and main_sun is None:
            main_sun = a
    main_sun = main_sun or (suns[0] if suns else None)
    for a in suns:
        if a != main_sun:
            c = a.get_component_by_class(unreal.DirectionalLightComponent)
            c.set_editor_property("intensity", 0.0)
            c.set_visibility(False)
            warn(f"luz direcional repetida desligada: {a.get_actor_label()}")
    for a in skys[1:]:
        c = a.get_component_by_class(unreal.SkyLightComponent)
        c.set_editor_property("intensity", 0.0)
        c.set_visibility(False)
        warn(f"SkyLight repetida desligada: {a.get_actor_label()}")


def process(mod, path):
    if not EAL.does_asset_exist(path):
        warn(f"mapa não existe: {path}")
        return
    if not LES.load_level(path):
        raise RuntimeError(f"não abriu {path}")
    base = dict(mod.PRESETS[PRESET])
    mod.PRESETS[PRESET].update(MAP_TUNING.get(path, {}))
    try:
        info = {"tuning": MAP_TUNING.get(path, {})}
        dedupe(info)
        sky_info = mod.apply_to_current_level(PRESET, save=False)
        info["sky"] = sky_info
        fix_local_lights(info)
        if not LES.save_current_level():
            warn(f"não salvou {path}")
        R["maps"][path] = info
    finally:
        mod.PRESETS[PRESET].clear()
        mod.PRESETS[PRESET].update(base)


def main():
    args = [a.lower() for a in sys.argv[1:]]
    maps = []
    if not args or "cidade" in args:
        maps.append(CITY_MAP)
    if not args or "arena" in args:
        maps.append(ARENA_MAP)
    mod = load_sky_module()
    for m in maps:
        try:
            process(mod, m)
        except Exception as exc:  # noqa: BLE001
            R["errors"].append(f"{m}: {exc}")
            unreal.log_error(f"[luz_v4] {m}: {exc}\n{traceback.format_exc()[-1500:]}")
    R["sky_module_warnings"] = list(mod.R.get("warnings", []))
    R["sky_module_errors"] = list(mod.R.get("errors", []))
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "fix_luz_v4.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    log(f"fim | mapas {len(R['maps'])} | avisos {len(R['warnings'])} | erros {len(R['errors']) + len(R['sky_module_errors'])}")


main()
