# Changelog

## 0.2.0 — 2026-11-16

- `feature-ui-compose`: ViewModels no longer start work in `init`. The stateful screen sends `UiAction.Started` from `LaunchedEffect(viewModel)`, and the ViewModel runs it once. The example, the offline-first rule, the tests and the final checklist follow the new pattern.

## 0.1.0 — 2026-11-15

First release.

- Skills: `feature-navigation-compose`, `feature-ui-compose`, `domain-layer`, `data-repository`, `data-room`, `data-datastore`.
- `pack/official-skills.txt` with the nine official Android skills that complement the kit.
- `scripts/install-pack.ps1` and `scripts/install-pack.sh`: install the official skills globally or into an app, and optionally copy the kit's skills into an app.
- Reviewed in three rounds between Claude and Codex; 20 findings resolved.
- Documentation of origin for every skill: kit, official Android skills and other authors, with licenses and notices.
