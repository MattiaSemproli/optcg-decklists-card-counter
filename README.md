# One Piece TCG Decklist Analyzer

Tool to analyze **One Piece TCG** decklists starting from **deckgen links** of [onepiecetopdecks.com](https://onepiecetopdecks.com).  
It computes average usage of each card across multiple decklists and displays results in a **GUI table**.

---

## Features

- **GUI-first workflow** (Tkinter / ttkbootstrap theme):
  - Input window to paste multiple deckgen URLs.
  - Live validation of links, invalids highlighted.
  - Proceed to analysis only with valid links.
- **Automatic grouping by Leader**:
  - One summary window per different Leader in the selected decks.
  - Leaders excluded from the table, only used for grouping/labels.
- **Advanced summary table**:
  - Columns: Avg · Occ · Total · ID · Name · Cost · Color(s) · Power
  - Sortable by column, search bar, zebra striping.
  - Copy selection to clipboard, export to CSV/TXT.
- **CLI fallback**:
  - If Tkinter is not available, you can still paste deckgen links in the terminal.
- **Automatic tiling**:
  - Arranges summary windows depending on how many decks are analyzed.
    - 1 summary → 80% × 80% centered.
    - 2 summaries → 40% width × 80% height, side by side.
    - 3 summaries → 30% width × 80% height, in one row.
    - 4 summaries → 40% width × 40% height, 2×2 grid.
    - >4 summaries → compact grid layout (max 3 columns).

---

## Requirements

- Python 3.10+  
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) (optional but recommended for modern theme)  
- [colorama](https://pypi.org/project/colorama/) (optional, colors CLI errors)

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python -m op_tcg_tool
```

- Paste one or more deckgen links (one per line).  
- Press **Next →** to open the analysis.  
- One window per **Leader** will appear.  
- Close all windows to quit.

Example deckgen link:

```
https://onepiecetopdecks.com/deck-list/english-op-12-deck-list-legacy-of-the-master/deckgen?dn=Red%20Rayleigh&date=9/21/2025&cn=NA&au=Choas&pl=1st%20Place&tn=Pirates%20League(4-1)&hs=PlayTCG&dg=1nOP12-001a4nOP01-016a4nOP03-008...
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
