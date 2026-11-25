#!/usr/bin/env python3
"""Build The Southern Africa Brief: turn episode scripts into audio and a podcast feed.

Reads episodes/YYYY-MM-DD.md, creates site/audio/YYYY-MM-DD.mp3 for any episode
that has no audio yet, then rewrites site/feed.xml and site/index.html.
Usage: python3 tools/build.py [--no-audio]   (--no-audio only checks scripts and rebuilds the feed)
"""
import asyncio, datetime as dt, html, json, re, shutil, sys, time
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
EP_DIR, SITE, AUDIO = ROOT / "episodes", ROOT / "site", ROOT / "site" / "audio"
CFG = json.loads((ROOT / "podcast.json").read_text(encoding="utf-8"))
SAST = dt.timezone(dt.timedelta(hours=2))
MIN_WORDS, MAX_WORDS = 120, 2200


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("missing the --- header block at the top")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip().strip('"')
    body = m.group(2)
    parts = re.split(r"^##\s+", body, flags=re.M)
    sections = {}
    for p in parts[1:]:
        head, _, rest = p.partition("\n")
        sections[head.strip().lower()] = rest.strip()
    if "script" not in sections:
        raise ValueError("missing a '## Script' section")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get("date", "")):
        raise ValueError("date must be YYYY-MM-DD")
    if meta["date"] != path.stem:
        raise ValueError(f"date {meta['date']} does not match the file name")
    for k in ("title", "description"):
        if not meta.get(k):
            raise ValueError(f"missing '{k}' in the header")
    spoken = spoken_text(sections["script"])
    words = len(spoken.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        raise ValueError(f"script is {words} words; expected {MIN_WORDS} to {MAX_WORDS}")
    sources = re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", sections.get("sources", ""))
    return {"meta": meta, "spoken": spoken, "words": words, "sources": sources, "path": path}


def spoken_text(script):
    out = []
    for line in script.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"\**\[[A-Z0-9 ]+\]\**", line):
            continue  # section labels such as **[STORY 1]** are not read aloud
        line = re.sub(r"\*\*|__|`|^#+\s*|^[-*]\s+", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = line.replace("—", ", ").replace("–", ", ")
        out.append(line)
    return "\n\n".join(out)


def publishable(ep):
    status = ep["meta"].get("status", "publish").lower()
    if status == "draft":
        return False
    return CFG.get("auto_publish", True) or status == "approved"


async def edge(text, out):
    import edge_tts
    await edge_tts.Communicate(text, CFG["voice"], rate=CFG.get("voice_rate", "+0%")).save(str(out))


def synthesise(text, out):
    tmp = out.with_suffix(".part.mp3")
    for attempt in range(3):
        try:
            asyncio.run(edge(text, tmp))
            if tmp.stat().st_size > 20000:
                tmp.replace(out)
                return "Microsoft Edge voice " + CFG["voice"]
        except Exception as e:  # network or service change
            print(f"  edge voice attempt {attempt + 1} failed: {e}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    from gtts import gTTS  # fallback: Google voice with a South African accent
    gTTS(text, lang="en", tld=CFG.get("fallback_voice_tld", "co.za")).save(str(tmp))
    tmp.replace(out)
    return "fallback Google voice (co.za)"


def duration(mp3):
    from mutagen.mp3 import MP3
    return int(round(MP3(str(mp3)).info.length))


def hms(sec):
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def build_feed(eps):
    base = CFG["site_url"].rstrip("/") + "/"
    now = format_datetime(dt.datetime.now(SAST))
    items = []
    for ep in eps:
        m, mp3 = ep["meta"], AUDIO / f"{ep['meta']['date']}.mp3"
        pub = dt.datetime.fromisoformat(m["date"]).replace(hour=6, tzinfo=SAST)
        notes = f"<p>{escape(m['description'])}</p><p>This episode is voiced by AI and written with AI research, reviewed by Lethabo Machabaphala.</p>"
        if ep["sources"]:
            notes += "<p>Sources:</p><ul>" + "".join(
                f'<li><a href="{escape(u)}">{escape(t)}</a></li>' for t, u in ep["sources"]) + "</ul>"
        items.append(f"""    <item>
      <title>{escape(m['title'])}</title>
      <description><![CDATA[{notes}]]></description>
      <itunes:summary>{escape(m['description'])}</itunes:summary>
      <pubDate>{format_datetime(pub)}</pubDate>
      <guid isPermaLink="false">{escape(base)}episodes/{m['date']}</guid>
      <enclosure url="{escape(base)}audio/{m['date']}.mp3" length="{mp3.stat().st_size}" type="audio/mpeg"/>
      <itunes:duration>{hms(ep['seconds'])}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(CFG['title'])}</title>
    <link>{escape(base)}</link>
    <atom:link href="{escape(base)}feed.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(CFG['description'])}</description>
    <language>{CFG['language']}</language>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{escape(CFG['author'])}</itunes:author>
    <itunes:summary>{escape(CFG['description'])}</itunes:summary>
    <itunes:owner><itunes:name>{escape(CFG['owner_name'])}</itunes:name><itunes:email>{escape(CFG['owner_email'])}</itunes:email></itunes:owner>
    <itunes:image href="{escape(base)}cover.jpg"/>
    <image><url>{escape(base)}cover.jpg</url><title>{escape(CFG['title'])}</title><link>{escape(base)}</link></image>
    <itunes:category text="{escape(CFG['category'])}"><itunes:category text="{escape(CFG['subcategory'])}"/></itunes:category>
    <itunes:explicit>{'true' if CFG['explicit'] else 'false'}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (SITE / "feed.xml").write_text(feed, encoding="utf-8")


def build_page(eps):
    rows = "".join(f"""
    <article>
      <h2>{html.escape(e['meta']['title'])}</h2>
      <p>{html.escape(e['meta']['description'])}</p>
      <audio controls preload="none" src="audio/{e['meta']['date']}.mp3"></audio>
      {'<details><summary>Sources</summary><ul>' + ''.join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for t, u in e['sources']) + '</ul></details>' if e['sources'] else ''}
    </article>""" for e in eps)
    page = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(CFG['title'])}</title>
<link rel="alternate" type="application/rss+xml" title="{html.escape(CFG['title'])}" href="feed.xml">
<style>
body{{font:17px/1.6 Georgia,serif;max-width:720px;margin:0 auto;padding:32px 20px;color:#14213d;background:#fbf8f2}}
header{{display:flex;gap:20px;align-items:center;margin-bottom:28px}} header img{{width:120px;border-radius:10px}}
h1{{margin:0;font-size:28px}} h2{{font-size:19px;margin:0 0 6px}} article{{padding:18px 0;border-top:1px solid #e3dccd}}
audio{{width:100%;margin-top:6px}} a{{color:#112047}} .sub{{color:#555;font-size:15px}}
</style></head><body>
<header><img src="cover.jpg" alt=""><div><h1>{html.escape(CFG['title'])}</h1>
<p class="sub">{html.escape(CFG['description'])}</p><p class="sub"><a href="feed.xml">Podcast feed (RSS)</a></p></div></header>
{rows or '<p>The first episode is on its way.</p>'}
</body></html>
"""
    (SITE / "index.html").write_text(page, encoding="utf-8")


def main():
    make_audio = "--no-audio" not in sys.argv
    AUDIO.mkdir(parents=True, exist_ok=True)
    if (ROOT / "cover.jpg").exists():
        shutil.copy(ROOT / "cover.jpg", SITE / "cover.jpg")
    eps, problems = [], []
    for path in sorted(EP_DIR.glob("*.md")):
        try:
            ep = parse(path)
        except ValueError as e:
            problems.append(f"{path.name}: {e}")
            continue
        if not publishable(ep):
            print(f"{path.name}: not published (status {ep['meta'].get('status')})")
            continue
        mp3 = AUDIO / f"{ep['meta']['date']}.mp3"
        if not mp3.exists():
            if not make_audio:
                print(f"{path.name}: valid, {ep['words']} words, audio not made (--no-audio)")
                continue
            print(f"{path.name}: making audio ({ep['words']} words)")
            print("  voice used:", synthesise(ep["spoken"], mp3))
        ep["seconds"] = duration(mp3)
        eps.append(ep)
    eps.sort(key=lambda e: e["meta"]["date"], reverse=True)
    build_feed(eps)
    build_page(eps)
    print(f"Feed built with {len(eps)} episode(s).")
    if problems:
        print("Scripts with problems (not published):\n  " + "\n  ".join(problems), file=sys.stderr)
        sys.exit(3)  # the workflow still publishes the good episodes, then reports the failure


if __name__ == "__main__":
    main()
