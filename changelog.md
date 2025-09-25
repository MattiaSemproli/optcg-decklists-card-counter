### V1.0.0
- Initial release.
- Folder-based structure with old decklists, cardlist and average decklist counter script.
- Supported sets until OP09.

### V2.0.0
- Data and scope upgrade.
- Added all products after OP09 up to OP12, including ST, PROMOS, EB/PRB.
- Introduced first version of the CLI and basic GUI (manual list input).
- Decklist aggregation and averages supported.

### V3.0.0
- Major refactor and feature upgrade.
- New GUI-first workflow with input window and advanced summary tables.
- Direct support for deckgen URLs (no more manual decklist copy-paste).
- Improved deck summary: shows Cost, Color(s), and Power, with leaders excluded from tables.
- Automatic grouping by Leader: opens one summary window per different deck leader.
- Enhanced table: sortable columns, search, copy/export to CSV/TXT, zebra striping.
- Improved error handling (invalid inputs highlighted instead of breaking).
- Modularized codebase in preparation for package release.

### V3.1.0
- Added automatic tiling for summary windows:
  - 1 summary → 80% × 80% centered.
  - 2 summaries → 40% width × 80% height, side by side.
  - 3 summaries → 30% width × 80% height, in one row.
  - 4 summaries → 40% width × 40% height, 2×2 grid.
  - >4 summaries → compact grid layout (max 3 columns).
- Improved GUI flow stability (no more crash when closing Input window).