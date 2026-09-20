"""
Builds the synthetic local MUNIN runs on.

SIMULATED DATA. No real local, no real contractor, no real job.
The local number is XXX and always will be: it could be any local anywhere.
"""
import sqlite3, os, random
from datetime import date, timedelta
import munin

LOCAL = "Electricians Local XXX"
SEED = 369

TERRITORIES = [
    ("Philadelphia", "Agent 1"),
    ("Montgomery",   "Agent 2"),
    ("Bucks",        "Agent 3"),
    ("Delaware",     "Agent 4"),
    ("Chester",      "Agent 5"),
    ("Berks",        "Agent 6"),
    ("Lehigh",       "Agent 7"),   # newly tracked, almost no history
]

SIGNATORIES = [
    "Ironvale Electric", "Kestrel Power", "Brandt & Sons Electric",
    "Northgate Electrical", "Halloran Systems", "Copperline Contractors",
    "Marden Electric", "Quarry Ridge Electric", "Bellweather Power",
    "Sutton Line Electric", "Ardmore Circuit", "Voss Brothers Electric",
    "Penrose Electrical",
]

NON_UNION = ["Ridgeway Services", "Tri-State Mechanical & Electric",
             "Aspen Field Services", "Clearpoint Electrical", "Dorsey Group"]

PROJECT_WORDS = [
    "Distribution Center", "Medical Office Building", "High School Addition",
    "Water Treatment Upgrade", "Warehouse Fit-Out", "Municipal Garage",
    "Data Hall Buildout", "Senior Housing", "Community College Lab",
    "Transit Substation", "Cold Storage Facility", "Laboratory Renovation",
]
PLACES = ["Kingsbridge", "Marlow", "Pennfield", "Hartwell", "Sandbrook",
          "Elmglen", "Wexford", "Dunmore", "Ashby", "Colebrook", "Fenwick"]

GCS = ["Talbot Construction", "H. Reese Builders", "Orchard Ridge GC",
       "Whitmore & Vance", "Carrick Building Group", "Sterling Pike Inc."]


def build(path=munin.DB):
    if os.path.exists(path):
        os.remove(path)
    rng = random.Random(SEED)
    conn = munin.connect(path)
    conn.executescript(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "schema.sql")).read())

    # Effective-dated rates, modeled on a published Philadelphia building
    # trades schedule (the contract year turns over May 1). Shaded, not copied:
    # this is a simulated local, and no real local's exact figures appear here.
    # Three funds only. Retiree health, SUB and the working assessment are
    # not part of a job recovery waiver.
    conn.executemany(
        "INSERT INTO fund_rates VALUES (?,?,?,?,?)",
        [("2025-05-01", 16.60, 9.75, 16.10, "2025-26 contract year"),
         ("2026-05-01", 17.10, 10.10, 16.55, "2026-27 contract year, split set at the May meeting")])

    conn.executemany("INSERT INTO territories VALUES (?,?)", TERRITORIES)
    conn.executemany("INSERT INTO signatories VALUES (?,?)",
                     [(s, "on file") for s in SIGNATORIES])

    start = date(2025, 7, 1)
    rows = []
    n = 0

    # Three contractors are deliberately thin: GUNGNIR must refuse to rank them.
    thin = set(SIGNATORIES[-3:])

    for i in range(189):
        n += 1
        d = start + timedelta(days=rng.randint(0, 430))
        terr = rng.choice(TERRITORIES[:6])[0]
        sig = rng.choice(SIGNATORIES[:-3] if rng.random() < 0.94 else SIGNATORIES[-3:])
        project = f"{rng.choice(PLACES)} {rng.choice(PROJECT_WORDS)}"
        our_bid = round(rng.uniform(180_000, 3_400_000), -2)
        # man-hours roughly track the number, with real spread
        est_hours = round(our_bid / rng.uniform(220, 320), 0)

        r = rng.random()
        if r < 0.20:
            outcome, winning, winner, wu = "won", round(our_bid * rng.uniform(0.955, 0.999), -2), sig, 1
        elif r < 0.88:
            outcome = "lost"
            # most losses are close; that is the whole argument
            margin = rng.choice([rng.uniform(0.004, 0.030),
                                 rng.uniform(0.004, 0.030),
                                 rng.uniform(0.030, 0.075),
                                 rng.uniform(0.075, 0.180)])
            winning = round(our_bid * (1 - margin), -2)
            union_won = rng.random() < 0.22
            winner = rng.choice([s for s in SIGNATORIES if s != sig]) if union_won else rng.choice(NON_UNION)
            wu = 1 if union_won else 0
        else:
            outcome, winning, winner, wu = "open", None, None, None

        # waivers are rare and sized by feel, which is the practice today
        waived = 0.0
        if outcome in ("won", "lost") and rng.random() < 0.14:
            waived = float(rng.choice([80, 120, 160, 240, 320]))

        rows.append((f"J-{1000+n}", d.isoformat(), terr, project,
                     rng.choice(GCS), sig, our_bid, winning, winner, wu,
                     est_hours, waived, outcome, "business agent", "seeded"))

    # A territory the local only started tracking this quarter. Too thin to
    # project from, and GUNGNIR has to say so instead of inventing a number.
    for k in range(4):
        d = date(2026, 7, 6) + timedelta(days=k * 11)
        our_bid = round(rng.uniform(300_000, 1_200_000), -2)
        won = k == 0
        rows.append((f"J-{3000+k}", d.isoformat(), "Lehigh",
                     f"{rng.choice(PLACES)} {rng.choice(PROJECT_WORDS)}",
                     rng.choice(GCS), SIGNATORIES[1], our_bid,
                     round(our_bid * (0.99 if not won else 0.97), -2),
                     SIGNATORIES[1] if won else rng.choice(NON_UNION), 1 if won else 0,
                     round(our_bid / 270, 0), 0.0, "won" if won else "lost",
                     "business agent", "seeded"))
    rows.append((f"J-3900", "2026-08-30", "Lehigh",
                 f"{rng.choice(PLACES)} {rng.choice(PROJECT_WORDS)}",
                 rng.choice(GCS), SIGNATORIES[1], 740_000.0, None, None, None,
                 2740.0, 0.0, "open", "business agent", "seeded"))

    # Two records dated before any rate schedule exists. MUNIN must refuse to
    # price these rather than reach for today's rate.
    for k in range(2):
        d = date(2025, 4, 12 + k * 9)
        our_bid = round(rng.uniform(400_000, 900_000), -2)
        rows.append((f"J-{2000+k}", d.isoformat(), "Philadelphia",
                     f"{rng.choice(PLACES)} {rng.choice(PROJECT_WORDS)}",
                     rng.choice(GCS), SIGNATORIES[0], our_bid,
                     round(our_bid * 0.985, -2), rng.choice(NON_UNION), 0,
                     round(our_bid / 270, 0), 0.0, "lost", "business agent", "seeded"))

    conn.executemany(
        "INSERT INTO bids VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return conn


if __name__ == "__main__":
    c = build()
    print("local:", LOCAL, "(SIMULATED)")
    for k, q in [("bids", "SELECT COUNT(*) c FROM bids"),
                 ("lost", "SELECT COUNT(*) c FROM bids WHERE outcome='lost'"),
                 ("won",  "SELECT COUNT(*) c FROM bids WHERE outcome='won'"),
                 ("open", "SELECT COUNT(*) c FROM bids WHERE outcome='open'"),
                 ("priced","SELECT COUNT(*) c FROM bids WHERE winning_bid IS NOT NULL")]:
        print(f"  {k:7} {c.execute(q).fetchone()['c']}")
