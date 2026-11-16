"""V-1 (task 2.2): check cronsim timezone-aware behavior. Throwaway; not imported by app code."""
import sys
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from zoneinfo import ZoneInfo
from cronsim import CronSim

NY = ZoneInfo("America/New_York")
MV = ZoneInfo("America/Montevideo")
UTC = timezone.utc
results = []

def fires(expr, ref, until):
    it, out = CronSim(expr, ref), []
    while True:
        d = next(it)
        if d.astimezone(UTC) >= until.astimezone(UTC):
            return out
        out.append(d)
        if len(out) > 1000:
            raise RuntimeError("too many")

def fmt(d):
    return f"{d.isoformat()} (fold={d.fold}, utc={d.astimezone(UTC).strftime('%Y-%m-%dT%H:%MZ')})"

def record(name, expected, observed, ok):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n   expected: {expected}\n   observed: {observed}")

def nv(name, reason):
    print(f"[NOT VERIFIED] {name}\n   reason: {reason}")

print(f"python={sys.version.split()[0]} cronsim={version('cronsim')}")

# 1. NY spring-forward gap 2026-03-08 02:00 -> 03:00 (02:30 does not exist)
ref = datetime(2026, 3, 7, 12, tzinfo=NY)
day = fires("30 2 * * *", ref, datetime(2026, 3, 9, 0, tzinfo=NY))
exp = datetime(2026, 3, 8, 3, 0, tzinfo=NY)
record("NY gap: '30 2 * * *' fires once on 2026-03-08, at first valid instant after the gap (03:00 EDT)",
       f"1 fire at {fmt(exp)}", f"{len(day)} fire(s): {[fmt(d) for d in day]}",
       len(day) == 1 and day[0] == exp and day[0].utcoffset() == timedelta(hours=-4))
nxt = next(CronSim("30 2 * * *", day[0]))
record("NY gap: next day returns to 02:30 EDT", "2026-03-09T02:30:00-04:00", fmt(nxt),
       nxt == datetime(2026, 3, 9, 2, 30, tzinfo=NY))

# 2. NY fall-back overlap 2026-11-01 (01:00-02:00 occurs twice)
ref = datetime(2026, 11, 1, 0, tzinfo=NY)
day = fires("30 1 * * *", ref, datetime(2026, 11, 2, 0, tzinfo=NY))
exp = datetime(2026, 11, 1, 1, 30, tzinfo=NY)  # fold=0 -> EDT, first occurrence
record("NY overlap: '30 1 * * *' fires once on 2026-11-01, at first occurrence (01:30 EDT)",
       f"1 fire at {fmt(exp)}", f"{len(day)} fire(s): {[fmt(d) for d in day]}",
       len(day) == 1 and day[0].astimezone(UTC) == exp.astimezone(UTC) and day[0].utcoffset() == timedelta(hours=-4))
nxt = next(CronSim("30 1 * * *", day[0]))
record("NY overlap: next result after the fire is 2026-11-02 01:30 EST (not the second occurrence)",
       "2026-11-02T01:30:00-05:00", fmt(nxt), nxt == datetime(2026, 11, 2, 1, 30, tzinfo=NY))

# 3. Strictly after reference
cases = [
    ("0 12 * * *", datetime(2026, 3, 9, 12, tzinfo=NY)),
    ("0 12 * * *", datetime(2026, 3, 9, 12, tzinfo=MV)),
    ("*/15 * * * *", datetime(2026, 6, 1, 10, 15, tzinfo=MV)),
    ("30 1 * * *", datetime(2026, 11, 1, 1, 30, tzinfo=NY)),             # ref = first occurrence, fold=0
    ("30 1 * * *", datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=NY)),     # ref = second occurrence
    ("30 2 * * *", datetime(2026, 3, 8, 3, 0, tzinfo=NY)),               # ref = gap-fire instant
    ("* * * * *", datetime(2026, 6, 1, 10, 15, 0, 1, tzinfo=MV)),        # sub-second ref
]
bad = []
for expr, r in cases:
    n = next(CronSim(expr, r))
    ok = n.astimezone(UTC) > r.astimezone(UTC)
    print(f"   strict-after case {expr!r} ref={fmt(r)} -> {fmt(n)} {'ok' if ok else 'NOT AFTER'}")
    if not ok:
        bad.append((expr, r))
record("Strictly-after: next result is never equal to (or before) the reference, incl. ref on a match instant",
       "every result > reference (compared as UTC instants)", f"{len(cases) - len(bad)}/{len(cases)} ok; bad={bad}", not bad)

# 4. Montevideo (UTC-3, no DST since 2015)
ref = datetime(2026, 1, 1, 0, tzinfo=MV)
seq = fires("0 9 * * *", ref, datetime(2027, 1, 1, 0, tzinfo=MV))
ok = len(seq) == 365 and all(d.hour == 9 and d.utcoffset() == timedelta(hours=-3) for d in seq)
record("Montevideo 2026: '0 9 * * *' fires 365 times, always 09:00 at UTC-3, results tz-aware in that zone",
       "365 fires, all 09:00-03:00, tzinfo America/Montevideo",
       f"{len(seq)} fires; first={fmt(seq[0])}; last={fmt(seq[-1])}; tz={seq[0].tzinfo}", ok and seq[0].tzinfo == MV)
utc_seq = next(CronSim("0 9 * * *", datetime(2026, 6, 1, 0, tzinfo=MV)))
record("Montevideo: same wall clock differs from NY in UTC (zone of the reference is honored)",
       "MV 09:00 = 12:00Z; NY 09:00 EDT = 13:00Z on 2026-06-01",
       f"MV={fmt(utc_seq)}; NY={fmt(next(CronSim('0 9 * * *', datetime(2026, 6, 1, 0, tzinfo=NY))))}",
       utc_seq.astimezone(UTC).hour == 12 and next(CronSim("0 9 * * *", datetime(2026, 6, 1, 0, tzinfo=NY))).astimezone(UTC).hour == 13)

# 5. Montevideo historical DST (tzdata; Uruguay observed DST until 2015). Transitions found by scanning zoneinfo:
#    2014-03-09: 02:00 -02 -> 01:00 -03 (01:00-02:00 repeats); 2014-10-05: 02:00 -03 -> 03:00 -02 (02:00-03:00 missing)
a, b = datetime(2014, 10, 4, 12, tzinfo=MV), datetime(2014, 10, 6, 12, tzinfo=MV)
if a.utcoffset() != b.utcoffset():
    day = fires("30 2 * * *", a, datetime(2014, 10, 6, 0, tzinfo=MV))
    exp = datetime(2014, 10, 5, 3, 0, tzinfo=MV)
    record("Montevideo historical gap (2014-10-05): '30 2 * * *' fires once at first valid instant (03:00 -02)",
           f"1 fire at {fmt(exp)}", f"{len(day)} fire(s): {[fmt(d) for d in day]}",
           len(day) == 1 and day[0] == exp and day[0].utcoffset() == timedelta(hours=-2))
    day = fires("30 1 * * *", datetime(2014, 3, 9, 0, tzinfo=MV), datetime(2014, 3, 10, 0, tzinfo=MV))
    exp = datetime(2014, 3, 9, 1, 30, tzinfo=MV)  # fold=0 -> first occurrence (-02)
    record("Montevideo historical overlap (2014-03-09): '30 1 * * *' fires once at first occurrence (01:30 -02)",
           f"1 fire at {fmt(exp)}", f"{len(day)} fire(s): {[fmt(d) for d in day]}",
           len(day) == 1 and day[0].astimezone(UTC) == exp.astimezone(UTC) and day[0].utcoffset() == timedelta(hours=-2))
else:
    nv("Montevideo historical DST (2014)", "zoneinfo has no 2014 offset change on this host")

print("RESULT:", "ALL PASS" if all(results) else "FAILURES", f"({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
