"""Turn report/REPORT.md into report/REPORT.html, ready to print to PDF.

    python scripts/build_pdf.py
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --no-pdf-header-footer \\
        --print-to-pdf=report/REPORT.pdf report/REPORT.html

Needs markdown-it-py, which this project does not depend on; use any Python that has it.
The layout follows the Apart Research submission template: title, author, "With Apart Research",
abstract, numbered sections, references, appendix, LLM usage statement.
"""

from pathlib import Path

from markdown_it import MarkdownIt

REPORT = Path(__file__).resolve().parent.parent / "report"

CSS = """
@page { size: A4; margin: 2.2cm 2.3cm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 6pt; text-align: center; }
h1 + p, h1 + p + p, h1 + p + p + p { text-align: center; margin: 2pt 0; }
h1 + p + p + p { font-size: 9pt; color: #555; margin-bottom: 12pt; }
h2 { font-size: 13pt; margin: 15pt 0 5pt; }
h3 { font-size: 11pt; margin: 11pt 0 4pt; }
p { margin: 0 0 6.5pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 6.5pt; padding-left: 18pt; }
li { margin-bottom: 2.5pt; }
table { border-collapse: collapse; margin: 4pt auto 9pt; font-size: 9pt; }
th, td { border-top: 0.6pt solid #999; border-bottom: 0.6pt solid #999; padding: 2.5pt 7pt; text-align: left; }
th { border-top: 1pt solid #111; border-bottom: 1pt solid #111; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; }
pre { font-size: 7.2pt; line-height: 1.25; background: #f6f6f4; padding: 6pt 8pt; overflow: hidden; white-space: pre-wrap; }
pre code { font-size: inherit; }
img { display: block; margin: 6pt auto 3pt; width: 92%; }
a { color: #1c5cab; text-decoration: none; word-break: break-all; }
h2, h3 { break-after: avoid; }
table, img, pre { break-inside: avoid; }
"""


def main() -> None:
    text = (REPORT / "REPORT.md").read_text()
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
    html = f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Report</title><style>{CSS}</style></head><body>{body}</body></html>"
    (REPORT / "REPORT.html").write_text(html)
    print("wrote", REPORT / "REPORT.html", len(html), "characters")


if __name__ == "__main__":
    main()
