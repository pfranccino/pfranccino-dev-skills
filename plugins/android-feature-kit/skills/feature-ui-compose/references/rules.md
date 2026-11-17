# feature-ui-compose rules

Every normative rule of the feature-ui-compose skill, with a stable ID. Reviews cite these IDs, and the skill's "Before finishing" checklist points to them. The Source column names the section of `SKILL.md` that explains the rule. When a rule changes in `SKILL.md`, change it here too. IDs are never reused.

## Rules shared by every skill of the kit

These rules have the same IDs in every skill's rules file. Where a skill has no sentence for a rule, the rule is kit policy, marked as such in the Source column.

| ID | Rule | Source |
| :--- | :--- | :--- |
| KIT-01 | The skill applies even when the task arrives as a detailed plan or ticket: the plan says what to build, the skill says how the team builds it. If the plan and the skill disagree, say so and follow the plan. A review does not flag a deviation the plan required. | Introduction of every skill |
| KIT-02 | The module's existing naming, packages and conventions win over the skill's examples when they differ in style. A review does not flag a style that follows the module. | Scope of domain-layer, data-repository, feature-ui-compose and feature-navigation-compose; kit policy for data-room and data-datastore, which have no such sentence |
| KIT-03 | The module is inferred from the paths or files the user gave; ask before writing only if more than one module fits. | Scope of domain-layer, data-repository, feature-ui-compose and feature-navigation-compose; kit policy for data-room and data-datastore, which have no such sentence |
| KIT-04 | Other modules are not edited. Each change needed outside the module is reported under "Changes needed outside this module" with the module, the reason and the exact snippet, or the report says "None". | Scope and Before finishing of every skill |
| KIT-05 | The concrete names the skill's examples stand for (the project's `Either`, MVI delegate, network helper, side effect collector, design system, dispatcher qualifier, application scope) are read from the project before writing. A required piece that does not exist is asked about, never invented or copied privately into the feature. | Read before writing of every skill, generalized as kit policy |
| KIT-06 | Before finishing, the module is built and tested with its real path and variant, and the report says which checks could not run. | Before finishing of every skill |
| KIT-07 | The final report lists what was created or changed, by file. If other team skills also apply to the task, they give one combined report instead of one per skill. | Before finishing of every skill |

## UI rules

| ID | Rule | Source |
| :--- | :--- | :--- |
| UI-01 | Work in the presentation package of one feature module. Other modules are not edited (KIT-04). | Scope |
| UI-02 | The feature keeps its layers as packages. Presentation imports from `domain` only, never anything from `data`. | Scope |
| UI-03 | The MVI delegate, the side effect collector and the `Either` are required: if one does not exist yet, ask where it should live, and never create a private copy inside the feature. Anything else missing does not block: build the screen from the design system pieces that exist and report what is missing. | Read before writing |
| UI-04 | One `internal` contract per screen holds its `UiState`, `UiAction` and `SideEffect`. | Contract |
| UI-05 | `UiState` is an immutable `data class` whose defaults are the initial state, with loading, content, empty and error modeled explicitly. | Contract |
| UI-06 | What the screen shows is a presentation model when it needs formatting or combines several domain models. Amounts, dates and masks are formatted when mapping to it, not inside composables. | Contract |
| UI-07 | `UiAction` names what is happening on the screen, in the present tense with an `On` prefix like Compose callbacks (`OnStart`, `OnCancelClick`, `OnRetryClick`, `OnAmountChange`), not what the ViewModel will do next. A screen that loads data has an `OnStart` action, with that same name on every screen. | Contract |
| UI-08 | `SideEffect` is only for one-off events that state cannot express (a flow exit that becomes a navigation callback, a one-time message). If it can be shown as state, it is state. | Contract |
| UI-09 | Errors in `UiState` are presentation errors (a sealed type or a string resource id) mapped from the domain error. Domain errors never reach composables. | Contract |
| UI-10 | One `internal` `@HiltViewModel` per screen implements the MVI contract by delegation. State and effects go only through the delegate; no extra `MutableStateFlow`, `Channel` or `SharedFlow` next to it. | ViewModel |
| UI-11 | The ViewModel depends on use cases only. It never receives a repository (not even its domain interface), a data source, a DAO, an API or a `Context`. | ViewModel |
| UI-12 | `onAction` is an exhaustive `when` with no `else` branch, and so is every `when` over actions or effects. | ViewModel |
| UI-13 | The ViewModel starts no work when it is created: the constructor, `init` blocks and property initializers make no use case calls and launch no coroutines (`launch`, `launchIn`). Reading route arguments there is fine. | ViewModel |
| UI-14 | With the MVI delegate, the stateful screen sends `OnStart` from `LaunchedEffect(viewModel)`, not from a lifecycle `ON_START` observer, and the ViewModel runs it once per instance, tracked in a plain field (not in `SavedStateHandle`), so the new instance after process death starts again. If the delegate or the module's screens already start the first load another way that runs no work at construction, that way is used instead of `OnStart`. If that way runs work at construction, the reply says so and `OnStart` is used. | ViewModel |
| UI-15 | Offline-first screens observe and refresh separately. `OnStart` starts the observation, with a `.catch` that turns a local read failure into an error state, and calls the refresh use case. `OnRetryClick` starts the observation again when it is no longer active and calls the refresh use case, and is ignored while a refresh is still running. Cached content stays on screen while refreshing, and a refresh error is shown next to the content without replacing it. | ViewModel |
| UI-16 | Every `Either` result is handled: a `Left` updates state or emits an effect; it is never dropped. | ViewModel |
| UI-17 | `CancellationException` is never caught, directly or through `catch (e: Exception)` or `runCatching`. | ViewModel |
| UI-18 | No navigation, no `NavController` and no Android resources resolved in the ViewModel. Text is resolved from resources in the composable. | ViewModel |
| UI-19 | Route arguments are read with `savedStateHandle.toRoute<Route>()`, passing the same `typeMap` the graph registers when the route has a custom argument type. `SavedStateHandle` holds anything else only when it is small, non-sensitive input that must survive process death, and never PINs, passwords, OTPs, tokens, full card numbers or CVVs. | ViewModel |
| UI-20 | Every destination has an `internal` stateful `XScreen` and an `internal` stateless `XScreenContent`. | Screens |
| UI-21 | `XScreen` resolves the ViewModel with `hiltViewModel()`, sends `OnStart` from `LaunchedEffect(viewModel)` when the screen loads data, collects state with `collectAsStateWithLifecycle()` and turns each `SideEffect` into a call to a callback. Its callbacks have no default values, so a missing wiring fails to compile. | Screens |
| UI-22 | `XScreenContent` is stateless: state in, `onAction` out. It never sends `OnStart`, so previews and UI tests that target it load nothing. | Screens |
| UI-23 | No screen receives `NavController` or `NavBackStackEntry`, and no composable is named `XRoute` (`Route` is reserved for navigation routes). | Screens |
| UI-24 | The `hiltViewModel()` import matches the project's Hilt version (`androidx.hilt.lifecycle.viewmodel.compose` on Hilt 1.3 or later, `androidx.hilt.navigation.compose` before); use the one the project already imports. | Screens |
| UI-25 | `modifier: Modifier = Modifier` is the first optional parameter and is applied once, to the root element. | Composables |
| UI-26 | Composables use design system components and tokens, with no hardcoded colors, sizes or text styles. When the design system lacks a component, the screen is composed from its pieces and tokens, and the missing reusable component is reported instead of created inside the feature. | Composables |
| UI-27 | All user-visible text comes from string resources. | Composables |
| UI-28 | Meaningful icons and images have a `contentDescription` and decorative ones pass `null`; touch targets are at least 48dp; custom controls declare their role and state with `semantics`; information is never conveyed by color alone. | Composables |
| UI-29 | Lazy lists pass a stable `key` for each item. | Composables |
| UI-30 | Composables display state and report actions. They do not decide business outcomes or call use cases. | Composables |
| UI-31 | `@Immutable` and `@Stable` are not added by reflex. When the task is about performance, the jetpack-compose-performance skill applies. | Composables |
| UI-32 | Each meaningful state of `XScreenContent` (content, loading, empty, error) has a preview, with a `PreviewParameterProvider` when there are several. Previews are `private` and use fake presentation models, never a ViewModel. | Previews |
| UI-33 | ViewModel unit tests use fake use cases and the project's main dispatcher rule (and Turbine if the project already has it), and check that creating the ViewModel calls no use case, `OnStart` loads once even when sent twice, `OnRetryClick` before `OnStart` leaves a single observation, each action produces the expected state, each effect is emitted once, and each `Left` ends up in state or in an effect. A Compose UI test targets `XScreenContent` when the module already has UI tests. | Tests |
| UI-34 | The final report lists every change to what the screen exposes to navigation (callbacks and their parameters), since the feature graph depends on it. | Before finishing |
| UI-35 | Before writing, find in the project: the MVI contract and delegate (how state is updated, how effects are emitted, and whether it already starts a screen's first load), the Compose side effect collector, the `Either` and its functions, the design system's components, theme, spacing and typography tokens, and one existing screen in the module if there is one. | Read before writing |
| UI-36 | Before finishing, when Android CLI is installed, render the new previews with `android preview render --fqn <fully.qualified.PreviewFunction> --component-tree`, look at the PNG, and check that the component tree has the expected texts and semantics. | Before finishing |
