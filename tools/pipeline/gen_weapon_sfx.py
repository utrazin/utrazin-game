"""Sintetiza os sons das armas de plasma (A-057): WAV 48 kHz 16 bits mono, gerados do zero (licença: projeto).

Uso:  python tools/pipeline/gen_weapon_sfx.py [--out assets/work/audio/weapons]
Requer numpy e scipy. Semente fixa: rodar de novo gera os mesmos arquivos.
Sons: tiro da pistola (zap agudo + baque), tiro da escopeta (carga + estouro grosso + crepitar), bombear da
escopeta, impacto (chiado), gatilho sem célula, recarga (pistola/escopeta), marcadores de acerto/abate, carne.
"""
import argparse
import os
import wave

import numpy as np
from scipy import signal

SR = 48000
_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "assets", "work", "audio", "weapons"))
OUT = os.path.abspath(_ap.parse_args().out)
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def t(d): return np.arange(int(SR * d)) / SR
def env(n, a, d, curve=4.0):
    x = np.arange(n) / SR
    e = np.minimum(1, x / max(a, 1e-4)) * np.exp(-np.maximum(0, x - a) * curve / max(d, 1e-4))
    return e
def chirp(f0, f1, d, k=6.0):
    x = t(d); f = f1 + (f0 - f1) * np.exp(-x * k / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def noise(d): return rng.standard_normal(int(SR * d))
def bp(x, lo, hi, o=4): return signal.sosfilt(signal.butter(o, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def lp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, "lowpass", fs=SR, output="sos"), x)
def hp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, "highpass", fs=SR, output="sos"), x)
def pad(x, n): return np.pad(x, (0, max(0, n - len(x))))[:n]
def fade(x, ms=8):
    n = int(SR * ms / 1000); x = x.copy(); x[-n:] *= np.linspace(1, 0, n); x[:32] *= np.linspace(0, 1, 32); return x
def save(name, x, peak=0.89):
    x = fade(x); x = x / (np.max(np.abs(x)) + 1e-9) * peak
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(name, round(len(x) / SR, 3), "s")

# Pistola: zap agudo descendo (2,4k -> 300 Hz) com FM, estalo inicial e baque grave
d = 0.42; n = int(SR * d)
zap = chirp(2600, 260, d, 9) * env(n, 0.002, 0.16, 3.5)
fm = np.sin(2 * np.pi * np.cumsum(1400 * np.exp(-t(d) * 18) + 300) / SR + 3 * np.sin(2 * np.pi * 90 * t(d)))
fm *= env(n, 0.001, 0.08, 4) * 0.5
snap = hp(noise(d), 3000) * env(n, 0.0005, 0.015, 5) * 0.6
thump = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-t(d) * 12) + 45) / SR) * env(n, 0.002, 0.12, 5) * 0.9
tail = bp(noise(d), 600, 3000) * env(n, 0.01, 0.3, 4) * 0.12
save("SFX_Plasma_Pistol_Fire", zap * 0.8 + fm + snap + thump + tail)

# Escopeta: carga curta (hum subindo) + estouro grosso + crepitar
d = 0.95; n = int(SR * d)
x = t(d)
burst = (chirp(900, 120, d, 7) + 0.6 * chirp(1300, 160, d, 8) + 0.5 * chirp(620, 90, d, 6)) * env(n, 0.002, 0.3, 3)
body = lp(noise(d), 1800) * env(n, 0.001, 0.22, 4) * 1.2
sub = np.sin(2 * np.pi * np.cumsum(80 * np.exp(-x * 6) + 32) / SR) * env(n, 0.003, 0.35, 4) * 1.3
crack = np.zeros(n)
for i in range(70):
    p = int(rng.uniform(0.04, 0.8) * SR); L = int(rng.uniform(0.0008, 0.004) * SR)
    if p + L < n: crack[p:p + L] += rng.standard_normal(L) * rng.uniform(0.2, 1) * np.exp(-((p / SR) - 0.04) * 3.5)
crack = hp(crack, 2500) * 0.5
pre = np.zeros(n); pre[:int(0.05 * SR)] = (np.sin(2 * np.pi * np.cumsum(np.linspace(200, 900, int(0.05 * SR))) / SR)
                                          * np.linspace(0, 0.35, int(0.05 * SR)))
sh = int(0.045 * SR)
main = np.concatenate([np.zeros(sh), (burst * 0.7 + body + sub + crack)[:n - sh]])
save("SFX_Plasma_Shotgun_Fire", pre + main)

# Escopeta: "bombear" (recarrega a célula): clique duplo + zumbido subindo
d = 0.55; n = int(SR * d); x = t(d)
c1 = hp(noise(d), 1500) * env(n, 0.0005, 0.02, 5)
c2 = np.roll(c1, int(0.16 * SR)) * 0.8
hum = (np.sin(2 * np.pi * np.cumsum(np.linspace(140, 520, n)) / SR) + 0.3 * np.sin(2 * np.pi * np.cumsum(np.linspace(280, 1040, n)) / SR))
hum *= np.clip((x - 0.05) / 0.2, 0, 1) * np.exp(-np.maximum(0, x - 0.3) * 10) * 0.35
save("SFX_Plasma_Shotgun_Pump", c1 + c2 + hum)

# Impacto: chiado (sizzle) + estalo
d = 0.5; n = int(SR * d); x = t(d)
pop = (hp(noise(d), 800) * env(n, 0.0005, 0.03, 5)) + np.sin(2 * np.pi * np.cumsum(500 * np.exp(-x * 30) + 120) / SR) * env(n, 0.001, 0.05, 5) * 0.6
siz = hp(noise(d), 3500) * (0.4 + 0.6 * (rng.random(n) > 0.85)) * env(n, 0.005, 0.45, 3.5) * 0.35
save("SFX_Plasma_Impact", pop + siz)

# Gatilho sem célula (clique seco + zumbido morto)
d = 0.22; n = int(SR * d); x = t(d)
click = hp(noise(d), 2000) * env(n, 0.0003, 0.01, 6) + bp(noise(d), 900, 1600) * env(n, 0.0005, 0.02, 6) * 0.5
dud = np.sin(2 * np.pi * 95 * x) * env(n, 0.005, 0.12, 4) * 0.25 * (1 + 0.5 * np.sign(np.sin(2 * np.pi * 50 * x)))
save("SFX_Plasma_DryFire", click + dud, peak=0.7)

# Recarga: tira célula (clique), zumbido carregando subindo, trava
def reload(dur, f0, f1, name):
    n = int(SR * dur); x = t(dur)
    out = hp(noise(dur), 1500) * env(n, 0.0005, 0.02, 5) * 0.8
    hum = np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(np.linspace(f0 * 2.01, f1 * 2.01, n)) / SR)
    trem = 1 + 0.3 * np.sin(2 * np.pi * np.linspace(6, 30, n) * x)
    hum *= np.clip((x - 0.25) / (dur * 0.5), 0, 1) * trem * 0.3
    hum[int(n * 0.9):] *= np.linspace(1, 0, n - int(n * 0.9))
    lock = np.roll(hp(noise(dur), 1200) * env(n, 0.0005, 0.03, 5), int(0.88 * n)) * 0.9
    save(name, out + hum + lock)
reload(1.5, 120, 700, "SFX_Plasma_Reload_Pistol")
reload(2.2, 90, 520, "SFX_Plasma_Reload_Shotgun")

# Marcadores de acerto (UI)
d = 0.09; n = int(SR * d); x = t(d)
save("SFX_UI_HitMarker", (np.sin(2 * np.pi * 2300 * x) * 0.5 + hp(noise(d), 4000) * 0.4) * env(n, 0.0005, 0.03, 5), peak=0.5)
d = 0.28; n = int(SR * d); x = t(d)
k = np.sin(2 * np.pi * 1500 * x) * env(n, 0.0005, 0.05, 5) + np.roll(np.sin(2 * np.pi * 2000 * x) * env(n, 0.0005, 0.12, 4), int(0.05 * SR))
save("SFX_UI_KillMarker", k + np.sin(2 * np.pi * np.cumsum(140 * np.exp(-x * 10) + 50) / SR) * env(n, 0.002, 0.1, 5) * 0.6, peak=0.6)

# Acerto em carne (respingo molhado)
d = 0.3; n = int(SR * d); x = t(d)
sq = lp(noise(d), 1400) * env(n, 0.002, 0.12, 4) + bp(noise(d), 200, 600) * env(n, 0.001, 0.05, 5) * 0.8
for i in range(8):
    p = int(rng.uniform(0.02, 0.2) * SR); L = int(0.004 * SR)
    sq[p:p + L] += bp(rng.standard_normal(L), 1500, 4000) * 0.3
save("SFX_Flesh_Hit", sq, peak=0.75)

# Rifle de precisão (A-057): carga aguda curta + disparo grosso com estalo supersônico e cauda longa
d = 1.6; n = int(SR * d); x = t(d)
charge = np.sin(2 * np.pi * np.cumsum(np.linspace(600, 2400, int(0.07 * SR))) / SR) * np.linspace(0, 0.3, int(0.07 * SR))
crack = hp(noise(d), 2500) * env(n, 0.0003, 0.02, 6) * 1.2
beam = (chirp(3200, 180, d, 10) + 0.7 * chirp(1500, 90, d, 8)) * env(n, 0.002, 0.5, 3)
boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-x * 5) + 28) / SR) * env(n, 0.003, 0.6, 3.5) * 1.5
tail = bp(noise(d), 300, 1800) * env(n, 0.03, 1.3, 3) * 0.25
sh = int(0.07 * SR)
main = np.concatenate([np.zeros(sh), (crack + beam * 0.8 + boom + tail)[:n - sh]])
save("SFX_Plasma_Sniper_Fire", pad(charge, n) + main)

# Rifle: "ferrolho" de energia (clique, zumbido subindo, trava)
d = 0.9; n = int(SR * d); x = t(d)
k1 = hp(noise(d), 1800) * env(n, 0.0004, 0.02, 5)
k2 = np.roll(k1, int(0.55 * SR)) * 1.1
hum = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 900, n)) / SR) * np.clip((x - 0.1) / 0.3, 0, 1) * np.exp(-np.maximum(0, x - 0.55) * 12) * 0.3
save("SFX_Plasma_Sniper_Bolt", k1 + k2 + hum)

# Luneta: zoom (servo curto)
d = 0.25; n = int(SR * d); x = t(d)
servo = bp(noise(d), 2000, 6000) * (0.5 + 0.5 * np.sin(2 * np.pi * 90 * x)) * env(n, 0.01, 0.18, 4) * 0.4
save("SFX_Scope_Zoom", servo + hp(noise(d), 3000) * env(n, 0.0003, 0.01, 6) * 0.5, peak=0.5)
