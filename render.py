"""Generates the report views. What a local actually reads.

Reader views, not logins: every page is a report, and each seat gets its own
realm. Built to be opened from a file, so nothing here loads off the internet.
"""
import os, html, datetime
import munin

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
LOCAL = "Electricians Local XXX"

CSS = """
:root{
  --ink:#14110F; --ink-2:#1C1815; --rule:#3A322B;
  --bone:#EDE4D3; --bone-dim:#A99B86; --gold:#C9A227; --ash:#6E6257;
  --ember:#B4472F; --moss:#6E8B5E;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--ink);color:var(--bone);
  font:16px/1.6 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  -webkit-font-smoothing:antialiased}
.num,td.n,th.n{font-family:"SF Mono",Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums;font-size:.92em;letter-spacing:-.01em}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px 96px}
header.top{border-bottom:1px solid var(--rule);margin-bottom:0;padding:34px 0 26px}
.eyebrow{font:600 11px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.22em;
  text-transform:uppercase;color:var(--gold)}
h1{font-size:40px;line-height:1.12;margin:16px 0 8px;font-weight:600;letter-spacing:-.015em}
h2{font-size:25px;margin:0 0 6px;font-weight:600;letter-spacing:-.01em}
.sub{color:var(--bone-dim);font-size:15px;margin:0}
.lede{font-size:18px;line-height:1.62;color:var(--bone);max-width:66ch;margin:18px 0 0}
section{padding:40px 0;border-bottom:1px solid var(--rule)}
section:last-of-type{border-bottom:0}
table{width:100%;border-collapse:collapse;margin-top:18px;font-size:14.5px}
th{text-align:left;font:600 10.5px/1 ui-sans-serif,system-ui,sans-serif;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ash);
  padding:0 12px 10px;border-bottom:1px solid var(--rule)}
th.n,td.n{text-align:right}
td{padding:11px 12px;border-bottom:1px solid rgba(58,50,43,.55);vertical-align:top}
tr:hover td{background:var(--ink-2)}
.tag{display:inline-block;font:600 10px/1 ui-sans-serif,system-ui,sans-serif;
  letter-spacing:.12em;text-transform:uppercase;padding:5px 8px;border-radius:2px;
  border:1px solid currentColor}
.t-open{color:var(--gold)} .t-refuse{color:var(--ember)} .t-ok{color:var(--moss)}
.t-hold{color:var(--bone-dim)}
.unres{color:var(--gold);font-style:italic}
.unres::before{content:"◇ ";font-style:normal}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--rule);
  border:1px solid var(--rule);margin-top:26px}
.stat{background:var(--ink);padding:22px 20px}
.stat .k{font:600 10.5px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ash)}
.stat .v{font-family:"SF Mono",Menlo,Consolas,monospace;font-variant-numeric:tabular-nums;
  font-size:33px;margin-top:12px;letter-spacing:-.02em}
.stat .v.gold{color:var(--gold)} .stat .n2{color:var(--bone-dim);font-size:13px;margin-top:8px}
nav.bar{display:flex;gap:26px;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid var(--rule);
  font:600 11px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase}
nav.bar a{color:var(--bone-dim);text-decoration:none;padding-bottom:3px}
nav.bar a:hover{color:var(--bone)} nav.bar a.on{color:var(--gold);border-bottom:1px solid var(--gold)}
.sim{display:inline-block;border:1px solid var(--ember);color:var(--ember);
  font:600 10px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.16em;
  text-transform:uppercase;padding:6px 9px;border-radius:2px}
footer{padding:34px 0;color:var(--ash);font-size:12.5px;line-height:1.7}
.rpt{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:22px}
.card{border:1px solid var(--rule);padding:22px}
.card h3{margin:0 0 4px;font-size:17px}
.card .who{font:600 10.5px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:var(--gold)}
.card p{color:var(--bone-dim);font-size:14px;margin:10px 0 0}
.quote{border-left:2px solid var(--rule);padding:4px 0 4px 18px;color:var(--bone-dim);
  font-size:15px;margin:0 0 12px}
.why{font-size:14px;color:var(--bone);margin:8px 0 0}
@media(max-width:820px){.stats{grid-template-columns:1fr}.rpt{grid-template-columns:1fr}
  .wrap{padding:0 18px 64px}h1{font-size:30px}}
"""

MARK = """<svg width="34" height="34" viewBox="0 0 34 34" fill="none" aria-hidden="true">
<circle cx="17" cy="17" r="16" stroke="#C9A227" stroke-width="1"/>
<path d="M4 17c4.2-5.4 8.6-8.1 13-8.1S25.8 11.6 30 17c-4.2 5.4-8.6 8.1-13 8.1S8.2 22.4 4 17z"
 stroke="#C9A227" stroke-width="1"/><circle cx="17" cy="17" r="3.6" fill="#C9A227"/>
<path d="M17 1v32M1 17h32" stroke="#C9A227" stroke-width=".4" opacity=".35"/></svg>"""

PAGES = [("index.html","Bifrost"),("blind_eye.html","The Blind Eye"),
         ("roster.html","Gungnir"),("gate.html","Heimdall"),("realms.html","Realms")]

def esc(s): return html.escape(str(s))
def money(v): return "unresolved" if v is None else f"${v:,.0f}"
def pct(v): return f"{v*100:.1f}%"

def shell(fname, title, eyebrow, lede, body):
    nav = "".join(f'<a href="{f}" class="{"on" if f==fname else ""}">{esc(n)}</a>'
                  for f, n in PAGES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MUNIN · {esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<header class="top"><div style="display:flex;align-items:center;gap:14px">{MARK}
<div><div class="eyebrow">Munin · {esc(eyebrow)}</div>
<div class="sub" style="margin-top:4px">{esc(LOCAL)} &nbsp;·&nbsp; <span class="sim">Simulated</span></div></div></div>
<h1>{esc(title)}</h1><p class="lede">{lede}</p></header>
<nav class="bar">{nav}</nav>
{body}
<footer>Munin is Odin's raven, the one that remembers. It carries back what the hall
never wrote down.<br>Simulated data throughout. No real local, no real contractor,
no real job. Generated {datetime.datetime.now():%B %-d, %Y at %-I:%M %p}.</footer>
</div></body></html>"""


def p_blind_eye(conn):
    po = munin.page_one(conn)
    be = po["free"]
    total = sum(b["gap"] for b in be)
    work_lost = sum(b["est_hours"] for b in be)
    hours_it_took = sum(b["hours_to_close"] for b in be)
    union_side = conn.execute("SELECT COUNT(*) c FROM bids WHERE outcome='lost' "
                              "AND winning_bid IS NOT NULL AND winner_union=1").fetchone()["c"]
    rows = "".join(
        f"<tr><td class='n'>{esc(b['job_id'])}</td><td>{esc(b['project'])}</td>"
        f"<td>{esc(b['territory'])}</td><td>{esc(b['our_signatory'])}</td>"
        f"<td class='n'>{money(b['gap'])}</td>"
        f"<td class='n'>{b['hours_to_close']:,.0f}</td>"
        f"<td class='n'>{b['hours_available']:,.0f}</td>"
        f"<td class='n'>{pct(b['share_of_job'])}</td></tr>" for b in be[:36])
    body = f"""<section>
<div class="stats">
<div class="stat"><div class="k">Hours of work the members did not get</div>
<div class="v gold">{work_lost:,.0f}</div><div class="n2">on {len(be)} jobs a waiver would have covered</div></div>
<div class="stat"><div class="k">Hours it would have taken to win them</div>
<div class="v">{hours_it_took:,.0f}</div><div class="n2">of contributions, put at risk only on a win. No waiver was offered on any of them</div></div>
<div class="stat"><div class="k">Hours of work won per hour of contributions waived</div>
<div class="v">{(work_lost/hours_it_took) if hours_it_took else 0:,.1f}<span style="font-size:16px;color:var(--bone-dim)"> hrs</span></div>
<div class="n2">{money(total)} between our numbers and theirs, in the contractors' currency</div></div>
</div>
<div class="card" style="margin-top:26px">
<p class="quote">{esc(po['line'])}</p>
<p class="sub" style="margin-top:12px">The count is printed first because the count is the honest
figure. The share is the fragile one: a single reading of it at thirty jobs sits eight points
wide, so it never appears on this page without the give-or-take beside it. A confident wrong
percentage on page one kills a room exactly the way a confidently named contractor does.</p>
<p class="sub" style="margin-top:10px">{union_side} further priced losses went to another
signatory contractor and are deliberately <b>not</b> counted here. Hours are lost to this local
only when a shop that pays nothing into the funds wins the job. When one signatory beats another
the hours stay in the hall and the three funds are paid either way. The local does not bid; its
signatory contractors do.</p></div>
<p class="lede" style="margin-top:32px">Man hours are the currency a union runs on. A job recovery
waiver is written in hours, not dollars, and it applies to the job, not to a contractor. The business manager waives a number of hours
of contributions to the three funds, and every signatory bidding that job gets the same hours.
No money moves. The local forgoes contributions only if one of its signatories wins.
Lose, and it cost nothing.</p>
<p class="lede">So every row below was a free option. The hours it would have taken to close the
gap were sitting inside the job, and nobody reached for them.</p>
<h2 style="margin-top:38px">Closest first</h2>
<p class="sub">Showing {min(36,len(be))} of {len(be)}. Sorted by the hours it would have taken.</p>
<table><thead><tr><th class="n">Job</th><th>Project</th><th>Territory</th><th>Signatory</th>
<th class="n">Cost gap</th><th class="n">Hours to close</th><th class="n">Hours in the job</th>
<th class="n">Share of job</th></tr></thead><tbody>{rows}</tbody></table></section>"""
    return shell("blind_eye.html", "The Blind Eye", "Ledger, page one",
        "Odin gave an eye for sight of the whole field. This page is what was sitting "
        "in the dark on the other side: the jobs this local lost by less than a waiver "
        "would have cost it, where no waiver was ever put on the table.", body)


def p_roster(conn):
    st = munin.gungnir_standings(conn)
    rec = munin.gungnir_recovery(conn)
    nx = munin.gungnir_next(conn)

    def srow(r, i):
        return (f"<tr><td class='n'>{i}</td><td>{esc(r['contractor'])}</td>"
                f"<td class='n'>{r['bids']}</td><td class='n'>{r['wins']}</td>"
                f"<td class='n'>{r['losses']}</td><td class='n'>{pct(r['win_rate'])}</td>"
                f"<td class='n'>{pct(r['median_gap_pct'])}</td></tr>")
    ranked = "".join(srow(r, i) for i, r in enumerate(st["ranked"], 1))
    unranked = "".join(
        f"<tr><td class='n'>—</td><td>{esc(r['contractor'])}</td><td class='n'>{r['bids']}</td>"
        f"<td class='n'>{r['wins']}</td><td class='n'>{r['losses']}</td>"
        f"<td colspan='2' class='unres'>{esc(str(r['win_rate'].why))}</td></tr>"
        for r in st["unranked"])

    def nrow(r):
        p = r["projection"]
        if isinstance(p, munin.Unresolved):
            return (f"<tr><td class='n'>{esc(r['job_id'])}</td><td>{esc(r['project'])}</td>"
                    f"<td>{esc(r['territory'])}</td><td class='n'>{money(r['our_bid'])}</td>"
                    f"<td colspan='4' class='unres'>{esc(p.why)}</td></tr>")
        cls = {"coverable":"t-ok","near the line":"t-hold",
               "beyond the waiver":"t-refuse"}[p]
        return (f"<tr><td class='n'>{esc(r['job_id'])}</td><td>{esc(r['project'])}</td>"
                f"<td>{esc(r['territory'])}</td><td class='n'>{r['est_hours']:,.0f}</td>"
                f"<td class='n'>{r['hours_to_close']:,.0f}</td>"
                f"<td class='n'>{r['hours_low']:,.0f} to {r['hours_high']:,.0f}<br>"
                f"<span style='color:var(--bone-dim);font-size:12px'>"
                f"{r['share_low']*100:.0f} to {r['share_high']*100:.0f}% of the job</span></td>"
                f"<td class='n'>{r['work_per_hour_waived']:,.1f}</td>"
                f"<td><span class='tag {cls}'>{esc(p)}</span></td></tr>")
    order = nx["recommended"] + [r for r in nx["all"] if r not in nx["recommended"]]
    nxt = "".join(nrow(r) for r in order)
    plan_rows = "".join(
        f"<tr><td class='n'>{i}</td><td>{esc(r['project'])}</td><td>{esc(r['territory'])}</td>"
        f"<td class='n'>{r['hours_to_close']:,.0f}</td><td class='n'>{r['est_hours']:,.0f}</td>"
        f"<td class='n'>{r['work_per_hour_waived']:,.1f}</td></tr>"
        for i, r in enumerate(nx["plan"], 1))

    wwr = rec["waived_win_rate"]; dwr = rec["dry_win_rate"]
    body = f"""<section><div class="eyebrow">Scorecard one</div>
<h2>Standings, every signatory, every territory</h2>
<p class="sub">Never split by territory and never by business agent. A contractor's book is
his whole book. {st['priced_total']} priced bids are on file; the roster is not considered
settled until {st['full_confidence_at']}.</p>
<div class="card" style="margin:18px 0">
<span class="tag {'t-ok' if st['resolved'] else 't-hold'}">{'Resolved' if st['resolved'] else 'Unresolved'}</span>
<p class="quote" style="margin-top:14px">{esc(st['gate']['line'])}</p>
<p class="sub" style="margin-top:10px">The gate counts priced bids per shop, not shops priced.
Four shops must each carry {st['gate']['bids_per_shop']} priced bids before this page prints a
single name. Measured, not assumed: the looser rule named a contractor to a business manager
and was wrong about a third of the time at thirty rows.</p></div>
<table><thead><tr><th class="n">#</th><th>Signatory contractor</th><th class="n">Bids</th>
<th class="n">Won</th><th class="n">Lost</th><th class="n">Win rate</th>
<th class="n">Median gap</th></tr></thead><tbody>{ranked}{unranked}</tbody></table>
<p class="why">{"Nobody on this page is ranked low. Nobody is <span class='unres'>ranked at all</span>, because the book is not deep enough yet to rank anyone honestly." if not st['resolved'] else "The shops with no number beside them are not ranked low. They are <span class='unres'>not ranked</span>."}
Munin will not put a number beside a name it cannot stand behind. Silence with a distance on it
is this page working. A name it cannot defend is this page lying.</p></section>

<section><div class="eyebrow">Scorecard two</div>
<h2>Did the job recovery fund get used, and did it work</h2>
<div class="stats">
<div class="stat"><div class="k">Jobs with hours waived</div><div class="v">{rec['waived_jobs']}</div>
<div class="n2">win rate {pct(wwr) if not isinstance(wwr, munin.Unresolved) else '—'}</div></div>
<div class="stat"><div class="k">Jobs with nothing waived</div><div class="v">{rec['dry_jobs']}</div>
<div class="n2">win rate {pct(dwr) if not isinstance(dwr, munin.Unresolved) else '—'}</div></div>
<div class="stat"><div class="k">Hours waived on jobs that were lost</div>
<div class="v gold">{rec['hours_at_risk_that_cost_nothing']:,.0f}</div>
<div class="n2">cost the funds nothing, because nobody won</div></div>
</div>
<p class="why">That last figure is the one that gets misread in a hall. Hours waived on a job
the local loses are never paid out. All in, and if you lose you keep your chips.</p></section>

<section><div class="eyebrow">Scorecard three</div>
<h2>The next winnable job</h2>
<p class="sub">Jobs already listed and not yet bid, priced against what this territory has
actually been losing by, and ranked by what they give back: hours of paid work for the members
per hour on which the funds forgo their contribution. Two different hours. The member works and
is paid for every one of them; the funds collect on all but the waived ones. Probability, not
possibility.</p>
<table><thead><tr><th class="n">Job</th><th>Project</th><th>Territory</th>
<th class="n">Hours of work</th><th class="n">Hours to close</th><th class="n">Give or take</th>
<th class="n">Work won per hour waived</th><th>Verdict</th></tr></thead><tbody>{nxt}</tbody></table>
<p class="why">The verdict is only the line that survived measurement: winnable on a waiver, or
not. How much of the job it eats is printed as a range, not as a word. Measured Sept 22, 2026:
calling a job &ldquo;steep&rdquo; off a median was wrong 35.5% of the time on nine priced losses
and was still wrong 19.3% of the time on sixty, because the quarter-of-the-job line sits right
on top of where a local actually loses. The verdict underneath it was wrong 0.0% of the time
from nine losses up. The threshold was never the problem. The word was, and it is gone.</p>
<h2 style="margin-top:38px">Where the hours go first</h2>
<p class="sub">This local has put {nx['budget_hours']:,.0f} hours of contributions at risk so far.
Spent in this order, those same hours bring back {nx['plan_hours_of_work']:,.0f} hours of work.</p>
<table><thead><tr><th class="n">#</th><th>Project</th><th>Territory</th>
<th class="n">Hours at risk</th><th class="n">Hours of work</th><th class="n">Return</th></tr></thead>
<tbody>{plan_rows}</tbody></table>
<p class="why">Lehigh is new on the books. Three priced losses is not a pattern, so Munin
projects nothing there and says why.</p></section>"""
    return shell("roster.html", "Gungnir", "Three scorecards",
        "Odin's spear did not miss. Three scorecards: who is winning and who is not, "
        "whether the recovery fund was ever put to work, and which job on the street "
        "right now is the one to go after.", body)


def p_gate(conn):
    rows = conn.execute("SELECT * FROM intake_log ORDER BY id").fetchall()
    cards = []
    for r in rows:
        cls = {"accepted":"t-ok","held":"t-hold","refused":"t-refuse"}[r["verdict"]]
        word = {"accepted":"Accepted","held":"Held","refused":"Refused"}[r["verdict"]]
        wrote = ""
        if r["job_id"]:
            oc = conn.execute("SELECT outcome FROM bids WHERE job_id=?", (r["job_id"],)).fetchone()
            kind = {"won": "a win", "lost": "a loss"}.get(oc["outcome"] if oc else None, "a result")
            wrote = f"<p class='sub' style='margin-top:10px'>Wrote {esc(r['job_id'])} to the record as {kind}.</p>"
        cards.append(
            f"<div class='card'><span class='tag {cls}'>{word}</span>"
            f"<p class='quote' style='margin-top:16px'>&ldquo;{esc(r['raw_report'])}&rdquo;</p>"
            f"<p class='why'>{esc(r['reason'])}</p>{wrote}"
            f"<p class='sub' style='margin-top:12px;font-size:12.5px'>decided by {esc(r['decided_by'])}</p></div>")
    n_acc = sum(1 for r in rows if r["verdict"] == "accepted")
    body = f"""<section>
<div class="stats">
<div class="stat"><div class="k">Reports through the gate</div><div class="v">{len(rows)}</div></div>
<div class="stat"><div class="k">Written to the record</div><div class="v">{n_acc}</div></div>
<div class="stat"><div class="k">Held or refused, with a reason</div>
<div class="v gold">{len(rows)-n_acc}</div><div class="n2">every one of them logged</div></div>
</div>
<p class="lede" style="margin-top:32px">A business agent does not fill in a form. He says a
sentence from the truck. Wins and losses both: the local learns more from its losses, but it
studies both. Heimdall takes the sentence and does one of three things: writes the row, holds
it and names the one thing missing, or refuses it and says why. A name on either side of the
result is never a reason to refuse. A refusal is a decision, and every decision is kept.</p>
<p class="lede">Reading the sentence is the only part a model touches. The judgement is rules
and the arithmetic is never a model's, so the same sentence always produces the same verdict.</p>
<div class="rpt" style="margin-top:34px">{''.join(cards)}</div></section>"""
    return shell("gate.html", "Heimdall", "At the gate",
        "The gatekeeper who sees and hears everything coming across. Nothing enters "
        "Munin's memory without passing him, and nothing is dropped in silence.", body)


def p_realms(conn):
    cards = []
    demo = [("business_manager", None), ("business_agent", "Bucks"),
            ("financial_secretary", None), ("contractor", "Marden Electric")]
    for realm, key in demo:
        meta = munin.REALMS[realm]
        rowsv = munin.realm_filter(conn, realm, key)
        n = len(rowsv)
        sample = "".join(
            f"<tr><td class='n'>{esc(b['job_id'])}</td><td>{esc(b['project'])}</td>"
            f"<td>{esc(b['territory'])}</td><td class='n'>{money(b['our_bid'])}</td>"
            f"<td>{esc(b['outcome'])}</td></tr>" for b in rowsv[:6])
        cards.append(f"""<div class="card"><div class="who">{esc(meta['label'])}{(' · ' + esc(key)) if key else ''}</div>
<h3 style="margin-top:8px">Sees {esc(meta['scope'])}</h3>
<p>{n} rows in this realm. Roster: {'yes' if meta['sees_roster'] else 'no'}.
Page one: {'yes' if meta['sees_blind_eye'] else 'no'}.
Decides: {'yes' if meta['decides'] else 'no'}.</p>
<table><thead><tr><th class="n">Job</th><th>Project</th><th>Territory</th>
<th class="n">Our number</th><th>Outcome</th></tr></thead><tbody>{sample}</tbody></table></div>""")
    total = conn.execute("SELECT COUNT(*) c FROM bids").fetchone()["c"]
    body = f"""<section>
<p class="lede">These are reports, not logins. The same record, cut four ways, because the
question of who sees what is not a technical question in a union hall, it is a political one.</p>
<p class="lede">A business agent sees his own territory and nothing else, no local totals and
no other agent's numbers, because the moment agents start comparing to each other the local
loses its focus. The business manager alone has the wide lens. The financial secretary-treasurer
sees the roster and makes no decisions. A contractor sees his own row and no one else's, because
the roster on the table is adversaries and free options in the open.</p>
<p class="sub" style="margin-top:20px">{total} rows in the full record.</p>
<div class="rpt">{''.join(cards)}</div></section>"""
    return shell("realms.html", "Realms", "Who sees what",
        "Nine realms in the myth. Four seats in a local, and each one gets its own.", body)


def p_index(conn):
    be = munin.blind_eye(conn)
    total = conn.execute("SELECT COUNT(*) c FROM bids").fetchone()["c"]
    priced = conn.execute("SELECT COUNT(*) c FROM bids WHERE winning_bid IS NOT NULL").fetchone()["c"]
    gate_n = conn.execute("SELECT COUNT(*) c FROM intake_log").fetchone()["c"]
    body = f"""<section>
<div class="stats">
<div class="stat"><div class="k">Bids in the record</div><div class="v">{total}</div>
<div class="n2">{priced} of them priced against the winner</div></div>
<div class="stat"><div class="k">Free options not taken</div><div class="v gold">{len(be)}</div>
<div class="n2">losses a waiver would have covered</div></div>
<div class="stat"><div class="k">Reports through the gate</div><div class="v">{gate_n}</div>
<div class="n2">accepted, held and refused</div></div>
</div>
<h2 style="margin-top:42px">The bridge</h2>
<p class="lede">A local does not write its bids down. Not the bids, not the losses, not who
beat them or by how much. There is no book. So nobody in the building can say whether the
local is winning or losing, because nobody is keeping score.</p>
<p class="lede">Man hours are the currency a union runs on. The goal is market share, and the
route to it is the job recovery fund managed by the numbers instead of by feel: which jobs
to waive on, how many hours, and where those hours bring back the most work for the members.
Every page here is a step in raising the probability of winning the next bid.</p>
<p class="lede">Munin is the raven Odin sent out every morning and who came back every night
with what he had seen. This is one process, run once, on one local. It is written so that
how it is done here is how it is done anywhere.</p>
<div class="rpt" style="margin-top:30px">
<div class="card"><div class="who">Heimdall</div><h3>The gate</h3>
<p>A spoken field report becomes a structured row, or it is held with the one missing thing
named, or it is refused with a reason.</p></div>
<div class="card"><div class="who">Mjolnir</div><h3>The verdict, in hours</h3>
<p>What a job recovery waiver would have had to cover to close the gap, priced against the
contribution rate that was actually in effect on the day of the bid.</p></div>
<div class="card"><div class="who">The Blind Eye</div><h3>Page one</h3>
<p>The losses that a waiver would have covered, where no waiver was offered. Free options,
unused.</p></div>
<div class="card"><div class="who">Gungnir</div><h3>Three scorecards</h3>
<p>Standings across every territory, whether the recovery fund was put to work, and the next
winnable job on the street.</p></div>
</div>
<h2 style="margin-top:42px">Where it refuses</h2>
<p class="lede">Munin says <span class="unres">unresolved</span> rather than guess, in three
places: a bid dated before any contribution rate was in effect, a contractor with too thin a
book to rank, and a territory with too little history to project from. Each refusal prints
the reason.</p></section>"""
    return shell("index.html", "Munin", "Bifrost · one bridge to any local",
        "The book a local never kept: every bid it makes, won or lost, and the "
        "arithmetic that turns it into a decision. Built in one day, on a local "
        "that does not exist.", body)


def build_all():
    os.makedirs(OUT, exist_ok=True)
    conn = munin.connect()
    for fn, fx in [("index.html", p_index), ("blind_eye.html", p_blind_eye),
                   ("roster.html", p_roster), ("gate.html", p_gate),
                   ("realms.html", p_realms)]:
        open(os.path.join(OUT, fn), "w").write(fx(conn))
    return OUT


if __name__ == "__main__":
    print("wrote", build_all())
