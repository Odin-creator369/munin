"""Tests for the roster gate, each stated so it can fail."""
import seed, munin

def add_priced(conn, contractor, n, tag):
    base = conn.execute("SELECT COUNT(*) c FROM bids").fetchone()["c"]
    for i in range(n):
        conn.execute("INSERT INTO bids VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"{tag}-{base+i}", "2026-06-15", "Philadelphia", f"{tag} job {base+i}",
             "GC", contractor, 1_000_000.0, 980_000.0, "Ridgeway Services", 0,
             3500.0, 0.0, "lost", "test", "test"))
    conn.commit()

def st(conn): return munin.gungnir_standings(conn)

fails = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("  " + detail if detail else ""))
    if not cond: fails.append(name)

print("T1.1  a thin book names nobody")
c = seed.build(); s = st(c)
check("no contractor is ranked", len(s["ranked"]) == 0, f"ranked={len(s['ranked'])}")
check("the page is not mute", "UNRESOLVED" in s["gate"]["line"] and
      str(s["gate"]["priced_bids_still_needed"]) in s["gate"]["line"])

print("\nT1.2  the stated distance is the true distance")
need = s["gate"]["priced_bids_still_needed"]
closest = s["gate"]["closest"]
c2 = seed.build()
short = 0
for name, n in closest:
    gap = max(0, munin.MIN_BIDS_TO_RANK - n)
    if gap: add_priced(c2, name, gap, "T12"); short += gap
check("distance matches what it actually takes", short == need, f"added {short}, said {need}")
check("gate OPENS once the distance is closed", st(c2)["resolved"] is True)
check("and exactly four shops qualify", len(st(c2)["ranked"]) == 4)

print("\nT1.3  one bid short must stay closed")
c3 = seed.build()
done = 0
for name, n in closest:
    gap = max(0, munin.MIN_BIDS_TO_RANK - n)
    if gap:
        take = gap - 1 if done == 0 else gap
        if take: add_priced(c3, name, take, "T13")
        done += 1
s3 = st(c3)
check("still unresolved at one bid short", s3["resolved"] is False, s3["gate"]["line"][:60])
check("and it says exactly 1 more is needed", s3["gate"]["priced_bids_still_needed"] == 1,
      f"says {s3['gate']['priced_bids_still_needed']}")

print("\nT1.4  silence is not the resting state: a real book resolves")
c4 = seed.build()
for name in [n for n, _ in closest] + ["Kestrel Power"]:
    add_priced(c4, name, 40, "T14")
s4 = st(c4)
check("resolves on a full book", s4["resolved"] is True, f"ranked={len(s4['ranked'])}")
check("every ranked shop carries 25+", all(r["priced"] >= 25 for r in s4["ranked"]))
check("no unranked shop is given a win rate",
      all(isinstance(r["win_rate"], munin.Unresolved) for r in s4["unranked"]))

print("\n" + ("ALL PASS" if not fails else f"FAILED: {fails}"))
raise SystemExit(1 if fails else 0)
