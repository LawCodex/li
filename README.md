# LawCodex — Liechtenstein (li)

Liechtenstein law as Markdown: every text **in force** in the **systematic collection of
Liechtenstein law** (*Systematische Sammlung der liechtensteinischen Rechtsvorschriften*,
LR numbers), in its current **consolidated** version, as published by the Government's legal
service (*Rechtsdienst der Regierung*) on **LILEX** — https://www.gesetze.li.

Retrieved: **2026-10-13** (consolidated versions applicable on that date).

## Coverage

**3,681 Markdown files**, one per LR entry in force:

| Part | Directory | Files |
|---|---|---|
| Domestic law (*Landesrecht*, LR 1–9) | `1/` … `9/` | 1,239 |
| International law (*Staatsverträge*, LR 0.x), including the EEA Agreement and the EEA Joint Committee decisions published in Liechtenstein | `0/` | 2,442 |

By front-matter `type`:

| `type` | Files |
|---|---|
| `constitution` (LR 101) | 1 |
| `constitutional_act` | 4 |
| `code` | 15 |
| `act` (Gesetze) | 377 |
| `ordinance` (Verordnungen) | 738 |
| `resolution` (Finanzbeschlüsse, Landtagsbeschlüsse) | 62 |
| `announcement` (Kundmachungen) | 16 |
| `other` | 26 |
| `treaty` (LR 0.x) | 2,442 |

`code` is used for the big codes (ABGB 210.0, Sachenrecht 214.0, PGR 216.0, HGB 217.0, ZPO 271.0,
JN 272.0, EO 281.0, StGB 311.0, StPO 312.0 and their introductory acts);
`constitutional_act` for *Verfassungsgesetze* and the *Hausgesetz*; `resolution` for
*Finanzbeschlüsse* and similar Landtag resolutions; `other` for princely *Handschreiben*,
historical Austrian *Hofdekrete* still in force, etc.

### Not covered

- Repealed texts (*aufgehoben*) and earlier consolidated versions (LILEX keeps the full version
  history; only the version in force on the retrieval date is mirrored).
- The chronological collection (*Landesgesetzblatt*, LGBl.) as originally published —
  amending acts are only reflected through the consolidations.
- Municipal law, court decisions (gerichtsentscheidungen.li).
- Images (a few diagrams, signs, forms) are not copied; they are replaced by a link to the
  image on gesetze.li.

## Structure

The tree mirrors the LR numbering (same layout as the Swiss SR in LawCodex/ch):

```
1/10/101-verfassung-des-furstentums-liechtenstein-vom-5-oktober-1921.md   LR 101
2/21/210.0-allgemeines-burgerliches-gesetzbuch-vom-1-juni-1811.md
3/31/311.0-strafgesetzbuch-stgb-vom-24-juni-1987.md
0/0.1/0.10/0.101-konvention-vom-4-november-1950-zum-schutze-der-menschenrecht.md   LR 0.101 (ECHR)
0/0.1/0.11/0.110-....md                                                   EEA Agreement and annexes
```

Domestic law: `<1st digit>/<first 2 digits>/<LR>-<slug>.md`; international law:
`0/0.<d>/0.<dd>/<LR>-<slug>.md`. The slug is the official abbreviation when the title ends with
one (e.g. `urg`, `glg`), otherwise the beginning of the title. When several texts share an
LR number (e.g. the annexes of the EEA Agreement, LR 0.110), each has its own file.
The EEA texts under LR 0.110 (more than 1,400 files, mostly EEA Joint Committee decisions
0.110.0NN.x) get one more directory level, `0/0.1/0.11/0.110.0NN/`, so that no directory exceeds
~400 files.

Front matter:

```yaml
title: "Verfassung des Fürstentums Liechtenstein vom 5. Oktober 1921"
identifier: "LR 101"            # systematic number
lgbl: "LGBl. 1921 Nr. 15"       # original publication in the Landesgesetzblatt
type: constitution              # constitution | constitutional_act | code | act | ordinance | resolution | announcement | treaty | other
jurisdiction: li
language: de
date: 1921-10-05                # date of the act (from its title)
published: 1921-10-24           # LGBl. issue date
last_amended: 2026-01-01        # start of validity of the consolidated version mirrored
version: 45                     # LILEX version number
status: in_force
source: "https://www.gesetze.li/konso/1921015000"
retrieved: 2026-10-13
```

Body: the division headings (*Hauptstück*, *Abschnitt*, *Kapitel*... — LILEX `tit1`, `tit2`...
levels) become `##`, `###`..., articles (*Art.* / *§*) the next heading level, with the
*Sachüberschrift* (article heading) in italics below it. LILEX footnotes (amendment history:
"abgeändert durch LGBl. …") are kept as Markdown footnotes `[^n]` with links to the amending
LGBl. Tables are Markdown tables.

## Sources

- List of texts in force: LILEX consolidated-law search (`/konso/suche`, status *geltend*,
  queried by LR prefix 0–9).
- For each text: the overview page `https://www.gesetze.li/konso/<id>` (current version and its
  validity period) and the HTML of that version, `https://www.gesetze.li/konso/html/<id>?version=<n>`.
- gesetze.li has no robots.txt and its *Impressum* / *Datenschutzerklärung* contain no
  restriction on automated access; requests were made at ≤ 4 concurrent connections with a
  LawCodex User-Agent.

## Licence / copyright

Laws, ordinances, international treaties and other official acts are not protected by copyright
in Liechtenstein (Urheberrechtsgesetz, URG, LR 231.1, Art. 5). The consolidated texts on LILEX are
not the authentic publication — only the Landesgesetzblatt (LGBl.) is legally binding.

## Regenerate

```sh
pip install -r scripts/requirements.txt
python scripts/li_fetch.py      # list + download into ../_raw/li/ (cached; the site is slow, ~2 h)
python scripts/li_convert.py    # write Markdown into this repository
```
