#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skapar/uppdaterar en prenumererbar iCal-kalender för Fotbolls-VM 2026
från Svensk Fotbolls TV-schema.

Fokus:
- Behåller samma kalenderfil: docs/fotbolls-vm-2026-tv4-svt.ics
- Behåller stabila UID:er för att undvika dubbletter i prenumererad kalender.
- Kalenderhändelserna startar vid avspark.
- Titlar: 🇲🇽Mexiko - 🇸🇪Sverige (TV4)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import sys
import urllib.request

SOURCE_URL = "https://www.svenskfotboll.se/nyheter/landslag/2026/05/sa-sands-vm/"
TV4PLAY_URL = "https://www.tv4play.se/"
SVTPLAY_URL = "https://www.svtplay.se/"
OUTFILE = Path("docs/fotbolls-vm-2026-tv4-svt.ics")
TIMEZONE = "Europe/Stockholm"

MONTHS = {
    "januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6,
    "juli": 7, "augusti": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
    "jun": 6, "jul": 7,
}

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
    "DR Kongo": "🇨🇩", "Demokratiska republiken Kongo": "🇨🇩",
    "England": "🏴", "Kroatien": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
    "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
}

# Samma namnform som tidigare kalender när det går.
DISPLAY_ALIASES = {
    "Bosnien-Hercegovina": "Bosnien",
    "Bosnien och Hercegovina": "Bosnien",
    "Elfbenskusten": "Elfenbenskusten",
    "Curaçao": "Curacao",
    "Demokratiska republiken Kongo": "DR Kongo",
}

# Matchnummer för slutspel enligt tidigare TV4-tabell.
# Används för att behålla exakt samma UID som tidigare för slutspelsmatcherna:
# fifa-world-cup-2026-73@vm2026-calendar-updater osv.
KNOCKOUT_MATCH_NUMBERS_BY_DATETIME = {
    "2026-06-28 21:00": "73",
    "2026-06-29 19:00": "76",
    "2026-06-29 22:30": "74",
    "2026-06-30 03:00": "75",
    "2026-06-30 19:00": "78",
    "2026-06-30 23:00": "77",
    "2026-07-01 03:00": "79",
    "2026-07-01 18:00": "80",
    "2026-07-01 22:00": "82",
    "2026-07-02 02:00": "81",
    "2026-07-02 21:00": "84",
    "2026-07-03 01:00": "83",
    "2026-07-03 05:00": "85",
    "2026-07-03 20:00": "88",
    "2026-07-04 00:00": "86",
    "2026-07-04 03:30": "87",
    "2026-07-04 19:00": "90",
    "2026-07-04 23:00": "89",
    "2026-07-05 22:00": "91",
    "2026-07-06 02:00": "92",
    "2026-07-06 21:00": "93",
    "2026-07-07 02:00": "94",
    "2026-07-07 18:00": "95",
    "2026-07-07 22:00": "96",
    "2026-07-09 22:00": "97",
    "2026-07-10 21:00": "98",
    "2026-07-11 23:00": "99",
    "2026-07-12 03:00": "100",
    "2026-07-14 21:00": "101",
    "2026-07-15 21:00": "102",
    "2026-07-18 23:00": "103",
    "2026-07-19 21:00": "104",
}

@dataclass
class Match:
    date: datetime
    kickoff: str
    home: str
    away: str
    channel: str
    raw_line: str

class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.replace("\xa0", " ").split())
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.parts)

def fetch_page_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 vm2026-calendar-updater/3.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()

def normalize(value: str) -> str:
    value = value.replace("\xa0", " ").replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" :")

def display_team(name: str) -> str:
    name = normalize(name)
    return DISPLAY_ALIASES.get(name, name)

def channel_from_line(line: str) -> str | None:
    upper = line.upper()
    if "TV4" in upper:
        return "TV4"
    if "SVT" in upper:
        return "SVT"
    return None

def clean_team_name(name: str) -> str:
    return display_team(normalize(name))

def split_teams(blob: str) -> tuple[str, str] | None:
    blob = normalize(blob)
    blob = re.sub(r"\s*\([^)]*\)\s*", " ", blob)
    blob = normalize(blob)

    # Format: "Mexiko - Sydafrika", "Kanada - Bosnien-Hercegovina", "W73 - W75"
    m = re.match(r"^(.+?)\s*-\s*(.+)$", blob)
    if m:
        return clean_team_name(m.group(1)), clean_team_name(m.group(2))

    # Fallback om bindestreck saknas.
    parts = blob.split()
    if len(parts) >= 2:
        mid = len(parts) // 2
        return clean_team_name(" ".join(parts[:mid])), clean_team_name(" ".join(parts[mid:]))

    return None

def get_kickoff(line: str) -> str | None:
    # Prioritera uttrycklig avspark.
    m = re.search(r"avspark\s+(\d{1,2})\.(\d{2})", line, flags=re.IGNORECASE)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    # Annars första tid i raden.
    m = re.search(r"(?<!\d)(\d{1,2})\.(\d{2})(?!\d)", line)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    return None

def extract_team_blob(line: str) -> str | None:
    line = normalize(line)

    # Om raden har kolon, står lagen oftast efter kolon.
    candidate = line.split(":", 1)[1] if ":" in line else line

    # Ta bort inledande sändningstid eller matchrubrik.
    candidate = re.sub(r"^[A-Za-zÅÄÖåäö ]*\s*\d{1,2}\.\d{2}(?:-\d{1,2}\.\d{2})?\s*", "", candidate)
    candidate = re.sub(r"^\([^)]*\)\s*", "", candidate)
    candidate = normalize(candidate)

    # Klipp vid arena/ort eller parentes.
    candidate = candidate.split(",", 1)[0]
    candidate = re.sub(r"\([^)]*\)", "", candidate)
    candidate = normalize(candidate)
    return candidate or None

def parse_matches(text: str) -> list[Match]:
    matches: list[Match] = []
    current_date: datetime | None = None

    heading_re = re.compile(
        r"^(?:Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+(\d{1,2})\s+([a-zåäö]+)$",
        flags=re.IGNORECASE
    )

    lines = [normalize(l) for l in text.splitlines() if normalize(l)]

    expanded_lines: list[str] = []
    for line in lines:
        line = re.sub(
            r"\s+(Måndag|Tisdag|Onsdag|Torsdag|Fredag|Lördag|Söndag)\s+(\d{1,2})\s+(juni|juli)\b",
            r"\n\1 \2 \3",
            line,
            flags=re.IGNORECASE
        )
        expanded_lines.extend([normalize(x) for x in line.splitlines() if normalize(x)])

    for line in expanded_lines:
        h = heading_re.match(line)
        if h:
            day = int(h.group(1))
            month = MONTHS[h.group(2).lower()]
            current_date = datetime(2026, month, day, tzinfo=ZoneInfo(TIMEZONE))
            continue

        if current_date is None:
            continue

        channel = channel_from_line(line)
        if not channel:
            continue

        kickoff = get_kickoff(line)
        if not kickoff:
            continue

        blob = extract_team_blob(line)
        if not blob:
            continue

        teams = split_teams(blob)
        if not teams:
            continue

        home, away = teams
        matches.append(Match(
            date=current_date,
            kickoff=kickoff,
            home=home,
            away=away,
            channel=channel,
            raw_line=line,
        ))

    seen: set[tuple[str, str, str, str]] = set()
    unique: list[Match] = []
    for m in matches:
        key = (m.date.strftime("%Y-%m-%d"), m.kickoff, m.home, m.away)
        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique

def flag_team(team: str) -> str:
    return f"{FLAGS.get(team, '')}{team}"

def esc_ical(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold_ical_line(line: str) -> str:
    out: list[str] = []
    while len(line.encode("utf-8")) > 75:
        cut = len(line)
        while len(line[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)

def old_style_uid(match: Match, start: datetime) -> str:
    dt_key = start.strftime("%Y-%m-%d %H:%M")
    matchno = KNOCKOUT_MATCH_NUMBERS_BY_DATETIME.get(dt_key)

    # Slutspel: samma UID-format som workflow-paketet från TV4-versionen.
    if matchno:
        return f"fifa-world-cup-2026-{matchno}@vm2026-calendar-updater"

    # Gruppspel: samma UID-format som workflow-paketet från TV4-versionen.
    identity = f"{start:%Y%m%d%H%M}-{match.home}-{match.away}-{match.channel}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", identity).strip("-").lower()
    return f"fifa-world-cup-2026-{slug}@vm2026-calendar-updater"

def build_ics(matches: list[Match]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sebastian//Fotbolls-VM 2026 Svensk Fotboll//SV",
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

    for match in matches:
        hour, minute = map(int, match.kickoff.split(":"))
        start = match.date.replace(hour=hour, minute=minute, second=0)
        end = start + timedelta(minutes=15)  # Endast avsparkstid.
        stream_url = TV4PLAY_URL if match.channel == "TV4" else SVTPLAY_URL
        title = f"{flag_team(match.home)} - {flag_team(match.away)} ({match.channel})"
        description = "\n".join([
            "Avsparkstid enligt Svensk Fotboll.",
            f"Kanal: {match.channel}",
            f"Källa: {SOURCE_URL}",
            f"Streaming: {stream_url}",
            f"Originalrad: {match.raw_line}",
        ])

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{old_style_uid(match, start)}",
            f"DTSTAMP:{now}",
            f"DTSTART;TZID={TIMEZONE}:{start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={TIMEZONE}:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{esc_ical(title)}",
            f"DESCRIPTION:{esc_ical(description)}",
            f"LOCATION:{esc_ical(match.channel)}",
            f"URL:{esc_ical(stream_url)}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ical_line(line) for line in lines) + "\r\n"

def main() -> int:
    text = fetch_page_text(SOURCE_URL)
    matches = parse_matches(text)

    if len(matches) < 90:
        print(f"Fel: hittade bara {len(matches)} matcher. Sidans format kan ha ändrats.", file=sys.stderr)
        return 1

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(build_ics(matches), encoding="utf-8")

    index = f"""<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <title>Fotbolls-VM 2026 kalender</title>
</head>
<body>
  <h1>Fotbolls-VM 2026 - TV4/SVT</h1>
  <p><a href="fotbolls-vm-2026-tv4-svt.ics">Prenumerera/ladda ner kalenderfilen</a></p>
  <p>Källa: <a href="{SOURCE_URL}">Svensk Fotboll</a></p>
  <p>Senast genererad: {datetime.now(timezone.utc).isoformat(timespec="seconds")}</p>
</body>
</html>
"""
    (OUTFILE.parent / "index.html").write_text(index, encoding="utf-8")
    print(f"OK: skrev {OUTFILE} med {len(matches)} matcher.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
