"""Packs the repo into reports/MUNIN.zip so a copy of the code can be handed
to the judges. Simulated data only; no key, no database file."""
import os, zipfile
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "reports", "MUNIN.zip")
SKIP = {"munin.db", "MUNIN.zip", "__pycache__", ".git", ".vercel", "shots",
        "node_modules", "munin_key.txt"}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if f in SKIP or f.endswith(".pyc") or f.endswith(".db-journal"):
                continue
            p = os.path.join(dp, f)
            z.write(p, "munin/" + os.path.relpath(p, ROOT))
print("packed", OUT)
