#!/usr/bin/env bash

set -euo pipefail

PATCH_NOTES_URL="${PATCH_NOTES_URL:-https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/01}"
OUTPUT_FILE="${1:-hero_changes_latest_patch.csv}"

readonly HERO_ROSTER=(
  "Ana"
  "Anran"
  "Ashe"
  "Baptiste"
  "Bastion"
  "Brigitte"
  "Cassidy"
  "D.Va"
  "Domina"
  "Doomfist"
  "Echo"
  "Emre"
  "Freja"
  "Genji"
  "Hanzo"
  "Hazard"
  "Illari"
  "Jetpack Cat"
  "Junker Queen"
  "Junkrat"
  "Juno"
  "Kiriko"
  "Lifeweaver"
  "Lúcio"
  "Mauga"
  "Mei"
  "Mercy"
  "Mizuki"
  "Moira"
  "Orisa"
  "Pharah"
  "Ramattra"
  "Reaper"
  "Reinhardt"
  "Roadhog"
  "Sierra"
  "Sigma"
  "Sojourn"
  "Soldier: 76"
  "Sombra"
  "Symmetra"
  "Torbjörn"
  "Tracer"
  "Vendetta"
  "Venture"
  "Widowmaker"
  "Winston"
  "Wrecking Ball"
  "Wuyang"
  "Zarya"
  "Zenyatta"
)

csv_escape() {
  local value=${1//$'\r'/ }
  value=${value//$'\n'/ }
  value=${value//\"/\"\"}
  printf '"%s"' "$value"
}

fetch_html() {
  local url=$1
  local output_path=$2
  curl -fsSL "$url" >"$output_path"
}

extract_changes_tsv() {
  local input_path=$1
  local output_path=$2

  perl -MHTML::Entities -0ne '
    sub clean_text {
      my ($text) = @_;
      $text = decode_entities($text // q{});
      $text =~ s/<br\s*\/?>/ /gis;
      $text =~ s/<[^>]+>//g;
      $text =~ s/\x{a0}/ /g;
      $text =~ s/\s+/ /g;
      $text =~ s/^\s+|\s+$//g;
      return $text;
    }

    my %month = (
      January => 1, February => 2, March => 3, April => 4,
      May => 5, June => 6, July => 7, August => 8,
      September => 9, October => 10, November => 11, December => 12,
    );

    my $html = $_;
    my @patches = split /<div class="PatchNotes-patch PatchNotes-live">/i, $html;
    shift @patches;

    my $latest_key = 0;
    my $latest_patch = q{};

    for my $patch (@patches) {
      next unless $patch =~ m{<h3 class="PatchNotes-patchTitle">\s*Overwatch Retail Patch Notes - ([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\s*</h3>}is;
      my ($month_name, $day, $year) = ($1, $2, $3);
      next unless exists $month{$month_name};
      my $key = sprintf("%04d%02d%02d", $year, $month{$month_name}, $day);
      if ($key > $latest_key) {
        $latest_key = $key;
        $latest_patch = $patch;
      }
    }

    die "Could not find the latest patch section\n" if !$latest_patch;

    my @heroes = split /<div class="PatchNotesHeroUpdate">/i, $latest_patch;
    shift @heroes;

    for my $hero_chunk (@heroes) {
      my ($hero_name) = $hero_chunk =~ m{<h5 class="PatchNotesHeroUpdate-name">(.*?)</h5>}is;
      next if !defined $hero_name;
      $hero_name = clean_text($hero_name);
      $hero_name = "Jetpack Cat" if $hero_name eq "Jet Pack Cat";

      while ($hero_chunk =~ m{<div class="PatchNotesAbilityUpdate-name">(.*?)</div>\s*<div class="PatchNotesAbilityUpdate-detailList">\s*<ul>(.*?)</ul>}gis) {
        my ($ability_name, $details_block) = ($1, $2);
        $ability_name = clean_text($ability_name);
        next if $ability_name eq q{};

        while ($details_block =~ m{<li>(.*?)</li>}gis) {
          my $detail = clean_text($1);
          next if $detail eq q{};
          print $hero_name, "\t", $ability_name, ": ", $detail, "\n";
        }
      }
    }
  ' "$input_path" >"$output_path"
}

write_csv() {
  local changes_path=$1
  local output_path=$2
  local roster_joined
  roster_joined=$(printf '%s\n' "${HERO_ROSTER[@]}")

  ROSTER_JOINED="$roster_joined" awk -F '\t' '
    function csv_escape(text, escaped) {
      escaped = text
      gsub(/\r/, " ", escaped)
      gsub(/\n/, " ", escaped)
      gsub(/"/, "\"\"", escaped)
      return "\"" escaped "\""
    }

    BEGIN {
      roster_count = split(ENVIRON["ROSTER_JOINED"], roster, "\n")
      print "\"Hero Name\",\"Exact Changes Made\""
    }

    NF >= 2 {
      hero = $1
      change = $2
      if (changes[hero] == "") {
        changes[hero] = change
      } else if (index(changes[hero], change) == 0) {
        changes[hero] = changes[hero] " | " change
      }
    }

    END {
      for (i = 1; i <= roster_count; i++) {
        hero = roster[i]
        if (hero == "") {
          continue
        }
        value = changes[hero]
        if (value == "") {
          value = "No Change"
        }
        print csv_escape(hero) "," csv_escape(value)
      }
    }
  ' "$changes_path" >"$output_path"
}

main() {
  local tmp_dir html_file changes_file
  tmp_dir=$(mktemp -d)
  html_file="$tmp_dir/patch-notes.html"
  changes_file="$tmp_dir/latest-patch-changes.tsv"

  trap "rm -rf '$tmp_dir'" EXIT

  fetch_html "$PATCH_NOTES_URL" "$html_file"
  extract_changes_tsv "$html_file" "$changes_file"
  write_csv "$changes_file" "$OUTPUT_FILE"
  printf '%s\n' "$(cd "$(dirname "$OUTPUT_FILE")" && pwd)/$(basename "$OUTPUT_FILE")"
}

main "$@"
