"""
MUNIN — measuring MIN_LOSSES_TO_PROJECT.  Sept 22, 2026.

The roster gate was put through 108 checks in September and moved from 9 to 25.
The TERRITORY gate sat at 9 beside it and was never measured once. This measures
it, the same way and against the same standard: how often does the projection
print a verdict a business manager would act on, that a full book says is wrong?

Stated so it can fail. If 9 is right, this run says 9 is right.

The method: a territory has a TRUE loss-margin distribution (the mixture seed.py
draws from, which is the product's own assumption about how a local loses). The
true verdict on an open job is the verdict computed from the true median. The
printed verdict is the one computed from a sample of n recorded losses. The
wrong rate is how often those two disagree.
"""
import random, statistics, sys

RATE = 17.10 + 10.10 + 16.55          # the 2026-27 contract year, three funds
STEEP = 0.25
REPLAYS = 4000

def margin(rng):
    """seed.py's own loss-margin mixture. Most losses are close."""
    return rng.choice([rng.uniform(0.004, 0.030), rng.uniform(0.004, 0.030),
                       rng.uniform(0.030, 0.075), rng.uniform(0.075, 0.180)])

def true_median(rng, n=400_000):
    return statistics.median(margin(rng) for _ in range(n))

def verdict(gap, our_bid, est_hours):
    hours = our_bid * gap / RATE
    if hours > est_hours:
        return "beyond the waiver"
    return "steep" if hours / est_hours > STEEP else "coverable"

def main():
    rng = random.Random(369)
    truth_gap = true_median(rng)
    print(f"true median loss margin for the territory: {truth_gap*100:.2f}%")
    print(f"combined fund rate on the day: ${RATE:.2f}/hr\n")
    # TWO different questions, and they do not have the same answer.
    #  LABEL     coverable / steep / beyond the waiver, exactly as printed
    #  DECISION  is this job winnable on a waiver at all, or is it not
    # A business manager acts on the decision. "Steep" is a shade of yes.
    print(f"{'losses on file':>15}  {'wrong LABEL':>13}  {'wrong DECISION':>15}  {'sample gap':>12}")
    rows = []
    for n in (3, 6, 9, 12, 15, 20, 25, 30, 40, 60):
        wrong = dwrong = 0; gaps = []
        for _ in range(REPLAYS):
            sample = statistics.median(margin(rng) for _ in range(n))
            gaps.append(sample)
            our_bid = rng.uniform(180_000, 3_400_000)
            est_hours = our_bid / rng.uniform(220, 320)
            a = verdict(sample, our_bid, est_hours)
            b = verdict(truth_gap, our_bid, est_hours)
            if a != b:
                wrong += 1
            if (a == "beyond the waiver") != (b == "beyond the waiver"):
                dwrong += 1
        pct, dpct = 100 * wrong / REPLAYS, 100 * dwrong / REPLAYS
        rows.append((n, pct, dpct))
        flag = "  <-- shipped" if n == 9 else ""
        print(f"{n:>15}  {pct:>12.1f}%  {dpct:>14.1f}%  {statistics.median(gaps)*100:>11.2f}%{flag}")
    print()
    for bar in (10.0, 5.0, 2.0, 1.0):
        ok = next((n for n, p, d in rows if p <= bar), None)
        okd = next((n for n, p, d in rows if d <= bar), None)
        print(f"  at or under {bar:>4.1f}% wrong:   label {str(ok) if ok else 'never by 60':>11}"
              f"   decision {str(okd) if okd else 'never by 60':>11}")

def banded():
    """The Sept 22 fix, measured against the same truth.

    PASS is three things at once, and it can fail on any of them:
      1. the verdict is never wrong at MIN_LOSSES_TO_PROJECT and above
      2. "near the line" is rare, so the page is not mute
      3. (the "steep" word is measured for the record, not graded: it is gone)
    """
    import munin
    rng = random.Random(963)
    truth_gap = true_median(rng)
    print("\n\nTHE FIX, MEASURED  (verdict = the line; magnitude = a range)")
    print("  the 'steep' label was removed on Sept 22: the false-steep column below is")
    print("  what it would have cost, and is why the share is printed as a range instead.")
    print(f"{'losses on file':>15}  {'wrong VERDICT':>14}  {'near the line':>14}  {'false steep':>12}")
    ok = True
    for n in (3, 6, 9, 12, 25, 60):
        wrong = near = falsesteep = 0
        for _ in range(REPLAYS):
            gaps = [margin(rng) for _ in range(n)]
            med = statistics.median(gaps); glo, ghi = munin.median_band(gaps)
            our_bid = rng.uniform(180_000, 3_400_000)
            est = our_bid / rng.uniform(220, 320)
            hl, hh = our_bid*glo/RATE, our_bid*ghi/RATE
            said = ("beyond the waiver" if hl > est else
                    "near the line" if hh > est else "coverable")
            truth_winnable = verdict(truth_gap, our_bid, est) != "beyond the waiver"
            if said == "near the line":
                near += 1
            elif (said == "coverable") != truth_winnable:
                wrong += 1
            if hl/est > STEEP and verdict(truth_gap, our_bid, est) != "steep":
                falsesteep += 1
        w, nr, fs = 100*wrong/REPLAYS, 100*near/REPLAYS, 100*falsesteep/REPLAYS
        flag = "  <-- shipped" if n == 9 else ""
        print(f"{n:>15}  {w:>13.1f}%  {nr:>13.1f}%  {fs:>11.1f}%{flag}")
        # the bar is on what MUNIN actually prints. It prints the verdict and a
        # range; it no longer prints the word. So the word is measured and
        # shown, and it is not part of pass or fail.
        if n >= 9 and (w > 0.5 or nr > 15.0):
            ok = False
    print("\n  " + ("PASS  verdict clean at 9 and above, and the page is not mute"
                    if ok else "FAIL  see the row above"))
    return ok

if __name__ == "__main__":
    main()
    raise SystemExit(0 if banded() else 1)
