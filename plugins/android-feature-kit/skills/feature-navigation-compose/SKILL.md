---
name: feature-navigation-compose
description: "Team pattern for navigation inside one Android feature module with Navigation Compose 2 type-safe routes. Use it before writing or migrating any navigation code in a feature module, even when the task is a plan or ticket that already lists the rules. Covers creating a nav graph (NavGraphBuilder extension, graph marker such as PinGraph), routes or destinations, new or empty screens wired to a graph, exit callbacks (onCompleted, onDismiss), back handling, entry or result extensions, and migrating a module's existing navigation to a closed graph, one module at a time and internals only. Not for Navigation 3 (NavDisplay, back stack as state), review-only tasks or screen internals (feature-ui-compose). Also for requests in Spanish such as navegación, grafo, rutas, destinos, pantallas con navegación, migrar a grafos."
---

# Feature navigation with Navigation Compose

Creates navigation code for one feature module following the team's multi-feature navigation pattern. Targets Navigation 2 with type-safe routes (`navigation-compose` 2.8+). Do not use Navigation 3 APIs (`NavDisplay`, back stack as state).

Before writing, read the pinned Navigation, Hilt, Lifecycle and kotlinx-serialization versions in the version catalog, and do not upgrade them. On Hilt 1.3 or later, `hiltViewModel` is imported from `androidx.hilt.lifecycle.viewmodel.compose`; before that, from `androidx.hilt.navigation.compose`. If you are unsure about an API, check `android docs search "<topic>"` when Android CLI is available instead of guessing.

This skill covers creating navigation and migrating a module's existing navigation to this pattern. It is not a review checklist for existing code.

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

## Scope: one module only

Work only inside the module the user gave as context.

- Infer the module from the paths or files the user gave. Ask before writing only if more than one module fits.
- Read other modules only when needed to understand a shared type. Never edit them.
- Never edit the orchestrator (`:app`, the `NavHost` builder, a root graph) or another feature, even if the change there is obvious.
- When the work needs a change outside the module (wiring a new callback, calling a new entry extension, a shared model type), do not make it. List it at the end under "Changes needed outside this module", with the exact snippet the owner should add.
- Do not refactor existing navigation in the module that the task does not touch. If existing code breaks these rules, mention it in one line and move on.
- Follow the module's existing naming, packages, and MVI conventions over the examples here when they differ in style.

## The principle

A feature graph is closed to external modification and open to configuration by parameters.

1. Destinations are `internal`. Outside the module their names, arguments and order do not exist.
2. The only public route is the graph marker: a `@Serializable data object` with no arguments and no behavior. It is used to enter and for `popUpTo`.
3. Configuration enters through the signature of the graph extension.
4. Exits are callbacks. A feature never navigates to another feature. It reports what happened and the orchestrator decides.

## Public surface of a feature

```kotlin
// FeatureRoutes.kt
@Serializable
data object FeatureGraph                      // public marker

internal sealed class FeatureRoutes {
    @Serializable
    data object Start : FeatureRoutes()

    @Serializable
    data class Detail(val itemId: String) : FeatureRoutes()
}

// FeatureGraph.kt
fun NavGraphBuilder.featureGraph(
    navController: NavController,             // internal navigation only
    /* configuration parameters */
    /* exit callbacks */
) {
    navigation<FeatureGraph>(startDestination = FeatureRoutes.Start) {
        composable<FeatureRoutes.Start> { /* ... */ }
        composable<FeatureRoutes.Detail> { backStackEntry ->
            val route = backStackEntry.toRoute<FeatureRoutes.Detail>()
            /* ... */
        }
    }
}
```

Everything else is `internal`: screens, ViewModels, contracts, presentation models.

Public only when needed:

- `fun NavController.navigateToX(args, navOptions: NavOptions? = null)`: entry to an internal destination that must be reached from outside with arguments. The route stays `internal`.
- `fun NavController.setXResult(value)`: delivers an ephemeral UI selection to a screen of this feature that is still on the stack. The key stays `internal`.

Rules for the graph extension:

- Take `NavController`, not `NavHostController`.
- `navController` is for the feature's own routes. Never call `navigate` with another feature's marker or extension.
- Call `toRoute<T>()` once per destination and keep it in a `val`.
- Use `navOptions { launchSingleTop = true }` on navigations that a double tap could duplicate.
- Use named arguments at call sites.
- Do not declare `deepLinks` in `composable<>`. External entry goes through the deep link processor, which uses the marker or a `navigateToX()` extension.
- A configuration value baked into `startDestination` is fixed when the graph is built. If it can change during the flow, it comes from a ViewModel.

## Exit callbacks

Three kinds, all lambdas in the graph signature, all named by what happened inside the feature and never by where the user should go next.

| Kind | Shape | Example |
| :--- | :--- | :--- |
| The feature needs something it does not resolve | `onXRequested: () -> Unit` | `onHelpRequested` |
| The flow finished | `onXCompleted: (result) -> Unit` | `onCompleted(orderId)` |
| Left without completing | `onDismiss: () -> Unit` | `onDismiss` |

- Wrong: `onNavigateToReceiptScreen`, `onGoToSupport`. Right: `onCompleted`, `onHelpRequested`.
- Name lambda parameters when the type does not say it all: `(goalId: String, rut: String) -> Unit`.
- Default payload is an identifier or primitives. A callback may carry an object only if all four hold: the type is public and lives in a shared domain or model module; it is an immutable value object with no logic; the consumer needs it whole; it cannot be rebuilt from an id.

## Getting data from one screen to another

Choose by the kind of data, not by preference.

| The data... | Path |
| :--- | :--- |
| Goes to a new destination | Route argument |
| Is a business fact | Data layer: the producer persists it, the screen on the stack observes its repository, the graph only closes the producer |
| Is an ephemeral UI selection returning to a screen still on the stack (picker, confirmation) | `savedStateHandle` |

Before using `savedStateHandle`, rule out that the data is a business fact. That is the common mistake.

`savedStateHandle` restrictions:

- Key is an `internal const` of the feature that reads. Never a string literal in two files.
- Ids and primitives only.
- Written in the graph and read in the graph: read with `getStateFlow<T?>(KEY, null)` inside `composable<>`, pass the value to the screen as a parameter, and when the screen reports that it consumed it, the graph sets `savedStateHandle[KEY] = null`. Do not call `remove(KEY)` while the flow is collected: `remove` detaches the flow, and the next result never arrives. Test two consecutive results on the same entry.
- If the writer is outside the module, expose a `setXResult()` extension instead of the key.

One ViewModel per screen, resolved in the stateful screen. Do not create ViewModels scoped to a graph or Activity to move data between screens.

Only exception, the flow ViewModel: a multi-step flow that builds a draft (onboarding, checkout, long form). Conditions: scoped to the feature's own graph marker; holds only the draft; each screen keeps its own ViewModel; it never returns results; the `composable<>` resolves it with `remember(navController, backStackEntry) { navController.getBackStackEntry(FeatureGraph) }` and hands it to the stateful screen. Ask the user only when it is unclear which screens own the draft.

## What may travel in a route or savedStateHandle

| Level | Examples | Allowed |
| :--- | :--- | :--- |
| Secrets | PIN, password, token, OTP, full card number, CVV | Never |
| Personal or transactional data | RUT, amount, account alias | Only if all three conditions below hold |
| Identifiers | `goalId`, `orderId` | Default |

Personal or transactional data may travel when: it is the input the destination needs to operate; it cannot be rebuilt from an id; and the route with arguments is not logged or sent to analytics.

Never pass domain entities (`User`, `Order`) or large objects. Pass the id and let the ViewModel resolve it. An amount in a route is input, not truth: the backend revalidates it.

## Custom NavType

Only for a small immutable value object that identifies the destination (filters, a date range, an open mode), never for entities. Before writing or changing one, read `references/custom-navtype.md` in this skill's folder: registration in every `typeMap`, encoding with `Uri.encode`, and the test it needs.

## Screens

Every destination has a pair, both `internal`:

- `XScreen` (stateful): resolves the ViewModel with `hiltViewModel()`, collects state with `collectAsStateWithLifecycle()`, maps side effects to callbacks. This is what `composable<>` consumes.
- `XScreenContent` (stateless): receives state and lambdas with `= {}` defaults. `@Preview` and tests target this one.

No screen receives `NavController` or `NavBackStackEntry`. Do not name composables `XRoute`; `Route` is reserved for navigation routes.

The contract, ViewModel and composables inside each screen follow feature-ui-compose.

## MVI connection

`UiState`, `UiAction` and `SideEffect` are `internal`. A `SideEffect` dies in the screen: the stateful screen collects it and translates it into a call to the hoisted callback. Never pass the effect itself up to the graph.

`CollectSideEffect` is the project's lifecycle-aware collector. Find it before using it; do not write a new one in the feature.

```kotlin
CollectSideEffect(viewModel.sideEffect) {
    when (it) {
        is InitContract.SideEffect.GoToChallengeScreen ->
            onChallengeSelected(it.goalId, it.rut)
    }
}
```

No `else` branch in a `when` over an enum or sealed type.

## Back handling

```kotlin
// Back from a destination that is not the first of the flow
onBackAction = { navController.popBackStack() }

// Back from the first destination of the flow: exit through the callback
onBackAction = { onDismiss() }

// System back intercepted at one destination
BackHandler { onDismiss() }
```

The first destination of the flow calls `onDismiss` directly, for both the toolbar back and the system back. Do not rely on `popBackStack()` returning `false`: the graph lives inside the host's `NavHost`, where it almost never does. If a destination can be first or not depending on configuration, decide with that configuration.

One owner of back per level. Do not add a `BackHandler` if the host already intercepts back.

An enabled `BackHandler` turns off the system predictive back animation for that destination. Use it only where back must be intercepted, and use `PredictiveBackHandler` when the destination needs its own back animation.

## Recipes

New feature:

1. `FeatureRoutes.kt`: public marker plus `internal sealed class` of destinations.
2. `FeatureGraph.kt`: the `NavGraphBuilder` extension with configuration and exit callbacks in its signature.
3. Screens as stateful and stateless pairs, `internal`, without `NavController`.
4. Report the mounting and wiring snippet for the orchestrator. Do not edit the orchestrator.

New destination in an existing feature:

1. Add the route to the sealed class.
2. Register `composable<>` in the feature graph.
3. Create the stateful and stateless pair.
4. Connect the origin screen's `SideEffect` to its callback, and the callback to `navController.navigate(...)` in the graph.
5. If the destination must leave the feature, add a callback to the graph signature. If it must be reached from outside with arguments, add a `navigateToX()` extension. Both change the public contract: report them.

## Migrating existing navigation in a module

Use this mode when the module already has navigation that breaks the pattern above (string routes, public destination routes, screens that receive `NavController`, an Activity or Fragment per screen, direct navigation to another feature) and the task is to move it to the closed graph. Before editing anything, read `references/migration.md` in this skill's folder: it holds the scope rule (one module per task, internals only), the steps, the bridges that keep consumers compiling, and what the migration report adds.

## Before finishing

Check the code you wrote. `references/rules.md` in this skill's folder lists every rule of this skill with a stable ID (NAV-01 to NAV-32, plus the kit-wide KIT-01 to KIT-07); reviews cite those IDs.

- Destinations `internal`; the marker is the only public route (NAV-04).
- No import of another feature's routes, marker or extensions (NAV-06).
- Exits are callbacks in the signature, named by the fact (NAV-14).
- Graph takes `NavController`; screens take neither `NavController` nor `NavBackStackEntry` (NAV-07, NAV-21).
- Arguments are ids or allowed data; no secrets, no entities (NAV-19).
- `toRoute()` once per destination; `launchSingleTop` where a double tap could duplicate (NAV-08, NAV-09).
- Custom `NavType` registered in every destination's `typeMap` (NAV-20).
- Each screen resolves its own ViewModel; `@Preview` targets the stateless composable (NAV-18, NAV-21).
- No `deepLinks` declared in `composable<>` (NAV-11).
- No file outside the given module was modified (NAV-02).
- In a migration, the `@Deprecated` bridges and temporary `TODO` defaults described under "Bridges" in `references/migration.md` are allowed exceptions to the checks above (NAV-31). List them separately in the report (NAV-32).

Then verify:

- Build and test the module, for example `.\gradlew.bat :feature:orders:compileDebugKotlin :feature:orders:testDebugUnitTest`, using the module's real path and variant.
- When you added or changed destinations, cover them with a navigation test using `TestNavHostController` with `ComposeNavigator`: the start destination, the arguments each destination receives, and the callbacks fired when the flow exits.
- Say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

Then end the reply with:

- What was created or changed, by file.
- "Changes needed outside this module": each one with the module, the reason and the snippet. Write "None" if there are none.
- Any change to the feature's public contract (signature, marker, extensions, callback payload types), since it is a breaking change for its consumers.
