# Handoff — stem-lab

Living reference for transferring this project and the active session. Last updated **2026-08-20**.

## What this is

Public CLI for **full-band stem extraction and remix sessions** (Demucs 2/4/6 stems, mix rebuild, country/reggae accompaniment). Audio never belongs in git.

Repo: https://github.com/bcharleson/stem-lab  
Local: `~/Developer/stem-lab`

## Do not touch

| Path | Why |
|------|-----|
| `~/Developer/vdrums-td716` | Roland **TD-716 / V71** hardware desk only (firmware, SD, Editor, `vdrums strip` for kit play-along). Not a remixer. |
| [bcharleson/drum-separator](https://github.com/bcharleson/drum-separator) | Older drums-only Demucs CLI. Candidate to **archive** once stem-lab extract is the default. Do not grow it. |
| `ai-genre-remix` YouTube factory | Country'ai / Ragg'ai upload pipeline. Steal Suno bits only. |

## Transfer checklist

`work/` is **gitignored**. Cloning the GitHub repo is not enough.

1. Clone `stem-lab` (public).
2. Copy `work/` privately (source audio, stems, remixes, lyrics, Suno MP3s).
3. Copy `.cache/MuseScore_General.sf3` if you need FluidSynth country guitar (~38MB, gitignored).
4. Suno: the org key lives in `~/Documents/DeveloperProjects/ai-genre-remix/.env` (official suno.com key is empty). Do not commit secrets.
5. Demucs: either `./scripts/install.sh` or reuse an existing `demucs` on `PATH` (this machine uses the vdrums venv binary — do not hardcode that path in the repo).
6. Country produce extras: `ffmpeg`, `librosa`, `pretty_midi`, `brew install fluid-synth`.

```bash
cd ~/Developer/stem-lab
./bin/stem-lab doctor
```

## Layout

```
~/Developer/stem-lab/          public CLI (this repo)
  src/stemlab/                 extract, mix, guitar, produce, CLI
  work/                        LOCAL ONLY — gitignored
    <artist>/<song>/
      source/                  original
      stems/htdemucs/          raw 4-stem split
      stems/balanced/          LUFS-matched vocals/drums/bass
      stems/generated/         MIDI / sampled guitar
      remixes/                 mixes + suno/
      lyrics.txt               Whisper transcript
      lyrics-suno.txt          cleaned lyrics for Custom mode
      session.json             relative paths only
  .cache/                      soundfonts (gitignored)
```

Override library root with `STEM_LAB_WORK`. Never commit a machine-specific home path.

## CLI

```bash
./bin/stem-lab doctor
./bin/stem-lab ingest FILE --artist NAME --title TITLE
./bin/stem-lab extract --artist NAME --title TITLE --stems 4
./bin/stem-lab mix --artist NAME --title TITLE --mute vocals
./bin/stem-lab accompany --artist NAME --title TITLE --style country-acoustic
./bin/stem-lab accompany --artist NAME --title TITLE --style dirty-heads
./bin/stem-lab lib
```

`--stems 4` → vocals, drums, bass, other  
`--stems 6` → + guitar, piano (`htdemucs_6s`)  
`--stems 2` → drums + no_drums  

Country `accompany` calls `produce_country()`: balance stems to target LUFS, render **steel acoustic** via FluidSynth, EQ/comp/reverb/limiter, keep original vocal. Dirty-heads still uses synthesized offbeat skank (not production-ready).

## Active session — Zach Peterson, “I Wanna Be”

Friend sent a complete demo mix (country vibe, distorted guitar he couldn’t shake, proud of drum fills). Goal: **finished acoustic-country song**. He will compensate time. Original vocal is his.

**Source:** `work/zach-peterson/i-wanna-be/source/I Wanna Be - EQ - 4-24-24.m4a`  
~3:19, AAC 44.1 kHz stereo. Ingested from `~/Downloads/I Wanna Be - EQ - 4:24:24.m4a` (colon stripped in the copy).

**Analysis:** ~**86 BPM**, key **G** (G / Em / C / D country I–vi–IV–V).

### Stem loudness (why early mixes failed)

Raw Demucs `stems/htdemucs/`:

| Stem | Integrated LUFS | Problem |
|------|-----------------|--------|
| bass | −15.6 | ~7 dB hotter than the vocal |
| vocals | −22.5 | too quiet vs bass |
| other (guitar) | −25.1 | distorted guitar |
| drums | −27.5 | quiet vs bass |

Balanced copies in `stems/balanced/`: vocals −18, drums −21, bass −21.

### What we tried (and the verdict)

| File | Verdict |
|------|---------|
| `remixes/dirty-heads.wav` | Skip. Unbalanced, not production-ready. |
| Karplus-Strong acoustic (first country) | Skip. Sounds like a synth pluck. |
| `remixes/country-acoustic.wav` | Better: FluidSynth steel guitar + LUFS balance + mix chain, **his vocal kept**. Still MIDI-stiff, not a finished record. |
| **`remixes/suno/i-wanna-be-suno-country-2.mp3`** | **Current deliverable.** Full Suno V5 song, ~3:20, acoustic country, his lyrics. Suno’s singer, not Zach. |
| `remixes/suno/i-wanna-be-suno-country-1.mp3` | Alternate take, ~2:28. |

Play:

```bash
open work/zach-peterson/i-wanna-be/remixes/suno/i-wanna-be-suno-country-2.mp3
open work/zach-peterson/i-wanna-be/remixes/suno/i-wanna-be-suno-country-1.mp3
```

Suno metadata / task JSON: `work/zach-peterson/i-wanna-be/remixes/suno/` (gitignored). Files expire on Suno’s side after ~15 days; local MP3s are the keepers.

## Suno CLI (finished songs)

There is no `suno` binary on PATH. Use **SunoAPI.org** from `ai-genre-remix`:

- Client: `~/Documents/DeveloperProjects/ai-genre-remix/src/music/suno_api_org_client.py`
- Wrapper: `scripts/test_sunoapi_org.py` (treats `prompt` as lyrics in custom mode — pass **actual lyrics**, not a “transform this song” blurb)
- Auth: org key in that project’s `.env` (name starts with `SUNOAPI_ORG_`)
- Generate: `POST https://api.sunoapi.org/api/v1/generate`
- Status: `GET /api/v1/generate/record-info?taskId=` (not `/api/v1/generate/{id}`)
- Credits: `GET /api/v1/get-credits` (the old `/api/v1/account/credits` 404s)
- Each generate returns **two** songs. Response tracks live at `data.response.data[]` with `audioUrl`.
- Models: V5 used. V5_5 supports `duration` in custom mode.
- `vocalGender`: `m`. `negativeTags` used to kill distorted guitar / EDM / autotune.

Lyrics for Custom mode: `work/zach-peterson/i-wanna-be/lyrics-suno.txt` (Whisper on the vocal stem, then light ASR cleanup). Raw transcript: `lyrics.txt`.

Style tags used:

```
acoustic country, traditional country, steel guitar, acoustic guitar,
live band, warm analog production, storytelling male vocals, 85 bpm,
intimate, organic, porch-song, no autotune
```

## Decisions

- **Keep vdrums and stem-lab separate.** Kit play-along stays in vdrums.
- **Public repo, private audio.** `.gitignore` blocks `work/**`, `*.wav`/`*.mp3`/`*.m4a`, `.cache/`, soundfonts. CI: `scripts/check-oss.sh`.
- Direction for this song: **acoustic country**, not reggae.
- Stem-lab cannot produce a “finished record” by itself. Suno is the finished-song tool. Stem-lab is for split / balance / vocal-on-top experiments.

## Next (if continuing this song)

1. Listen to Suno take **2** vs **1**; pick one.
2. If he must hear **his** voice: Suno **upload-and-cover** of the original m4a, or generate a Suno **instrumental** and mix `stems/balanced/vocals.wav` on top.
3. Optional 6-stem extract if guitar isolation still matters.
4. Archive `drum-separator` after you’re happy stem-lab extract is the replacement.

## OSS / secrets

- No API keys, no `.env`, no home-directory paths in tracked files.
- Do not commit `work/`, `.cache/`, or `record-info.json`.
- Author on GitHub is the public identity; keep gmail out of new files.
