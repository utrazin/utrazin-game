import setup_ai_director as sad


def test_package_from_world_path():
    assert sad.package_from_world_path("/Game/Levels/Test/L_VehicleTest.L_VehicleTest") == "/Game/Levels/Test/L_VehicleTest"
    assert sad.package_from_world_path("/Temp/Untitled_1.Untitled_1") is None
    assert sad.package_from_world_path("") is None


def test_maps_to_process_sem_repetir():
    exists = {"/Game/A", "/Game/Levels/Test/L_VehicleTest"}.__contains__
    out = sad.maps_to_process("/Game/A", ["/Game/Levels/Test/L_VehicleTest", "/Game/A", "/Game/Nao"], exists)
    assert out == ["/Game/A", "/Game/Levels/Test/L_VehicleTest"]
    assert sad.maps_to_process(None, ["/Game/A"], exists) == ["/Game/A"]


def test_elite_so_no_pico():
    available = {k: True for k in sad.ENEMIES}
    build_up = sad.resolve_table(sad.BUILD_UP_TABLE, available)
    peak = sad.resolve_table(sad.PEAK_TABLE, available)
    elite = sad.ENEMIES["elite"]
    assert all(path != elite for path, _, _ in build_up)
    assert [(w, mx) for path, w, mx in peak if path == elite] == [(0.3, 1)]


def test_tabela_sem_asset():
    available = {"melee": True}
    assert sad.resolve_table(sad.PEAK_TABLE, available) == [(sad.ENEMIES["melee"], 10.0, 0)]
