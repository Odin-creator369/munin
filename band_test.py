"""Tests for the give-or-take on page one. Each stated so it can fail."""
import random, math, seed, munin, heimdall
from reports import REPORTS

fails=[]
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ")+name+("  "+detail if detail else ""))
    if not cond: fails.append(name)

c = seed.build()
for r in REPORTS: heimdall.gate(r, c)
po = munin.page_one(c)

print("T3.1  the band is a band")
lo,hi = po["band"]
check("contains the point estimate", lo <= po["share"] <= hi, f"{lo:.1f} <= {po['share']:.1f} <= {hi:.1f}")
check("stays inside 0 to 100", 0.0 <= lo and hi <= 100.0)
check("the count is printed before the share", po["line"].index(str(po["hits"])) < po["line"].index("%"))
check("the share never appears without the band", "sits between" in po["line"])

print("\nT3.2  wide at thirty jobs, tight at a thousand.  FAIL if it does not narrow")
w = {}
for n in (30, 100, 400, 1000):
    l,h = munin.give_or_take(round(0.79*n), n); w[n] = h-l
    print(f"    n={n:<5} band {l:5.1f}% to {h:5.1f}%   width {h-l:5.1f} points")
check("narrows monotonically", w[30] > w[100] > w[400] > w[1000])
check("wide enough at 30 to stop a confident read", w[30] > 25)
check("tight enough at 1000 to be useful", w[1000] < 6)

print("\nT3.3  WILSON vs the textbook interval where the share sits near a boundary")
print("      (this is the Sept 17 finding. FAIL if the textbook one is fine)")
def textbook(f, j, z=1.96):
    p=f/j; h=z*math.sqrt(p*(1-p)/j) if j else 0
    return (max(0,100*(p-h)), min(100,100*(p+h)))
rng=random.Random(369); TRUE=0.96; N=6000
for j in (30, 100):
    wc=tc=0
    for _ in range(N):
        f=sum(1 for _ in range(j) if rng.random()<TRUE)
        a,b=munin.give_or_take(f,j);   wc += (a <= TRUE*100 <= b)
        a,b=textbook(f,j);             tc += (a <= TRUE*100 <= b)
    print(f"    j={j:<5} wilson covers {100*wc/N:5.1f}%   textbook covers {100*tc/N:5.1f}%   (nominal 95%)")
    check(f"wilson holds near 95% at j={j}", 90.0 <= 100*wc/N <= 99.0, f"{100*wc/N:.1f}%")
    if j==30:
        check("textbook is visibly worse at j=30", 100*tc/N < 90.0, f"{100*tc/N:.1f}%")

print("\nT3.4  a signatory win is never counted as an hours loss")
before = munin.page_one(c)["judged"]
row = c.execute("SELECT job_id FROM bids WHERE outcome='lost' AND winner_union=0 "
                "AND winning_bid IS NOT NULL LIMIT 1").fetchone()
c.execute("UPDATE bids SET winner_union=1 WHERE job_id=?", (row["job_id"],)); c.commit()
after = munin.page_one(c)["judged"]
check("moving one loss to the union side drops it from the denominator",
      after == before-1, f"{before} -> {after}")
c.execute("UPDATE bids SET winner_union=0 WHERE job_id=?", (row["job_id"],)); c.commit()

print("\n" + ("ALL PASS" if not fails else f"FAILED: {fails}"))
raise SystemExit(1 if fails else 0)
