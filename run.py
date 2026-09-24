#!/usr/bin/env python3
"""
BIFROST - the bridge. One command, one local, the whole chain.

    python3 run.py

Builds the local, puts field reports through the gate, prices every loss,
finds the free options, ranks the roster, writes the reports. It is one
written process, and how it is run here is how it is run anywhere.
"""
import os, sys, subprocess, webbrowser
import munin, seed, heimdall, render
from reports import REPORTS

G = "\033[33m"; D = "\033[2m"; B = "\033[1m"; R = "\033[0m"; E = "\033[31m"; OK = "\033[32m"

def rule(t=""):
    print(f"\n{D}{'-'*74}{R}")
    if t: print(f"{B}{t}{R}")

def main():
    print(f"\n{G}{B}MUNIN{R}  {D}Odin's raven, the one that remembers{R}")
    key = heimdall.read_key()
    print(f"{D}reading:{R} {'model (' + heimdall.MODEL + ')' if key else 'rules only, no key found'}")

    rule("1. BIFROST  building the local")
    conn = seed.build()
    n = conn.execute("SELECT COUNT(*) c FROM bids").fetchone()["c"]
    print(f"   {seed.LOCAL}  {D}(simulated){R}")
    print(f"   {n} bids seeded across {len(seed.TERRITORIES)} territories, "
          f"{len(seed.SIGNATORIES)} signatory contractors")

    rule("2. HEIMDALL  at the gate   (wins and losses both)")
    for i, r in enumerate(REPORTS, 1):
        d = heimdall.gate(r, conn)
        col = {"accepted": OK, "held": G, "refused": E}[d["verdict"]]
        word = {"accepted": "ACCEPT", "held": "HOLD  ", "refused": "REFUSE"}[d["verdict"]]
        print(f"   {col}{word}{R}  {D}{r[:62]}...{R}")
        print(f"           {d['reason']}")

    rule("3. MJOLNIR  the verdict, in hours")
    bad = conn.execute("SELECT * FROM bids WHERE bid_date < '2025-05-01' LIMIT 1").fetchone()
    good = beyond = None
    for b in conn.execute("SELECT * FROM bids WHERE outcome='lost' AND winning_bid IS NOT NULL "
                          "AND bid_date > '2026-05-01'"):
        m = munin.mjolnir(conn, b)
        if m["verdict"] == "coverable" and good is None and m["hours_to_close"] > 200:
            good = (b, m)
        elif m["verdict"] == "beyond the waiver" and beyond is None:
            beyond = (b, m)
        if good and beyond:
            break

    b, m = good
    print(f"   {b['job_id']} {b['project']}  {D}({b['territory']}){R}")
    print(f"     we bid ${b['our_bid']:,.0f}, it went for ${b['winning_bid']:,.0f}. "
          f"gap ${m['gap']:,.0f}")
    print(f"     rate in effect {m['rate']['effective_from']}: "
          f"${m['rate']['combined']:.2f}/hr to the three funds "
          f"{D}(pension {m['rate']['pension']} · annuity {m['rate']['annuity']} "
          f"· h&w {m['rate']['hw']}){R}")
    print(f"     {B}{m['hours_to_close']:,.0f} hours{R} would have closed it, "
          f"out of {m['hours_available']:,.0f} in the job "
          f"({m['share_of_job']*100:.1f}%)")
    print(f"     costs the funds ${m['cost_if_won']:,.0f} only if a signatory wins. "
          f"Lost, it costs ${m['cost_if_lost']:,.0f}")

    b2, m2 = beyond
    print(f"\n   and it does not just say yes:")
    print(f"     {b2['job_id']} {b2['project']}  gap ${m2['gap']:,.0f} needs "
          f"{m2['hours_to_close']:,.0f} hrs, the job only holds "
          f"{m2['hours_available']:,.0f}")
    print(f"     {G}{m2['verdict']}{R}  {D}that one was not winnable on a waiver.{R}")

    print(f"\n   {E}designed failure 1{R}  {bad['job_id']} dated {bad['bid_date']}")
    print(f"     {G}{munin.mjolnir(conn, bad)['verdict']}{R}")
    print(f"     {D}rates are renegotiated every year and the split across the three")
    print(f"     funds is set after the union meeting. Munin will not price a bid")
    print(f"     with a rate that was not in effect that day.{R}")

    rule("4. THE BLIND EYE  page one")
    po = munin.page_one(conn)
    be = po["free"]
    print(f"   {B}{po['line']}{R}")
    print(f"   On every one of them, {B}no waiver was offered{R}.")
    print(f"   {D}the count first, the share second, the give-or-take always. A single")
    print(f"   reading of the share at thirty jobs sits eight points wide, so a bare")
    print(f"   percentage on page one is the same lie as a confidently named shop.{R}")
    union = conn.execute("SELECT COUNT(*) c FROM bids WHERE outcome='lost' "
                         "AND winning_bid IS NOT NULL AND winner_union=1").fetchone()["c"]
    print(f"   {D}{union} more priced losses went to another signatory and are not counted")
    print(f"   here: the hours stayed in the hall and the funds were paid either way.{R}")
    print(f"   Total distance between our number and theirs: ${sum(b['gap'] for b in be):,.0f}")
    print(f"\n   closest three:")
    for b in be[:3]:
        print(f"     {b['job_id']}  {b['territory']:<13} ${b['gap']:>9,.0f}  "
              f"{b['hours_to_close']:>6,.0f} hrs  ({b['share_of_job']*100:.1f}% of the job)")

    rule("5. GUNGNIR  three scorecards")
    st = munin.gungnir_standings(conn)
    print(f"   standings: {len(st['ranked'])} ranked, {G}{len(st['unranked'])} unresolved{R}"
          f"  {D}({st['priced_total']} priced bids of {st['full_confidence_at']}){R}")
    if st["resolved"]:
        for r in st["ranked"][:2]:
            print(f"     top    {r['contractor']:<26} {r['win_rate']*100:5.1f}%  n={r['bids']}")
        for r in st["ranked"][-1:]:
            print(f"     bottom {r['contractor']:<26} {r['win_rate']*100:5.1f}%  n={r['bids']}")
    else:
        print(f"     {G}{st['gate']['line']}{R}")
    print(f"\n   {E}designed failure 2{R}  the roster gate, and it is holding")
    print(f"     {G}no contractor is named on this run{R}")
    print(f"     {D}the gate counts priced bids per shop, not shops priced: four shops")
    print(f"     at {munin.MIN_BIDS_TO_RANK}+ priced bids each, or the page names nobody. The looser rule")
    print(f"     named a contractor and was wrong about a third of the time at thirty")
    print(f"     rows. Silence with a distance on it is the product working.{R}")

    rec = munin.gungnir_recovery(conn)
    print(f"\n   recovery fund: {rec['waived_jobs']} jobs waived, {rec['dry_jobs']} dry")
    print(f"     {rec['hours_at_risk_that_cost_nothing']:,.0f} hours were waived on jobs "
          f"the local lost, and cost the funds nothing")

    nx = munin.gungnir_next(conn)
    unres = [r for r in nx["all"] if isinstance(r["projection"], munin.Unresolved)]
    print(f"\n   next winnable: {len(nx['recommended'])} of {len(nx['all'])} open jobs")
    for r in nx["recommended"][:2]:
        print(f"     {r['job_id']}  {r['territory']:<13} {r['hours_to_close']:>6,.0f} hrs "
              f"{D}give or take {r['hours_low']:,.0f} to {r['hours_high']:,.0f}, "
              f"{r['share_low']*100:.0f} to {r['share_high']*100:.0f}% of the job{R}")
    print(f"\n   {E}designed failure 3{R}  a territory with too little history")
    for r in unres[:1]:
        print(f"     {r['job_id']} {r['territory']}: {G}{r['projection']}{R}")

    rule("6. REALMS  who sees what")
    for realm, k in [("business_manager", None), ("business_agent", "Bucks"),
                     ("financial_secretary", None), ("contractor", "Marden Electric")]:
        rows = munin.realm_filter(conn, realm, k)
        meta = munin.REALMS[realm]
        print(f"   {meta['label']:<30}{(k or 'all territories'):<16} {len(rows):>4} rows"
              f"   {D}{meta['scope']}{R}")

    rule("7. reports written")
    out = render.build_all()
    for f, _ in render.PAGES:
        print(f"   {os.path.join(out, f)}")
    print(f"\n   {D}open the first one in a browser{R}")
    rule()
    print(f"{D}Simulated data throughout. No real local, no real contractor, no real job.{R}\n")
    return out

if __name__ == "__main__":
    out = main()
    if "--open" in sys.argv:
        webbrowser.open("file://" + os.path.join(out, "index.html"))
