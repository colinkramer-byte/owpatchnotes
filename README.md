# Overwatch Patch Notes CSV Generator

This project is a Bash script that reads the latest live Overwatch patch notes from Blizzard’s website and creates a CSV file showing hero changes.

## What it does

- Connects to the live Overwatch patch notes page
- Reads the newest patch automatically
- Extracts hero ability changes from the HTML
- Writes a CSV file with:
  - Column 1: Hero Name
  - Column 2: Exact Changes Made
- If a hero has no change in the newest patch, the script writes `No Change`

## Files

- `overwatch_patch_notes_to_csv.sh` - main Bash script
- `hero_changes_latest_patch.csv` - output CSV file
- `overwatch_patch_notes_to_csv.py` - older Python version

## How to run

```bash
cd "/Users/colinkramer/Documents/Overwatch_patchnotes"
bash overwatch_patch_notes_to_csv.sh
