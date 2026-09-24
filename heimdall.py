"""
HEIMDALL - the gatekeeper. Nothing enters MUNIN's memory without passing him.

A business agent does not file a form. He phones it in, or types a line from
the truck. Wins and losses both. The local learns more from its losses, but it
studies both, and a name on either side of the result is never a reason to
refuse. HEIMDALL takes the sentence and decides one of three things:

    ACCEPT  everything needed is there and the contractor is a signatory
    HOLD    one thing is missing; name it and ask for that one thing
    REFUSE  it cannot be a loss record and here is why

A refusal is a decision, and every decision is written down. Nothing is
silently dropped. The reading of the sentence is the only part a model
touches. The judgement is rules, and the arithmetic is never a model's.
"""
import os, re, json, urllib.request, datetime
import munin

MODEL = "claude-opus-5"
KEY_PATHS = [
    os.environ.get("MUNIN_KEY_FILE", ""),
    os.path.expanduser("~/Desktop/NORRIN/munin_key.txt"),
    os.path.expanduser("~/Desktop/NORRIN/_Keys/munin_key.txt"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "munin_key.txt"),
]

REQUIRED = ["project", "territory", "our_signatory", "our_bid", "est_hours", "outcome"]


def read_key():
    for p in KEY_PATHS:
        if p and os.path.exists(p):
            k = open(p).read().strip()
            if k.startswith("sk-ant-"):
                return k
    return None


# ------------------------------------------------------------ the reading

def _model_extract(text, key):
    """The model's only job: turn a sentence into fields, or say null."""
    prompt = (
        "You read one spoken field report from a construction union business "
        "agent about a job his local bid. Return ONLY JSON with these keys: "
        "project, territory, our_signatory, our_bid, winning_bid, winner, "
        "est_hours, outcome, bid_date. Use null for anything the report does "
        "not state. Never estimate, never infer a number that is not said. "
        "our_bid and winning_bid are dollars as plain numbers. outcome is "
        "won, lost, or open.\n\nReport: " + text
    )
    body = json.dumps({
        "model": MODEL, "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    raw = out["content"][0]["text"]
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)), "heimdall/model"


_AMOUNT = re.compile(r"\$?\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,}(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:k|m|million|thousand))",
                     re.I)
_COMPANY = re.compile(
    r"\b([A-Z][\w&'.-]*(?:\s+(?:&|and)\s+[A-Z][\w&'.-]*|\s+[A-Z][\w&'.-]*){0,3}"
    r"\s+(?:Electric|Electrical|Power|Systems|Services|Contractors|Group|Mechanical|Circuit|Line))\b")


def _to_number(tok):
    t = tok.lower().replace(",", "").replace("$", "").strip()
    mult = 1
    if t.endswith(("k", "thousand")):
        t = t.rstrip("k").replace("thousand", "").strip(); mult = 1_000
    elif t.endswith(("m", "million")):
        t = t.rstrip("m").replace("million", "").strip(); mult = 1_000_000
    try:
        return float(t) * mult
    except ValueError:
        return None


def _offline_extract(text):
    """Runs when no key is present, so the gate never stops. Deterministic.

    This reader is the floor, not the ceiling. It finds amounts by size and
    order rather than by phrasing, because a man in a truck does not phrase
    things the same way twice. Reading a sentence properly is the model's job.
    """
    t = text.lower()
    conn = munin.connect()

    signatories = [s["name"] for s in conn.execute("SELECT name FROM signatories")]
    territories = [r["name"] for r in conn.execute("SELECT name FROM territories")]

    # every company-shaped name in the sentence, in the order it was said.
    # one of ours is a signatory. anyone else is the other side of the result.
    companies = [c.strip() for c in _COMPANY.findall(text)]

    # IN THE ORDER IT WAS SAID, which is what this comment always claimed and
    # what the code did not do. Until Sept 22, 2026 the signatories were taken
    # in the order they sit in the local's list, so on a union-against-union
    # report the shop named second could land in our chair and the shop that
    # won be recorded as the bidder. The agent says his own shop first.
    def _said_at(name):
        i = t.find(name.lower())
        if i >= 0:
            return i
        first = name.lower().split()[0]
        return next((t.find(w) for w in t.split() if w.strip(",.") == first), -1)

    named_sigs = [s for s in signatories
                  if s.lower() in t or s.lower().split()[0] in t.split()]
    named_sigs.sort(key=lambda s: (_said_at(s) if _said_at(s) >= 0 else 10**6))
    ours = named_sigs[0] if named_sigs else None
    other = next((c for c in companies if c != ours), None)
    if other is None and len(named_sigs) > 1:
        other = named_sigs[1]          # union against union: a loss for ours, a win for the hall

    terr = next((r for r in territories if r.lower() in t), None)

    # hours
    hours = None
    mh = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:man[\s-]?hours|hours|hrs)", t)
    if mh:
        hours = _to_number(mh.group(1))

    # every money-sized amount, in order. hours are excluded by position.
    hours_span = mh.span() if mh else (-1, -1)
    amounts = [_to_number(m.group(1)) for m in _AMOUNT.finditer(text)
               if not (hours_span[0] <= m.start(1) < hours_span[1])]
    amounts = [a for a in amounts if a and a >= 10_000]
    our_bid = amounts[0] if amounts else None
    winning = amounts[1] if len(amounts) > 1 else None

    got = re.search(r"\b(we|they|[A-Z][\w&'.-]+(?:\s+[A-Z][\w&'.-]+){0,3})\s+"
                    r"(?:got|won|took|had|landed)\s+(?:it|that|the job|this one)\b", text, re.I)
    first = ours.lower().split()[0] if ours else None
    if re.search(r"\bwe (got|won|took|landed) (it|that|the job|this one)\b|\bwe won\b|\bwe were low\b", t) \
       or (first and re.search(r"\b" + re.escape(first) + r"\b[^.]{0,40}?\b(got|won|took|landed)\b", t)
           and not re.search(r"\b(lost|went to|beat us)\b", t)):
        outcome = "won"
    elif re.search(r"\b(lost|we lost|went to|beat us|they got it|and they got it|lost it)\b", t):
        outcome = "lost"
    elif got and ours and got.group(1).lower().split()[0] == ours.lower().split()[0]:
        outcome = "won"
    elif got:
        outcome = "lost"
    else:
        outcome = None

    proj = None
    mp = re.search(r"\b((?:[A-Z][\w'-]+\s+){1,4}(?:Building|Center|Centre|School|Facility|"
                   r"Renovation|Substation|Garage|Housing|Lab|Laboratory|Upgrade|"
                   r"Fit-Out|Buildout|Addition|Hall))\b", text)
    if mp:
        proj = mp.group(1).strip()

    return {
        "project": proj, "territory": terr, "our_signatory": ours,
        "our_bid": our_bid, "winning_bid": winning, "winner": other,
        "est_hours": hours, "outcome": outcome, "bid_date": None,
    }, "heimdall/rules"


def read_report(text):
    key = read_key()
    if key:
        try:
            return _model_extract(text, key)
        except Exception as e:
            f, _ = _offline_extract(text)
            f["_model_error"] = str(e)[:160]
            return f, "heimdall/rules"
    return _offline_extract(text)


# --------------------------------------------------------- the judgement

def decide(fields, conn):
    """Rules, not a model. Same sentence in, same verdict out."""
    missing = [k for k in REQUIRED if not fields.get(k)]

    if fields.get("our_signatory"):
        known = conn.execute("SELECT 1 FROM signatories WHERE name=?",
                             (fields["our_signatory"],)).fetchone()
        if not known:
            # the reader put the wrong party in our chair. move it, do not refuse.
            fields["winner"] = fields["winner"] or fields["our_signatory"]
            fields["our_signatory"] = None
            fields["outcome"] = fields.get("outcome") or "lost"

    if not fields.get("our_signatory"):
        who = fields.get("winner")
        if who:
            return ("held", f"{who} got it. Which of our signatories bid it? "
                            f"The result is recorded either way; it needs a name on our side.")

    if fields.get("territory"):
        known = conn.execute("SELECT 1 FROM territories WHERE name=?",
                             (fields["territory"],)).fetchone()
        if not known:
            return ("refused", f"{fields['territory']} is not a territory of this local.")

    if missing:
        first = missing[0].replace("our_", "our ").replace("_", " ")
        return ("held", f"cannot write the row without the {first}. "
                        f"Still needed: {', '.join(m.replace('_',' ') for m in missing)}.")

    dup = conn.execute(
        "SELECT job_id FROM bids WHERE project=? AND territory=? AND our_signatory=?",
        (fields["project"], fields["territory"], fields["our_signatory"])).fetchone()
    if dup:
        return ("refused", f"already on file as {dup['job_id']}. A result counted twice is a "
                           f"score that lies.")

    if fields.get("outcome") == "lost" and not fields.get("winning_bid"):
        return ("held", "a loss with no winning number is a rumour, not a record. "
                        "Ask who got it and for how much.")

    if fields.get("our_bid") and fields.get("winning_bid") and \
       fields["winning_bid"] > fields["our_bid"] and fields.get("outcome") == "lost":
        return ("refused", "the reported winning bid is higher than ours on a job we lost. "
                           "One of the two numbers is wrong.")
    _settle_sides(fields, conn)
    return ("accepted", "complete, and the contractor is on the signatory list")


def _settle_sides(fields, conn):
    """Which side of the funds the winner sits on. Rules, and exact match only.

    This is the field page one counts on, and until Sept 22, 2026 nothing set
    it: every row the gate wrote carried a null here and dropped straight out
    of the denominator without a word. Hours are lost only when a shop that
    pays nothing into the funds wins the job, so this field IS the loss.

    Exact match, case and whitespace normalised, checked against both lists.
    No similarity matching, not once, not behind a question mark. A name on
    neither list is not on our side, and that is a statement, not a guess:
    it is left null and the row is honest about not knowing.
    """
    def on_list(name, table):
        if not name:
            return False
        return conn.execute(
            f"SELECT 1 FROM {table} WHERE lower(trim(name))=?",
            (name.strip().lower(),)).fetchone() is not None

    if fields.get("outcome") == "won":
        # the local does not bid. Our signatory won it, and he is on the list.
        fields["winner"] = fields["our_signatory"]
        fields["winner_union"] = 1
        return
    w = fields.get("winner")
    if not w:
        fields["winner_union"] = None
    elif on_list(w, "signatories"):
        fields["winner_union"] = 1      # union against union: hours stay in the hall
    else:
        fields["winner_union"] = 0      # the hours left the funds


def gate(text, conn=None, write=True):
    """One report through the gate. Returns the whole decision, for showing."""
    conn = conn or munin.connect()
    fields, who = read_report(text)
    verdict, reason = decide(fields, conn)
    job_id = None
    if verdict == "accepted" and write:
        n = conn.execute("SELECT COUNT(*) c FROM bids").fetchone()["c"]
        job_id = f"J-{5000+n}"
        conn.execute(
            "INSERT INTO bids VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, fields.get("bid_date") or datetime.date.today().isoformat(),
             fields["territory"], fields["project"], fields.get("owner_gc"),
             fields["our_signatory"], fields["our_bid"], fields.get("winning_bid"),
             fields.get("winner"), fields.get("winner_union"), fields["est_hours"],
             0.0, fields["outcome"], "business agent",
             datetime.datetime.now().isoformat(timespec="seconds")))
    conn.execute("INSERT INTO intake_log (received_at, raw_report, verdict, reason, job_id, decided_by)"
                 " VALUES (?,?,?,?,?,?)",
                 (datetime.datetime.now().isoformat(timespec="seconds"),
                  text, verdict, reason, job_id, who))
    conn.commit()
    return {"report": text, "fields": fields, "verdict": verdict,
            "reason": reason, "job_id": job_id, "decided_by": who}
