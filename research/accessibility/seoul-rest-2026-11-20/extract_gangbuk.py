"""Extract the official Gangbuk 2026/2027 cold shelter PDF table."""
import argparse
from collections import Counter
import csv
from pathlib import Path

import pdfplumber

SOURCE_URL = "https://m.blog.naver.com/gangbuk_official/224475389845"
SOURCE_COLUMNS = ["연번", "행정동", "쉼터명", "소재지", "연락처", "시설구분", "운영시간"]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("original_pdf", type=Path)
parser.add_argument("output_csv", type=Path)
parser.add_argument("--retrieved-date", required=True)
args = parser.parse_args()

rows = []
with pdfplumber.open(args.original_pdf) as document:
    for page in document.pages:
        table, = page.extract_tables()
        for row in table:
            if row[0] and row[0].isdigit():
                if len(row) != len(SOURCE_COLUMNS):
                    raise ValueError(f"Unexpected table schema on page {page.page_number}")
                # A closing address bracket crosses into the telephone column in this printed table.
                if row[4] and row[4].startswith(")") and row[3].count("(") == row[3].count(")") + 1:
                    row[3] += ")"
                    row[4] = row[4][1:].lstrip()
                rows.append(row)
if [int(row[0]) for row in rows] != list(range(1, 97)):
    raise ValueError("PDF records must include sequential rows 1–96")
if any(not (row[1] and row[2] and row[3] and row[5] and row[6]) for row in rows):
    raise ValueError("Missing required facility details")

with args.output_csv.open("w", newline="", encoding="utf-8-sig") as output:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(SOURCE_COLUMNS + [
        "district", "season_start", "season_end", "retrieved_date", "source_url", "field_verified"
    ])
    for row in rows:
        writer.writerow(row + ["강북구", "2026-11-15", "2027-03-15", args.retrieved_date, SOURCE_URL, False])

print(len(rows), "district neighborhoods", len({r[1] for r in rows}),
      "missing contacts", sum(not r[4] for r in rows), Counter(r[5] for r in rows))
