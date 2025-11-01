from itertools import islice
from pathlib import Path
import scripture

# Use shared scripture utilities to find references consistently with the app

owen_path = Path('Other Works') / 'Catechisms John Owen.txt'
text = owen_path.read_text(encoding='utf-8')

# Use the centralised reference finder to avoid divergence from app behaviour
refs = scripture.find_scripture_references(text)

# Prepare tuples for reporting
matches: list[tuple[str, str, int, str]] = [
    (r['text'], r['book'], int(r['chapter']), str(r['verse'])) for r in refs
]

# Write a simple report
out_path = Path('owen_references_report.txt')
with out_path.open('w', encoding='utf-8') as f:
    f.write(f"Total references found: {len(matches)}\n\n")
    for s, b, c, v in  islice(matches, 200):
        f.write(f"{s} -> book='{b}' chap={c} verses='{v}'\n")
    if len(matches) > 200:
        f.write(f"... ({len(matches)-200} more)\n")
print(f"Wrote {len(matches)} references to {out_path}")
