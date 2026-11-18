"""Gera os sons do jogo (Etapa 10, A-061): carro, zumbis, herói, mundo, ambiente, interface e música.

Uso:  python tools/pipeline/gen_game_audio.py [--raw assets/raw/audio] [--out assets/work/audio]
Requer numpy, scipy e ffmpeg no PATH (para ler os .ogg da Kenney). Semente fixa: rodar de novo gera os mesmos arquivos.

Duas origens:
  * Kenney (CC0 1.0): zips em assets/raw/audio/kenney/ (impact, interface, rpg, sci-fi, digital, ui). Cortados
    (silêncio fora), convertidos para 48 kHz mono, normalizados e às vezes misturados com camadas sintetizadas.
  * Síntese própria (numpy/scipy, licença do projeto): vozes dos zumbis/herói, motor, derrapagem, fogo,
    ambientes, música e o que a Kenney não tem.

Saída: assets/work/audio/<grupo>/<Nome>.wav (16 bits, 48 kHz; SFX mono, ambiente e música estéreo) e
CREDITS.md por grupo. Os nomes seguem design/audio-bible/AUDIO_BIBLE.md (SFX_, AMB_, MUS_) e são lidos por
tools/unreal/setup_audio.py (lista SOUNDS lá: id do banco -> arquivos). Loops têm a emenda cruzada (sem clique).
Grupo "weapons" não é tocado aqui (gen_weapon_sfx.py).
"""
import argparse
import glob
import os
import shutil
import subprocess
import tempfile
import wave
import zipfile

import numpy as np
from scipy import signal

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument("--raw", default=os.path.join(HERE, "..", "..", "assets", "raw", "audio"))
_ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "assets", "work", "audio"))
ARGS = _ap.parse_args()
RAW = os.path.abspath(ARGS.raw)
OUT = os.path.abspath(ARGS.out)
rng = np.random.default_rng(1010)
# [A-075] sons trocados/novos usam um gerador próprio: os outros arquivos saem idênticos aos de antes
rng2 = np.random.default_rng(2075)
def noise2(d): return rng2.standard_normal(n_(d))
CREDITS = {}  # grupo -> [(arquivo, origem, licença)]
KENNEY_LIC = "CC0 1.0 (Kenney, www.kenney.nl)"
OWN_LIC = "Própria (sintetizado por tools/pipeline/gen_game_audio.py)"

# ---------------------------------------------------------------- utilidades de sinal
def t(d): return np.arange(int(SR * d)) / SR
def n_(d): return int(SR * d)
def noise(d): return rng.standard_normal(n_(d))
def sos_bp(lo, hi, o=2): return signal.butter(o, [max(20, lo), min(SR / 2 - 100, hi)], "bandpass", fs=SR, output="sos")
def bp(x, lo, hi, o=2): return signal.sosfilt(sos_bp(lo, hi, o), x)
def lp(x, f, o=4): return signal.sosfilt(signal.butter(o, min(f, SR / 2 - 100), "lowpass", fs=SR, output="sos"), x)
def hp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, "highpass", fs=SR, output="sos"), x)
def pad(x, n): return np.pad(x, (0, max(0, n - len(x))))[:n]
def norm(x, peak=1.0): return x / (np.max(np.abs(x)) + 1e-9) * peak
def adsr(n, a, r, curve=1.0):
    """Envelope simples: sobe em a segundos, cai em r segundos no fim (sustain no meio)."""
    e = np.ones(n)
    na, nr = max(1, n_(a)), max(1, n_(r))
    e[:na] = np.linspace(0, 1, na) ** curve
    e[-nr:] *= np.linspace(1, 0, nr) ** curve
    return e
def expdecay(n, a, d):
    x = np.arange(n) / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.exp(-np.maximum(0, x - a) / max(d, 1e-4))
def smooth_noise(n, rate_hz, seed_scale=1.0):
    """Ruído lento (interpolado) em [-1, 1]."""
    k = max(2, int(n / SR * rate_hz) + 2)
    pts = rng.uniform(-1, 1, k) * seed_scale
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
def mix(*parts):
    n = max(len(p) for p in parts)
    return sum(pad(p, n) for p in parts)
def at(x, start_s, total):
    """Coloca x começando em start_s dentro de um buffer de total amostras."""
    out = np.zeros(total)
    s = int(start_s * SR)
    if s >= total:
        return out
    m = min(len(x), total - s)
    out[s:s + m] = x[:m]
    return out
def trim(x, db=-50.0, keep_ms=10):
    thr = np.max(np.abs(x)) * 10 ** (db / 20)
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    k = int(SR * keep_ms / 1000)
    return x[max(0, idx[0] - k): min(len(x), idx[-1] + k)]
def fade(x, ms_in=2, ms_out=15):
    x = x.copy()
    a, b = max(1, int(SR * ms_in / 1000)), max(1, int(SR * ms_out / 1000))
    if x.ndim == 1:
        x[:a] *= np.linspace(0, 1, a); x[-b:] *= np.linspace(1, 0, b)
    else:
        x[:a] *= np.linspace(0, 1, a)[:, None]; x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x
def loopify(x, xfade_s):
    """x tem (L + X) amostras: devolve L amostras com o fim cruzado no começo (emenda sem clique)."""
    X = n_(xfade_s)
    L = len(x) - X
    out = x[:L].copy()
    w = np.linspace(0, np.pi / 2, X)
    fi, fo = np.sin(w), np.cos(w)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    out[:X] = x[:X] * fi + x[L:] * fo
    return out
def stereo(l, r): return np.stack([l, r], axis=1)
def widen(x, delay_ms=11, amount=0.6):
    """Mono -> estéreo com atraso curto e ruído de pan lento."""
    d = int(SR * delay_ms / 1000)
    r = np.concatenate([x[-d:], x[:-d]]) if d > 0 else x
    return stereo(x * (1 - 0.5 * amount) + r * 0.5 * amount, r * (1 - 0.5 * amount) + x * 0.5 * amount)
def saw(phase): return 2 * (phase % 1.0) - 1
def osc_phase(freq): return np.cumsum(freq) / SR if np.ndim(freq) else None

# ---------------------------------------------------------------- saída
def write(group, name, x, peak=0.89, src=OWN_LIC, lic=None, is_loop=False):
    d = os.path.join(OUT, group)
    os.makedirs(d, exist_ok=True)
    if not is_loop:
        x = fade(x)
    x = norm(x, peak)
    data = np.clip(x, -1, 1)
    ch = 1 if data.ndim == 1 else data.shape[1]
    with wave.open(os.path.join(d, name + ".wav"), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((data * 32767).astype("<i2").tobytes())
    CREDITS.setdefault(group, []).append((name + ".wav", src, lic or (OWN_LIC if src == OWN_LIC else KENNEY_LIC)))
    print(f"  {group}/{name}.wav  {len(data) / SR:.2f}s  {'loop' if is_loop else ''}")

# ---------------------------------------------------------------- Kenney
KDIR = None
def kenney_extract():
    global KDIR
    KDIR = tempfile.mkdtemp(prefix="jr_kenney_")
    zips = sorted(glob.glob(os.path.join(RAW, "kenney", "*.zip")))
    if not zips:
        raise SystemExit(f"Sem zips da Kenney em {RAW}/kenney (baixe de kenney.nl/assets: impact-sounds, interface-sounds, "
                         "rpg-audio, sci-fi-sounds, digital-audio, ui-audio)")
    for z in zips:
        name = os.path.splitext(os.path.basename(z))[0].replace("kenney_", "")
        with zipfile.ZipFile(z) as f:
            for m in f.namelist():
                if m.lower().endswith(".ogg") and not os.path.isabs(m) and ".." not in m:
                    f.extract(m, os.path.join(KDIR, name))
_kcache = {}
def K(pack, fname, src_list=None):
    """Lê um .ogg da Kenney (pack = impact-sounds, rpg-audio...) como mono 48 kHz, cortado."""
    key = (pack, fname)
    if key not in _kcache:
        path = os.path.join(KDIR, pack, "Audio", fname)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                             check=True, capture_output=True).stdout
        _kcache[key] = trim(np.frombuffer(raw, dtype="<f4").astype(np.float64))
    if src_list is not None:
        src_list.append(f"Kenney {pack}/{fname}")
    return _kcache[key].copy()
def ksrc(lst): return "; ".join(lst)

# ---------------------------------------------------------------- instrumentos sintéticos
def voice(dur, f0, vowels, breath=0.25, rough=0.0, rough_hz=40.0, jitter=0.03, drive=1.5, sub=0.0, env=None):
    """Voz rouca: fonte glotal (dente-de-serra suavizada) + sopro, filtrada por formantes que vão de vowels[0] a vowels[-1].

    f0: número ou array (Hz por amostra). vowels: lista de [(F, largura, ganho), ...]. rough: modulação de
    amplitude grave (rosnado); sub: sub-harmônico (meia frequência)."""
    n = n_(dur)
    f = np.full(n, float(f0)) if np.ndim(f0) == 0 else pad(np.asarray(f0, float), n)
    f = f * (1 + jitter * smooth_noise(n, 25))
    ph = np.cumsum(f) / SR
    src = saw(ph) + sub * saw(ph * 0.5)
    src = lp(src, 900, 1) * 0.8 + src * 0.2
    if rough > 0:
        am = 1 + rough * np.sin(2 * np.pi * np.cumsum(rough_hz * (1 + 0.3 * smooth_noise(n, 6))) / SR)
        src = src * am
    br = bp(rng.standard_normal(n), 400, 5000) * breath * (1 + 0.5 * smooth_noise(n, 9))
    exc = src + br
    outs = []
    for v in vowels:
        y = np.zeros(n)
        for (F, bw, g) in v:
            y += bp(exc, F - bw / 2, F + bw / 2, 2) * g
        outs.append(y)
    if len(outs) == 1:
        y = outs[0]
    else:
        pos = np.linspace(0, len(outs) - 1, n)
        y = np.zeros(n)
        for i, o in enumerate(outs):
            y += o * np.clip(1 - np.abs(pos - i), 0, 1)
    y = np.tanh(drive * norm(y))
    e = env if env is not None else adsr(n, 0.06, dur * 0.4)
    return y * pad(e, n)
UH = [(600, 160, 1.0), (1000, 200, 0.6), (2400, 300, 0.25)]
AA = [(760, 180, 1.0), (1200, 220, 0.7), (2550, 300, 0.3)]
OO = [(350, 120, 1.0), (800, 160, 0.5), (2300, 300, 0.15)]
EH = [(520, 150, 1.0), (1750, 250, 0.6), (2550, 300, 0.3)]
RR = [(450, 200, 1.0), (1300, 300, 0.7), (1700, 300, 0.4)]  # rosnado
def glide(f_a, f_b, dur, k=3.0):
    x = np.linspace(0, 1, n_(dur))
    return f_a + (f_b - f_a) * (1 - np.exp(-k * x)) / (1 - np.exp(-k))
def contour(points, dur):
    """points = [(tempo_rel 0..1, Hz)] -> array."""
    x = np.linspace(0, 1, n_(dur))
    return np.interp(x, [p[0] for p in points], [p[1] for p in points])
def pad_synth(freqs, dur, detune=0.006, cutoff=1800, attack=2.0, release=2.0, voices=3):
    n = n_(dur)
    y = np.zeros(n)
    for f in freqs:
        for v in range(voices):
            d = 1 + detune * (v - (voices - 1) / 2)
            ph = rng.uniform() + np.arange(n) * f * d / SR
            y += saw(ph) / (voices * len(freqs))
    y = lp(y, cutoff, 2)
    return y * adsr(n, attack, release)
def bell(f, dur, ratio=2.76, index=2.5, decay=1.2):
    x = t(dur)
    mod = index * np.exp(-x / (decay * 0.5)) * np.sin(2 * np.pi * f * ratio * x)
    return np.sin(2 * np.pi * f * x + mod) * expdecay(len(x), 0.004, decay)
def pluck_bass(f, dur, cutoff=600, decay=0.25):
    x = t(dur)
    y = saw(f * x) * 0.7 + np.sin(2 * np.pi * f * 0.5 * x) * 0.5
    return lp(y, cutoff, 2) * expdecay(len(x), 0.005, decay)
def kick(dur=0.35, f_hi=140, f_lo=45):
    x = t(dur)
    f = f_lo + (f_hi - f_lo) * np.exp(-x / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * expdecay(len(x), 0.002, 0.18)
def snare(dur=0.25):
    x = t(dur)
    body = np.sin(2 * np.pi * 190 * x) * expdecay(len(x), 0.001, 0.05)
    nz = hp(rng.standard_normal(len(x)), 1500) * expdecay(len(x), 0.001, 0.08)
    return body * 0.6 + nz
def hat(dur=0.06, open_=False):
    x = t(dur)
    return hp(rng.standard_normal(len(x)), 7000) * expdecay(len(x), 0.001, 0.12 if open_ else 0.02)
def tom(f, dur=0.4):
    x = t(dur)
    ff = f * (1 + 0.6 * np.exp(-x / 0.05))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * expdecay(len(x), 0.002, 0.2)
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)

# ================================================================= CARRO
def gen_vehicle():
    g = "vehicle"
    print("[carro]")
    # Motor: harmônicos de 45 Hz (pitch 1.0 = marcha lenta; o C++ sobe até ~2.6). 2 s exatos (90 ciclos) + emenda.
    d, X = 2.0, 0.25
    n = n_(d + X)
    x = np.arange(n) / SR
    f0 = 45.0
    y = np.zeros(n)
    for k in range(1, 36):
        amp = 1.0 / k ** 0.75
        if k % 2 == 0:
            amp *= 1.35  # 4 cilindros: 2a ordem forte
        jit = 1 + 0.08 * smooth_noise(n, 4)
        y += amp * jit * np.sin(2 * np.pi * f0 * k * x + rng.uniform(0, 2 * np.pi))
    puls = 1 + 0.35 * np.sin(2 * np.pi * f0 * 0.5 * x)  # batida de ignição
    y = y * puls + 0.25 * lp(rng.standard_normal(n), 600, 2) * (1 + np.sin(2 * np.pi * f0 * x))
    y = np.tanh(1.6 * norm(lp(y, 2200, 2)))
    write(g, "SFX_Vehicle_Engine_Loop", loopify(y, X), peak=0.8, is_loop=True)

    # Nitro: arranque (Kenney thrusterFire + chiado) e loop de rugido.
    s = []
    a = K("sci-fi-sounds", "thrusterFire_000.ogg", s)[:n_(1.4)] * adsr(n_(1.4), 0.005, 0.6)
    wh = bp(noise(1.2), 300, 4000) * expdecay(n_(1.2), 0.15, 0.5)
    write(g, "SFX_Vehicle_Nitro_Start", mix(a, wh * 0.5), src=ksrc(s) + " + síntese")
    n = n_(2.0 + 0.3)
    r = bp(rng.standard_normal(n), 250, 2600) * (1 + 0.4 * np.sin(2 * np.pi * 26 * np.arange(n) / SR))
    r += 0.6 * lp(rng.standard_normal(n), 180, 2)
    write(g, "SFX_Vehicle_Nitro_Loop", loopify(np.tanh(1.5 * norm(r)), 0.3), peak=0.75, is_loop=True)

    # Derrapagem: chiado de borracha (tom ~1100 Hz com vibrato) + ruído.
    n = n_(2.0 + 0.3)
    xx = np.arange(n) / SR
    fq = 1050 + 120 * smooth_noise(n, 3) + 40 * np.sin(2 * np.pi * 9 * xx)
    ph = np.cumsum(fq) / SR
    sq = np.sin(2 * np.pi * ph) + 0.4 * np.sin(4 * np.pi * ph) + 0.15 * np.sin(6 * np.pi * ph)
    sq *= 0.6 + 0.4 * (0.5 + 0.5 * smooth_noise(n, 14))
    sk = sq * 0.6 + bp(rng.standard_normal(n), 800, 4000) * 0.5
    write(g, "SFX_Vehicle_Skid_Loop", loopify(sk, 0.3), peak=0.75, is_loop=True)

    # Batidas: leve = placas de metal médias; forte = metal pesado + chapa + baque grave.
    for i in range(3):
        s = []
        a = K("impact-sounds", f"impactPlate_medium_00{i}.ogg", s)
        write(g, f"SFX_Vehicle_Impact_Light_0{i + 1}", a, src=ksrc(s))
    for i in range(3):
        s = []
        a = K("impact-sounds", f"impactMetal_heavy_00{i}.ogg", s)
        b = K("impact-sounds", f"impactPlate_heavy_00{i + 1}.ogg", s)
        th = np.sin(2 * np.pi * 55 * t(0.5)) * expdecay(n_(0.5), 0.002, 0.12)
        cr = hp(noise(0.6), 2500) * expdecay(n_(0.6), 0.001, 0.08) * 0.3
        write(g, f"SFX_Vehicle_Impact_Heavy_0{i + 1}", mix(a, b * 0.8, th * 0.9, cr), src=ksrc(s) + " + síntese")

    # Pneu furado: estouro + chiado de ar.
    pop = hp(noise(0.05), 600) * expdecay(n_(0.05), 0.0005, 0.012)
    th = np.sin(2 * np.pi * 70 * t(0.25)) * expdecay(n_(0.25), 0.001, 0.06)
    hs = hp(noise(1.4), 2500) * adsr(n_(1.4), 0.01, 1.1, 2)
    write(g, "SFX_Vehicle_TireBurst_01", mix(pop * 1.5, th, at(hs * 0.45, 0.03, n_(1.45))))

    # Aterrissagem do pulo: baque macio pesado + chapa leve.
    for i in range(2):
        s = []
        a = K("impact-sounds", f"impactSoft_heavy_00{i}.ogg", s)
        b = K("impact-sounds", f"impactPlate_light_00{i}.ogg", s)
        th = np.sin(2 * np.pi * 48 * t(0.4)) * expdecay(n_(0.4), 0.002, 0.1)
        write(g, f"SFX_Vehicle_Land_0{i + 1}", mix(a, b * 0.5, th), src=ksrc(s) + " + síntese")

    # [A-075] O buggy NÃO tem portas (antes: trinco + rangido e porta batendo). Ids Car.Door.* mantidos:
    # Door_Open = descer (mão no santantônio, roupa, bota no chão); Door_Close = subir (corpo no banco, chassi balança).
    s = []
    tot = n_(0.9)
    y = mix(at(lp(K("impact-sounds", "impactMetal_light_002.ogg", s), 4000) * 0.35, 0.0, tot),
            at(K("rpg-audio", "cloth3.ogg", s) * 0.8, 0.05, tot),
            at(K("rpg-audio", "footstep05.ogg", s), 0.38, tot))
    write(g, "SFX_Vehicle_Door_Open", y, src=ksrc(s))
    s = []
    tot = n_(0.9)
    y = mix(at(K("rpg-audio", "cloth2.ogg", s) * 0.7, 0.0, tot),
            at(K("impact-sounds", "impactSoft_medium_002.ogg", s), 0.12, tot),
            at(lp(K("impact-sounds", "impactPlate_light_003.ogg", s), 3500) * 0.3, 0.14, tot),
            at(pad(lp(K("rpg-audio", "creak3.ogg", s), 1800), n_(0.45)) * 0.25 * adsr(n_(0.45), 0.01, 0.3), 0.16, tot))
    write(g, "SFX_Vehicle_Door_Close", y, src=ksrc(s))

    # Fogo (loop): ronco grave + estalos.
    d, X = 4.0, 0.4
    n = n_(d + X)
    roar = lp(rng.standard_normal(n), 400, 2) * (1 + 0.4 * smooth_noise(n, 3))
    cr = np.zeros(n)
    for _ in range(int(18 * (d + X))):
        p = rng.integers(0, n - n_(0.05))
        L = n_(rng.uniform(0.004, 0.03))
        cr[p:p + L] += hp(rng.standard_normal(L), rng.uniform(1500, 5000)) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.3, 1.0)
    write(g, "SFX_Vehicle_Fire_Loop", loopify(norm(roar) * 0.6 + norm(cr) * 0.7, X), peak=0.7, is_loop=True)

    # Explosão: estrondo grave + "crunch" da Kenney + detritos.
    for i in range(2):
        s = []
        a = K("sci-fi-sounds", f"lowFrequency_explosion_00{i}.ogg", s)
        b = K("sci-fi-sounds", f"explosionCrunch_00{i}.ogg", s)
        boom = lp(noise(2.5), 180, 2) * expdecay(n_(2.5), 0.005, 0.7)
        deb = np.zeros(n_(2.5))
        for _ in range(25):
            p = rng.uniform(0.2, 1.8)
            L = n_(0.03)
            deb += at(hp(rng.standard_normal(L), 1200) * np.exp(-np.arange(L) / 300) * rng.uniform(0.1, 0.4), p, n_(2.5))
        write(g, f"SFX_Vehicle_Explosion_0{i + 1}", mix(a, b * 0.8, norm(boom) * 0.9, deb), src=ksrc(s) + " + síntese")

    # Buzina (dois tons).
    x = t(0.7)
    hn = sum(signal.square(2 * np.pi * f * x) * 0.5 for f in (415, 523))
    write(g, "SFX_Vehicle_Horn", np.tanh(1.2 * lp(hn, 2800)) * adsr(len(x), 0.01, 0.06))

    # Raspão na parede (metal arrastando).
    for i in range(2):
        d = 0.8
        n = n_(d)
        nz = rng.standard_normal(n)
        y = sum(bp(nz, f - 60, f + 60, 2) * rng.uniform(0.4, 1) for f in rng.uniform(900, 4500, 6))
        y += bp(nz, 1500, 7000) * 0.4
        y *= (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * rng.uniform(25, 45) * t(d)))) * adsr(n, 0.02, 0.35)
        write(g, f"SFX_Vehicle_Scrape_0{i + 1}", y)

# ================================================================= ZUMBIS
def gen_zombie():
    g = "zombie"
    print("[zumbis]")
    for i in range(4):  # gemido parado
        d = rng.uniform(1.6, 2.4)
        f = contour([(0, rng.uniform(95, 115)), (0.4, rng.uniform(85, 100)), (1, rng.uniform(65, 80))], d)
        y = voice(d, f, [UH, OO] if i % 2 == 0 else [AA, UH], breath=0.5, rough=0.35, rough_hz=rng.uniform(28, 40),
                  jitter=0.05, drive=1.8, env=adsr(n_(d), 0.25, d * 0.5))
        write(g, f"SFX_Zombie_Moan_0{i + 1}", y)
    for i in range(3):  # rosnado de aggro
        d = rng.uniform(0.8, 1.2)
        f = contour([(0, 80), (0.15, rng.uniform(120, 150)), (1, 70)], d)
        y = voice(d, f, [RR, AA], breath=0.4, rough=0.8, rough_hz=rng.uniform(35, 55), jitter=0.06, drive=3.0,
                  sub=0.5, env=expdecay(n_(d), 0.03, d * 0.45))
        write(g, f"SFX_Zombie_Growl_0{i + 1}", y)
    for i in range(2):  # grito da horda: várias vozes agudas sobrepostas
        d = 3.0
        tot = n_(d)
        acc = np.zeros(tot)
        for v in range(7):
            dd = rng.uniform(1.4, 2.4)
            f = contour([(0, rng.uniform(180, 240)), (0.3, rng.uniform(320, 420)), (1, rng.uniform(150, 200))], dd)
            y = voice(dd, f, [AA, EH], breath=0.6, rough=0.5, rough_hz=rng.uniform(40, 70), jitter=0.08, drive=4.0,
                      env=adsr(n_(dd), 0.08, dd * 0.6))
            acc += at(y * rng.uniform(0.5, 1.0), rng.uniform(0, 0.6), tot)
        write(g, f"SFX_Zombie_HordeScream_0{i + 1}", acc)
    for i in range(4):  # passos arrastados: pisada abafada + arrasto
        s = []
        st = lp(K("impact-sounds", f"footstep_concrete_00{i}.ogg", s), 1800)
        dr = bp(noise(0.35), 300, 2500) * adsr(n_(0.35), 0.08, 0.2) * 0.35
        write(g, f"SFX_Zombie_Step_0{i + 1}", mix(st, at(dr, 0.05, n_(0.45))), peak=0.7, src=ksrc(s) + " + síntese")
    for i in range(3):  # golpe: deslocamento de ar + grunhido curto
        d = 0.5
        wh = bp(noise(d), 400, 2500) * np.sin(np.pi * np.linspace(0, 1, n_(d))) ** 3
        gr = voice(0.35, glide(160, 110, 0.35), [AA], breath=0.4, rough=0.6, drive=3.0, env=expdecay(n_(0.35), 0.02, 0.12))
        write(g, f"SFX_Zombie_Attack_0{i + 1}", mix(wh * 0.6, at(gr, 0.05, n_(d))))
    for i in range(3):  # dor
        d = rng.uniform(0.35, 0.5)
        y = voice(d, glide(rng.uniform(170, 210), 110, d), [EH, UH], breath=0.5, rough=0.5, drive=3.0,
                  env=expdecay(n_(d), 0.01, d * 0.35))
        write(g, f"SFX_Zombie_Pain_0{i + 1}", y)
    for i in range(3):  # morte: grunhido que cai + gargarejo
        d = rng.uniform(1.1, 1.5)
        f = contour([(0, rng.uniform(140, 170)), (0.3, 110), (1, 45)], d)
        y = voice(d, f, [AA, UH, OO], breath=0.6, rough=0.9, rough_hz=rng.uniform(9, 14), jitter=0.08, drive=2.5,
                  env=adsr(n_(d), 0.02, d * 0.7))
        write(g, f"SFX_Zombie_Death_0{i + 1}", y)
    for i in range(3):  # corpo batendo no carro
        s = []
        a = K("impact-sounds", f"impactPunch_heavy_00{i}.ogg", s)
        b = K("impact-sounds", f"impactSoft_heavy_00{i + 2}.ogg", s)
        c = K("impact-sounds", f"impactPlate_medium_00{i + 2}.ogg", s)
        write(g, f"SFX_Zombie_HitCar_0{i + 1}", mix(a, b * 0.8, c * 0.5), src=ksrc(s))
    for i in range(3):  # unhas no capô: arranhões agudos com "stick-slip"
        d = rng.uniform(0.5, 0.8)
        tot = n_(d + 0.15)
        acc = np.zeros(tot)
        for k in range(3):
            n = n_(d)
            nz = rng.standard_normal(n)
            y = sum(bp(nz, f - 80, f + 80, 2) for f in rng.uniform(2200, 6500, 4))
            y *= 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rng.uniform(35, 70) * t(d)))
            acc += at(y * adsr(n, 0.03, d * 0.4), k * 0.05, tot)
        write(g, f"SFX_Zombie_Nails_0{i + 1}", acc)
    for i in range(2):  # rugido do elite: grave, sub-harmônico e muito áspero
        d = 2.2
        f = contour([(0, 60), (0.2, rng.uniform(85, 95)), (0.7, 75), (1, 50)], d)
        y = voice(d, f, [AA, RR, UH], breath=0.5, rough=1.0, rough_hz=rng.uniform(28, 36), jitter=0.07, drive=5.0,
                  sub=1.0, env=adsr(n_(d), 0.12, 0.9))
        bass = lp(saw(np.cumsum(f * 0.5) / SR), 200, 2) * adsr(n_(d), 0.1, 0.9)
        write(g, f"SFX_Zombie_EliteRoar_0{i + 1}", mix(y, bass * 0.6))

# ================================================================= HERÓI
def gen_hero():
    g = "hero"
    print("[herói]")
    for i in range(5):
        s = []
        write(g, f"SFX_Hero_Step_Dirt_0{i + 1}", K("rpg-audio", f"footstep0{i}.ogg", s), peak=0.7, src=ksrc(s))
    for i in range(4):
        s = []
        write(g, f"SFX_Hero_Step_Grass_0{i + 1}", K("impact-sounds", f"footstep_grass_00{i}.ogg", s), peak=0.7, src=ksrc(s))
        s = []
        write(g, f"SFX_Hero_Step_Sand_0{i + 1}", lp(K("impact-sounds", f"footstep_snow_00{i}.ogg", s), 5000), peak=0.7, src=ksrc(s) + " (filtrado)")
        s = []
        write(g, f"SFX_Hero_Step_Stone_0{i + 1}", K("impact-sounds", f"footstep_concrete_00{i}.ogg", s), peak=0.7, src=ksrc(s))
        s = []
        a = K("impact-sounds", f"footstep_concrete_00{(i + 1) % 5}.ogg", s)
        b = K("impact-sounds", f"impactPlate_light_00{i}.ogg", s)
        write(g, f"SFX_Hero_Step_Metal_0{i + 1}", mix(a * 0.8, b * 0.5), peak=0.7, src=ksrc(s))
        s = []
        write(g, f"SFX_Hero_Step_Wood_0{i + 1}", K("impact-sounds", f"footstep_wood_00{i}.ogg", s), peak=0.7, src=ksrc(s))
    for i in range(3):
        s = []
        cl = K("rpg-audio", f"cloth{i + 1}.ogg", s)
        br = bp(noise(0.25), 500, 2500) * adsr(n_(0.25), 0.03, 0.18) * 0.25
        write(g, f"SFX_Hero_Jump_0{i + 1}", mix(cl, br), peak=0.7, src=ksrc(s) + " + síntese")
    for i in range(2):
        s = []
        a = K("impact-sounds", f"impactSoft_medium_00{i}.ogg", s)
        b = K("impact-sounds", f"footstep_concrete_00{i + 2}.ogg", s)
        write(g, f"SFX_Hero_Land_0{i + 1}", mix(a, b * 0.7), peak=0.8, src=ksrc(s))
    for i in range(3):  # dor curta (voz masculina sintetizada, sem palavras)
        d = rng.uniform(0.25, 0.4)
        y = voice(d, glide(rng.uniform(150, 175), rng.uniform(115, 130), d), [EH, UH], breath=0.35, rough=0.15,
                  jitter=0.02, drive=1.6, env=expdecay(n_(d), 0.01, d * 0.35))
        write(g, f"SFX_Hero_Hurt_0{i + 1}", y)
    d = 1.4
    y = voice(d, contour([(0, 160), (0.25, 140), (1, 80)], d), [AA, UH, OO], breath=0.5, rough=0.25, rough_hz=12,
              jitter=0.04, drive=1.8, env=adsr(n_(d), 0.02, 1.0))
    write(g, "SFX_Hero_Death", y)
    # Vida baixa (loop): coração 100 bpm + respiração ofegante. 4,2 s = 7 batidas = 2 respirações.
    d, X = 4.2, 0.0
    n = n_(d)
    hb = np.zeros(n)
    for b in range(7):
        t0 = b * 0.6
        hb += at(np.sin(2 * np.pi * 52 * t(0.12)) * expdecay(n_(0.12), 0.004, 0.03), t0, n)
        hb += at(np.sin(2 * np.pi * 44 * t(0.11)) * expdecay(n_(0.11), 0.004, 0.025) * 0.7, t0 + 0.2, n)
    hb = lp(hb, 160, 2)
    brt = np.zeros(n)
    for b in range(2):
        t0 = b * 2.1
        inh = bp(noise(0.8), 600, 2200) * np.sin(np.pi * np.linspace(0, 1, n_(0.8))) ** 2
        exh = bp(noise(1.0), 300, 1500) * np.sin(np.pi * np.linspace(0, 1, n_(1.0))) ** 2
        brt += at(inh * 0.6, t0 + 0.05, n) + at(exh * 0.5, t0 + 0.95, n)
    y = norm(hb) + norm(brt) * 0.35
    y[:n_(0.01)] *= np.linspace(0, 1, n_(0.01))  # começo/fim em silêncio: loop sem clique
    y[-n_(0.01):] *= np.linspace(1, 0, n_(0.01))
    write(g, "SFX_Hero_LowHealth_Loop", y, peak=0.85, is_loop=True)
    for i, f in enumerate(("handleSmallLeather.ogg", "beltHandle1.ogg")):
        s = []
        write(g, f"SFX_Hero_Pickup_0{i + 1}", K("rpg-audio", f, s), peak=0.75, src=ksrc(s))
    s = []
    tot = n_(1.5)
    y = mix(at(K("rpg-audio", "cloth1.ogg", s), 0.0, tot), at(K("rpg-audio", "cloth3.ogg", s), 0.35, tot),
            at(K("rpg-audio", "cloth4.ogg", s), 0.75, tot), at(K("rpg-audio", "clothBelt.ogg", s) * 0.7, 1.05, tot))
    write(g, "SFX_Hero_Bandage", y, peak=0.75, src=ksrc(s))
    # [A-075] Fúria ativada (antes: bipe de pickup). Baque grave + sopro subindo + batida dupla do coração.
    d = 1.6
    tot = n_(d)
    x = t(d)
    boom = np.sin(2 * np.pi * np.cumsum(40 + 70 * np.exp(-x / 0.12)) / SR) * expdecay(tot, 0.003, 0.5)
    xs = np.linspace(0, 1, n_(0.9))
    whoosh = bp(noise2(0.9), 300, 5000) * xs ** 2
    whoosh = lp(whoosh, 6000) * np.sin(np.pi * xs) ** 0.5
    hb = np.zeros(tot)
    for t0 in (0.95, 1.18):
        hb += at(np.sin(2 * np.pi * 50 * t(0.14)) * expdecay(n_(0.14), 0.003, 0.04), t0, tot)
    y = mix(np.tanh(2.0 * boom), at(whoosh * 0.6, 0.05, tot), hb * 0.8)
    write(g, "SFX_Hero_Fury", y, peak=0.85)

# ================================================================= MUNDO
def gen_world():
    g = "world"
    print("[mundo]")
    # [A-075] antes: powerUp2/powerUp7 da Kenney digital-audio (bipe de videogame 8 bits, destoava do resto).
    # Agora: cápsula de energia (dois sinos FM subindo + brilho de ruído filtrado).
    for i, (m0, m1) in enumerate(((76, 83), (79, 86))):
        tot = n_(0.9)
        y = mix(at(bell(midi(m0), 0.7, ratio=2.0, index=1.2, decay=0.25), 0.0, tot),
                at(bell(midi(m1), 0.8, ratio=2.0, index=1.0, decay=0.35) * 0.8, 0.07, tot),
                at(bp(noise2(0.5), 3000, 9000) * np.linspace(1, 0, n_(0.5)) ** 2 * 0.12, 0.02, tot),
                at(np.sin(2 * np.pi * 110 * t(0.25)) * expdecay(n_(0.25), 0.003, 0.08) * 0.4, 0.0, tot))
        write(g, f"SFX_World_Pickup_0{i + 1}", y, peak=0.6)
    s = []
    write(g, "SFX_World_Pickup_Ammo", mix(K("rpg-audio", "metalClick.ogg", s), at(K("impact-sounds", "impactMetal_light_001.ogg", s) * 0.5, 0.06, n_(0.5))),
          peak=0.7, src=ksrc(s))
    # [A-075] antes: drawKnife2 (faca saindo da bainha) para QUALQUER arma, até o graveto. Agora: mão pegando
    # (couro), peso na mão (baque leve) e um clique curto de equipamento.
    s = []
    tot = n_(0.7)
    y = mix(at(K("rpg-audio", "handleSmallLeather2.ogg", s), 0.0, tot),
            at(lp(K("impact-sounds", "impactGeneric_light_001.ogg", s), 2500) * 0.5, 0.05, tot),
            at(K("rpg-audio", "metalClick.ogg", s) * 0.45, 0.16, tot))
    write(g, "SFX_World_Pickup_Weapon", y, peak=0.75, src=ksrc(s))
    s = []
    tot = n_(1.4)
    y = mix(at(K("rpg-audio", "metalLatch.ogg", s), 0, tot), at(K("rpg-audio", "creak1.ogg", s) * 0.8, 0.12, tot),
            at(K("rpg-audio", "doorOpen_1.ogg", s) * 0.5, 0.2, tot))
    write(g, "SFX_World_Chest_Open", y, src=ksrc(s))
    # Combustível: gorgolejo (bolhas subindo) + líquido.
    d = 2.0
    n = n_(d)
    y = lp(rng.standard_normal(n), 900, 2) * 0.25
    tt = 0.05
    while tt < d - 0.1:
        L = rng.uniform(0.03, 0.07)
        f0 = rng.uniform(180, 380)
        x = t(L)
        y += at(np.sin(2 * np.pi * np.cumsum(f0 * (1 + 2.5 * x / L)) / SR) * np.sin(np.pi * x / L), tt, n) * rng.uniform(0.5, 1)
        tt += rng.uniform(0.06, 0.16)
    write(g, "SFX_World_Fuel_Fill", y * adsr(n, 0.05, 0.3), peak=0.75)
    for i in range(2):
        s = []
        a = K("sci-fi-sounds", f"explosionCrunch_00{i + 2}.ogg", s)
        b = K("sci-fi-sounds", f"lowFrequency_explosion_00{i}.ogg", s)
        boom = lp(noise(1.8), 220, 2) * expdecay(n_(1.8), 0.004, 0.45)
        write(g, f"SFX_World_Barrel_Explode_0{i + 1}", mix(a, b * 0.7, norm(boom) * 0.8), src=ksrc(s) + " + síntese")
    s = []
    write(g, "SFX_World_Spikes", mix(K("rpg-audio", "knifeSlice.ogg", s), K("impact-sounds", "impactMetal_light_003.ogg", s) * 0.7,
                                     at(K("rpg-audio", "knifeSlice2.ogg", s) * 0.8, 0.08, n_(0.6))), src=ksrc(s))
    # Lago tóxico (loop 3D): bolhas graves + borbulhar.
    d, X = 6.0, 0.5
    n = n_(d + X)
    y = lp(rng.standard_normal(n), 250, 2) * 0.3 * (1 + 0.5 * smooth_noise(n, 1.5))
    tt = 0.0
    while tt < d + X - 0.2:
        L = rng.uniform(0.04, 0.12)
        f0 = rng.uniform(120, 450)
        x = t(L)
        y += at(np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.8 * x / L)) / SR) * np.sin(np.pi * x / L) ** 2, tt, n) * rng.uniform(0.3, 1)
        tt += rng.exponential(0.22)
    s = []
    sl = K("sci-fi-sounds", "slime_000.ogg", s)
    y += at(sl * 0.4, 2.0, n)
    write(g, "SFX_World_Toxic_Loop", loopify(y, X), peak=0.7, is_loop=True, src=ksrc(s) + " + síntese")
    # Portão: explosão + pedras/metal caindo.
    s = []
    tot = n_(3.0)
    y = mix(at(K("sci-fi-sounds", "explosionCrunch_004.ogg", s), 0, tot), at(K("sci-fi-sounds", "doorOpen_000.ogg", s) * 0.6, 0.15, tot))
    for k in range(10):
        y += at(K("impact-sounds", f"impactWood_heavy_00{k % 5}.ogg", None if k else s) * rng.uniform(0.2, 0.5), 0.3 + k * rng.uniform(0.1, 0.2), tot)
    write(g, "SFX_World_Gate_Open", y, src=ksrc(s) + " + síntese")
    for i in range(3):
        s = []
        write(g, f"SFX_World_Bridge_Creak_0{i + 1}", K("rpg-audio", f"creak{i + 1}.ogg", s), peak=0.7, src=ksrc(s))
    # [A-075] portas dos interiores (AJRDoor, A-076): rangido curto abrindo (0,5 s) e batida fechando (0,3 s).
    s = []
    op = pad(K("rpg-audio", "doorOpen_2.ogg", s), n_(0.5)) * adsr(n_(0.5), 0.002, 0.12)
    cr = pad(lp(K("rpg-audio", "creak1.ogg", s), 3000), n_(0.45)) * 0.45
    write(g, "SFX_World_Door_Open", mix(op, at(cr, 0.04, n_(0.5)))[:n_(0.5)], peak=0.75, src=ksrc(s))
    s = []
    cl = pad(K("rpg-audio", "doorClose_2.ogg", s), n_(0.3)) * adsr(n_(0.3), 0.001, 0.08)
    th = pad(lp(K("impact-sounds", "impactWood_medium_001.ogg", s), 2500), n_(0.3)) * 0.5
    write(g, "SFX_World_Door_Close", mix(cl, th)[:n_(0.3)], peak=0.8, src=ksrc(s))
    for i in range(2):
        s = []
        a = K("impact-sounds", f"impactWood_heavy_00{i + 2}.ogg", s)
        b = K("impact-sounds", f"impactPlank_medium_00{i}.ogg", s)
        write(g, f"SFX_World_Barricade_Break_0{i + 1}", mix(a, at(b * 0.7, 0.05, n_(1.0))), src=ksrc(s))

# ================================================================= AMBIENTE (estéreo)
def amb_wind(d):
    n = n_(d)
    def ch():
        nz = rng.standard_normal(n)
        gust = 0.55 + 0.45 * smooth_noise(n, 0.25)
        cut = 500 + 400 * (0.5 + 0.5 * smooth_noise(n, 0.4))
        lo = lp(nz, 350, 2) * gust
        hi = bp(nz, 700, 1600) * gust ** 2 * 0.35
        whistle = np.sin(2 * np.pi * np.cumsum(cut * 1.2) / SR) * 0.02 * gust ** 3
        return lo + hi + whistle
    return stereo(ch(), ch())
def amb_insects(d):
    n = n_(d)
    L, R = np.zeros(n), np.zeros(n)
    for _ in range(int(d * 2.5)):  # trinados alienígenas (FM)
        dur = rng.uniform(0.4, 2.0)
        x = t(dur)
        fc = rng.uniform(2500, 7000)
        rate = rng.uniform(18, 45)
        y = np.sin(2 * np.pi * fc * x + 3 * np.sin(2 * np.pi * rate * x)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rate * 0.5 * x)))
        y *= adsr(len(x), 0.05, dur * 0.4) * rng.uniform(0.05, 0.2)
        p = rng.uniform(0, 1)
        s0 = rng.uniform(0, d - dur)
        L += at(y * np.sqrt(1 - p), s0, n); R += at(y * np.sqrt(p), s0, n)
    for _ in range(int(d * 0.6)):  # "uuuip" descendente
        dur = rng.uniform(0.3, 0.6)
        x = t(dur)
        f = np.linspace(rng.uniform(1500, 2500), rng.uniform(500, 900), len(x))
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x / dur) ** 2 * rng.uniform(0.05, 0.12)
        p = rng.uniform(0, 1)
        s0 = rng.uniform(0, d - dur)
        L += at(y * np.sqrt(1 - p), s0, n); R += at(y * np.sqrt(p), s0, n)
    bed = hp(rng.standard_normal((2, n)), 5000) * 0.015
    return stereo(L + bed[0], R + bed[1])
def amb_plants(d):
    n = n_(d)
    x = np.arange(n) / SR
    pulse = (0.5 + 0.5 * np.sin(2 * np.pi * x / 2.0 - np.pi / 2)) ** 3  # pulso a cada 2 s
    low = np.sin(2 * np.pi * 62 * x) + 0.5 * np.sin(2 * np.pi * 93 * x)
    shim_l = sum(np.sin(2 * np.pi * f * x + rng.uniform(0, 6)) for f in (523.3, 784.0, 1046.5)) * 0.08
    shim_r = sum(np.sin(2 * np.pi * f * 1.003 * x + rng.uniform(0, 6)) for f in (523.3, 784.0, 1046.5)) * 0.08
    wob = 0.5 + 0.5 * np.sin(2 * np.pi * 0.125 * x)
    return stereo(low * pulse * 0.6 + shim_l * wob * pulse, low * pulse * 0.6 + shim_r * (1 - wob) * pulse)
def amb_ship(d):
    n = n_(d)
    x = np.arange(n) / SR
    hum = sum(np.sin(2 * np.pi * 50 * k * x) / k for k in (1, 2, 3, 5)) * (1 + 0.2 * np.sin(2 * np.pi * 0.5 * x))
    beat = np.sin(2 * np.pi * 110 * x) * np.sin(2 * np.pi * 110.5 * x)
    arcs = np.zeros(n)
    for _ in range(int(d * 0.8)):
        L = n_(rng.uniform(0.05, 0.4))
        arcs += at(hp(rng.standard_normal(L), 3000) * (rng.random(L) > 0.7) * 0.3, rng.uniform(0, d - 0.5), n)
    roar = lp(rng.standard_normal(n), 300, 2) * 0.5
    m = hum * 0.5 + beat * 0.2 + roar
    return stereo(m + arcs, m + np.roll(arcs, n_(0.013)))
def amb_spores(d):
    n = n_(d)
    def ch():
        y = bp(rng.standard_normal(n), 2000, 9000) * 0.05
        dr = np.zeros(n)
        idx = rng.integers(0, n - 200, int(d * 120))
        for p in idx:
            L = rng.integers(40, 160)
            dr[p:p + L] += rng.uniform(0.05, 0.25) * np.exp(-np.arange(L) / (L / 5)) * np.sign(rng.standard_normal(L))
        return y + bp(dr, 1500, 8000) + lp(rng.standard_normal(n), 200, 2) * 0.05
    return stereo(ch(), ch())
def gen_ambience():
    g = "ambience"
    print("[ambiente]")
    d, X = 24.0, 2.0
    for name, fn, peak in (("AMB_Valley_Wind", amb_wind, 0.7), ("AMB_Forest_Insects", amb_insects, 0.6),
                           ("AMB_Forest_PlantPulse", amb_plants, 0.6), ("AMB_Ship_Hum", amb_ship, 0.6),
                           ("AMB_Spore_Rain", amb_spores, 0.6)):
        write(g, name + "_Loop", loopify(fn(d + X), X), peak=peak, is_loop=True)
    for i in range(3):
        d = 7.0
        n = n_(d)
        y = np.zeros(n)
        for k in range(rng.integers(3, 6)):
            s0 = 0.2 + k * rng.uniform(0.3, 0.9)
            L = rng.uniform(1.5, 4.0)
            y += at(lp(noise(L), rng.uniform(120, 260), 2) * expdecay(n_(L), rng.uniform(0.05, 0.3), L * 0.3), s0, n) * rng.uniform(0.5, 1)
        write(g, f"AMB_Thunder_Distant_0{i + 1}", widen(y, 17, 0.8), peak=0.7)

# ================================================================= INTERFACE
def gen_ui():
    g = "ui"
    print("[interface]")
    for name, pack, f, pk in (("SFX_UI_Wheel_Open", "interface-sounds", "maximize_006.ogg", 0.6),
                              ("SFX_UI_Wheel_Close", "interface-sounds", "minimize_006.ogg", 0.6),
                              ("SFX_UI_Wheel_Hover", "interface-sounds", "tick_002.ogg", 0.45),
                              ("SFX_UI_Wheel_Tab", "interface-sounds", "switch_002.ogg", 0.55),
                              ("SFX_UI_Objective", "interface-sounds", "confirmation_002.ogg", 0.65),
                              ("SFX_UI_Toast", "interface-sounds", "glass_002.ogg", 0.4)):
        s = []
        write(g, name, K(pack, f, s), peak=pk, src=ksrc(s))
    # [A-075] Gasolina na reserva: antes error_005 (som de "erro" de menu). Agora: aviso de painel de carro
    # (dois toques descendo, repetidos), sem ruído.
    tot = n_(1.1)
    y = np.zeros(tot)
    for k, (f, t0) in enumerate(((988, 0.0), (740, 0.2), (988, 0.55), (740, 0.75))):
        x = t(0.18)
        tone = np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x) + 0.15 * signal.sawtooth(2 * np.pi * f * x, 0.5)
        y += at(tone * adsr(len(x), 0.004, 0.09), t0, tot)
    write(g, "SFX_UI_LowFuel", np.tanh(1.3 * y), peak=0.65)
    # Rádio: bipe de abrir, estática com "voz" ininteligível e bipe de fechar.
    d = 1.3
    n = n_(d)
    st = bp(rng.standard_normal(n), 400, 3200) * (0.4 + 0.6 * (0.5 + 0.5 * smooth_noise(n, 20)))
    cr = (rng.random(n) > 0.995) * rng.standard_normal(n) * 2
    mur = bp(saw(np.cumsum(140 * (1 + 0.2 * smooth_noise(n, 5))) / SR), 500, 2000) * (0.5 + 0.5 * smooth_noise(n, 7)) * 0.4
    y = (st * 0.5 + bp(cr, 500, 4000) + mur) * adsr(n, 0.03, 0.08)
    beep = np.sin(2 * np.pi * 1200 * t(0.07)) * adsr(n_(0.07), 0.005, 0.01) * 0.6
    y = mix(beep, at(y, 0.08, n_(d + 0.25)), at(beep * 0.8, d + 0.12, n_(d + 0.25)))
    write(g, "SFX_UI_Radio", y, peak=0.7)

# ================================================================= MÚSICA (estéreo)  [A-075] refeita
# Gerador próprio e separado (mrng): mudar a música não mexe em nenhum outro som. Tudo em numpy/scipy:
# supersaw com filtro que abre e fecha, baixo com sub, arpejo com eco pingue-pongue, bateria sintetizada
# (bumbo com clique, caixa, chimbal "808" metálico, tons), sidechain (o bumbo "abre espaço"), reverb de verdade
# (pentes + passa-tudo, estilo Freeverb) e um barramento final com compressão suave e saturação.
mrng = np.random.default_rng(7575)

def m_noise(n): return mrng.standard_normal(n)

def m_osc_saw(freq, n, phase0=None):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    ph = (mrng.uniform() if phase0 is None else phase0) + np.cumsum(f) / SR
    return saw(ph)

def m_supersaw(freq, n, voices=7, detune=0.018):
    y = np.zeros(n)
    for v in range(voices):
        d = 1 + detune * (v - (voices - 1) / 2) / max(1, (voices - 1) / 2)
        y += m_osc_saw(np.asarray(freq, float) * d, n)
    return y / voices

def sweep_lp(x, cutoff, q_order=2, block=256):
    """Passa-baixa com corte variando no tempo (blocos com estado carregado)."""
    n = len(x)
    cutoff = np.broadcast_to(np.asarray(cutoff, float), (n,))
    y = np.zeros(n)
    zi = np.zeros((1, 2))
    for s in range(0, n, block):
        fc = float(np.clip(cutoff[min(n - 1, s + block // 2)], 40, SR / 2 - 200))
        sos = signal.butter(q_order, fc, "lowpass", fs=SR, output="sos")
        if sos.shape[0] != zi.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y[s:s + block], zi = signal.sosfilt(sos, x[s:s + block], zi=zi)
    return y

def env_ad(n, a, d):
    return expdecay(n, a, d)

def env_asr(n, a, r):
    return adsr(n, a, r)

def comb_fb(x, delay_s, g, damp=0.3):
    """Pente com realimentação (y[n] = x[n] + g * lp(y[n - D])), calculado em pedaços de D amostras."""
    D = max(1, int(delay_s * SR))
    n = len(x)
    y = np.zeros(n)
    b, a = [1 - damp], [1, -damp]
    zi = np.zeros(1)
    prev = np.zeros(D)
    for s in range(0, n, D):
        e = min(n, s + D)
        fb, zi = signal.lfilter(b, a, prev[:e - s], zi=zi)
        y[s:e] = x[s:e] + g * fb
        prev = y[s:e] if e - s == D else np.pad(y[s:e], (0, D - (e - s)))
    return y

def allpass(x, delay_s, g=0.5):
    D = max(1, int(delay_s * SR))
    n = len(x)
    y = np.zeros(n)
    xp = np.zeros(D)
    yp = np.zeros(D)
    for s in range(0, n, D):
        e = min(n, s + D)
        k = e - s
        y[s:e] = -g * x[s:e] + xp[:k] + g * yp[:k]
        xp = np.pad(x[s:e], (0, D - k))
        yp = np.pad(y[s:e], (0, D - k))
    return y

def m_reverb(buf, wet=0.3, size=1.0, damp=0.35, pre_ms=12):
    """Reverb estéreo (4 pentes + 2 passa-tudo por lado, tempos diferentes em cada lado)."""
    out = buf.copy()
    pre = int(SR * pre_ms / 1000)
    combs = (0.0297, 0.0371, 0.0411, 0.0437)
    for c in range(2):
        x = np.concatenate([np.zeros(pre), buf[:, c]])[:len(buf)]
        x = hp(lp(x, 6000, 2), 120, 2)
        acc = np.zeros(len(x))
        for k, dl in enumerate(combs):
            acc += comb_fb(x, dl * size + 0.0023 * c, 0.84, damp)
        acc /= len(combs)
        for dl in (0.0051, 0.0126):
            acc = allpass(acc, dl + 0.0007 * c, 0.6)
        out[:, c] += acc * wet
    return out

def pingpong(buf, delay_s, fb=0.35, wet=0.3, tone=3000):
    """Eco pingue-pongue: L vai para R e volta."""
    D = int(delay_s * SR)
    n = len(buf)
    mono = lp((buf[:, 0] + buf[:, 1]) * 0.5, tone, 2)
    out = buf.copy()
    tap = mono.copy()
    for k in range(1, 8):
        s = D * k
        if s >= n:
            break
        g = wet * fb ** (k - 1)
        tap = lp(tap, tone, 1)
        out[s:, k % 2] += tap[:n - s] * g
    return out

def sidechain(n, hits_s, depth=0.5, release=0.18):
    g = np.ones(n)
    x = np.arange(n) / SR
    for h in hits_s:
        s = int(h * SR)
        if s >= n:
            continue
        L = min(n - s, int(release * 6 * SR))
        g[s:s + L] = np.minimum(g[s:s + L], 1 - depth * np.exp(-x[:L] / release))
    return g

def master(buf, drive=1.3, glue=0.6):
    """Compressão suave (envelope lento) + saturação + corte de graves inúteis."""
    for c in range(2):
        buf[:, c] = hp(buf[:, c], 28, 2)
    lvl = np.abs(buf).max(axis=1)
    env = signal.lfilter([0.002], [1, -0.998], lvl)
    env = env / (env.max() + 1e-9)
    gain = 1 / (1 + glue * env)
    buf = buf * gain[:, None]
    buf = np.tanh(drive * buf / (np.abs(buf).max() + 1e-9)) / np.tanh(drive)
    return buf

def m_place(buf, x, start_s, gain=1.0, pan=0.5):
    if x.ndim == 2:
        s = int(start_s * SR)
        if s >= len(buf):
            return
        m = min(len(x), len(buf) - s)
        buf[s:s + m] += x[:m] * gain
        return
    place(buf, x, start_s, gain, pan)

def place(buf, x, start_s, gain=1.0, pan=0.5):
    s = int(start_s * SR)
    if s >= len(buf):
        return
    m = min(len(x), len(buf) - s)
    buf[s:s + m, 0] += x[:m] * gain * np.sqrt(1 - pan)
    buf[s:s + m, 1] += x[:m] * gain * np.sqrt(pan)

# ---- instrumentos
def i_pad(notes, dur, cutoff=(500, 2200), attack=1.5, release=1.5, voices=7, detune=0.016, wide=True):
    """Pad estéreo: supersaw por nota, filtro que abre no ataque e fecha devagar, um seno quente por baixo."""
    n = n_(dur)
    L, R = np.zeros(n), np.zeros(n)
    for m in notes:
        f = midi(m)
        L += m_supersaw(f, n, voices, detune) + 0.35 * np.sin(2 * np.pi * f * np.arange(n) / SR)
        R += m_supersaw(f * 1.0015, n, voices, detune) + 0.35 * np.sin(2 * np.pi * f * 1.0015 * np.arange(n) / SR + 1.3)
    xs = np.linspace(0, 1, n)
    cut = cutoff[0] + (cutoff[1] - cutoff[0]) * np.sin(np.pi * np.clip(xs * 1.3, 0, 1)) ** 2
    e = env_asr(n, attack, release)
    L, R = sweep_lp(L, cut) * e, sweep_lp(R, cut * 1.03) * e
    if not wide:
        L = R = (L + R) * 0.5
    return stereo(L, R) / max(1, len(notes))

def i_sub(m, dur, attack=0.05, release=0.3, grit=0.15):
    n = n_(dur)
    x = np.arange(n) / SR
    f = midi(m)
    y = np.sin(2 * np.pi * f * x) + grit * lp(m_osc_saw(f, n), 400, 2)
    return y * env_asr(n, attack, release)

def i_pluck(m, dur=0.5, bright=3500, decay=0.22, detune=0.004):
    n = n_(dur)
    f = midi(m)
    y = m_osc_saw(f, n) + m_osc_saw(f * (1 + detune), n) + 0.5 * signal.square(2 * np.pi * f * 0.5 * np.arange(n) / SR)
    cut = 250 + bright * np.exp(-np.arange(n) / SR / (decay * 0.6))
    return sweep_lp(y * 0.4, cut) * env_ad(n, 0.003, decay)

def i_glass(m, dur=2.5, vib=0.004):
    """Lead de vidro (FM leve + vibrato que entra devagar)."""
    n = n_(dur)
    x = np.arange(n) / SR
    f = midi(m) * (1 + vib * np.sin(2 * np.pi * 5.2 * x) * np.clip(x / 0.6, 0, 1))
    ph = np.cumsum(f) / SR
    mod = 1.2 * np.exp(-x / 0.8) * np.sin(2 * np.pi * ph * 3.0)
    y = np.sin(2 * np.pi * ph + mod) + 0.25 * np.sin(4 * np.pi * ph)
    return y * env_asr(n, 0.03, dur * 0.55)

def i_theremin(m0, m1, dur):
    n = n_(dur)
    x = np.arange(n) / SR
    f = midi(m0) * (midi(m1) / midi(m0)) ** (np.clip(x / dur, 0, 1) ** 1.5)
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 6.0 * x))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return y * np.sin(np.pi * np.clip(x / dur, 0, 1)) ** 1.5

def i_brass(notes, dur, attack=0.12, bright=2600):
    n = n_(dur)
    y = sum(m_supersaw(midi(m), n, 5, 0.008) for m in notes) / max(1, len(notes))
    cut = 400 + bright * (1 - np.exp(-np.arange(n) / SR / attack)) * np.exp(-np.arange(n) / SR / (dur * 1.5))
    return np.tanh(1.6 * sweep_lp(y, cut)) * env_asr(n, attack * 0.6, min(0.4, dur * 0.4))

def d_kick(dur=0.45, f_hi=150, f_lo=44, punch=0.12):
    n = n_(dur)
    x = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-x / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.001, 0.22)
    click = hp(m_noise(n), 3000) * env_ad(n, 0.0003, 0.004) * punch * 4
    return np.tanh(1.4 * (body + click))

def d_snare(dur=0.32, tone=185):
    n = n_(dur)
    x = np.arange(n) / SR
    body = (np.sin(2 * np.pi * tone * x) + 0.5 * np.sin(2 * np.pi * tone * 1.6 * x)) * env_ad(n, 0.001, 0.06)
    nz = bp(m_noise(n), 1800, 9000) * env_ad(n, 0.001, 0.12)
    return body * 0.7 + nz

def d_clap(dur=0.3):
    n = n_(dur)
    y = np.zeros(n)
    for k, dt in enumerate((0.0, 0.011, 0.023, 0.034)):
        y += at(bp(m_noise(n_(0.2)), 900, 5000) * env_ad(n_(0.2), 0.0005, 0.012 if k < 3 else 0.09), dt, n)
    return y

def d_hat(dur=0.08, open_=False):
    """Chimbal metálico: 6 ondas quadradas em razões inarmônicas (como na 808) + passa-alta."""
    n = n_(dur)
    x = np.arange(n) / SR
    y = sum(signal.square(2 * np.pi * f * x) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
    y = hp(bp(y, 6000, 15000), 7000)
    return y * env_ad(n, 0.0005, 0.16 if open_ else 0.025)

def d_shaker(dur=0.1):
    n = n_(dur)
    return bp(m_noise(n), 5000, 12000) * env_asr(n, 0.02, 0.06)

def d_tom(f, dur=0.5):
    n = n_(dur)
    x = np.arange(n) / SR
    ff = f * (1 + 0.5 * np.exp(-x / 0.06))
    return (np.sin(2 * np.pi * np.cumsum(ff) / SR) + 0.2 * bp(m_noise(n), 200, 2000) * env_ad(n, 0.001, 0.03)) * env_ad(n, 0.002, 0.25)

def d_crash(dur=2.5):
    n = n_(dur)
    x = np.arange(n) / SR
    y = sum(signal.square(2 * np.pi * f * x) for f in (311.0, 422.0, 537.0, 691.0, 863.0, 1103.0)) * 0.15
    y = hp(y + m_noise(n) * 0.8, 4000)
    return y * env_ad(n, 0.002, 0.9)

def fx_riser(dur, f0=300, f1=6000):
    n = n_(dur)
    xs = np.linspace(0, 1, n)
    nz = m_noise(n)
    cut = f0 * (f1 / f0) ** (xs ** 2)
    return sweep_lp(nz, cut) * xs ** 2

def fx_hit(dur=2.0):
    n = n_(dur)
    x = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-x / 0.08)) / SR) * env_ad(n, 0.002, 0.7)
    return np.tanh(2 * boom) + lp(m_noise(n), 900, 2) * env_ad(n, 0.002, 0.25) * 0.5

def loop_buf(d, X):
    return np.zeros((n_(d + X), 2))

def music_explore():
    """Exploração (vale alienígena): 72 bpm, 16 compassos, Ré menor dórico. Pad que respira, baixo quente,
    arpejo com eco, tema de vidro e um teremim alienígena de vez em quando; percussão leve na 2a metade."""
    bpm, bars = 72, 16
    beat = 60 / bpm
    bar = 4 * beat
    d = bars * bar
    X = 4.0
    buf = loop_buf(d, X)
    prog = [  # (acorde do pad, baixo) a cada 2 compassos
        ([62, 65, 69, 72, 76], 38),   # Dm9
        ([58, 62, 65, 69, 72], 34),   # Bbmaj7 (add9)
        ([60, 64, 65, 69, 72], 41),   # Fmaj7/C
        ([60, 62, 67, 69, 74], 36),   # C6/9
        ([62, 65, 69, 72, 76], 38),   # Dm9
        ([58, 62, 64, 69, 72], 34),   # Bbmaj7#11
        ([55, 58, 62, 65, 69], 31),   # Gm9
        ([57, 61, 64, 67, 69], 33),   # A7sus -> A7 (puxa para o Dm do começo do loop)
    ]
    kicks = []
    for i, (chord, root) in enumerate(prog + prog[:1]):
        t0 = i * 2 * bar
        m_place(buf, i_pad(chord, 2 * bar + 2.0, cutoff=(450, 1900 if i % 4 else 2600), attack=1.2, release=2.0), t0, 0.55)
        for k, (off, ln) in enumerate(((0, 3), (3, 1), (4, 2.5), (6.5, 1.5))):
            m_place(buf, i_sub(root, ln * beat + 0.2, 0.04, 0.35), t0 + off * beat, 0.45 if k == 0 else 0.32)
        if i >= 1:
            arp = sorted(chord) + [chord[1] + 12, chord[2] + 12]
            for s8 in range(16):
                m = arp[(s8 * 3) % len(arp)] + (12 if s8 % 8 >= 6 else 0)
                bright = 1200 + 2600 * (i / len(prog))
                m_place(buf, i_pluck(m, 0.45, bright, 0.2), t0 + s8 * beat / 2, 0.11 if s8 % 2 else 0.15,
                        0.3 if s8 % 4 < 2 else 0.7)
        if i >= 4:  # percussão leve
            for b4 in range(8):
                tt = t0 + b4 * beat
                if b4 % 4 == 0:
                    m_place(buf, d_kick(0.4, 110, 42, 0.05), tt, 0.33)
                    kicks.append(tt)
                if b4 % 4 == 3:
                    m_place(buf, d_clap(), tt, 0.07, 0.6)
                for s16 in range(4):
                    m_place(buf, d_shaker(), tt + s16 * beat / 4, 0.035 if s16 % 2 else 0.055, 0.75)
    # tema (compassos 5 a 8 e 13 a 16): frase de pergunta e resposta
    theme = [(0, 69, 1.5), (1.5, 72, 0.5), (2, 74, 1.0), (3, 72, 1.0), (4, 69, 2.0), (6, 67, 1.0), (7, 65, 1.0),
             (8, 64, 1.5), (9.5, 65, 0.5), (10, 67, 1.0), (11, 69, 1.0), (12, 62, 3.0)]
    for start_bar in (4, 12):
        for (bt, m, ln) in theme:
            m_place(buf, i_glass(m + 12, ln * beat + 1.2), start_bar * bar + bt * beat, 0.16, 0.42)
    for tb, (m0, m1) in ((2.5, (86, 81)), (9.25, (81, 88)), (14.5, (88, 79))):
        m_place(buf, i_theremin(m0, m1, 2.6), tb * bar, 0.06, 0.15 if tb < 9 else 0.85)
    sc = sidechain(len(buf), kicks, 0.18, 0.2)
    buf *= sc[:, None]
    buf = pingpong(buf, beat * 0.75, 0.38, 0.22, 2800)
    buf = m_reverb(buf, 0.42, 1.25, 0.45)
    return loopify(master(buf, 1.15, 0.5), X)  # emenda por último (sem clique)

def music_tension():
    """Tensão (zumbis por perto): 100 bpm, 12 compassos, Ré frígio. Ostinato de semicolcheias (cordas sintéticas),
    tambor grave tipo batida de coração, cluster dissonante que cresce, relógio metálico e sopros de subida."""
    bpm, bars = 100, 12
    beat = 60 / bpm
    bar = 4 * beat
    d = bars * bar
    X = 1.2
    buf = loop_buf(d, X)
    roots = [38, 38, 39, 38, 38, 38, 41, 39, 38, 38, 39, 37]
    kicks = []
    for b in range(bars + 1):
        r = roots[b % bars]
        t0 = b * bar
        pat = [0, 0, 12, 0, 0, 1, 0, 12, 0, 0, 12, 0, 3, 1, 0, 12]
        for s16 in range(16):
            acc = 1.0 if s16 % 4 == 0 else 0.6
            m_place(buf, i_pluck(r + 12 + pat[s16], 0.22, 900 + 900 * (b % 4) / 3, 0.09, 0.006), t0 + s16 * beat / 4,
                    0.16 * acc, 0.35 if s16 % 2 else 0.65)
        m_place(buf, i_sub(r, bar + 0.1, 0.02, 0.2, 0.35), t0, 0.32)
        for hb in (0.0, 0.42, 2.0, 2.42):  # "tum-tum" do coração
            m_place(buf, d_tom(52, 0.5), t0 + hb * beat, 0.42 if hb in (0.0, 2.0) else 0.28)
            if hb in (0.0, 2.0):
                kicks.append(t0 + hb * beat)
        for e in range(8):
            m_place(buf, d_hat(0.04), t0 + e * beat / 2 + beat / 4, 0.045, 0.8)
        if b % 4 == 0:
            m_place(buf, i_pad([r + 24, r + 25, r + 31, r + 36], 4 * bar + 1.0, cutoff=(300, 2600), attack=3.0, release=1.5,
                               detune=0.022), t0, 0.32)
        if b >= 4:  # cordas agudas trêmulas
            n = n_(bar + 0.3)
            trem = 0.6 + 0.4 * np.sin(2 * np.pi * 11.5 * np.arange(n) / SR)
            hi = i_pad([r + 36, r + 39], bar + 0.3, cutoff=(1500, 4500), attack=0.3, release=0.3, voices=5) * trem[:, None]
            m_place(buf, hi, t0, 0.12)
        if b % 4 == 2:
            m_place(buf, stereo(*(fx_riser(2 * bar, 200, 7000) for _ in range(2))), t0, 0.06)
        if b % 4 == 0 and b > 0:
            m_place(buf, stereo(*(fx_hit(2.0) for _ in range(2))), t0, 0.35)
    sc = sidechain(len(buf), kicks, 0.3, 0.15)
    buf *= sc[:, None]
    buf = pingpong(buf, beat * 0.5, 0.3, 0.12, 2200)
    buf = m_reverb(buf, 0.3, 1.0, 0.4)
    return loopify(master(buf, 1.3, 0.6), X)  # emenda por último (sem clique)

def music_horde():
    """Horda: 140 bpm, 16 compassos, Ré frígio. Bateria cheia (bumbo, caixa com clap, chimbal, viradas de tom,
    pratos), baixo distorcido em riff, acordes de força pesados com sidechain e metais de alarme."""
    bpm, bars = 140, 16
    beat = 60 / bpm
    bar = 4 * beat
    d = bars * bar
    X = 0.6
    buf = loop_buf(d, X)
    riff = [0, 0, 12, 0, 1, 0, 0, 12, 0, 0, 3, 0, 1, 0, 13, 12]
    chords = [(38, 0), (38, 0), (41, 3), (39, 1)]  # Ré, Ré, Fá, Mi bemol (por compasso, em ciclos de 4)
    kicks = []
    for b in range(bars + 1):
        t0 = b * bar
        root, _ = chords[(b // 2) % 4]
        last_of_4 = b % 4 == 3
        for s16 in range(16):
            tt = t0 + s16 * beat / 4
            if s16 in (0, 3, 6, 8, 10, 11) and not (last_of_4 and s16 >= 12):
                m_place(buf, d_kick(0.4, 170, 45, 0.18), tt, 0.62)
                kicks.append(tt)
            if s16 in (4, 12) and not (last_of_4 and s16 == 12):
                m_place(buf, d_snare(), tt, 0.4, 0.48)
                m_place(buf, d_clap(), tt, 0.16, 0.52)
            if not (last_of_4 and s16 >= 12):
                m_place(buf, d_hat(0.06, open_=(s16 % 8 == 6)), tt, 0.06 if s16 % 2 else 0.09, 0.72)
            bass = np.tanh(3.5 * i_pluck(root - 12 + riff[s16], 0.18, 1600, 0.1, 0.01))
            m_place(buf, bass, tt, 0.3, 0.5)
            m_place(buf, i_sub(root - 12 + (0 if riff[s16] in (0, 12) else riff[s16] % 12), 0.16, 0.003, 0.05, 0.0), tt, 0.25)
        if last_of_4:
            for k, f in enumerate((240, 200, 165, 130)):
                m_place(buf, d_tom(f, 0.4), t0 + (3 + k * 0.25) * beat, 0.4, 0.25 + 0.17 * k)
        if b % 4 == 0:
            m_place(buf, stereo(d_crash(), d_crash()), t0, 0.22)
        # acordes de força (quinta + oitava) em colcheias abafadas, guitarra sintética distorcida
        for e in range(8):
            if last_of_4 and e >= 6:
                continue
            n = n_(beat / 2 * 0.9)
            y = sum(m_supersaw(midi(m), n, 3, 0.01) for m in (root, root + 7, root + 12))
            y = np.tanh(4 * lp(y, 1700 if e % 2 else 2400, 2)) * env_ad(n, 0.002, 0.12)
            m_place(buf, stereo(y, np.roll(y, n_(0.012))), t0 + e * beat / 2, 0.17)
        if b % 2 == 1:  # metais de alarme
            m_place(buf, stereo(*(i_brass([root + 24, root + 31, root + 37], beat * 1.5) for _ in range(2))),
                    t0 + 2.5 * beat, 0.22)
    sc = sidechain(len(buf), kicks, 0.35, 0.09)
    buf *= sc[:, None]
    buf = m_reverb(buf, 0.18, 0.8, 0.5)
    return loopify(master(buf, 1.6, 0.8), X)  # emenda por último (sem clique)

def music_victory():
    """Vitória (~7 s): Sol, Lá, Ré maior com metais crescendo, arpejo brilhante, prato e um "boom" no acorde final."""
    d = 7.5
    buf = np.zeros((n_(d), 2))
    seq = [(0.0, [55, 59, 62, 67], 43), (0.9, [57, 61, 64, 69], 45), (1.8, [62, 66, 69, 74, 78], 38)]
    for k, (t0, ch, bs) in enumerate(seq):
        ln = 0.95 if k < 2 else 5.0
        m_place(buf, stereo(*(i_brass(ch, ln, 0.08, 3200) for _ in range(2))), t0, 0.36)
        m_place(buf, i_sub(bs, ln, 0.01, 0.6 if k < 2 else 2.5), t0, 0.5)
    for k, m in enumerate((74, 78, 81, 86, 90, 93, 98)):
        m_place(buf, i_glass(m, 2.2, 0.0), 1.8 + 0.07 * k, 0.12, 0.2 + 0.1 * k)
    m_place(buf, stereo(fx_riser(1.8, 400, 9000), fx_riser(1.8, 400, 9000)), 0.0, 0.08)
    m_place(buf, stereo(d_crash(3.5), d_crash(3.5)), 1.8, 0.3)
    m_place(buf, stereo(fx_hit(2.5), fx_hit(2.5)), 1.8, 0.4)
    m_place(buf, d_kick(0.5, 120, 40, 0.1), 1.8, 0.6)
    buf = m_reverb(buf, 0.45, 1.3, 0.35)
    return master(buf, 1.1, 0.4)

def music_defeat():
    """Derrota (~7 s): sino grave dobrando, linha que desce (Ré, Dó, Si bemol, Lá) sobre pad desafinado e um
    zumbido que some."""
    d = 7.5
    buf = np.zeros((n_(d), 2))
    for k, m in enumerate((74, 72, 70, 69)):
        m_place(buf, i_glass(m, 2.4, 0.006), 0.55 * k, 0.17, 0.38 + 0.08 * k)
    m_place(buf, i_pad([50, 53, 57, 62], 6.8, cutoff=(800, 300), attack=0.2, release=3.5, detune=0.03), 0.0, 0.5)
    m_place(buf, i_pad([46, 50, 53, 58], 4.5, cutoff=(500, 250), attack=1.5, release=3.0, detune=0.035), 1.6, 0.35)
    for k in range(3):
        m_place(buf, bell(midi(38), 3.0, ratio=1.41, index=2.0, decay=1.6), 0.1 + 1.6 * k, 0.32 - 0.07 * k)
    drone = i_sub(26, 6.5, 0.4, 3.5, 0.3)
    m_place(buf, drone, 0.2, 0.45)
    buf = m_reverb(buf, 0.5, 1.4, 0.5)
    return master(buf, 1.05, 0.4)

def gen_music():
    g = "music"
    print("[música]")
    write(g, "MUS_L01_Explore_Loop", music_explore(), peak=0.8, is_loop=True)
    write(g, "MUS_L01_Tension_Loop", music_tension(), peak=0.8, is_loop=True)
    write(g, "MUS_L01_Horde_Loop", music_horde(), peak=0.85, is_loop=True)
    write(g, "MUS_Stinger_Victory", music_victory(), peak=0.8)
    write(g, "MUS_Stinger_Defeat", music_defeat(), peak=0.8)

# ================================================================= créditos
def write_credits():
    for g, rows in CREDITS.items():
        p = os.path.join(OUT, g, "CREDITS.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"# Créditos de áudio: {g}\n\n")
            f.write("Gerado por `tools/pipeline/gen_game_audio.py` (A-061). Kenney: CC0 1.0 (domínio público; crédito "
                    "opcional, feito aqui por cortesia). Originais em `assets/raw/audio/kenney/*.zip`.\n\n")
            f.write("| Arquivo | Origem | Licença |\n|---|---|---|\n")
            for name, src, lic in rows:
                f.write(f"| {name} | {src} | {lic} |\n")

def main():
    kenney_extract()
    try:
        gen_vehicle(); gen_zombie(); gen_hero(); gen_world(); gen_ambience(); gen_ui(); gen_music()
        write_credits()
    finally:
        shutil.rmtree(KDIR, ignore_errors=True)
    total = sum(os.path.getsize(p) for p in glob.glob(os.path.join(OUT, "*", "*.wav")))
    print(f"total em {OUT}: {total / 1e6:.1f} MB")

if __name__ == "__main__":
    main()
