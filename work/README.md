# Local session library

This folder is **not** part of the public git tree. Put original recordings, extracted stems, and remixes here.

Layout:

```
work/<artist-slug>/<song-slug>/
  source/          original file (m4a, wav, mp3, …)
  stems/<model>/   vocals.wav drums.wav bass.wav other.wav
  remixes/         rebuilt mixes and experiments
  session.json     relative paths only
```

Example:

```bash
stem-lab ingest ./demo.m4a --artist example-artist --title demo-song
stem-lab extract --artist example-artist --title demo-song --stems 4
stem-lab mix --artist example-artist --title demo-song --mute vocals
```

Override the location with `STEM_LAB_WORK` if you want the library outside the clone.
