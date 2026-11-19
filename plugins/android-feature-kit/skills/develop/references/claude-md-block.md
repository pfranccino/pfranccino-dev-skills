<!-- android-feature-kit:start -->
## Android feature work (android-feature-kit)

Requests to build or change a feature (a new feature, screen, endpoint, entity or flow, a ticket to implement) go through the kit's `develop` skill. Questions about the code, failing builds or tests, reviews and architecture questions go through its `analyze` skill. During kit work, a build, test or on-device check that fails or hangs goes first to the kit's `build-doctor` or `test-analyst`, before any diagnosis of your own. A small change in one layer uses that layer's skill directly. Code changes, small ones included, start only after the user approves the plan in Plan Mode; analysis plans are approved in the conversation. The kit's limits and routine choices for this repository are in `.claude/android-feature-kit.md`.
<!-- android-feature-kit:end -->
