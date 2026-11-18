#!/usr/bin/env python3
"""Content Experiment Automation: run a pay-per-view clipping test for a peakst8 app.

Usage:
  python3 cx.py init      create config.json from the example
  python3 cx.py links     one tracked signup link per clipper   -> out/links.csv
  python3 cx.py brief     creator brief from the swipe file      -> out/brief.md
  python3 cx.py refresh   pull YouTube Shorts views (needs YOUTUBE_API_KEY)
  python3 cx.py report    payouts, cost per signup, verdict      -> out/report.md

Standard library only (Python 3.9+). Data lives in data/*.csv; edit those in any spreadsheet app.
"""
import csv
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")


def path(*parts):
    return os.path.join(ROOT, *parts)


def load_config():
    p = path("config.json")
    if not os.path.exists(p):
        p = path("config.example.json")
        print("note: config.json not found, using config.example.json (run `init` to make your own)")
    with open(p) as f:
        return json.load(f)


def read_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name, rows, fields, folder=DATA):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def num(value):
    try:
        return float(str(value).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def money(cfg, value):
    return f"{cfg['currency']}{value:,.2f}"


# ---------- init ----------

def cmd_init(cfg):
    target = path("config.json")
    if os.path.exists(target):
        print("config.json already exists; edit it directly.")
        return
    shutil.copy(path("config.example.json"), target)
    print("created config.json; set app name, signup link, rate and budget before launch.")


# ---------- links ----------

def tracked_link(cfg, clipper_id):
    params = {
        "utm_source": "clipping",
        "utm_medium": "short_video",
        "utm_campaign": cfg["campaign"],
        "utm_content": clipper_id,
    }
    base = cfg["signup_url"]
    sep = "&" if "?" in base else "?"
    return base + sep + urllib.parse.urlencode(params)


def cmd_links(cfg):
    rows = []
    for c in read_csv("clippers.csv"):
        rows.append({"clipper_id": c["clipper_id"], "handle": c["handle"], "link": tracked_link(cfg, c["clipper_id"])})
    write_csv("links.csv", rows, ["clipper_id", "handle", "link"], folder=OUT)
    print(f"wrote {len(rows)} tracked links to out/links.csv")


# ---------- brief ----------

def cmd_brief(cfg):
    formats = [f for f in read_csv("formats.csv") if f.get("use", "").lower() in ("yes", "y", "1")]
    rules = cfg["rules"]
    lines = [
        f"# {cfg['app_name']}: clipping brief",
        "",
        f"**What it is:** {cfg['one_liner']}",
        f"**Who it's for:** {cfg['audience']}",
        f"**Call to action:** {cfg['cta']}",
        "",
        "## How you get paid",
        f"- {money(cfg, cfg['rate_per_1k_views'])} per 1,000 verified views.",
        f"- A clip earns nothing under {int(cfg['min_views']):,} views.",
        f"- One clip can earn at most {money(cfg, cfg['max_payout_per_clip'])}.",
        "- Clips are reviewed within 24 hours; off-brief clips are rejected.",
        "",
        "## Formats to copy (make your own version)",
    ]
    for i, f in enumerate(formats, 1):
        lines += [
            f"### {i}. {f['format']}",
            f"- Hook: \"{f['hook']}\"",
            f"- Why it works: {f['why_it_works']}",
            f"- Reference: {f['example_url']}",
            "",
        ]
    lines += ["## Must do"] + [f"- {r}" for r in rules["must"]]
    lines += ["", "## Never do"] + [f"- {r}" for r in rules["never"]]
    lines += ["", "## Assets", f"- {cfg['assets_url']}"]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "brief.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote out/brief.md with {len(formats)} formats")


# ---------- refresh ----------

YT_ID = re.compile(r"(?:shorts/|v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def cmd_refresh(cfg):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("YOUTUBE_API_KEY not set. Enter TikTok/Instagram/YouTube views in data/clips.csv by hand"
              " (or paste them from the Whop dashboard), then run `report`.")
        return
    clips = read_csv("clips.csv")
    fields = list(clips[0].keys()) if clips else []
    ids = {}
    for c in clips:
        m = YT_ID.search(c["url"])
        if m:
            ids[m.group(1)] = c
    updated = 0
    id_list = list(ids)
    for start in range(0, len(id_list), 50):
        batch = id_list[start:start + 50]
        q = urllib.parse.urlencode({"part": "statistics", "id": ",".join(batch), "key": key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/videos?{q}", timeout=20) as r:
            data = json.load(r)
        for item in data.get("items", []):
            s = item["statistics"]
            c = ids[item["id"]]
            c["views"] = s.get("viewCount", c["views"])
            c["likes"] = s.get("likeCount", c["likes"])
            c["comments"] = s.get("commentCount", c["comments"])
            updated += 1
    write_csv("clips.csv", clips, fields)
    print(f"updated {updated} YouTube clips; other platforms stay as entered")


# ---------- report ----------

def review(cfg, clip):
    """Return (status, payout, note) for one clip."""
    views, likes, comments = num(clip["views"]), num(clip["likes"]), num(clip["comments"])
    if clip.get("ad_tag", "").lower() not in ("yes", "y", "1"):
        return "reject", 0.0, "no #ad / paid-partnership tag"
    if clip.get("on_brief", "yes").lower() in ("no", "n", "0"):
        return "reject", 0.0, "off brief"
    note = ""
    flags = cfg["fraud_flags"]
    if views >= flags["check_above_views"]:
        if views and likes / views < flags["min_like_rate"]:
            note = f"check: like rate {likes / views:.2%}"
        elif comments < flags["min_comments"]:
            note = f"check: only {int(comments)} comments"
    if views < cfg["min_views"]:
        return "approved", 0.0, note or "under minimum views"
    payout = min(views / 1000 * cfg["rate_per_1k_views"], cfg["max_payout_per_clip"])
    return ("hold" if note else "approved"), payout, note


def cmd_report(cfg):
    clips = read_csv("clips.csv")
    signups = read_csv("signups.csv")
    clippers = {c["clipper_id"]: c["handle"] for c in read_csv("clippers.csv")}

    signups_by = defaultdict(int)
    for s in signups:
        if s.get("utm_campaign") == cfg["campaign"]:
            signups_by[s.get("utm_content", "")] += 1
    survey = sum(1 for s in signups if s.get("heard_from", "").lower() in ("tiktok", "reels", "instagram", "shorts", "youtube"))

    per_clip, by_clipper, by_format = [], defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0, 0])
    total_views = paid = held = 0.0
    for c in clips:
        status, payout, note = review(cfg, c)
        v = num(c["views"])
        per_clip.append((c, status, payout, note))
        if status == "reject":
            continue
        total_views += v
        if status == "hold":
            held += payout
            continue
        paid += payout
        by_clipper[c["clipper_id"]][0] += v
        by_clipper[c["clipper_id"]][1] += payout
        f = by_format[c["format"]]
        f[0] += v
        f[1] += payout
        f[2] += 1

    attributed = sum(signups_by[k] for k in by_clipper) or 0
    cpm = (paid + held) / total_views * 1000 if total_views else 0
    cps = paid / attributed if attributed else None
    budget_left = cfg["budget"] - paid - held
    target = cfg["paid_ads_cost_per_signup"]

    if cps is None or attributed < cfg["min_signups_for_verdict"]:
        verdict = f"NOT ENOUGH DATA: {attributed} tracked signups so far; wait for {cfg['min_signups_for_verdict']}."
    elif cps <= target * 0.8:
        verdict = f"SCALE: {money(cfg, cps)} per signup beats paid ads ({money(cfg, target)}) by 20%+."
    elif cps <= target:
        verdict = f"KEEP TESTING: {money(cfg, cps)} per signup is level with paid ads ({money(cfg, target)})."
    else:
        verdict = f"STOP OR CHANGE FORMATS: {money(cfg, cps)} per signup is worse than paid ads ({money(cfg, target)})."

    L = [
        f"# {cfg['app_name']}: clipping report ({cfg['campaign']})",
        "",
        f"**Verdict:** {verdict}",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Clips submitted | {len(clips)} |",
        f"| Verified views (approved + held) | {int(total_views):,} |",
        f"| Payable now | {money(cfg, paid)} |",
        f"| On hold for fraud check | {money(cfg, held)} |",
        f"| Budget left | {money(cfg, budget_left)} of {money(cfg, cfg['budget'])} |",
        f"| Effective cost per 1,000 views | {money(cfg, cpm)} |",
        f"| Signups from tracked links | {attributed} |",
        f"| Signups saying they came from short video | {survey} |",
        f"| Cost per tracked signup | {money(cfg, cps) if cps is not None else '-'} |",
        f"| Paid ads cost per signup (target) | {money(cfg, target)} |",
        "",
        "## Top clippers",
        "| Clipper | Views | Payout | Signups |",
        "| --- | --- | --- | --- |",
    ]
    for cid, (v, p) in sorted(by_clipper.items(), key=lambda kv: -kv[1][0])[:5]:
        L.append(f"| {clippers.get(cid, cid)} | {int(v):,} | {money(cfg, p)} | {signups_by[cid]} |")
    L += ["", "## Formats", "| Format | Clips | Views | Payout |", "| --- | --- | --- | --- |"]
    for name, (v, p, n) in sorted(by_format.items(), key=lambda kv: -kv[1][0]):
        L.append(f"| {name} | {n} | {int(v):,} | {money(cfg, p)} |")
    L += ["", "## Clip review (approve in Whop to match)", "| Clip | Clipper | Views | Status | Payout | Note |",
          "| --- | --- | --- | --- | --- | --- |"]
    for c, status, payout, note in per_clip:
        L.append(f"| {c['url']} | {clippers.get(c['clipper_id'], c['clipper_id'])} | {int(num(c['views'])):,} "
                 f"| {status} | {money(cfg, payout)} | {note} |")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L[:18]))
    print("\nfull report: out/report.md")


COMMANDS = {"init": cmd_init, "links": cmd_links, "brief": cmd_brief, "refresh": cmd_refresh, "report": cmd_report}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](load_config())
