# Fixtures

Each `AD-2.LFxx.txt` mimics the output of `pdftotext -layout` on the
corresponding SIA VAC chart, trimmed to the header and the fuel section.
They exist so the parsing tests run without the eAIP package, which is
several hundred megabytes and not redistributable.

| Fixture | Exercises |
|---|---|
| `AD-2.LFOU.txt` | Ordinary chart, section `10 - AVT` closed by section 11 |
| `AD-2.LFLY.txt` | Amended paragraph (`←`) and the `UL AERO SUPER+` brand name, which must not be read as mogas |
| `AD-2.LFCU.txt` | Genuine mogas (`SP 98`) alongside 100LL |
| `AD-2.LFJB.txt` | `AVT : NIL`, an aerodrome with no fuel at all |
| `AD-2.LFOJ.txt` | Military chart with no fuel section, plus a two-column header |
| `AD-2.LFDA.txt` | Section closed by 12 instead of 11; **coordinates altered to the southern hemisphere** to cover the sign handling |

Apart from the noted change to `AD-2.LFDA.txt`, the text is faithful to the
2026-05-14 AIRAC cycle.
