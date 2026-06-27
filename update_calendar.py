#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uppdaterar en prenumererbar ICS-kalender från TVmatchen.nu:
https://www.tvmatchen.nu/fotboll/fotbolls-vm

Regler:
- Använder tiden som står på TVmatchen.
- Tar bara med matcher där kanal kan fastställas till SVT eller TV4.
- Titlar: 🇲🇽Mexiko - 🇸🇪Sverige (TV4)
- Kalenderfilen skrivs till docs/fotbolls-vm-2026-tv4-svt.ics
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import re
import sys
import urllib.parse
import urllib.request

SOURCE_URL = "https://www.tvmatchen.nu/fotboll/fotbolls-vm"
OUTFILE = Path("docs/fotbolls-vm-2026-tv4-svt.ics")
TIMEZONE = "Europe/Stockholm"
TV4PLAY_URL = "https://www.tv4play.se/"
SVTPLAY_URL = "https://www.svtplay.se/"

FLAGS = {
    "Mexiko": "🇲🇽", "Sydafrika": "🇿🇦", "Sydkorea": "🇰🇷", "Tjeckien": "🇨🇿",
    "Kanada": "🇨🇦", "Bosnien": "🇧🇦", "Bosnien-Hercegovina": "🇧🇦",
    "Bosnien och Hercegovina": "🇧🇦", "USA": "🇺🇸", "Paraguay": "🇵🇾",
    "Qatar": "🇶🇦", "Schweiz": "🇨🇭", "Brasilien": "🇧🇷", "Marocko": "🇲🇦",
    "Haiti": "🇭🇹", "Skottland": "🏴", "Australien": "🇦🇺", "Turkiet": "🇹🇷",
    "Tyskland": "🇩🇪", "Curacao": "🇨🇼", "Curaçao": "🇨🇼", "Nederländerna": "🇳🇱",
    "Japan": "🇯🇵", "Elfenbenskusten": "🇨🇮", "Elfbenskusten": "🇨🇮", "Ecuador": "🇪🇨",
    "Sverige": "🇸🇪", "Tunisien": "🇹🇳", "Spanien": "🇪🇸", "Kap Verde": "🇨🇻",
    "Belgien": "🇧🇪", "Egypten": "🇪🇬", "Saudiarabien": "🇸🇦", "Uruguay": "🇺🇾",
    "Iran": "🇮🇷", "Nya Zeeland": "🇳🇿", "Frankrike": "🇫🇷", "Senegal": "🇸🇳",
    "Irak": "🇮🇶", "Norge": "🇳🇴", "Argentina": "🇦🇷", "Algeriet": "🇩🇿",
    "Österrike": "🇦🇹", "Jordanien": "🇯🇴", "Portugal": "🇵🇹",
    "DR Kongo": "🇨🇩", "D.R. Kongo": "🇨🇩", "Demokratiska republiken Kongo": "🇨🇩",
    "England": "🏴", "Kroatien": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
    "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
}

ALIASES = {
    "Bosnien-Hercegovina": "Bosnien",
    "Bosnien och Hercegovina": "Bosnien",
    "Elfbenskusten": "Elfenbenskusten",
    "Curaçao": "Curacao",
    "D.R. Kongo": "DR Kongo",
    "Demokratiska republiken Kongo": "DR Kongo",
}

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Maj": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Dec": 12,
}

@dataclass
class LinkChunk:
    href: str
    text: str
    attrs_text: str

@dataclass
class Match:
    start: datetime
    home: str
    away: str
    channel: str
    source_link: str

class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_a = False
        self.href = ""
        self.attrs_text = ""
        self.buf: list[str] = []
        self.links: list[LinkChunk] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        attr_values = " ".join(str(v) for _, v in attrs if v)
        if tag.lower() == "a":
            self.in_a = True
            self.href = attrs_dict.get("href", "")
            self.attrs_text = attr_values
            self.buf = []
        elif self.in_a:
            self.attrs_text += " " + attr_values

    def handle_data(self, data):
        if self.in_a:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.in_a:
            text = normalize(" ".join(self.buf))
            href = self.href
            if href:
                self.links.append(LinkChunk(href=href, text=text, attrs_text=normalize(self.attrs_text)))
            self.in_a = False
            self.href = ""
            self.attrs_text = ""
            self.buf = []

def normalize(s: str) -> str:
    s = html.unescape(s or "")
    s = s.replace("\xa0", " ").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()

def display_team(name: str) -> str:
    name = normalize(name)
    return ALIASES.get(name, name)

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 vm2026-calendar-updater/4.0",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")

def absolute_url(href: str) -> str:
    return urllib.parse.urljoin(SOURCE_URL, href)

def channel_from_text(text: str) -> str | None:
    t = normalize(text).upper()
    # Godkänn bara SVT eller TV4. Inga andra kanaler skrivs in i kalendern.
    if re.search(r"\bTV4\b|TV4 PLAY", t):
        return "TV4"
    if re.search(r"\bSVT\b|SVT1|SVT2|SVT PLAY", t):
        return "SVT"
    return None

def date_time_from_text(text: str) -> tuple[int, int, int, int] | None:
    # Ex: 27 Jun 21:00, 01 Jul 01:00
    m = re.search(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|Maj|Jun|Jul|Aug|Sep|Okt|Nov|Dec)\s+(\d{1,2}):(\d{2})\b", text)
    if not m:
        return None
    return int(m.group(1)), MONTHS[m.group(2)], int(m.group(3)), int(m.group(4))

def teams_from_text(text: str) -> tuple[str, str] | None:
    text = normalize(text)
    if " - " not in text:
        return None
    # Undvik att fånga rubriker eller odds.
    if "Fotbolls-VM" in text or len(text) > 80:
        return None
    left, right = [display_team(x) for x in text.split(" - ", 1)]
    if not left or not right:
        return None
    return left, right

def parse_main_page(raw_html: str) -> list[dict]:
    parser = AnchorCollector()
    parser.feed(raw_html)

    # Gruppera alla länktexter på samma href. TVmatchen har ofta separata länkar för tid, match och liga.
    grouped: dict[str, list[LinkChunk]] = {}
    for link in parser.links:
        grouped.setdefault(link.href, []).append(link)

    candidates = []
    for href, chunks in grouped.items():
        all_text = " | ".join([c.text for c in chunks if c.text] + [c.attrs_text for c in chunks if c.attrs_text])
        dt = None
        teams = None
        channel = channel_from_text(all_text)

        for c in chunks:
            if dt is None:
                dt = date_time_from_text(c.text) or date_time_from_text(c.attrs_text)
            if teams is None:
                teams = teams_from_text(c.text) or teams_from_text(c.attrs_text)

        if dt and teams:
            day, month, hour, minute = dt
            candidates.append({
                "start": datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TIMEZONE)),
                "home": teams[0],
                "away": teams[1],
                "channel": channel,
                "href": absolute_url(href),
                "all_text": all_text,
            })

    # Dedupe.
    seen = set()
    unique = []
    for c in candidates:
        key = (c["start"].strftime("%Y-%m-%d %H:%M"), c["home"], c["away"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    unique.sort(key=lambda x: x["start"])
    return unique

def fetch_detail_channel(url: str) -> str | None:
    try:
        page = fetch(url)
    except Exception:
        return None

    # Ta bort script/style grovt och sök text.
    page = re.sub(r"<script\b.*?</script>", " ", page, flags=re.I | re.S)
    page = re.sub(r"<style\b.*?</style>", " ", page, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", page)
    text = normalize(text)
    return channel_from_text(text)

def resolve_matches(candidates: list[dict]) -> list[Match]:
    matches: list[Match] = []
    for c in candidates:
        channel = c["channel"] or fetch_detail_channel(c["href"])
        if channel not in {"SVT", "TV4"}:
            print(f"Hoppar över utan SVT/TV4-kanal: {c['start']} {c['home']} - {c['away']}", file=sys.stderr)
            continue
        matches.append(Match(
            start=c["start"],
            home=c["home"],
            away=c["away"],
            channel=channel,
            source_link=c["href"],
        ))
    return matches

def flag_team(team: str) -> str:
    return f"{FLAGS.get(team, '')}{team}"

def esc_ical(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold_ical_line(line: str) -> str:
    out = []
    while len(line.encode("utf-8")) > 75:
        cut = len(line)
        while len(line[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)

def event_uid(m: Match) -> str:
    identity = f"{m.start:%Y%m%d%H%M}-{m.home}-{m.away}-{m.channel}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", identity).strip("-").lower()
    return f"fifa-world-cup-2026-{slug}@tvmatchen-calendar"

def build_ics(matches: list[Match]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sebastian//Fotbolls-VM 2026 TVmatchen//SV",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Fotbolls-VM 2026 - TV4/SVT",
        f"X-WR-TIMEZONE:{TIMEZONE}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT30M",
        "X-PUBLISHED-TTL:PT30M",
        "BEGIN:VTIMEZONE",
        f"TZID:{TIMEZONE}",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for m in matches:
        end = m.start + timedelta(minutes=15)
        stream = TV4PLAY_URL if m.channel == "TV4" else SVTPLAY_URL
        title = f"{flag_team(m.home)} - {flag_team(m.away)} ({m.channel})"
        description = "\n".join([
            "Tid enligt TVmatchen.",
            f"Kanal: {m.channel}",
            f"Källa: {SOURCE_URL}",
            f"Matchsida: {m.source_link}",
            f"Streaming: {stream}",
        ])
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event_uid(m)}",
            f"DTSTAMP:{now}",
            f"DTSTART;TZID={TIMEZONE}:{m.start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={TIMEZONE}:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{esc_ical(title)}",
            f"DESCRIPTION:{esc_ical(description)}",
            f"LOCATION:{esc_ical(m.channel)}",
            f"URL:{esc_ical(stream)}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ical_line(line) for line in lines) + "\r\n"

def write_index(match_count: int) -> None:
    index = f"""<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fotbolls-VM 2026 kalender</title>
</head>
<body>
  <h1>Fotbolls-VM 2026 - TV4/SVT</h1>
  <p>Kalendern uppdateras automatiskt från TVmatchen och använder tiden som står på sidan.</p>
  <p>Endast matcher med kanal SVT eller TV4 tas med.</p>
  <p><a href="fotbolls-vm-2026-tv4-svt.ics">Prenumerera på kalendern / ladda ner ICS</a></p>
  <p>Källa: <a href="{SOURCE_URL}">TVmatchen - Fotbolls-VM</a></p>
  <p>Senast genererad: {datetime.now(timezone.utc).isoformat(timespec="seconds")}</p>
  <p>Antal matcher i kalenderfilen: {match_count}</p>
</body>
</html>
"""
    (OUTFILE.parent / "index.html").write_text(index, encoding="utf-8")

def main() -> int:
    raw = fetch(SOURCE_URL)
    candidates = parse_main_page(raw)
    if len(candidates) < 20:
        print(f"Fel: hittade bara {len(candidates)} matcher på TVmatchen. Sidans format kan ha ändrats.", file=sys.stderr)
        return 1

    matches = resolve_matches(candidates)
    if len(matches) < 10:
        print(f"Fel: hittade bara {len(matches)} matcher med SVT/TV4. Kanalformatet kan ha ändrats.", file=sys.stderr)
        return 1

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(build_ics(matches), encoding="utf-8")
    write_index(len(matches))
    print(f"OK: skrev {OUTFILE} med {len(matches)} matcher från TVmatchen.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
