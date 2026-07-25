"""
test_sheets.py — one-off manual check that sheets_client.py can actually
reach UID_TRACKER before any FastAPI route depends on it.

Run locally with: python test_sheets.py
(needs the same env vars as the real app — GOOGLE_SERVICE_ACCOUNT at
minimum. Easiest way to get those into your local shell: copy them from
Railway's Variables tab into a local .env and load it, or export them
directly in your terminal for this one run.)

Safe to delete once you've confirmed it works — this isn't part of the
running app, main.py never imports it.
"""

from dotenv import load_dotenv
load_dotenv()

from sheets_client import get_sheets_client

client = get_sheets_client()
batches = client.get_batches()

print(f"Total batches (rows with both a METRC UID and a Batch ID): {len(batches)}")

if batches:
    print("\nFirst batch, as a sanity check on field mapping:")
    for key, value in batches[0].items():
        print(f"  {key}: {value}")

active = client.get_active_batches()
print(f"\nActive batches (inactive statuses filtered out): {len(active)}")

