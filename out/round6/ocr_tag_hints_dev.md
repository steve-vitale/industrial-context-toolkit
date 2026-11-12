# OCR tag hints on the round-6 development sets

Made by `pdf_tag_check.py --ocr auto`'s page_hints (tesseract 5.4.0.20240606), scored by `scripts/ocr_tag_hints_score.py`. Hints are never verified tags; this measures how often they are right. Text = letters and digits equal a truth tag; located = also inside the truth box (widened by 15/1000 of the page). Confident = hints with OCR confidence 80 or more. Held-out sets were not opened.

| Set | Run | Truth | Hints | Text P | Text R | Located P | Located R | Confident P |
|---|---|---|---|---|---|---|---|---|
| te-a | hints | 37 | 37 | 0.84 | 0.84 | 0.84 | 0.84 | 1.00 |
| te-a | control: perfect | 37 | 37 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| te-a | control: empty | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a | control: random | 37 | 37 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| te-a | control: shifted | 37 | 37 | 0.84 | 0.84 | 0.00 | 0.00 | 1.00 |
| te-d | hints | 56 | 63 | 0.87 | 0.98 | 0.87 | 0.98 | 1.00 |
| te-d | control: perfect | 56 | 56 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| te-d | control: empty | 56 | 0 | - | 0.00 | - | 0.00 | - |
| te-d | control: random | 56 | 63 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| te-d | control: shifted | 56 | 63 | 0.87 | 0.98 | 0.00 | 0.00 | 1.00 |
| te-a-scan-L1 | hints | 37 | 22 | 0.50 | 0.30 | 0.50 | 0.30 | 0.89 |
| te-a-scan-L1 | control: perfect | 37 | 37 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| te-a-scan-L1 | control: empty | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L1 | control: random | 37 | 22 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| te-a-scan-L1 | control: shifted | 37 | 22 | 0.50 | 0.30 | 0.00 | 0.00 | 0.89 |
| te-a-scan-L2 | hints | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L2 | control: perfect | 37 | 37 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| te-a-scan-L2 | control: empty | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L2 | control: random | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L2 | control: shifted | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L3 | hints | 37 | 9 | 0.00 | 0.00 | 0.00 | 0.00 | - |
| te-a-scan-L3 | control: perfect | 37 | 37 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| te-a-scan-L3 | control: empty | 37 | 0 | - | 0.00 | - | 0.00 | - |
| te-a-scan-L3 | control: random | 37 | 9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| te-a-scan-L3 | control: shifted | 37 | 9 | 0.00 | 0.00 | 0.00 | 0.00 | - |
| pahala-300dpi | hints | 27 | 26 | 0.73 | 0.70 | 0.73 | 0.70 | 1.00 |
| pahala-300dpi | control: perfect | 27 | 27 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| pahala-300dpi | control: empty | 27 | 0 | - | 0.00 | - | 0.00 | - |
| pahala-300dpi | control: random | 27 | 26 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| pahala-300dpi | control: shifted | 27 | 26 | 0.73 | 0.70 | 0.00 | 0.00 | 1.00 |
| pahala-200dpi | hints | 27 | 26 | 0.77 | 0.74 | 0.77 | 0.74 | 1.00 |
| pahala-200dpi | control: perfect | 27 | 27 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| pahala-200dpi | control: empty | 27 | 0 | - | 0.00 | - | 0.00 | - |
| pahala-200dpi | control: random | 27 | 26 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| pahala-200dpi | control: shifted | 27 | 26 | 0.77 | 0.74 | 0.00 | 0.00 | 1.00 |

## Per page

- **te-a 101**: 11/14 found, 13 hints, 2 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 2.0}; 2 one-letter equipment tags skipped by design
  - missed: AI 123, PI 107, SC 212
  - wrong (confidence): CWPID9011 (0.0), PID1011 (0.0)
- **te-a 102**: 12/13 found, 14 hints, 2 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 1.9}; 3 one-letter equipment tags skipped by design
  - missed: AI 129
  - wrong (confidence): CWPID9011 (0.0), PID1021 (0.0)
- **te-a 103**: 8/10 found, 10 hints, 2 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 1.8}; 1 one-letter equipment tags skipped by design
  - missed: AI 137, PI 116
  - wrong (confidence): LSPID9021 (0.0), PID1031 (0.0)
- **te-d 101**: 22/23 found, 25 hints, 3 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 1.9}; 2 one-letter equipment tags skipped by design
  - missed: SC 212
  - wrong (confidence): CWPID9011 (0.0), PID1011 (0.0), TOFIC104 (0.0)
- **te-d 102**: 17/17 found, 19 hints, 2 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 2.0}; 3 one-letter equipment tags skipped by design
  - wrong (confidence): CWPID9011 (0.0), PID1021 (0.0)
- **te-d 103**: 16/16 found, 19 hints, 3 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 9.0, 'scale': 2.44, 'seconds': 1.8}; 1 one-letter equipment tags skipped by design
  - wrong (confidence): LSPID9021 (0.0), PID1031 (0.0), TOFV117 (77.2)
- **te-a-scan-L1 101**: 5/14 found, 8 hints, 3 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 11.0, 'scale': 2.0, 'seconds': 2.1}
  - missed: AI 123, FV 201, FV 202, FV 203, LI 108, SC 212, TI 109, TI 121, TV 210
  - wrong (confidence): CWPE9011 (0.0), CWPRE9011 (0.0), PRH1011 (0.0)
- **te-a-scan-L1 102**: 3/13 found, 7 hints, 4 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 11.0, 'scale': 2.0, 'seconds': 2.0}
  - missed: AI 129, FI 105, FV 206, HV 205, JI 120, LI 112, PI 113, TI 111, TI 122, TV 211
  - wrong (confidence): CWPE9011 (0.0), FI 106 (84.5), PE1021 (0.0), PI 4113 (62.0)
- **te-a-scan-L1 103**: 3/10 found, 7 hints, 4 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 11.0, 'scale': 2.0, 'seconds': 1.9}
  - missed: AI 137, FI 119, FV 204, FV 209, LI 115, LV 208, TI 118
  - wrong (confidence): FI 118 (74.8), LSPE8021 (0.0), LSPID8021 (0.0), PH1031 (0.0)
- **te-a-scan-L2 101**: 0/14 found, 0 hints, 0 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 14.0, 'scale': 1.57, 'seconds': 1.9}
  - missed: AI 123, FI 101, FI 102, FI 103, FI 106, FV 201, FV 202, FV 203, LI 108, PI 107, SC 212, TI 109, TI 121, TV 210
- **te-a-scan-L2 102**: 0/13 found, 0 hints, 0 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 15.0, 'scale': 1.47, 'seconds': 1.9}
  - missed: AI 129, FI 105, FI 110, FI 114, FV 206, HV 205, JI 120, LI 112, LV 207, PI 113, TI 111, TI 122, TV 211
- **te-a-scan-L2 103**: 0/10 found, 0 hints, 0 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 15.5, 'scale': 1.42, 'seconds': 1.9}
  - missed: AI 137, FI 104, FI 117, FI 119, FV 204, FV 209, LI 115, LV 208, PI 116, TI 118
- **te-a-scan-L3 101**: 0/14 found, 4 hints, 4 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 6.0, 'scale': 3.67, 'seconds': 55.1}
  - missed: AI 123, FI 101, FI 102, FI 103, FI 106, FV 201, FV 202, FV 203, LI 108, PI 107, SC 212, TI 109, TI 121, TV 210
  - wrong (confidence): FG 7 (0.0), JH 3 (15.1), PP 4 (0.0), TH04 (0.0)
- **te-a-scan-L3 102**: 0/13 found, 2 hints, 2 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 6.0, 'scale': 3.67, 'seconds': 46.6}
  - missed: AI 129, FI 105, FI 110, FI 114, FV 206, HV 205, JI 120, LI 112, LV 207, PI 113, TI 111, TI 122, TV 211
  - wrong (confidence): OF56 (0.0), TT 4 (0.0)
- **te-a-scan-L3 103**: 0/10 found, 3 hints, 3 wrong; render {'dpi': 300.0, 'scan_cleaned': True, 'glyph_px': 6.0, 'scale': 3.67, 'seconds': 54.2}
  - missed: AI 137, FI 104, FI 117, FI 119, FV 204, FV 209, LI 115, LV 208, PI 116, TI 118
  - wrong (confidence): FYE 3 (0.0), OO 3 (0.0), WF 4 (0.0)
- **pahala-300dpi P-401**: 14/14 found, 14 hints, 0 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 38.0, 'scale': 1.0, 'seconds': 4.6}; rendered at 300 dpi, text layer removed
- **pahala-300dpi P-501**: 5/13 found, 12 hints, 7 wrong; render {'dpi': 300.0, 'scan_cleaned': False, 'glyph_px': 38.0, 'scale': 1.0, 'seconds': 4.5}; rendered at 300 dpi, text layer removed
  - missed: HS 500, 101, YI 500, 101, ZSC 500, 101, ZSC 500, 201, ZSC 500, 301, ZSO 500, 101, ZSO 500, 201, ZSO 500, 301
  - wrong (confidence): HS 0010 (0.0), ZSC 0010 (0.0), ZSC 0020 (0.0), ZSC 0030 (0.0), ZSO 0010 (0.0), ZSO 0020 (0.0), ZSO 0030 (0.0)
- **pahala-200dpi P-401**: 14/14 found, 14 hints, 0 wrong; render {'dpi': 200.0, 'scan_cleaned': False, 'glyph_px': 25.0, 'scale': 1.0, 'seconds': 2.3}; rendered at 200 dpi, text layer removed
- **pahala-200dpi P-501**: 6/13 found, 12 hints, 6 wrong; render {'dpi': 200.0, 'scan_cleaned': False, 'glyph_px': 25.0, 'scale': 1.0, 'seconds': 2.4}; rendered at 200 dpi, text layer removed
  - missed: YI 500, 101, ZSC 500, 101, ZSC 500, 201, ZSC 500, 301, ZSO 500, 101, ZSO 500, 201, ZSO 500, 301
  - wrong (confidence): ZSC 0010 (0.0), ZSC 0020 (0.0), ZSC 0030 (0.0), ZSO 0010 (0.0), ZSO 0020 (0.0), ZSO 0030 (0.0)

## OPEN100 sheets 0-5, clean and degraded (no key)

OPEN100 has no tag key: counts and clean-to-degraded agreement only, not accuracy

| Sheet | Clean hints | L1 hints (same as clean) | L2 | L3 |
|---|---|---|---|---|
| 0 | 31 | 3 (1) | 0 (0) | 3 (0) |
| 1 | 7 | 2 (1) | 0 (0) | 0 (0) |
| 2 | 18 | 2 (1) | 0 (0) | 1 (0) |
| 3 | 16 | 3 (1) | 0 (0) | 3 (0) |
| 4 | 18 | 0 (0) | 0 (0) | 1 (0) |
| 5 | 30 | 10 (2) | 0 (0) | 4 (0) |
