"""[A-098] Matemática pura do tools/unreal/ground_align.py e da textura da grama (sem Unreal/Blender)."""
import math

import ground_align as ga


def flat(res=9, h=32768):
    return ga.HeightField([h] * (res * res), res, -400, -400)


def ramp_x(res=9, step=128):
    # +1 m de altura (128 unidades com escala Z 100) por quad em X: rampa de 45 graus
    return ga.HeightField([32768 + i * step for _ in range(res) for i in range(res)], res, -400, -400)


def test_flat_height_and_normal():
    hf = flat()
    assert abs(hf.z(0, 0)) < 1e-6
    assert hf.normal(10, -20) == (0.0, 0.0, 1.0)


def test_ramp_height_interpolates_and_normal_tilts():
    hf = ramp_x()
    assert abs(hf.z(50, 0) - (hf.z(0, 0) + 50)) < 1e-6
    n = hf.normal(0, 0)
    assert n[0] < 0 and abs(n[1]) < 1e-9
    assert abs(hf.slope_deg(0, 0) - 45.0) < 0.01


def test_rotator_up_roundtrip():
    for up in ((0, 0, 1), (0.3, 0.1, 0.95), (-0.2, 0.4, 0.89)):
        for yaw in (0, 37, -120):
            roll, pitch, y = ga.rotator_from_up(up, yaw)
            u = ga.up_from_rotator(roll, pitch, y)
            nu = ga._norm(up)
            assert all(abs(a - b) < 1e-6 for a, b in zip(u, nu))
    r, p, y = ga.rotator_from_up((0, 0, 1), 37)
    assert abs(r) < 1e-9 and abs(p) < 1e-9 and abs(y - 37) < 1e-9


def test_partial_up_limits_angle():
    v = ga.partial_up((0.7071, 0, 0.7071), 0.35, 10.0)
    assert math.degrees(math.acos(v[2])) <= 10.0 + 1e-6


def test_building_sits_on_corner_average_minus_15():
    hf = ramp_x()
    p = ga.rule_building(hf, 0, 0, 0, 100, 100)
    assert abs(p.z - (hf.z(0, 0) - 15)) < 1e-6 and p.pitch == 0 and p.roll == 0


def test_plant_tilts_at_most_10_and_sinks():
    p = ga.rule_plant(ramp_x(), 0, 0, 0, 100)
    assert p.tilt_deg <= 10.0 + 1e-6 and p.sink_cm > 3.0


def test_align_follows_normal_and_pivot_offset():
    hf = ramp_x()
    p = ga.place(hf, "car", 0, 0, 0, (-200, -100, -50, 200, 100, 120))
    assert abs(p.tilt_deg - 45.0) < 0.5
    q = ga.place(flat(), "rock", 0, 0, 0, (-50, -50, -20, 50, 50, 40))
    assert abs(q.z - (0 - 4 + 20)) < 1e-6  # pivô 20 cm acima da base: sobe 20


def test_grass_texture_tiles_and_has_alpha():
    import importlib.util
    import pathlib

    np = __import__("pytest").importorskip("numpy")
    path = pathlib.Path(__file__).resolve().parents[2] / "tools" / "blender" / "gen_grass_tufts.py"
    spec = importlib.util.spec_from_file_location("gen_grass_tufts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    img = mod.blade_texture(size=128, n_blades=30)
    assert img.shape == (128, 128, 4)
    a = img[..., 3].astype(float) / 255
    assert 0.2 < a.mean() < 0.9
    assert a[-1].mean() > a[0].mean()  # base cheia, ponta rala
    assert abs(int(img[64, 0, 3]) - int(img[64, -1, 3])) < 200  # ladrilha em X (sem corte seco)
