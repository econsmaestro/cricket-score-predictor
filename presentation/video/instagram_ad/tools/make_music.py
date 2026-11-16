#!/usr/bin/env python3
"""Original synthesised background track for the ad (128 BPM, ~31 s). No samples, no AI model, no third-party music.
Writes assets/music_original.wav. Replace it with licensed Instagram audio if you prefer."""
import numpy as np, wave, pathlib, sys
SR = 44100; BPM = 128; B = 60 / BPM; BEATS = 66; N = int((BEATS * B + 1.0) * SR)
out = pathlib.Path(__file__).resolve().parent.parent / "assets" / "music_original.wav"
rng = np.random.default_rng(7); mix = np.zeros(N)
def add(sig, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i < N: mix[i:j] += g * sig[:j - i]
def env(n, a=.002, d=.2): t = np.arange(n) / SR; return np.minimum(t / a, 1) * np.exp(-t / d)
def kick():
    n = int(.32 * SR); t = np.arange(n) / SR; f = 45 + 110 * np.exp(-t * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, .001, .11) * 1.0
def clap():
    n = int(.22 * SR); x = rng.standard_normal(n); x = x - np.convolve(x, np.ones(30) / 30, 'same'); return x * env(n, .001, .05) * .5
def hat(o=False):
    n = int((.18 if o else .05) * SR); x = rng.standard_normal(n); x = x - np.convolve(x, np.ones(8) / 8, 'same'); return x * env(n, .0005, .05 if o else .015) * .22
def tone(f, n, kind='tri'):
    t = np.arange(n) / SR; ph = (f * t) % 1
    return (2 * np.abs(2 * ph - 1) - 1) if kind == 'tri' else (2 * ph - 1)
chords = [(55.0, [220.0, 261.63, 329.63]), (43.65, [174.61, 220.0, 261.63]), (65.41, [261.63, 329.63, 392.0]), (49.0, [196.0, 246.94, 293.66])]  # Am F C G
for b in range(BEATS):
    t0 = b * B; bar, beat_in_bar = divmod(b, 4); root, tones = chords[bar % 4]
    hook = b < 7                                     # first 7 beats: stripped back so the visual hook lands
    if b >= 2 or b == 0: add(kick(), t0, .95 if b >= 2 else .5)
    if b >= 4 and beat_in_bar in (1, 3): add(clap(), t0, 1.0)
    if b >= 2:
        add(hat(), t0 + B / 2, 1.0)
        if b >= 7: add(hat(), t0 + B / 4, .6); add(hat(), t0 + 3 * B / 4, .6)
    if b >= 7:                                       # bass on 8ths, ducked by the kick
        for k in range(2):
            n = int(B / 2 * SR); s = np.sin(2 * np.pi * root * 2 * np.arange(n) / SR) * env(n, .004, .18) * .55
            add(s, t0 + k * B / 2, 1.0)
    if b >= 7:                                       # soft 16th arp
        for k in range(4):
            f = tones[(beat_in_bar * 4 + k) % 3] * (2 if k % 2 else 1); n = int(B / 4 * SR)
            add(tone(f, n) * env(n, .003, .09) * .13, t0 + k * B / 4, 1.0)
    if beat_in_bar == 0 and b >= 41:                 # pad swell for the "more than" and CTA sections
        n = int(4 * B * SR); t = np.arange(n) / SR; p = sum(np.sin(2 * np.pi * f * t) for f in tones) * .06
        add(p * np.minimum(t / .5, 1) * np.minimum((n / SR - t) / .6, 1), t0, 1.0)
# riser into the call to action and an impact on its first beat
rn = int(2 * B * SR); r = rng.standard_normal(rn); t = np.arange(rn) / SR
r = (r - np.convolve(r, np.ones(40) / 40, 'same')) * (t / t[-1]) ** 2 * .35; add(r, 53 * B, 1.0)
imp = int(.9 * SR); ti = np.arange(imp) / SR; add(np.sin(2 * np.pi * 52 * ti) * np.exp(-ti * 4) * .9, 55 * B, 1.0)
# gentle limiter, fade out
mix = np.tanh(mix * 1.1); fade = int(1.4 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
mix = mix / np.max(np.abs(mix)) * .89
pcm = (np.stack([mix, np.roll(mix, int(.0004 * SR))], 1) * 32767).astype('<i2')
out.parent.mkdir(exist_ok=True)
with wave.open(str(out), 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', out, f'{N / SR:.1f}s')
