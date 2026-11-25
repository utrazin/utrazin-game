import pytest

import build_remap_f2 as f2


def test_nav_bounds_cobre_a_arena_maior():
    sx, sy, sz = f2.nav_bounds_scale(f2.NAV_M, f2.NAV_HEIGHT_M)
    assert sx == sy == f2.NAV_M * 100.0 / 200.0
    assert sz == f2.NAV_HEIGHT_M * 100.0 / 200.0
    # arena máxima 160 m (20 células de 8 m), centro livre até 2 células fora do meio
    assert f2.arena_fits_nav(160.0, 8.0, 2, f2.NAV_M)
    assert not f2.arena_fits_nav(160.0, 8.0, 2, 170.0)


def test_nav_bounds_invalido():
    with pytest.raises(ValueError):
        f2.nav_bounds_scale(0, 10)


def test_chao_com_topo_em_zero():
    center, size = f2.floor_box(f2.FLOOR_M)
    assert center[2] + size[2] / 2.0 == 0.0
    assert size[0] >= f2.NAV_M * 100.0


def test_remove_so_o_que_os_scripts_criaram():
    assert f2.is_old_actor(["RemapF1"])
    assert f2.is_old_actor(["Outro", "RemapF2"])
    assert not f2.is_old_actor(["RecastNavMesh"])
