import math

import setup_zombie_feel as szf


def _walk(speed=150.0, period=1.2, stance=0.6, frames=120, hips_speed=0.0):
    """Ciclo sintético: cada pé fica 'stance' do período no chão indo para trás em 'speed'."""
    stride = speed * stance * period
    out = []
    for i in range(frames):
        t = period * i / frames
        row = [t, (0.0, hips_speed * t, 95.0)]
        for offset in (0.0, 0.5):
            ph = (t / period + offset) % 1.0
            if ph < stance:  # apoio: anda para trás no chão
                y = stride / 2 - stride * ph / stance
                z = 10.0
            else:  # balanço: volta para frente no ar
                q = (ph - stance) / (1.0 - stance)
                y = -stride / 2 + stride * q
                z = 10.0 + 18.0 * math.sin(math.pi * q)
            row.append((12.0 if offset else -12.0, y + hips_speed * t, z))
        out.append(tuple(row))
    return out


def test_mede_animacao_no_lugar():
    speed, detail = szf.estimate_ground_speed(_walk(150.0))
    assert abs(speed - 150.0) < 8.0
    assert detail["modo"] == "pé de apoio"


def test_mede_animacao_com_deslocamento():
    speed, detail = szf.estimate_ground_speed(_walk(150.0, hips_speed=320.0))
    assert abs(speed - 320.0) < 5.0
    assert detail["modo"] == "quadril anda"


def test_poucos_quadros():
    assert szf.estimate_ground_speed(_walk(frames=5))[0] is None


def test_vagar_so_baixa():
    assert szf.wander_targets(60.0, 90.0, 140.0) == (51.0, 81.0)
    assert szf.wander_targets(150.0, 90.0, 140.0) is None  # andar medido rápido: não sobe o vagar
    assert szf.wander_targets(None, 90.0, 140.0) is None
    assert szf.wander_targets(20.0, 90.0, 140.0) == (45.0, 45.0)


def test_personagem_da_malha():
    assert szf.char_of_mesh_path("/Game/Characters/Zombies/ZMB_Tanque/SK_ZMB_Tanque.SK_ZMB_Tanque") == "ZMB_Tanque"
    assert szf.char_of_mesh_path("/Game/Enemies/Copzombie/SK_Copzombie") is None
