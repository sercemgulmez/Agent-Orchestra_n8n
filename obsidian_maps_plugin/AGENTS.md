# Obsidian Maps Agent Guide

This plugin is local-first. Do not add telemetry, hidden analytics, remote code execution, or cloud dependencies without a clear user-facing setting and documentation.

## Project shape

- Source code lives in `src/`.
- Keep `src/main.ts` focused on lifecycle, settings loading, view registration, and command registration.
- Put commands in `src/commands/`, UI views in `src/ui/`, shared interfaces in `src/types.ts`, and settings in `src/settings.ts`.
- Build output must produce `main.js` at the plugin root alongside `manifest.json` and `versions.json`.

## Obsidian behavior

- Register commands with stable IDs. Do not rename released command IDs.
- Load and save settings with `loadData()` and `saveData()`.
- Keep startup light. Defer map view work until the user opens the view.
- Register events, DOM listeners, and intervals through Obsidian cleanup helpers.
- Avoid vault-wide scans unless a user action requires them.

## Privacy and network

- Default custom tiles to disabled.
- If a future feature needs network requests, disclose what is sent and require explicit opt-in.
- Never transmit vault contents, filenames, or personal information by default.

## Quality

- Use strict TypeScript.
- Keep modules small and focused.
- Test production builds with `npm run build` before release.
