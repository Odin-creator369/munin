# MUNIN

**The book a local never kept: every bid it makes, won or lost, and the arithmetic that turns it into a decision.**

Built in one day at the Coffee & Code Philadelphia AI Agent Hackathon, September 20, 2026.
Team of one. Simulated data throughout: no real local, no real contractor, no real job.

---

## The problem

A construction union local does not write its bids down. Not the bids, not the losses,
not who beat them or by how much. There is no book. Ask a business manager what his
market share was last quarter and he cannot tell you, because nobody is keeping score.

Construction trade union density has fallen about a point a year for seventy-five years.
The cause is not effort. It is information.

Munin is the raven Odin sent out every morning, who came back every night with what he
had seen. This is a local's memory, and the arithmetic that sits on top of it.

## Run it

```
python3 run.py
```

No install, no dependencies, Python 3.9 or later. It builds the local, puts field
reports through the gate, prices every loss, finds the free options, ranks the roster
and writes five report pages into `reports/`. Open `reports/index.html` in a browser.

To let the gate read field reports with a model instead of rules, put an Anthropic API
key in a plain text file at `~/Desktop/NORRIN/_Keys/munin_key.txt`, or set `MUNIN_KEY_FILE`
to wherever yours lives. The key is never read into the repository, and it is not
needed to run anything else.

## The parts

Each is named twice on purpose: the name the room knows from the films, and the myth
it came out of.

| | |
|---|---|
| **HEIMDALL** | The gate. A spoken field report, win or loss, becomes a structured row, or is held with the one missing thing named, or is refused with a reason. |
| **MJOLNIR** | The waiver verdict, in hours, priced against the contribution rate that was actually in effect on the day of the bid. |
| **THE BLIND EYE** | Page one. The losses a waiver would have covered where no waiver was offered. Free options, unused. |
| **GUNGNIR** | Three scorecards: standings across every territory, whether the recovery fund was put to work, and the next winnable job. |
| **REALMS** | Reports, not logins. Four seats in a local, each with its own view. |
| **BIFROST** | The process. One bridge, and it runs the same way on any local. |
| **MUNIN** | The memory that holds all of it. |

## What the agent actually does

`heimdall.py` is the only part that touches a language model, and its only job is
reading. A business agent does not fill in a form; he says a sentence from the truck.
The model turns that sentence into fields, and returns null for anything the sentence
does not state.

Every judgement after that is rules, and every number is ordinary arithmetic. Same
sentence in, same verdict out. A language model is not allowed near the money.

Wins and losses both go in the book. The local learns more from its losses, but it
studies both, and a contractor's name on either side of a result is never a reason to
refuse it. The gate returns one of three decisions, and all three are written to `intake_log`:

- **accept** and write the row
- **hold**, and name the one thing missing
- **refuse**, and say why

A refusal is a decision. Nothing is dropped in silence.

## Where it refuses

Munin says **unresolved** rather than guess, and prints the reason:

1. **A bid dated before any contribution rate was in effect.** Fund rates are
   renegotiated every year and the split across pension, annuity and health & welfare
   is not set until after the union meeting. Munin will not reach for today's rate to
   price a bid from last year.
2. **A roster built on a book that is too thin.** The gate counts **priced bids per
   shop, not shops priced**. Four shops must each carry **25 or more priced bids**, or
   the page names nobody at all. Not ranked low. Not ranked.
3. **A territory with too little history.** Under nine priced losses, no projection.

The roster is not treated as settled until four hundred priced bids are on file, and
the page says how far from that it is.

**And it is never mute about it.** An unresolved page that says nothing looks broken,
so it prints the distance instead:

> UNRESOLVED. 0 of 4 shops have 25 or more priced bids. Closest 4: Marden Electric 22,
> Copperline Contractors 21, Halloran Systems 19, Kestrel Power 18. About 20 more priced
> bids closes it.

Silence with a distance on it is the product working. Silence on its own is the product
broken. A name it cannot defend is the product lying.

## Where it shows its own precision

**Page one never prints a bare percentage.** The count comes first because the count is
the honest figure; the share comes second; the give-or-take is always beside it:

> 97 of 114 judged non-signatory losses were free options. That reads 85%, and on 114
> jobs the true figure sits between 77% and 90%.

A single reading of that share at thirty jobs sits about eight points wide, so a bare
percentage on page one is the same lie as a confidently named contractor. The band is a
Wilson score interval rather than the textbook one: measured here, the textbook interval
contained the truth only 70% of the time at thirty jobs where the share sits near a
boundary, against 97% for Wilson.

The same rule runs on the third scorecard. The verdict there is only the line that
survived measurement, winnable on a waiver or not, and how much of the job it eats is
printed as a **range** rather than as a word. Calling a job "steep" off a median was
measured wrong 35.5% of the time on nine priced losses and still wrong 19.3% of the time
on sixty. The verdict underneath it was wrong 0.0% of the time from nine losses up. The
word was the defect, not the threshold, and the word is gone.

## What counts as a loss

**Hours are lost only when a shop that pays nothing into the funds wins the job.** When
one signatory beats another, the hours stay in the hall and the three funds are paid
either way, so page one does not count it. The local does not bid; its signatory
contractors do, and which one won is already a field on the row.

Both results still go in the book. A name on either side of a result is never a reason
to refuse it.

## How a job recovery waiver actually works

This is the part outsiders get wrong, so it is worth stating plainly.

A waiver applies to a **job**, not to a contractor. The business manager, at his sole
discretion, waives a number of **hours** of the three funds' contributions. The same
hours go to every signatory bidding that job, whatever each one's own estimate says.
No money changes hands. The local forgoes contributions only if one of its signatories
wins. If they all lose, it cost nothing.

All in, and if you lose you keep your chips. That is why page one exists.

## Files

```
run.py        the whole chain, one command
munin.py      memory and arithmetic. no model anywhere in this file
heimdall.py   the gate. the only part that calls a model
seed.py       builds the synthetic local
render.py     the report pages
reports.py    the field reports that go through the gate
schema.sql    the bid record, wins and losses

simulate.py               99 field reports through the gate, scored honestly
                          python3 simulate.py [seed]
gate_test.py              the roster gate, four tests stated so they can fail
band_test.py              the give-or-take on page one, and Wilson against the textbook
territory_gate_test.py    measures MIN_LOSSES_TO_PROJECT instead of assuming it
```

## Built with

Python 3, SQLite, the Anthropic API for reading field reports, and generated HTML.
No framework, no server, no account. It runs off a folder.
