"""Céu alienígena: funções puras de tools/unreal/setup_alien_sky.py e tools/blender/make_sky.py."""
import math

import pytest

import setup_alien_sky as sky


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def test_preset_por_argumento():
    assert sky.parse_preset([]) == "dusk"
    assert sky.parse_preset(["noite"]) == "night"
    assert sky.parse_preset(["--x", "DAY"]) == "day"
    assert sky.parse_preset(["qualquer"]) == sky.DEFAULT_PRESET


def test_eixos_do_rotator_ortonormais():
    x, y, z = sky.rotator_axes(9.0, 37.0, 16.0)
    for a in (x, y, z):
        assert abs(_norm(a) - 1) < 1e-9
    assert abs(sum(a * b for a, b in zip(x, y))) < 1e-9
    assert abs(sum(a * b for a, b in zip(x, z))) < 1e-9
    # sem rotação: identidade; yaw 90 leva X para +Y (convenção Unreal)
    assert sky.rotator_axes(0, 0, 0) == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    x90 = sky.rotator_axes(0, 90, 0)[0]
    assert abs(x90[1] - 1) < 1e-9


def test_sol_aponta_para_o_chao_e_vem_do_azimute():
    for name, p in sky.PRESETS.items():
        pitch, yaw, _ = sky.sun_rotator(p["sun_az"], p["sun_el"])
        fwd = sky.rotator_axes(pitch, yaw, 0)[0]
        to_sun = sky.sun_direction(p, 0.0)
        assert all(abs(fwd[i] + to_sun[i]) < 1e-9 for i in range(3)), name
        assert to_sun[2] > 0, name  # sol acima do horizonte em todos os presets


def test_astros_grandes_longe_e_acima_do_horizonte():
    for b in sky.BODIES:
        loc, rot, scale = sky.body_transform(b, (0, 0, 0), 0.0)
        dist = _norm(loc)
        assert abs(dist - b["dist_km"] * 100000) < 1
        radius = scale * sky.MESH_RADIUS_CM
        # parte de baixo do astro (com folga do anel) acima do horizonte
        extra = sky.RING_OUTER if b["key"] == "planet" else 1.0
        assert math.degrees(math.asin(loc[2] / dist)) - b["ang_r"] > 0, b["key"]
        assert radius * extra < dist, b["key"]
    planet = sky.body_transform(sky.BODIES[0])[2]
    assert planet > 5000  # gigante no horizonte


def test_cupula_atras_dos_astros():
    far = max(b["dist_km"] + b["dist_km"] * math.sin(math.radians(b["ang_r"])) * sky.RING_OUTER for b in sky.BODIES)
    assert sky.STAR_DOME["radius_km"] > far
    assert sky.AURORA["radius_km"] < min(b["dist_km"] for b in sky.BODIES)


def test_mapas_sem_repetir():
    exists = {"/Game/A", "/Game/Levels/Test/L_VehicleTest"}.__contains__
    out = sky.maps_to_process("/Game/A", ["/Game/Levels/Test/L_VehicleTest", "/Game/A", "/Game/N"], exists)
    assert out == ["/Game/A", "/Game/Levels/Test/L_VehicleTest"]
    assert sky.package_from_world_path("/Temp/Untitled_1.Untitled_1") is None


def test_tipo_de_textura():
    assert sky.texture_kind("T_Sky_Aurora.png") == "mask"
    assert sky.texture_kind("T_Sky_Stars.png") == "sky"
    assert sky.texture_kind("T_Sky_Planet.png") == "color"


def test_make_sky_puro(tmp_path):
    np = pytest.importorskip("numpy")
    import make_sky as ms
    prof = ms.ring_profile(256)
    assert prof[0] == 0 and prof[-1] == 0 and prof.max() <= 1
    img = (np.arange(4 * 6 * 3) % 255).astype("uint8").reshape(4, 6, 3)
    p = tmp_path / "t.png"
    ms.write_png(str(p), img)
    assert (ms.load_png(str(p)) == img).all()
    fade = ms.aurora_end_fade([ms.AURORA_A0, 0.0, ms.AURORA_A1])
    assert fade[0] == 0 and fade[1] == 1 and fade[2] == 0


def test_exposicao_fixa_por_preset():
    for name, p in sky.PRESETS.items():
        e = sky.exposure_settings(name)
        assert e["auto_exposure_method"] == "MANUAL", name
        assert e["auto_exposure_apply_physical_camera_exposure"] is False, name
        # mínimo = máximo: mesmo sem o modo Manual o olho não se adapta
        assert e["auto_exposure_min_brightness"] == e["auto_exposure_max_brightness"], name
        assert -4.0 <= e["auto_exposure_bias"] <= 4.0, name
        for k, v in e.items():
            if k.startswith("override_"):
                assert v is True and k[len("override_"):] in e, (name, k)
    assert sky.SKYLIGHT_REAL_TIME is False
