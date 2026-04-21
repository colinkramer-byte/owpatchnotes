#!/usr/bin/env python3

import argparse
import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.request import Request, urlopen

PATCH_NOTES_URL = "https://overwatch.blizzard.com/en-us/news/patch-notes/"
DEFAULT_OUTPUT = "hero_changes_latest_patch.csv"
HERO_ROSTER = [
    "Ana",
    "Anran",
    "Ashe",
    "Baptiste",
    "Bastion",
    "Brigitte",
    "Cassidy",
    "D.Va",
    "Domina",
    "Doomfist",
    "Echo",
    "Emre",
    "Freja",
    "Genji",
    "Hanzo",
    "Hazard",
    "Illari",
    "Jetpack Cat",
    "Junker Queen",
    "Junkrat",
    "Juno",
    "Kiriko",
    "Lifeweaver",
    "Lúcio",
    "Mauga",
    "Mei",
    "Mercy",
    "Mizuki",
    "Moira",
    "Orisa",
    "Pharah",
    "Ramattra",
    "Reaper",
    "Reinhardt",
    "Roadhog",
    "Sierra",
    "Sigma",
    "Sojourn",
    "Soldier: 76",
    "Sombra",
    "Symmetra",
    "Torbjörn",
    "Tracer",
    "Vendetta",
    "Venture",
    "Widowmaker",
    "Winston",
    "Wrecking Ball",
    "Wuyang",
    "Zarya",
    "Zenyatta",
]


class PatchNotesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_tag = None
        self._buffer: List[str] = []
        self.tokens: List[Tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"h3", "h4", "h5", "p", "li"}:
            self._capture_tag = tag
            self._buffer = []

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._capture_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == self._capture_tag:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.tokens.append((tag, text))
            self._capture_tag = None
            self._buffer = []


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_tokens(html: str) -> List[Tuple[str, str]]:
    parser = PatchNotesParser()
    parser.feed(html)
    return parser.tokens


def latest_patch_tokens(tokens: Sequence[Tuple[str, str]]) -> List[Tuple[str, str]]:
    start_index = None
    for index, (tag, text) in enumerate(tokens):
        if tag == "h3" and "Patch Notes" in text:
            start_index = index
            break

    if start_index is None:
        raise ValueError("Could not find a patch notes entry on the page.")

    section: List[Tuple[str, str]] = []
    for tag, text in tokens[start_index + 1 :]:
        if text == "Top of post":
            break
        if tag == "h3" and "Patch Notes" in text:
            break
        section.append((tag, text))
    return section


def hero_patterns(roster: Sequence[str]) -> Dict[str, re.Pattern[str]]:
    patterns: Dict[str, re.Pattern[str]] = {}
    for hero in roster:
        escaped = re.escape(hero)
        patterns[hero] = re.compile(rf"(?<!\w){escaped}(?:'s)?(?!\w)", re.IGNORECASE)
    return patterns


def extract_changes(
    section_tokens: Sequence[Tuple[str, str]], roster: Sequence[str]
) -> Dict[str, List[str]]:
    changes: Dict[str, List[str]] = {hero: [] for hero in roster}
    hero_heading_set = set(roster)
    mention_patterns = hero_patterns(roster)

    current_hero = None
    current_subheading = None

    for tag, text in section_tokens:
        if tag == "h4":
            current_hero = None
            current_subheading = None
            continue

        if tag == "h5":
            current_hero = text if text in hero_heading_set else None
            current_subheading = None
            continue

        if current_hero and tag == "p":
            current_subheading = text
            continue

        if tag != "li":
            continue

        if current_hero:
            change_text = (
                f"{current_subheading}: {text}" if current_subheading else text
            )
            if change_text not in changes[current_hero]:
                changes[current_hero].append(change_text)
            continue

        for hero in roster:
            if mention_patterns[hero].search(text) and text not in changes[hero]:
                changes[hero].append(text)

    return changes


def write_csv(changes: Dict[str, List[str]], output_path: Path, roster: Sequence[str]) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Hero Name", "Exact Changes Made"])
        for hero in roster:
            writer.writerow([hero, " | ".join(changes[hero]) if changes[hero] else "No Change"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the latest Overwatch patch-note hero changes to CSV."
    )
    parser.add_argument("--url", default=PATCH_NOTES_URL, help="Patch notes page URL.")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"CSV output path. Default: {DEFAULT_OUTPUT}",
    )
    args = parser.parse_args()

    try:
        html = fetch_html(args.url)
        tokens = parse_tokens(html)
        latest_section = latest_patch_tokens(tokens)
        changes = extract_changes(latest_section, HERO_ROSTER)
        output_path = Path(args.output).resolve()
        write_csv(changes, output_path, HERO_ROSTER)
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
