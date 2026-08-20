# stem-lab

Local CLI for **full-band stem extraction** and remix sessions.

No GUI. No cloud API. Audio never leaves your machine, and it is never committed to git.

This is the general-purpose successor to [drum-separator](https://github.com/bcharleson/drum-separator) (drums-only). Use **4 or 6 stems** when you want the rest of the band, not just a drumless backing track.

## Stems

| `--stems` | Model (default) | Files |
|-----------|-----------------|-------|
| `4` (default) | `htdemucs` | `vocals` `drums` `bass` `other` |
| `6` | `htdemucs_6s` | + `guitar` `piano` |
| `2` | `htdemucs` | `drums` `no_drums` |

`htdemucs_ft` is a slower, higher-quality 4-stem option: `--stems 4 --model htdemucs_ft`.

## Setup

Requires Python 3.10+ and [ffmpeg](https://ffmpeg.org/).

```bash
git clone https://github.com/bcharleson/stem-lab.git
cd stem-lab
./scripts/install.sh
./bin/stem-lab doctor
```

`install.sh` creates `.venv` and installs [Demucs](https://github.com/facebookresearch/demucs). The first extract downloads model weights (~80MB+).

If `demucs` is already on your `PATH`, you can skip the install script and run `./bin/stem-lab` from this checkout.

## Session layout

Originals, stems, and remixes live under `work/` (gitignored):

```
work/<artist>/<song>/
  source/          original recording
  stems/<model>/   extracted stems
  remixes/         rebuilt mixes
  session.json     relative paths only
```

```bash
stem-lab ingest ./demo.m4a --artist example-artist --title demo-song
stem-lab extract --artist example-artist --title demo-song --stems 4
stem-lab mix --artist example-artist --title demo-song --mute vocals
```

One-shot (no session), writes to `./output/`:

```bash
stem-lab extract ./demo.m4a --stems 4
```

## Mix

```bash
# Instrumental
stem-lab mix --artist example-artist --title demo-song --mute vocals

# Rhythm section only
stem-lab mix --artist example-artist --title demo-song --solo drums bass -o drums-bass.wav
```

## Acoustic country (keep the original vocal)

Requires `librosa` (`pip install librosa` in the venv). Detects chords from bass + `other`, renders a time-locked acoustic guitar, and mixes it under the original vocal. Drums and bass stay; the original guitar/`other` stem is left out.

```bash
stem-lab accompany --artist example-artist --title demo-song --style country-acoustic
# → remixes/country-acoustic.wav

stem-lab accompany --artist example-artist --title demo-song --style dirty-heads
# → remixes/dirty-heads.wav  (offbeat reggae skank, bass-forward, original vocal)
```

## Library

```bash
stem-lab lib          # print the work directory
```

Override with `STEM_LAB_WORK` (absolute or `~/…`). Do not hardcode a machine-specific home path in config you plan to commit.

## JSON

Every command accepts `--json` for scripts and agents.

## What this is not

- Not a drum-module / hardware manager.
- Not a hosting or sharing tool. Keep `work/` local.

## License

MIT
