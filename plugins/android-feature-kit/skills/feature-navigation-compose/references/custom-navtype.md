# Custom NavType

Part of the feature-navigation-compose skill. Read it before writing or changing a custom `NavType`.

Only for a small immutable value object that identifies the destination (filters, a date range, an open mode). Not for entities.

- If the project already has a `NavType` for the type, reuse it. If the module has another custom `NavType`, follow its implementation.
- Register it in the `typeMap` of every destination that uses the type, through a shared `internal val` in the navigation file. A missing registration fails at runtime. The destination's ViewModel passes the same map to `savedStateHandle.toRoute<Route>(typeMap = ...)`, which is why the map is `internal` and not `private`.
- `serializeAsValue` must escape with `Uri.encode`.
- Add a test that navigates for real with data containing `/`, `?`, `&` and `%`. A direct `parseValue(serializeAsValue(x))` round trip does not detect a missing encode.
