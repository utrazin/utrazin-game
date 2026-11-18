import placement_registry as pr


def test_overlap_rejected_and_adjacent_allowed():
    reg = pr.Registry()
    assert reg.add(0, 0, 100, "tree", "borda da trilha")
    assert not reg.add(150, 0, 100)          # sobrepõe
    assert reg.add(200, 0, 100)              # encosta sem sobrepor
    assert reg.find_overlaps() == []


def test_margin_and_ignore_tags():
    reg = pr.Registry()
    reg.add(0, 0, 100, "road", "estrada")
    assert not reg.can_place(250, 0, 100, margin=100)
    assert reg.can_place(250, 0, 100, margin=100, ignore_tags=["road"])


def test_force_creates_detectable_overlap_and_remove_tag():
    reg = pr.Registry()
    reg.add(0, 0, 100, "old")
    reg.add(50, 0, 100, "new", force=True)
    assert len(reg.find_overlaps()) == 1
    assert reg.remove_tag("old") == 1
    assert reg.find_overlaps() == []


def test_poisson_respects_registry_and_keepout_and_is_deterministic():
    def run():
        reg = pr.Registry()
        reg.add(500, 500, 300, "building", "posto")
        pts = pr.poisson_sample(reg, (0, 0, 2000, 2000), 80, 150, keep_out=[(1500, 1500, 400)], seed=7)
        return reg, pts
    reg, pts = run()
    assert len(pts) > 20
    assert reg.find_overlaps() == []
    assert all(((x - 500) ** 2 + (y - 500) ** 2) ** 0.5 >= 380 for x, y in pts)
    assert all(((x - 1500) ** 2 + (y - 1500) ** 2) ** 0.5 >= 480 for x, y in pts)
    assert run()[1] == pts


def test_missing_reason_and_roundtrip(tmp_path):
    reg = pr.Registry()
    reg.add(0, 0, 50, "prop", "")
    reg.add(500, 0, 50, "veg", "")
    assert len(reg.missing_reason()) == 1
    f = tmp_path / "r.json"
    reg.save(f)
    back = pr.Registry.load(f)
    assert len(back.items) == 2 and back.items[0].tag == "prop"
    assert pr.main(["check", str(f)]) == 1


def test_ok_pairs_on_place_and_audit_and_roundtrip(tmp_path):
    reg = pr.Registry()
    reg.allow("copa", "rocha")
    assert reg.add(0, 0, 400, "copa", "árvore")
    assert reg.add(100, 0, 80, "rocha", "pedra")            # debaixo da copa: permitido
    assert not reg.add(150, 0, 80, "cristal", "cristal")    # cristal na copa: não
    assert reg.conflict(150, 0, 80, tag="cristal").tag == "copa"
    assert reg.find_overlaps() == []
    f = tmp_path / "r.json"
    reg.save(f, compact=True, meta={"x": 1})
    back = pr.Registry.load(f)
    assert back.allowed("rocha", "copa") and back.find_overlaps() == []


def test_remove_ids():
    reg = pr.Registry()
    reg.add(0, 0, 100, "estrutura", "blockout", "Posto[3]")
    assert not reg.add(50, 0, 100, "cenario")
    assert reg.remove_ids(["Posto[3]", ""]) == 1
    assert reg.add(50, 0, 100, "cenario")
