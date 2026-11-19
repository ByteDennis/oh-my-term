# Requirements discussion deck

`requirements-alignment-template.pptx` contains two editable 16:9 slides:

1. The main discussion page: who will use the workspace, the questions it must
   answer, current PoC scope, and three requirements to confirm with stakeholders.
2. The attachment: the business question and information covered by each of the
   five views. People is included in Impact; owner information stays in the shared
   summary area, and email addresses copy on click.

Replace bracketed placeholders before presenting. Speaker notes are included.
The main page intentionally omits technical architecture, implementation detail,
test counts and unverified benefit metrics. Database discovery and recurring
quality execution are described as later phases.

The PDF and `slide-1.png` / `slide-2.png` are rendered exports of the actual deck.
To regenerate the editable deck, install the optional `python-pptx` dependency and
run `python build_template.py`. Use PowerPoint or LibreOffice to render exports.
