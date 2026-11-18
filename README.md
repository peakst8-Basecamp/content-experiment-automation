# [[Content Experiment Automation]]

**peakst8 Base Camp · owner: Jitin · test length: 3 weeks**

We pay freelance "clippers" per verified view to post short videos about our app. The goal is to find out if this gets signups more cheaply than paid ads. Nobody on our team films or edits anything. We write the brief, approve the clips and pay only for views that happened.

The idea comes from [this post](https://x.com/isakeng9/status/2119827102123933909). It claims roughly $0.40 per 1,000 views, and 9M views and 5,000+ downloads for one app. Those are an agency's own sales numbers, so we run it ourselves and measure.

## How it works

```
brief + formats  ->  clippers post 20-30 videos/day  ->  views verified  ->  pay per 1,000 views  ->  signups tracked per clipper
```

Two ways to run it. The script works with both.

| | Whop Content Rewards (recommended) | DIY |
| --- | --- | --- |
| Finding clippers | Marketplace brings them | We recruit (Discord, college clubs, fitness creators) |
| View checks + payouts | Whop handles them | We check and pay by UPI ourselves |
| Minimum budget | $1,000 (check on the setup screen) | Whatever we choose |
| Best for | Speed, volume | Tight control, India-only creators |

## Step by step for Jitin

1. **Set up (day 1–2).** Run `python3 cx.py init`, then fill `config.json`: app name, one-liner, signup link, budget, rate, and our current **paid ads cost per signup**. That last number is what we are trying to beat.
2. **Build the swipe file (day 2–4).** Find 8–10 viral short videos from apps near ours. Add each to `data/formats.csv` with its hook, why it works and the link. Mark the best ones `use=yes`.
3. **Make the creator pack (day 3–5).** Put screen recordings, b-roll and the logo in one Drive folder (`assets_url`). Run `python3 cx.py brief` to get `out/brief.md`.
4. **Launch (day 5).** On Whop: create a free Whop product → Content Rewards → Clipping. Paste the brief, set the rate per 1,000 views, minimum views and per-clip cap from `config.json`, then add the budget.
5. **Track each clipper.** Add every clipper who joins to `data/clippers.csv`, run `python3 cx.py links` and send each one their own link from `out/links.csv`. Also add a "How did you hear about us?" question at signup.
6. **Review daily (weeks 1–2).** Copy clip links and views into `data/clips.csv` (from Whop's dashboard, or `python3 cx.py refresh` for YouTube Shorts). Export signups into `data/signups.csv`. Run `python3 cx.py report`. Approve or reject in Whop to match the report, and message the top clippers to post more.
7. **Decide (end of week 2–3).** The report gives a verdict: **scale**, **keep testing** or **stop / change formats**. Share `out/report.md` with the team.

## The automation

Standard library Python 3.9+, no installs.

```bash
python3 cx.py init      # create config.json
python3 cx.py links     # tracked signup link per clipper -> out/links.csv
python3 cx.py brief     # creator brief from the swipe file -> out/brief.md
python3 cx.py refresh   # pull YouTube Shorts views (needs YOUTUBE_API_KEY)
python3 cx.py report    # payouts, cost per signup, verdict -> out/report.md
```

What `report` does for each clip:
- **Rejects** it if the #ad / paid-partnership tag is missing or it's off brief.
- **Pays nothing** under the minimum views. Otherwise pays the rate per 1,000 views, up to the per-clip cap.
- **Holds** clips that look botted: high views with a very low like rate or almost no comments.
- Totals views, spend, cost per 1,000 views and signups per clipper and format. It compares cost per signup with paid ads and gives a verdict once 30+ tracked signups are in.

The `data/` files ship with sample rows so every command runs right away. Replace them with real data.

| File | One row per | Filled by |
| --- | --- | --- |
| `data/formats.csv` | viral format we want copied | Jitin |
| `data/clippers.csv` | clipper in the campaign | Jitin |
| `data/clips.csv` | posted clip, with views/likes/comments | Jitin (or `refresh`) |
| `data/signups.csv` | signup, with its UTM tags | export from the app |

## Rules every clip follows

- Tagged #ad or uses the platform's paid-partnership label. ASCI requires disclosure in India.
- No health, weight-loss or medical promises.
- Brand written as lowercase **peakst8**.
- No bought views. Those clips get rejected and unpaid.

## Sign-off needed

- Budget for the test (suggested $1,000).
- Rate per 1,000 views (suggested $1) and per-clip cap (suggested $150).
- Which app or club to promote first.
- Whop or DIY.

## Sources

- [Isak on X, 9 Nov 2026](https://x.com/isakeng9/status/2119827102123933909)
- [Whop docs: Content Rewards](https://docs.whop.com/manage-your-business/growth-marketing/content-rewards)
- [Content Rewards: how brands pay creators per 1,000 views](https://contentrewards.com/articles/how-brands-pay-creators-per-1000-views)
- [Findclout: Whop clipping pricing](https://findclout.com/blog/whop-clipping-pricing)
