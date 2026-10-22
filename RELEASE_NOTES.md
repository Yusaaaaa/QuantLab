# QuantLab 2026.10.22

Release date: 2026-10-22. Tag: `v2026.10.22`.

This application release brings the existing daily engine, native desktop workbench, simple approved strategies/factor and bilingual manuals into the GitHub repository. Independent research studies and all real market/run data remain outside this release.

## Changes

- Align Python, npm, Cargo, Tauri and the UI version with `2026.10.22`; the UI reads its version from package metadata.
- Include the existing buy-and-hold, weekly AAPL/TSLA equal-weight and weekly AAPL relative-reversal strategies, the inert template, and the daily/weekly return-spread factor.
- Isolate damaged desktop archive entries so one broken JSON file does not break the history list; failed markers take precedence and complete metadata is required.
- Reject external directory symlinks in the desktop catalog/history; bound fill CSV reading to the visible row limit.
- Update Vite to the compatible patched 6.4.5 line and source-map-js to 1.2.2, removing the three advisories returned by the initial npm audit.
- Document application/research/data boundaries, clean-clone usage, review scope, validation evidence and current limitations.

## Compatibility

The trading rules, next-open timing, commission/slippage conventions and factor definitions are unchanged. Python >=3.12 is required. Native builds currently target macOS and require Node, Cargo and developer tools; the App still depends on the selected workspace's `.venv/bin/python`. Core and desktop dependency lock files are included. Historical market configurations require local datasets that are not distributed.

See `AUDIT_2026.10.22.md` for actual verification results and review limits. Historical acceptance documents describe earlier versions and are retained as history.
