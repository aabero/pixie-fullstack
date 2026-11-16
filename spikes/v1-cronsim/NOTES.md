# V-1 (task 2.2): verify cronsim

Date: 2026-11-15. Python: 3.14.4 (CPython, `/usr/bin/python3.14`, the version recorded in `docs/spike-p0-01-report.md` section 18). cronsim: **2.8** (`uv.lock` in this directory). uv 0.13.8.

Throwaway project: `spikes/v1-cronsim/` (own `pyproject.toml`, not part of the project manifest, not imported by application code). Created with `uv init --bare --python 3.14.4 --no-workspace` and `uv add cronsim`. Nothing was installed outside uv.

Run: `cd spikes/v1-cronsim && uv run python check_cronsim.py` (exit 0 = all pass). Raw output: `raw-output.txt`. Extra observation: `raw-observations-wildcard-hourly.txt`.

Zone data: the host's `zoneinfo` (system tzdata). Not checked: the version of that tzdata.

## Results

All checks use the command above; the "Observed" column is copied from `raw-output.txt`.

| # | Check | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| 1 | New_York spring-forward gap 2026-03-08 (02:00 to 03:00): `30 2 * * *`, ref 2026-03-07 12:00 | one fire, at 2026-03-08 03:00 EDT (first valid instant after the gap) | one fire, 2026-03-08T03:00:00-04:00 | PASS |
| 2 | New_York, day after the gap | back to 02:30 EDT | 2026-03-09T02:30:00-04:00 | PASS |
| 3 | New_York fall-back overlap 2026-11-01: `30 1 * * *`, ref 2026-11-01 00:00 | one fire, at first occurrence 01:30 EDT | one fire, 2026-11-01T01:30:00-04:00 (fold=0) | PASS |
| 4 | New_York, next after the overlap fire | 2026-11-02 01:30 EST | 2026-11-02T01:30:00-05:00 | PASS |
| 5 | Strictly after: 7 cases (reference on a match instant in NY and Montevideo, `*/15`, overlap first and second occurrence as reference, gap-fire instant as reference, reference with 1 microsecond) | every result later than the reference (UTC instants) | 7/7 later | PASS |
| 6 | Montevideo 2026, `0 9 * * *` from 2026-01-01 | 365 fires, all 09:00 at UTC-3, tzinfo America/Montevideo | 365 fires, first 2026-01-01T09:00-03:00, last 2026-12-31T09:00-03:00 | PASS |
| 7 | Reference zone is honored (2026-06-01 09:00) | Montevideo 12:00Z, New_York 13:00Z | 12:00Z and 13:00Z | PASS |
| 8 | Montevideo historical gap 2014-10-05 (02:00 to 03:00): `30 2 * * *` | one fire, 03:00 -02:00 | one fire, 2014-10-05T03:00:00-02:00 | PASS |
| 9 | Montevideo historical overlap 2014-03-09: `30 1 * * *` | one fire, first occurrence 01:30 -02:00 | one fire, 2014-03-09T01:30:00-02:00 (fold=0) | PASS |

Overall: **PASS, 9 of 9. cronsim 2.8 on Python 3.14.4 is usable behind `cron.py`.**

## Notes and limits

- Montevideo has had no DST since 2015, so a current-year gap or overlap does not exist there. Checks 8 and 9 use the 2014 transitions in tzdata (found by scanning `zoneinfo`). My first draft of check 8 assumed a gap at 00:00 to 01:00; that was my error (the real gap is 02:00 to 03:00), and I corrected the test, not the library.
- Wildcard-hour expressions fire in both repeated hours: `0 * * * *` from 2026-11-01 00:00 New_York gives 01:00 EDT and 01:00 EST (see `raw-observations-wildcard-hourly.txt`). "Fires once at the first occurrence" holds for fixed-hour expressions (check 3), not for wildcard hours. The task did not ask to test this, so it is recorded as an observation, not a pass or fail. Task 14.1 should decide whether the wrapper must suppress the second hourly fire.
- Not verified: `between` (cronsim has no such function; it is wrapper logic for 14.1), naive datetimes (not tested), expressions with day-of-month or day-of-week combinations, other zones, years other than 2026 and 2014, DST gaps that are not a whole hour, the tzdata version.
- Gap and strict-after behavior is as observed on one run each; the script is deterministic (no clock or randomness).
