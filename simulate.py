"""
Trial: a quarter of field reports through HEIMDALL, the way they actually
arrive. Varied phrasing, wins and losses, gaps and mistakes. Stated so it can
fail: the reader is scored on what it got right, and every miss is listed.
"""
import random, munin, seed, heimdall
from collections import Counter

rng = random.Random(963)
SIGS = seed.SIGNATORIES
NONU = seed.NON_UNION
TERR = [t[0] for t in seed.TERRITORIES]
PLACES, WORDS = seed.PLACES, seed.PROJECT_WORDS

def fmt(n):
    return rng.choice([f"{n:,.0f}", f"${n:,.0f}", f"{n/1e6:.2f} million" if n >= 1e6 else f"{n/1e3:.0f}k"])

def make():
    """Returns (sentence, truth). truth is what the gate SHOULD do."""
    ours = rng.choice(SIGS)
    proj = f"{rng.choice(PLACES)} {rng.choice(WORDS)}"
    terr = rng.choice(TERR)
    our_bid = round(rng.uniform(200_000, 3_000_000), -3)
    hours = round(our_bid / rng.uniform(160, 230), -1)
    kind = rng.choices(["win", "loss", "loss_no_number", "other_named_only",
                        "union_vs_union", "bad_numbers", "no_hours"],
                       [22, 40, 10, 8, 8, 6, 6])[0]
    if kind == "win":
        s = rng.choice([
            f"{ours} got the {proj} in {terr}, we were at {fmt(our_bid)}, about {hours:,.0f} hours.",
            f"Good one. {ours} took the {proj} out in {terr}. Our number was {fmt(our_bid)}, {hours:,.0f} man hours. We won it.",
            f"{ours}, {proj}, {terr}. {fmt(our_bid)}, {hours:,.0f} hrs. We got it.",
        ])
        return s, "accepted"
    if kind == "loss":
        win = round(our_bid * rng.uniform(0.94, 0.995), -3); other = rng.choice(NONU)
        s = rng.choice([
            f"{ours} bid the {proj} in {terr}, {fmt(our_bid)}, {hours:,.0f} hours. Lost it, {other} came in at {fmt(win)}.",
            f"Lost the {proj} in {terr}. {ours} was at {fmt(our_bid)} on {hours:,.0f} man hours and {other} got it at {fmt(win)}.",
            f"{ours} on the {proj}, {terr}, {hours:,.0f} hrs, we bid {fmt(our_bid)} and it went to {other} for {fmt(win)}.",
        ])
        return s, "accepted"
    if kind == "loss_no_number":
        s = f"{ours} lost the {proj} in {terr}. We were {fmt(our_bid)}, {hours:,.0f} hours. Don't know what it went for yet."
        return s, "held"
    if kind == "other_named_only":
        other = rng.choice(NONU); win = round(our_bid * 0.97, -3)
        s = f"{other} got the {proj} over in {terr} at {fmt(win)}, {hours:,.0f} hours on it."
        return s, "held"
    if kind == "union_vs_union":
        other = rng.choice([x for x in SIGS if x != ours]); win = round(our_bid * rng.uniform(0.95, 0.99), -3)
        s = f"{ours} bid the {proj} in {terr} at {fmt(our_bid)}, {hours:,.0f} hours. {other} got it at {fmt(win)}."
        return s, "accepted"
    if kind == "bad_numbers":
        win = round(our_bid * rng.uniform(1.02, 1.08), -3); other = rng.choice(NONU)
        s = f"{ours} lost the {proj} in {terr}. We bid {fmt(our_bid)}, {hours:,.0f} hours, {other} came in at {fmt(win)}."
        return s, "refused"
    if kind == "no_hours":
        win = round(our_bid * 0.97, -3); other = rng.choice(NONU)
        s = f"{ours} lost the {proj} in {terr}, {fmt(our_bid)} against {other} at {fmt(win)}."
        return s, "held"

N = 99
seed.build()
conn = munin.connect()
right = 0; misses = []; verdicts = Counter(); truths = Counter()
for i in range(N):
    s, truth = make()
    d = heimdall.gate(s, conn)
    verdicts[d["verdict"]] += 1; truths[truth] += 1
    if d["verdict"] == truth or (d["verdict"] == "refused" and "already on file" in d["reason"]):
        right += 1      # a duplicate the gate caught is the gate being right
    else:
        misses.append((truth, d["verdict"], d["reason"][:70], s[:95]))

print(f"TRIAL  {N} field reports through the gate, rules reader, no key")
print(f"  should have been : {dict(truths)}")
print(f"  gate decided     : {dict(verdicts)}")
print(f"  right            : {right}/{N}  ({right/N*100:.0f}%)")
print(f"\n  misses ({len(misses)}):")
for t, v, r, s in misses[:14]:
    print(f"   should {t:<8} got {v:<8} {r}")
    print(f"        {s}")
