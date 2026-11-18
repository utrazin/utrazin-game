import json, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = np.load(sys.argv[1] + "/l01_preview.npz"); L = json.load(open(sys.argv[1] + "/l01_layout.json"))
col, H = d["col"], d["H"]; HALF = 1000
fig, ax = plt.subplots(figsize=(10, 10))
gx, gy = np.gradient(H)
shade = np.clip(0.75 + (gx - gy) * 0.08, 0.4, 1.1)[..., None]
img = np.clip(col * shade, 0, 1)
ax.imshow(np.transpose(img, (1, 0, 2))[::-1], extent=(-HALF, HALF, -HALF, HALF))
ax.contour(np.linspace(-HALF, HALF, H.shape[0]), np.linspace(-HALF, HALF, H.shape[0]), H.T, levels=12, colors="k", linewidths=0.3, alpha=0.4)
r, t = d["road"], d["trail"]
ax.plot(r[:, 0], r[:, 1], color="#222", lw=3, label=f"estrada (carro) {L['road_length_m']} m")
ax.plot(t[:, 0], t[:, 1], color="#fff2c0", lw=2.2, ls="--", label=f"trilha a pé {L['trail_length_m']} m")
for p in L["props"]:
    if p["mesh"].startswith("SM_Tree"):
        ax.plot(p["loc"][0] / 100, -p["loc"][1] / 100, ".", color="#1d4d14", ms=2)
    elif p["mesh"] in ("SM_Ruin_House", "SM_Ruin_Wall", "SM_Watchtower"):
        ax.plot(p["loc"][0] / 100, -p["loc"][1] / 100, "s", color="#8a6", ms=4)
for e in L["enemies"]:
    ax.plot(e["loc"][0] / 100, -e["loc"][1] / 100, "^" if e["type"] == "archer" else "x", color="red", ms=6, mew=2)
ax.plot(r[0, 0], r[0, 1], "o", color="lime", ms=14, mec="k", label="início (carro)")
ax.plot(*d["plaza"], "s", color="dodgerblue", ms=12, mec="k", label="desembarque / checkpoint")
ax.add_patch(plt.Circle(d["arena"], float(d["arena_r"]), fill=False, color="red", lw=2.5))
ax.plot([], [], "o", mfc="none", mec="red", ms=12, label="arena da horda")
ax.plot(*d["cage"], "*", color="gold", ms=20, mec="k", label="cela do resgate")
ax.plot([], [], "x", color="red", label="zumbis"); ax.plot([], [], "^", color="red", label="arqueiros (torres)")
ax.legend(loc="lower right", fontsize=9); ax.set_xlabel("m (leste)"); ax.set_ylabel("m (norte)")
ax.set_title("Fase 1 - mapa 2 x 2 km (prévia de cima)")
plt.tight_layout(); plt.savefig(sys.argv[1] + "/l01_map.png", dpi=80)
