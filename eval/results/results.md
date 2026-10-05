# Eval results (synthetic set)

Run: 2026-10-05T10:42:05 to 2026-10-05T10:49:26 (local time). Machine: Windows 11, 12 CPU threads, 15 GB RAM, RTX 2050 4 GB. Ollama 0.35.1. **Internet reachable during run: no (Wi-Fi off)**.

Test set: `eval/gold.jsonl`, **60 synthetic lines** written by the builder in the style of a home-tuition register (Hinglish, typos, WhatsApp-style messages). Labels written by hand from the spec rules, not by running a model. It is a sanity check, not a benchmark, and none of it is real student data.

## Headline

| Model | Fact precision | Fact recall | Silent errors (no verifier) | Silent errors (with verifier) | Sent to Confirm tray | Saved green and correct | p50 latency | p95 latency | Peak RAM (Ollama) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma 4 E2B | 94% | 94% | 7 of 79 | 2 | 7 facts (9%) + 0 'missed?' cards | 70 of 76 | 3.3 s | 4.5 s | 0.3 GB |
| Gemma 3 1B | 56% | 52% | 34 of 73 | 4 | 42 facts (58%) + 7 'missed?' cards | 27 of 76 | 3.0 s | 4.1 s | 0.3 GB |

Definitions: a **fact** is one (student, type, status/amount, month/date) entry. **Silent error** = a wrong fact that would be saved without anyone being asked. *No verifier* means every extracted fact is saved, with code still parsing amounts/dates and taking the closest roster name. *With verifier* means only green (V1 to V8 passed) facts are saved; amber ones wait in the Confirm tray. Lines marked `must_confirm` (two Nehas, an unknown student, a ₹15,000 payment) count as a silent error if saved green.

## Details

| | Gemma 4 E2B | Gemma 3 1B |
|---|---:|---:|
| Lines | 60 | 60 |
| Gold facts | 79 | 79 |
| Facts extracted | 79 | 73 |
| Line exact match (no verifier) | 88% | 38% |
| Lines fully auto-saved, all correct | 51 | 18 |
| Tricky lines that should ask (caught) | 3 of 3 | 3 of 3 |
| Clean lines that still asked | 4 of 57 | 36 of 57 |
| Facts the model dropped | 5 | 38 |
| ...of which V7 flagged as 'missed?' | 0 | 8 |
| Cold first call (model load) | 17 s | 8 s |
| Mean latency | 3.5 s | 3.1 s |
| Errors / timeouts | 0 | 0 |

Peak RAM = peak resident memory of all Ollama processes (server + runner), sampled every 0.2 s with psutil. GPU memory is not included. Latency is per line, warm (model already loaded), measured around the HTTP call.

## Gemma 4 E2B: what went wrong

**Silent errors that got past the verifier (2 lines):**

- #15 `rohan ne 1200 jama kiye is mahine ke` → saved [{"student": "Rohan", "type": "payment", "amount": 1200, "for_month": null}]
- #55 `Ma'am Ishaan kal nahi aayega, shaadi mein ja rahe hain` → saved [{"student": "Ishaan", "type": "attendance", "status": "absent", "on_date": "2026-09-29"}]

**Wrong without the verifier, stopped by it (5 lines):**

- #40 `Neha 8th was late, Kavya absent` → would have saved [{"student": "Neha Gupta", "type": "attendance", "status": "late", "on_date": "2026-10-04"}]; flagged by V1
- #43 `arjun late, shrey ne 1500 diye sep ke` → would have saved [{"student": "Arjun", "type": "attendance", "status": "late", "on_date": "2026-09-25"}]; flagged by V1
- #52 `neha absent` → would have saved [{"student": "Neha Sharma", "type": "attendance", "status": "absent", "on_date": "2026-10-02"}]; flagged by V4
- #54 `rahul ne 1000 diye` → would have saved [{"student": "Aman", "type": "payment", "amount": 1000, "for_month": null}]; flagged by V4
- #56 `aman ne 15000 diye` → would have saved [{"student": "Aman", "type": "payment", "amount": 15000, "for_month": null}]; flagged by V3

**Lines where a fact was missing (5):**

- #15 `rohan ne 1200 jama kiye is mahine ke`: missing [{"student": "Rohan", "type": "payment", "amount": 1200, "for_month": "2026-10"}]
- #40 `Neha 8th was late, Kavya absent`: missing [{"student": "Neha Gupta", "type": "attendance", "status": "late", "on_date": "2026-10-05"}]
- #43 `arjun late, shrey ne 1500 diye sep ke`: missing [{"student": "Arjun", "type": "attendance", "status": "late", "on_date": "2026-09-26"}]
- #54 `rahul ne 1000 diye`: missing [{"student": "?", "student_any": [], "must_confirm": true, "type": "payment", "amount": 1000, "for_month": null}]
- #55 `Ma'am Ishaan kal nahi aayega, shaadi mein ja rahe hain`: missing [{"student": "Ishaan", "type": "attendance", "status": "absent", "on_date": "2026-10-01"}]

## Gemma 3 1B: what went wrong

**Silent errors that got past the verifier (4 lines):**

- #29 `kanu ki fees ab 1000 from nov` → saved [{"student": "Karan", "type": "payment", "amount": 1000, "for_month": "2026-11"}]
- #41 `riya nahi aayi, aman ne 1500 diye oct ke, baaki 500 next week` → saved [{"student": "Riya", "type": "payment", "amount": 1500, "for_month": "2026-10"}]
- #42 `karan aaya, priya nahi aayi, priya ki mummy ne 800 diye` → saved [{"student": "Priya", "type": "attendance", "status": "present", "on_date": "2026-09-23"}]
- #45 `pinky aur anu nahi aayi, rohan ne oct ke 1200 de diye` → saved [{"student": "Priyanka", "type": "payment", "amount": 1200, "for_month": "2026-10"}]

**Wrong without the verifier, stopped by it (25 lines):**

- #5 `vicky kal nahi aaya tha` → would have saved [{"student": "Vikram", "type": "attendance", "status": null, "on_date": "2026-09-25"}]; flagged by V6
- #7 `priya aur neha 6th absent, baaki sab aaye` → would have saved [{"student": "Priya", "type": "promise", "amount": null, "on_date": null}, {"student": "Neha Sharma", "type": "promise", "amount": null, "on_date": null}]; flagged by V4, V6
- #10 `anu aur pinky aayi, amu nahi aaya` → would have saved [{"student": "Ananya", "type": "promise", "amount": null, "on_date": null}, {"student": "Priyanka", "type": "promise", "amount": null, "on_date": null}]; flagged by V6, V7
- #12 `riya ne 800 diye` → would have saved [{"student": "Riya", "type": "payment", "amount": 800, "for_month": "2026-10"}]; flagged by V1
- #15 `rohan ne 1200 jama kiye is mahine ke` → would have saved [{"student": "Rohan", "type": "payment", "amount": 1200, "for_month": "2026-09,2026-10"}]; flagged by V1, V5
- #18 `pinky ki mummy ne 1.2k bheje` → would have saved [{"student": "Priyanka", "type": "payment", "amount": 1200, "for_month": "2026-09"}]; flagged by V1
- #20 `shreya ne 1,500 diye` → would have saved [{"student": "Shreya", "type": "payment", "amount": 1500, "for_month": "2026-11"}]; flagged by V1
- #25 `monu 1000 de gaya, 500 baaki hai 10 tarikh tak dega` → would have saved [{"student": "Mohit", "type": "payment", "amount": 1000, "for_month": "2026-10"}]; flagged by V1, V5
- #26 `shreya ne 3000 diye aug sep dono ke` → would have saved [{"student": "Shreya", "type": "payment", "amount": 3000, "for_month": "2026-09,2026-10"}]; flagged by V1
- #30 `ananya ki fees ab 1200 hogi` → would have saved [{"student": "Ananya", "type": "payment", "amount": 1200, "for_month": null}]; flagged by V1, V5
- #33 `Mam Sneha aaj nahi aa payegi, tabiyat thik nahi hai` → would have saved [{"student": "Sneha", "type": "attendance", "status": "late", "on_date": "2026-10-03"}]; flagged by V1, V5
- #40 `Neha 8th was late, Kavya absent` → would have saved [{"student": "Neha Sharma", "type": "attendance", "status": "late", "on_date": "2026-10-12"}]; flagged by V1, V4, V5
- … 13 more in `gemma3_1b.json`

**Lines where a fact was missing (30):**

- #4 `kavya aaj chhutti pe thi`: missing [{"student": "Kavya", "type": "attendance", "status": "absent", "on_date": "2026-09-24"}]
- #5 `vicky kal nahi aaya tha`: missing [{"student": "Vikram", "type": "attendance", "status": "absent", "on_date": "2026-09-24"}]
- #8 `rohit rohan dono late aaye`: missing [{"student": "Rohan", "type": "attendance", "status": "late", "on_date": "2026-09-28"}]
- #9 `mohit, arjun aur shreya nahi aaye`: missing [{"student": "Arjun", "type": "attendance", "status": "absent", "on_date": "2026-09-29"}, {"student": "Shreya", "type": "attendance", "status": "absent", "on_date": "2026-09-29"}] (V7 flagged)
- #10 `anu aur pinky aayi, amu nahi aaya`: missing [{"student": "Aman", "type": "attendance", "status": "absent", "on_date": "2026-09-30"}] (V7 flagged)
- #12 `riya ne 800 diye`: missing [{"student": "Riya", "type": "payment", "amount": 800, "for_month": null}]
- #15 `rohan ne 1200 jama kiye is mahine ke`: missing [{"student": "Rohan", "type": "payment", "amount": 1200, "for_month": "2026-10"}]
- #18 `pinky ki mummy ne 1.2k bheje`: missing [{"student": "Priyanka", "type": "payment", "amount": 1200, "for_month": null}]
- #20 `shreya ne 1,500 diye`: missing [{"student": "Shreya", "type": "payment", "amount": 1500, "for_month": null}]
- #21 `rohan ne 500 diye, baaki 700 agle hafte`: missing [{"student": "Rohan", "type": "promise", "amount": 700, "on_date": "2026-10-07"}]
- #22 `anu ne 600 diye oct ke, 400 baad mein degi`: missing [{"student": "Ananya", "type": "promise", "amount": 400, "on_date": null}]
- #23 `vikram ne 1000 diye baaki 500 kal`: missing [{"student": "Vikram", "type": "promise", "amount": 500, "on_date": "2026-10-03"}]
- … 18 more

