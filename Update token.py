#!/usr/bin/env python3
"""
update_token.py - Run this every morning to push your new Upstox token to Railway.

Usage:
  python update_token.py

Set these 3 values below (or as env vars) once:
  RAILWAY_URL    = your Railway app URL  (e.g. https://nse-bot.up.railway.app)
  ADMIN_SECRET   = the secret you set in Railway env vars
  UPSTOX_TOKEN   = today's fresh token from developer.upstox.com
"""

import os, requests, sys

RAILWAY_URL  = os.getenv("RAILWAY_URL",  "https://YOUR-APP.up.railway.app")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "YOUR_ADMIN_SECRET_HERE")
UPSTOX_TOKEN = os.getenv("NEW_TOKEN",    "PASTE_TODAYS_TOKEN_HERE")

if "YOUR" in RAILWAY_URL or "YOUR" in ADMIN_SECRET or "PASTE" in UPSTOX_TOKEN:
    print("Edit update_token.py and fill in RAILWAY_URL, ADMIN_SECRET, and UPSTOX_TOKEN first.")
    sys.exit(1)

print(f"Pushing new token to {RAILWAY_URL} ...")

try:
    r = requests.post(
        f"{RAILWAY_URL}/api/update-token",
        json={"admin_secret": ADMIN_SECRET, "token": UPSTOX_TOKEN},
        timeout=15
    )
    data = r.json()
    if data.get("ok"):
        print(f"SUCCESS: {data.get('message')}")
    else:
        print(f"FAILED : {data.get('error')}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR  : {e}")
    sys.exit(1)