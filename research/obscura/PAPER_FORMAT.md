# Research paper presentation

User request, 23 November 2026: use `2112.06343v2.pdf` only as a formatting reference, never as a source of scientific content.

The new canonical PDF uses US Letter, two 251-point columns separated by 12 points, embedded Times New Roman regular/bold/italic faces, 9.96-point body text, a 23.91-point spanning title, an 8.97-point bold abstract, Roman-numbered small-cap section headings, italic subsections, compact ruled tables, numbered linked references and upper-right page numbers. These match the reference's general IEEE journal presentation; this is not an assertion of an official IEEE template check or IEEE publication.

The reference uses Nimbus Roman; the embedded Times New Roman family is a close Times-style counterpart, not the exact same font binary. Its arXiv stamp, author details, illustrations, research, claims and text were not reused.

Content was captured from our previous report into `paper_content.json`. The 41 original paragraphs and every cell of all five tables are present in the formatted PDF. Eleven original references remain. Added index terms describe methods already in the paper. Section titles, table captions and citation presentation were adjusted for the paper layout. No measured value or scientific conclusion was changed.

All three final pages were rendered and inspected. Automated checks confirm text retention, table values, embedded Times fonts, two-column page geometry and no text outside the margins. See `FORMAT_VERIFICATION.json`. The earlier six-page brief and its builder are preserved separately.

Build: `python build_report.py`. Validate: `python verify_paper_format.py` (ReportLab, pypdf and pdfplumber; standard Windows Times font files).

Reference file SHA256: `b94b23b1466413d10c0fcead76faae6bf1f73dac103f0bb1d756001f8eb64aac`.
