"""Simulação em Python da planta da arena (JRArenaLayout.cpp com as regras A-089). Só para conferir a lógica
em centenas de sementes antes de compilar; o RNG não é o mesmo da Unreal."""
import math
import random
import sys

OUT, FREE, LOW, HIGH = 0, 1, 2, 3
T_NONE, T_COVER, T_PILLAR, T_ASM = 0, 1, 2, 3
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
MAX_SIGHT = 8
MIN_SPAWN, MIN_EXTR, MIN_OBJ = 6, 2, 3
CENTER_R = 2
HIGH_MAX_DIST = 2
MIN_FREE = 0.6
ROWS = {"Posto": ["SS", "YY", "YY"], "Patio": ["SSS", "SCY"], "FerroVelho": ["SYS", "YCL"], "Acampamento": ["LL", "CY"]}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def size_for_level(lv):
    return max(10, min(20, 10 + max(1, lv) - 1))


class L:
    def __init__(self):
        pass

    def valid(self, x, y):
        return 0 <= x < self.G and 0 <= y < self.G

    def get(self, x, y):
        return self.cells[x][y] if self.valid(x, y) else OUT

    def inside(self, x, y):
        return self.get(x, y) != OUT

    def setc(self, x, y, v):
        if self.valid(x, y):
            self.cells[x][y] = v

    def res(self, x, y):
        return self.valid(x, y) and self.reserved[x][y]

    def setr(self, x, y, v=True):
        if self.valid(x, y):
            self.reserved[x][y] = v

    def center_zone(self, p):
        return cheb(p, self.start) <= CENTER_R

    def asm_at(self, x, y):
        return self.asmat[x][y] if self.valid(x, y) else -1

    def distout(self, x, y):
        return self.dout[x][y] if self.valid(x, y) else 0

    def flood(self):
        seen = [[0] * self.G for _ in range(self.G)]
        if self.get(*self.start) != FREE:
            return seen
        st = [self.start]
        seen[self.start[0]][self.start[1]] = 1
        while st:
            p = st.pop()
            for d in DIRS4:
                q = (p[0] + d[0], p[1] + d[1])
                if self.get(*q) == FREE and not seen[q[0]][q[1]]:
                    seen[q[0]][q[1]] = 1
                    st.append(q)
        return seen

    def unreachable(self):
        s = self.flood()
        return sum(1 for x in range(self.G) for y in range(self.G) if self.cells[x][y] == FREE and not s[x][y])

    def find_long_run(self):
        for axis in range(2):
            for a in range(self.G):
                run = []
                for b in range(self.G + 1):
                    x, y = (b, a) if axis == 0 else (a, b)
                    c = self.get(x, y) if b < self.G else OUT
                    if c not in (OUT, HIGH):
                        run.append((x, y))
                    else:
                        if len(run) > MAX_SIGHT:
                            return run
                        run = []
        return None

    def longest(self):
        best = 0
        for axis in range(2):
            for a in range(self.G):
                ln = 0
                for b in range(self.G):
                    c = self.get(b, a) if axis == 0 else self.get(a, b)
                    ln = ln + 1 if c not in (OUT, HIGH) else 0
                    best = max(best, ln)
        return best

    def center_exits(self):
        e = 0
        for d in DIRS4:
            ok = False
            for k in (-1, 0, 1):
                x = self.start[0] + d[0] * 2 + (k if d[0] == 0 else 0)
                y = self.start[1] + d[1] * 2 + (k if d[1] == 0 else 0)
                ok |= self.get(x, y) == FREE
            e += ok
        return e

    def free_n4(self, p):
        return sum(1 for d in DIRS4 if self.get(p[0] + d[0], p[1] + d[1]) == FREE)

    def free_ratio(self):
        ins = fr = 0
        for x in range(self.G):
            for y in range(self.G):
                if self.cells[x][y] != OUT:
                    ins += 1
                    fr += self.cells[x][y] == FREE
        return fr / ins if ins else 0

    def fix_sight(self, rng):
        for _ in range(200):
            run = self.find_long_run()
            if not run:
                return True
            scored = []
            for i in range(1, len(run) - 1):
                p = run[i]
                c = self.get(*p)
                if c not in (FREE, LOW) or self.res(*p):
                    continue
                hn = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and self.get(p[0] + dx, p[1] + dy) == HIGH)
                scored.append((max(i, len(run) - 1 - i) + 3 * hn + rng.random() * 2 + (6 if self.center_zone(p) else 0), i))
            scored.sort()
            fixed = False
            for _, i in scored:
                p = run[i]
                old = self.get(*p)
                self.setc(*p, HIGH)
                if self.unreachable() > 0:
                    self.setc(*p, old)
                    continue
                self.tags[p[0]][p[1]] = T_COVER if (self.distout(*p) <= 1 and not self.center_zone(p)) else T_PILLAR
                fixed = True
                break
            if not fixed:
                return False
        return self.find_long_run() is None

    def compute_dout(self):
        G = self.G
        self.dout = [[0] * G for _ in range(G)]
        q = []
        for x in range(G):
            for y in range(G):
                if not self.inside(x, y):
                    continue
                self.dout[x][y] = 255
                for d in DIRS4:
                    if not self.inside(x + d[0], y + d[1]):
                        self.dout[x][y] = 1
                        q.append((x, y))
                        break
        h = 0
        while h < len(q):
            p = q[h]
            h += 1
            nd = self.dout[p[0]][p[1]] + 1
            for d in DIRS4:
                qq = (p[0] + d[0], p[1] + d[1])
                if self.inside(*qq) and self.dout[qq[0]][qq[1]] > nd:
                    self.dout[qq[0]][qq[1]] = nd
                    q.append(qq)

    def try_asm(self, kind, base, out, mirror, R):
        rows = ROWS[kind]
        along = (-out[1], out[0])
        if mirror:
            along = (-along[0], -along[1])
        W, D = len(rows[0]), len(rows)

        def loc(u, v):
            return (base[0] + along[0] * u - out[0] * v, base[1] + along[1] * u - out[1] * v)
        for v in range(D):
            for u in range(W):
                p = loc(u, v)
                if not self.inside(*p) or self.res(*p) or self.get(*p) != FREE or self.center_zone(p):
                    return False
                if v == 0 and self.inside(p[0] + out[0], p[1] + out[1]):
                    return False
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if self.asm_at(p[0] + dx, p[1] + dy) >= 0:
                            return False
        for u in range(W):
            f = loc(u, D)
            if not self.inside(*f) or self.get(*f) != FREE or self.asm_at(*f) >= 0:
                return False
        far = loc(W - 1, D - 1)
        mx, my = (base[0] + far[0]) / 2, (base[1] + far[1]) / 2
        if math.hypot(mx - self.start[0], my - self.start[1]) < 0.45 * R:
            return False
        ang = math.atan2(my - self.start[1], mx - self.start[0])
        for o in self.asms:
            d = (ang - o["ang"] + math.pi) % (2 * math.pi) - math.pi
            if abs(d) < math.radians(70):
                return False
        a = {"kind": kind, "cells": [], "solid": [], "low": [], "yard": [], "chest": None, "ang": ang, "out": out,
             "W": W, "loc0": [loc(u, 0) for u in range(W)]}
        for v in range(D):
            for u in range(W):
                p = loc(u, v)
                a["cells"].append(p)
                ch = rows[v][u]
                if ch == "S":
                    self.setc(*p, HIGH)
                    a["solid"].append(p)
                elif ch == "L":
                    self.setc(*p, LOW)
                    a["low"].append(p)
                else:
                    a["yard"].append(p)
                    if ch == "C":
                        a["chest"] = p
        if self.unreachable() > 0:
            for p in a["cells"]:
                self.setc(*p, FREE)
            return False
        idx = len(self.asms)
        for p in a["cells"]:
            self.setr(*p)
            self.tags[p[0]][p[1]] = T_ASM
            self.asmat[p[0]][p[1]] = idx
        for u in range(W):
            self.setr(*loc(u, D))
        self.asms.append(a)
        return True

    def place_asms(self, rng, R):
        wanted = 2 if self.N <= 12 else (3 if self.N <= 16 else 4)
        kinds = ["Patio", "FerroVelho", "Acampamento"]
        rng.shuffle(kinds)
        if rng.random() < 0.75:
            kinds.insert(0, "Posto")
        else:
            kinds.append("Posto")
        edges = [((x, y), d) for x in range(self.G) for y in range(self.G) if self.inside(x, y) for d in DIRS4
                 if not self.inside(x + d[0], y + d[1])]
        for k in kinds:
            if len(self.asms) >= wanted:
                break
            rng.shuffle(edges)
            for (b, d) in edges:
                if self.try_asm(k, b, d, rng.random() < 0.5, R):
                    break

    def generate(self, seed, level, forced, with_cover):
        rng = random.Random(seed)
        N = size_for_level(level)
        self.N = N
        G = self.G = N + 2
        self.cells = [[OUT] * G for _ in range(G)]
        self.reserved = [[False] * G for _ in range(G)]
        self.tags = [[0] * G for _ in range(G)]
        self.asmat = [[-1] * G for _ in range(G)]
        self.asms = []
        self.spawn, self.extr, self.obj, self.chest = [], [], [], []
        shape = forced if forced >= 0 else rng.randint(0, 4)
        self.shape = shape
        C = (N - 1) * 0.5

        def setin(ix, iy):
            if 0 <= ix < N and 0 <= iy < N:
                self.setc(ix + 1, iy + 1, FREE)
        if shape == 0:
            R0 = N * 0.5
            for x in range(N):
                for y in range(N):
                    if (x - C) ** 2 + (y - C) ** 2 <= R0 * R0 * 0.98:
                        setin(x, y)
        elif shape == 1:
            W = N * 0.2 + 0.01
            for x in range(N):
                for y in range(N):
                    if abs(x - C) <= W or abs(y - C) <= W:
                        setin(x, y)
        elif shape == 2:
            X0, X1, Y0 = N // 3, N - N // 3, N // 2
            turns = rng.randint(0, 3)
            for x in range(N):
                for y in range(N):
                    if X0 <= x < X1 and y >= Y0:
                        continue
                    rx, ry = x, y
                    for _ in range(turns):
                        rx, ry = N - 1 - ry, rx
                    setin(rx, ry)
        elif shape == 3:
            A = int(N * 0.6 + 0.5)
            mirror = rng.randint(0, 1) == 1
            for x in range(N):
                for y in range(N):
                    if (x < A and y < A) or (x >= N - A and y >= N - A):
                        setin(N - 1 - x if mirror else x, y)
        else:
            horiz = rng.randint(0, 1) == 1
            pts = [(x, y) for x in range(N) for y in range(N) if abs(y - C) <= 1.5]
            nall = 2 + N // 8
            aw = 2 if N < 14 else 3
            ax = [int(C)]
            for _ in range(50):
                if len(ax) >= nall:
                    break
                x = rng.randint(1, N - 3)
                if all(abs(x - o) >= 4 for o in ax):
                    ax.append(x)
            up, dn = int(C + 2), int(C - 2)
            for i, x in enumerate(ax):
                for side in (-1, 1):
                    if i != 0 and rng.random() >= 0.7:
                        continue
                    ln = N if i == 0 else rng.randint(N // 4, N // 2)
                    for k in range(ln):
                        y = up + k if side > 0 else dn - k
                        if 0 <= y < N:
                            for ww in range(aw):
                                pts.append((x + ww, y))
                    if i > 0:
                        ye = max(1, min(N - 2, up + ln - 1 if side > 0 else dn - ln + 1))
                        for dx in range(-1, 3):
                            for dy in range(-1, 2):
                                pts.append((x + dx, ye + dy))
            for (x, y) in pts:
                if horiz:
                    setin(x, y)
                else:
                    setin(y, x)
        best = None
        for x in range(1, G - 1):
            for y in range(1, G - 1):
                arms = sum(self.inside(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)))
                if arms < 3 or not all(self.inside(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    continue
                d = (x - 1 - C) ** 2 + (y - 1 - C) ** 2
                if best is None or d < best[0]:
                    best = (d, (x, y))
        if not best:
            return "sem centro 3x3"
        self.start = best[1]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.setr(self.start[0] + dx, self.start[1] + dy)
        for d in DIRS4:
            if self.inside(self.start[0] + d[0] * 2, self.start[1] + d[1] * 2):
                self.setr(self.start[0] + d[0] * 2, self.start[1] + d[1] * 2)
        R = N * 0.5
        self.compute_dout()
        if with_cover:
            self.place_asms(rng, R)
        inside = [(x, y) for x in range(G) for y in range(G) if self.inside(x, y)]
        self.fix_sight(rng)
        if with_cover:
            pats = {1: [(0, 0)], 2: [(0, 0), (1, 0)], 3: [(0, 0), (1, 0), (2, 0)], 4: [(0, 0), (1, 0), (0, 1)]}
            target = int(len(inside) * (0.12 + rng.random() * 0.06))
            blocked = 0
            for _ in range(600):
                if blocked >= target:
                    break
                base = inside[rng.randint(0, len(inside) - 1)]
                roll = rng.random()
                pat = pats[4] if roll >= 0.85 else pats[3] if roll >= 0.7 else pats[2] if roll >= 0.45 else pats[1]
                turns = rng.randint(0, 3)
                grp = []
                for d in pat:
                    for _ in range(turns):
                        d = (-d[1], d[0])
                    grp.append((base[0] + d[0], base[1] + d[1]))
                ok = True
                for p in grp:
                    if self.get(*p) != FREE or self.res(*p) or self.center_zone(p):
                        ok = False
                        break
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            q = (p[0] + dx, p[1] + dy)
                            if q in grp:
                                continue
                            if self.get(*q) in (LOW, HIGH):
                                ok = False
                    if not ok:
                        break
                if not ok:
                    continue
                single = len(pat) == 1
                near = all(self.distout(*p) <= HIGH_MAX_DIST for p in grp)
                high = near and (rng.random() < 0.2 if single else rng.random() < 0.5)
                for p in grp:
                    self.setc(*p, HIGH if high else LOW)
                    self.tags[p[0]][p[1]] = T_COVER
                blocked += len(grp)
        for _ in range(80):
            seen = self.flood()
            lost = lambda p: self.get(*p) == FREE and not seen[p[0]][p[1]]  # noqa: E731
            if not any(lost(p) for p in inside):
                break
            opened = False
            for p in inside:
                if self.get(*p) not in (LOW, HIGH) or self.res(*p):
                    continue
                ts = tl = False
                for d in DIRS4:
                    q = (p[0] + d[0], p[1] + d[1])
                    if not self.valid(*q):
                        continue
                    ts |= bool(seen[q[0]][q[1]])
                    tl |= lost(q)
                if ts and tl:
                    self.setc(*p, FREE)
                    opened = True
                    break
            if not opened:
                return "área fechada"
        if self.unreachable() > 0:
            return "área fechada"
        if not self.fix_sight(rng):
            return "linha de visão longa"
        if self.center_exits() < 3:
            return "saídas"
        freec = [p for p in inside if self.get(*p) == FREE and not self.res(*p)]

        def edge(p):
            return any(self.get(p[0] + dx, p[1] + dy) == OUT for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        cand = [p for p in freec if dist(p, self.start) >= max(3, 0.5 * R)]
        rng.shuffle(cand)
        cand.sort(key=lambda p: not edge(p))
        for p in cand:
            if all(cheb(p, o) >= 2 for o in self.spawn):
                self.spawn.append(p)
                if len(self.spawn) >= 20:
                    break
        if len(self.spawn) < MIN_SPAWN:
            return "surgimento"
        for p in self.spawn:
            self.setr(*p)
        for sec in range(4):
            bs, bp = -1, None
            for p in freec:
                if self.res(*p) or dist(p, self.start) < 0.35 * R:
                    continue
                ang = math.atan2(p[1] - self.start[1], p[0] - self.start[0])
                s = int(((ang + math.pi) / (2 * math.pi)) * 4) % 4
                if s != sec:
                    continue
                fa = sum(self.get(p[0] + dx, p[1] + dy) == FREE for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                sc = dist(p, self.start) + 0.5 * fa + rng.random()
                if sc > bs:
                    bs, bp = sc, p
            if bp:
                self.extr.append(bp)
                self.setr(*bp)
        if len(self.extr) < MIN_EXTR:
            return "nave"
        cand = [p for p in freec if not self.res(*p) and dist(p, self.start) >= 0.3 * R]
        rng.shuffle(cand)

        def nest_score(p):
            s = 1 if self.distout(*p) >= 2 else 0
            clean = all(self.get(p[0] + dx, p[1] + dy) not in (LOW, HIGH) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            return s + (2 if clean else 0)
        cand.sort(key=lambda p: -nest_score(p))
        for p in cand:
            if all(cheb(p, o) >= 3 for o in self.obj):
                self.obj.append(p)
                if len(self.obj) >= 6:
                    break
        if len(self.obj) < MIN_OBJ:
            return "objetivos"
        for p in self.obj:
            self.setr(*p)

        def chest_ok(p):
            return all(cheb(p, o) >= 2 for o in self.obj) and all(cheb(p, o) >= 4 for o in self.chest)
        slots = [a["chest"] for a in self.asms if a["chest"]]
        rng.shuffle(slots)
        for p in slots:
            if len(self.chest) < 2 and self.get(*p) == FREE and self.free_n4(p) >= 2 and chest_ok(p):
                self.chest.append(p)
        cand = [p for p in freec if not self.res(*p) and dist(p, self.start) >= 0.4 * R and self.distout(*p) <= 1
                and self.free_n4(p) >= 2]
        rng.shuffle(cand)
        for p in cand:
            if len(self.chest) >= 2:
                break
            if chest_ok(p):
                self.chest.append(p)
                self.setr(*p)
        return self.validate()

    def validate(self):
        if self.get(*self.start) != FREE:
            return "centro bloqueado"
        if self.unreachable():
            return "sem caminho"
        if self.longest() > MAX_SIGHT:
            return "visão"
        if self.center_exits() < 3:
            return "saídas"
        seen = self.flood()
        for lst in (self.spawn, self.extr, self.obj, self.chest):
            for p in lst:
                if self.get(*p) != FREE or not seen[p[0]][p[1]]:
                    return "ponto fora do caminho"
        for x in range(self.G):
            for y in range(self.G):
                if self.get(x, y) in (LOW, HIGH) and self.center_zone((x, y)) and self.tags[x][y] != T_PILLAR:
                    return "cobertura na zona central"
        for p in self.chest:
            if self.free_n4(p) < 2:
                return "baú 2 acessos"
        for a in self.asms:
            for p in a["loc0"]:
                if self.inside(p[0] + a["out"][0], p[1] + a["out"][1]):
                    return "conjunto solto"
        if self.free_ratio() < MIN_FREE:
            return "pouca área livre %.2f" % self.free_ratio()
        allp = self.spawn + self.extr + self.obj + self.chest
        if len(allp) != len(set(allp)):
            return "sobrepostos"
        return ""

    def ascii(self):
        lines = []
        for y in range(self.G - 1, -1, -1):
            row = ""
            for x in range(self.G):
                p = (x, y)
                c = self.get(x, y)
                ch = {OUT: " ", FREE: ".", LOW: "b", HIGH: "H"}[c]
                if self.tags[x][y] == T_PILLAR:
                    ch = "I"
                if self.asm_at(x, y) >= 0:
                    ch = {"Posto": "P", "Patio": "K", "FerroVelho": "F", "Acampamento": "A"}[self.asms[self.asm_at(x, y)]["kind"]] if c != FREE else "y"
                if p == self.start:
                    ch = "@"
                elif p in self.spawn:
                    ch = "s"
                elif p in self.extr:
                    ch = "E"
                elif p in self.obj:
                    ch = "o"
                elif p in self.chest:
                    ch = "c"
                row += ch
            lines.append(row)
        return "\n".join(lines)


def gen_retries(base, level, forced, attempts=12):
    last = ""
    for a in range(attempts):
        seed = base if a == 0 else (base * 7919 + a * 104729) & 0x7FFFFFFF
        lay = L()
        last = lay.generate(seed, level, forced, True)
        if last == "":
            return lay, a + 1, last
    lay = L()
    last = lay.generate(base, level, 0, False)
    return lay, attempts + 1, ("PLANO B: " + last)


if __name__ == "__main__":
    from collections import Counter
    fails, fallback, tries, nasm, kinds, chests, fr = Counter(), 0, [], [], Counter(), [], []
    for lv in (1, 3, 6, 10, 15):
        for sh in range(5):
            for sd in range(1, 21):
                lay, att, prob = gen_retries(sd * 977 + sh, lv, sh)
                tries.append(att)
                if prob.startswith("PLANO B"):
                    fallback += 1
                    fails[(lv, sh, prob)] += 1
                    if prob != "PLANO B: ":
                        fails[("BROKEN", prob)] += 1
                    continue
                nasm.append(len(lay.asms))
                for a in lay.asms:
                    kinds[a["kind"]] += 1
                chests.append(len(lay.chest))
                fr.append(lay.free_ratio())
    print("total", len(tries), "plano B", fallback, "tentativas média", sum(tries) / len(tries))
    print("conjuntos média", sum(nasm) / max(1, len(nasm)), kinds)
    print("baús média", sum(chests) / max(1, len(chests)), "livre média %.2f min %.2f" % (sum(fr) / len(fr), min(fr)))
    for k, v in fails.most_common(15):
        print(k, v)
    if len(sys.argv) > 1:
        for lv, sh in ((1, 0), (6, 1), (10, 4), (15, 2), (15, 3)):
            lay, att, prob = gen_retries(int(sys.argv[1]) + sh, lv, sh)
            print(f"\nnível {lv} molde {sh} tentativas {att} {prob} conjuntos {[a['kind'] for a in lay.asms]}")
            print(lay.ascii())
