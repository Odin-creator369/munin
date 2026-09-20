"""
MUNIN - the raven that remembers.

Core memory and arithmetic for a construction local's loss record.
Nothing in this file calls a language model. Same bids in, same verdict out.

  MJOLNIR    the waiver verdict, in hours
  GUNGNIR    the three scorecards
  BLIND EYE  page one: the free options not taken
  REALMS     who sees what
"""
import sqlite3, os, statistics
from datetime import date

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "munin.db")


class Unresolved:
    """Not a number and not a guess. MUNIN says so out loud."""
    __slots__ = ("why",)
    def __init__(self, why): self.why = why
    def __bool__(self): return False
    def __repr__(self): return f"unresolved: {self.why}"
    def __str__(self): return f"unresolved: {self.why}"


MIN_BIDS_TO_RANK = 9        # below this, a contractor does not get ranked
MIN_LOSSES_TO_PROJECT = 9   # below this, a territory gets no probability
STEEP_SHARE = 0.25          # above this share of a job, the waiver is called steep
FULL_CONFIDENCE_BIDS = 400  # the line where the whole roster is considered settled


def connect(path=DB):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


# ---------------------------------------------------------------- rates

def rate_on(conn, on_date):
    """Combined hourly contribution to the three funds in effect on a date.

    Rates are renegotiated every year and the split across the funds is not
    known until after the union meeting, so this is a lookup, never a constant.
    No schedule in effect on that date means no verdict. It does not guess
    with today's rate.
    """
    row = conn.execute(
        "SELECT * FROM fund_rates WHERE effective_from <= ? "
        "ORDER BY effective_from DESC LIMIT 1", (on_date,)).fetchone()
    if row is None:
        return Unresolved(f"no contribution rate in effect on {on_date}")
    return {
        "effective_from": row["effective_from"],
        "pension": row["pension_per_hour"],
        "annuity": row["annuity_per_hour"],
        "hw": row["hw_per_hour"],
        "combined": round(row["pension_per_hour"] + row["annuity_per_hour"] + row["hw_per_hour"], 4),
    }


# -------------------------------------------------------------- MJOLNIR

def mjolnir(conn, bid):
    """The waiver verdict for one job, stated in HOURS.

    A job recovery waiver applies to a JOB, not to a contractor. The business
    manager waives a number of HOURS of the three funds' contributions, and
    the same hours go to every signatory bidding that job. No money moves.
    The local forgoes contributions only if one of its signatories wins.
    Lose, and it cost nothing.
    """
    r = rate_on(conn, bid["bid_date"])
    if isinstance(r, Unresolved):
        return {"verdict": r, "rate": None}

    if bid["winning_bid"] is None:
        return {"verdict": Unresolved("the winning number was never recovered"), "rate": r}

    gap = round(bid["our_bid"] - bid["winning_bid"], 2)
    if gap <= 0:
        return {"verdict": "no waiver needed", "rate": r, "gap": gap,
                "hours_to_close": 0.0, "coverable": True,
                "cost_if_won": 0.0, "cost_if_lost": 0.0}

    hours_to_close = gap / r["combined"]
    coverable = hours_to_close <= bid["est_hours"]
    return {
        "verdict": "coverable" if coverable else "beyond the waiver",
        "rate": r,
        "gap": gap,
        "hours_to_close": round(hours_to_close, 1),
        "hours_available": bid["est_hours"],
        "share_of_job": round(hours_to_close / bid["est_hours"], 4) if bid["est_hours"] else None,
        # cost to the funds is incurred only on a win
        "cost_if_won": round(hours_to_close * r["combined"], 2),
        "cost_if_lost": 0.0,
        "was_waived": bid["waived_hours"] > 0,
        "waived_hours": bid["waived_hours"],
    }


# ------------------------------------------------------------ BLIND EYE

def blind_eye(conn, territory=None):
    """Page one. The jobs lost by less than a waiver would have cost,
    where no waiver was ever offered. Free options the local did not take.

    Odin traded an eye for sight of the whole field. This is the page that
    shows what was sitting in the dark.
    """
    q = "SELECT * FROM bids WHERE outcome='lost' AND winning_bid IS NOT NULL"
    args = []
    if territory:
        q += " AND territory = ?"; args.append(territory)
    out = []
    for b in conn.execute(q, args):
        m = mjolnir(conn, b)
        if isinstance(m["verdict"], Unresolved):
            continue
        if m["verdict"] == "coverable" and not m["was_waived"]:
            out.append({**dict(b), **m})
    out.sort(key=lambda x: x["hours_to_close"])
    return out


# -------------------------------------------------------------- GUNGNIR

def gungnir_standings(conn):
    """Scorecard one: every signatory contractor ranked on win-loss, across
    ALL territories. Never by territory and never by business agent.
    A contractor with too thin a book is not ranked. It says unresolved.
    """
    rows = []
    for s in conn.execute("SELECT name FROM signatories ORDER BY name"):
        name = s["name"]
        bids = conn.execute(
            "SELECT * FROM bids WHERE our_signatory=? AND outcome IN ('won','lost')",
            (name,)).fetchall()
        priced = [b for b in bids if b["winning_bid"] is not None]
        wins = [b for b in bids if b["outcome"] == "won"]
        rec = {"contractor": name, "bids": len(bids), "priced": len(priced),
               "wins": len(wins), "losses": len(bids) - len(wins)}
        if len(priced) < MIN_BIDS_TO_RANK:
            rec["win_rate"] = Unresolved(
                f"{len(priced)} priced bids on file, {MIN_BIDS_TO_RANK} needed to rank")
            rec["median_gap_pct"] = Unresolved("too few priced bids")
            rec["rankable"] = False
        else:
            rec["win_rate"] = round(len(wins) / len(bids), 4)
            gaps = [ (b["our_bid"] - b["winning_bid"]) / b["our_bid"]
                     for b in priced if b["outcome"] == "lost" and b["our_bid"] ]
            rec["median_gap_pct"] = round(statistics.median(gaps), 4) if gaps else 0.0
            rec["rankable"] = True
        rows.append(rec)
    ranked = sorted([r for r in rows if r["rankable"]],
                    key=lambda r: (-r["win_rate"], r["median_gap_pct"]))
    unranked = [r for r in rows if not r["rankable"]]
    return {"ranked": ranked, "unranked": unranked,
            "priced_total": conn.execute(
                "SELECT COUNT(*) c FROM bids WHERE winning_bid IS NOT NULL").fetchone()["c"],
            "full_confidence_at": FULL_CONFIDENCE_BIDS}


def gungnir_recovery(conn):
    """Scorecard two: did the job recovery fund get used, and did it work."""
    waived_won = waived_lost = dry_won = dry_lost = 0
    hours_spent = 0.0
    for b in conn.execute("SELECT * FROM bids WHERE outcome IN ('won','lost')"):
        if b["waived_hours"] > 0:
            if b["outcome"] == "won":
                waived_won += 1
                r = rate_on(conn, b["bid_date"])
                if not isinstance(r, Unresolved):
                    hours_spent += b["waived_hours"]
            else:
                waived_lost += 1
        else:
            dry_won += 1 if b["outcome"] == "won" else 0
            dry_lost += 1 if b["outcome"] == "lost" else 0
    waived = waived_won + waived_lost
    dry = dry_won + dry_lost
    return {
        "waived_jobs": waived,
        "waived_win_rate": round(waived_won / waived, 4) if waived else Unresolved("no waivers on file"),
        "dry_jobs": dry,
        "dry_win_rate": round(dry_won / dry, 4) if dry else Unresolved("no unwaived jobs on file"),
        "hours_actually_spent": round(hours_spent, 1),
        "hours_at_risk_that_cost_nothing": round(
            sum(b["waived_hours"] for b in conn.execute(
                "SELECT * FROM bids WHERE outcome='lost' AND waived_hours>0")), 1),
    }


def gungnir_next(conn):
    """Scorecard three: of the jobs already listed and not yet bid, which
    ones are winnable, and what would it take. Probability, not possibility.

    A territory with too few priced losses gets no projection. It says so.
    """
    prof = {}
    for t in conn.execute("SELECT name FROM territories"):
        losses = conn.execute(
            "SELECT * FROM bids WHERE territory=? AND outcome='lost' "
            "AND winning_bid IS NOT NULL", (t["name"],)).fetchall()
        if len(losses) < MIN_LOSSES_TO_PROJECT:
            prof[t["name"]] = Unresolved(
                f"{len(losses)} priced losses in this territory, {MIN_LOSSES_TO_PROJECT} needed")
        else:
            prof[t["name"]] = statistics.median(
                [(b["our_bid"] - b["winning_bid"]) / b["our_bid"] for b in losses])

    out = []
    for b in conn.execute("SELECT * FROM bids WHERE outcome='open' ORDER BY bid_date"):
        p = prof[b["territory"]]
        row = dict(b)
        if isinstance(p, Unresolved):
            row["projection"] = p
            out.append(row); continue
        r = rate_on(conn, b["bid_date"])
        if isinstance(r, Unresolved):
            row["projection"] = r
            out.append(row); continue
        expected_gap = b["our_bid"] * p
        hours = expected_gap / r["combined"]
        row["expected_gap"] = round(expected_gap, 2)
        row["hours_to_close"] = round(hours, 1)
        row["coverable"] = hours <= b["est_hours"]
        row["share_of_job"] = round(hours / b["est_hours"], 4) if b["est_hours"] else None
        # the return, in the currency the hall runs on: hours of PAID WORK for
        # the members per hour on which the funds forgo their contribution.
        # two different hours: the member works and is paid for all of them;
        # the funds collect on all but the waived ones.
        row["work_per_hour_waived"] = round(b["est_hours"] / hours, 1) if hours > 0 else None
        if not row["coverable"]:
            row["projection"] = "beyond the waiver"
        elif row["share_of_job"] > STEEP_SHARE:
            row["projection"] = "steep"
        else:
            row["projection"] = "coverable"
        out.append(row)
    coverable = [r for r in out if r.get("projection") == "coverable"]
    coverable.sort(key=lambda r: -r["work_per_hour_waived"])

    # the budget: the hours this local has already shown it is willing to waive.
    # spend them where they bring back the most work, first.
    budget = conn.execute("SELECT COALESCE(SUM(waived_hours),0) h FROM bids").fetchone()["h"]
    plan, spent, gained = [], 0.0, 0.0
    for r in coverable:
        if spent + r["hours_to_close"] <= budget:
            plan.append(r); spent += r["hours_to_close"]; gained += r["est_hours"]
    return {"all": out, "recommended": coverable,
            "budget_hours": round(budget, 0), "plan": plan,
            "plan_hours_at_risk": round(spent, 0), "plan_hours_of_work": round(gained, 0)}


# ---------------------------------------------------------------- REALMS

REALMS = {
    "business_manager": {
        "label": "Business Manager",
        "scope": "every territory",
        "sees_roster": True, "sees_blind_eye": True, "decides": True,
    },
    "business_agent": {
        "label": "Business Agent",
        "scope": "his own territory only",
        "sees_roster": False, "sees_blind_eye": True, "decides": False,
    },
    "financial_secretary": {
        "label": "Financial Secretary-Treasurer",
        "scope": "every territory, read only",
        "sees_roster": True, "sees_blind_eye": True, "decides": False,
    },
    "contractor": {
        "label": "Signatory Contractor",
        "scope": "his own row only",
        "sees_roster": False, "sees_blind_eye": False, "decides": False,
    },
}


def realm_filter(conn, realm, key=None):
    """Each seat gets its own realm and nothing past it. A business agent
    sees his territory, never the local totals and never another agent's
    numbers. A contractor sees his own row and no one else's.
    """
    if realm == "business_agent":
        if not key:
            return Unresolved("a business agent view needs a territory")
        return conn.execute("SELECT * FROM bids WHERE territory=? ORDER BY bid_date DESC", (key,)).fetchall()
    if realm == "contractor":
        if not key:
            return Unresolved("a contractor view needs a contractor")
        return conn.execute("SELECT * FROM bids WHERE our_signatory=? ORDER BY bid_date DESC", (key,)).fetchall()
    if realm in ("business_manager", "financial_secretary"):
        return conn.execute("SELECT * FROM bids ORDER BY bid_date DESC").fetchall()
    return Unresolved(f"no such realm: {realm}")
