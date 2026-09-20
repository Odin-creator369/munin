-- MUNIN / BIFROST schema. One bridge to any local.
-- Every table is local-agnostic: nothing here names a real local.

PRAGMA journal_mode=WAL;

-- Effective-dated fund contribution rates.
-- Rates change every year by contract. Which fund gets what is not known
-- until after the union meeting, so rates are effective-dated, never fixed.
CREATE TABLE IF NOT EXISTS fund_rates (
  effective_from TEXT PRIMARY KEY,      -- ISO date the rate takes effect
  pension_per_hour   REAL NOT NULL,
  annuity_per_hour   REAL NOT NULL,
  hw_per_hour        REAL NOT NULL,     -- health & welfare
  note TEXT
);

-- Signatory contractors. The local's own side of the table.
CREATE TABLE IF NOT EXISTS signatories (
  name TEXT PRIMARY KEY,
  signatory_since TEXT
);

-- Territories. One business agent per territory.
CREATE TABLE IF NOT EXISTS territories (
  name TEXT PRIMARY KEY,
  business_agent TEXT NOT NULL
);

-- THE LOSS RECORD. One row per bid the local can account for.
-- This table does not exist in a union hall today. That is the point.
CREATE TABLE IF NOT EXISTS bids (
  job_id            TEXT PRIMARY KEY,
  bid_date          TEXT NOT NULL,
  territory         TEXT NOT NULL REFERENCES territories(name),
  project           TEXT NOT NULL,
  owner_gc          TEXT,
  our_signatory     TEXT NOT NULL REFERENCES signatories(name),
  our_bid           REAL NOT NULL,
  winning_bid       REAL,               -- NULL = not yet known
  winner            TEXT,
  winner_union      INTEGER,            -- 1 union, 0 non-union, NULL unknown
  est_hours         REAL NOT NULL,      -- man-hours in the estimate
  waived_hours      REAL NOT NULL DEFAULT 0,  -- hours of fund contributions waived on THIS JOB
  outcome           TEXT NOT NULL CHECK (outcome IN ('won','lost','open')),
  reported_by       TEXT,
  recorded_at       TEXT NOT NULL
);

-- Everything HEIMDALL refused, and why. A refusal is a decision, and
-- a decision is evidence. Nothing is silently dropped.
CREATE TABLE IF NOT EXISTS intake_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at   TEXT NOT NULL,
  raw_report    TEXT NOT NULL,
  verdict       TEXT NOT NULL CHECK (verdict IN ('accepted','held','refused')),
  reason        TEXT,
  job_id        TEXT,
  decided_by    TEXT NOT NULL      -- 'heimdall/rules' or 'heimdall/model'
);
