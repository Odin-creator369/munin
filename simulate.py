"""
Trial: a quarter of field reports through HEIMDALL, the way they actually
arrive. Varied phrasing, wins and losses, gaps and mistakes. Stated so it can
fail: the reader is scored on what it got right, and every miss is listed.

THE SCORE IS THE SCORE. Fixed Sept 22, 2026. This scorer used to forgive any
refusal whose reason said "already on file", which turned five wrong calls into
right ones and printed 99/99 over two tallies that plainly disagreed with each
other. The forgiveness is gone. A verdict counts only if it matches the truth.

Duplicates are now TESTED instead of stumbled into. The generator used to draw
its jobs from the same pools the seeded book was built from, so it kept
inventing jobs the local had already recorded: four of the five refusals in the
old run were a report colliding with a SEEDED row, not an agent filing twice.
Every job already on file is now excluded before a report is written, so a
collision cannot happen by accident, and three reports the gate has already
accepted are sent again on purpose. Those three are expected to be refused, and
if the gate lets one through it is a miss like any other.
"""
import sys, random, munin, seed, heimdall
from collections import Counter

# python3 simulate.py [seed]   -- so the score can be checked on a seed it was
# never tuned on. A number that only holds on one seed is not a number.
TRIAL_SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 963
rng = random.Random(TRIAL_SEED)
SIGS = seed.SIGNATORIES
NONU = seed.NON_UNION
TERR = [t[0] for t in seed.TERRITORIES]
PLACES, WORDS = seed.PLACES, seed.PROJECT_WORDS

def fmt(n):
    return rng.choice([f"{n:,.0f}", f"${n:,.0f}", f"{n/1e6:.2f} million" if n >= 1e6 else f"{n/1e3:.0f}k"])

def make(used):
    """Returns (sentence, truth). truth is what the gate SHOULD do.

    `used` holds every (project, territory, signatory) already emitted. A
    repeat is redrawn, so the only duplicates in this trial are the ones put
    there on purpose.
    """
    for _ in range(200):
        ours = rng.choice(SIGS)
        proj = f"{rng.choice(PLACES)} {rng.choice(WORDS)}"
        terr = rng.choice(TERR)
        if (proj, terr, ours) not in used:
            used.add((proj, terr, ours))
            break
    else:
        raise RuntimeError("ran out of distinct jobs to invent")
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
DUP_AT = {33, 66, 88}   # reports the gate already accepted, sent a second time

seed.build()
conn = munin.connect()
right = 0; misses = []; verdicts = Counter(); truths = Counter()
# every job the local already has on the books. The trial reports NEW jobs.
used = {(b["project"], b["territory"], b["our_signatory"])
        for b in conn.execute("SELECT project, territory, our_signatory FROM bids")}
seeded = len(used)
accepted = []; dup_sent = 0

for i in range(N):
    if i in DUP_AT and accepted:
        s = rng.choice(accepted); truth = "refused"; dup_sent += 1
    else:
        s, truth = make(used)
    d = heimdall.gate(s, conn)
    verdicts[d["verdict"]] += 1; truths[truth] += 1
    if d["verdict"] == truth:
        right += 1
    else:
        misses.append((truth, d["verdict"], d["reason"][:70], s[:95]))
    if d["verdict"] == "accepted":
        accepted.append(s)

print(f"TRIAL  {N} field reports through the gate, rules reader, no key  (seed {TRIAL_SEED})")
print(f"  {seeded} jobs already on the books; every report below is a job the local has not recorded")
print(f"  should have been : {dict(truths)}")
print(f"  gate decided     : {dict(verdicts)}")
print(f"  right            : {right}/{N}  ({right/N*100:.0f}%)")
print(f"  {dup_sent} of those were deliberate double entries. All are expected to be refused.")
print(f"\n  misses ({len(misses)}):")
for t, v, r, s in misses[:14]:
    print(f"   should {t:<8} got {v:<8} {r}")
    print(f"        {s}")
if not misses:
    print("   none")

# THE GUARD. The old scorer printed 99/99 over two tallies that plainly did not
# agree, and nothing in the file objected. A first attempt at this guard only
# checked that right + missed = N, which the old scorer also satisfied: forgiving
# a wrong call moves it out of misses and into right and the sum never changes.
# This is the bound that actually binds. The gate can be right about a category
# no more often than the smaller of the two tallies for it, so:
#
#     right  <=  sum over categories of min(should have been, gate decided)
#
# On the Sunday code that ceiling is 70 + 24 + 1 = 95 against a claimed 99.
ceiling = sum(min(truths[c], verdicts[c]) for c in set(truths) | set(verdicts))
ok = (right == N - len(misses)) and right <= ceiling
print(f"\n  reconciles       : {'yes' if ok else 'NO'}"
      f"   ({right} right + {len(misses)} missed = {right + len(misses)} of {N};"
      f" the tallies allow at most {ceiling})")
if not ok:
    raise SystemExit(
        f"scoring is inconsistent with its own tallies: claims {right} right, "
        f"but 'should have been' and 'gate decided' can only agree on {ceiling}.")
