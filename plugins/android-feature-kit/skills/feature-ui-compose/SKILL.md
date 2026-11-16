---
name: feature-ui-compose
description: "Team pattern for the presentation layer of an Android feature module: MVI through interface delegation (a ViewModel that implements the MVI contract `by mvi(...)`), screen contracts with UiState, UiAction and SideEffect, stateful and stateless Compose screens, previews and ViewModel tests, with Hilt. Use it before creating or changing a screen, a ViewModel, UI state, a screen contract or a composable inside a feature, even when the task is a ticket or plan that already lists the steps. Not for navigation graphs, routes or exit callbacks (feature-navigation-compose) and not for use cases, repositories or storage. Also for requests in Spanish such as pantalla, vista, ViewModel, estado de UI, contrato, acción, efecto, componente Compose."
---

# Feature UI with Compose and MVI

Creates the presentation layer of one feature module: the screen contract, its ViewModel and its composables. Every screen is built the same way so that navigation, tests and previews plug in without adaptation.

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

## Scope

- Work inside one feature module, in its presentation package. Infer the module from the paths or files the user gave; ask only if more than one module fits.
- The feature keeps its layers as packages (`presentation`, `domain`, `data`, or the names the module already uses). Presentation imports from `domain` only. It never imports anything from `data`.
- Do not edit other modules. If the work needs a change outside the module, list it at the end under "Changes needed outside this module" with the exact snippet.
- Follow the module's existing naming and style over the examples here.

## Read before writing

The examples use placeholder names. Find the real ones in the project and use them:

- The MVI contract interface and its delegate (`MVI<S, A, E>` and `mvi(initialState)` here): how state is updated and how side effects are emitted.
- The Compose side effect collector (`CollectSideEffect` here).
- The project's `Either` and its functions (`fold`, `map`, `mapLeft` or whatever it calls them).
- The design system: components, theme, spacing and typography tokens.
- One existing screen in the module, if there is one.

The MVI delegate, the side effect collector and the `Either` are required: if one of them does not exist yet, ask the user where it should live, and do not create a private copy inside the feature. Anything else missing does not block the task: build the screen from the design system pieces that exist and report what is missing.

## Contract

One contract per screen, `internal`, holding the three types:

```kotlin
internal object OrderDetailContract {
    data class UiState(
        val isLoading: Boolean = true,
        val order: OrderUi? = null,
        val error: OrderDetailError? = null,
    )

    sealed interface UiAction {
        data object Started : UiAction
        data object Retry : UiAction
        data object CancelClicked : UiAction
        data object HelpClicked : UiAction
    }

    sealed interface SideEffect {
        data class Cancelled(val orderId: String) : SideEffect
        data object HelpRequested : SideEffect
    }
}
```

- `UiState` is an immutable `data class` whose defaults are the initial state. Model loading, content, empty and error explicitly.
- What the screen shows is a presentation model (`OrderUi`) when it needs formatting or combines several domain models. Format amounts, dates and masks when mapping to it, not inside composables.
- `UiAction` is named by what happened on the screen (`Started`, `CancelClicked`, `Retry`, `AmountChanged`), not by what the ViewModel will do next. A screen that loads data has a `Started` action.
- `SideEffect` is only for one-off events that state cannot express: a flow exit that becomes a navigation callback, a one-time message. If it can be shown as state, it is state.
- Errors in `UiState` are presentation errors (a sealed type or a string resource id) mapped from the domain error. Domain errors never reach composables.

## ViewModel

```kotlin
@HiltViewModel
internal class OrderDetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val observeOrder: ObserveOrderUseCase,
    private val refreshOrder: RefreshOrderUseCase,
    private val cancelOrder: CancelOrderUseCase,
) : ViewModel(),
    MVI<OrderDetailContract.UiState, OrderDetailContract.UiAction, OrderDetailContract.SideEffect>
    by mvi(OrderDetailContract.UiState()) {

    private val orderId = OrderId(savedStateHandle.toRoute<OrderRoutes.Detail>().orderId)
    private var started = false
    private var observeJob: Job? = null
    private var refreshJob: Job? = null

    override fun onAction(action: OrderDetailContract.UiAction) {
        when (action) {
            OrderDetailContract.UiAction.Started -> start()
            OrderDetailContract.UiAction.Retry -> {
                if (observeJob?.isActive != true) observe()
                refresh()
            }
            OrderDetailContract.UiAction.CancelClicked -> cancel()
            OrderDetailContract.UiAction.HelpClicked ->
                viewModelScope.emitSideEffect(OrderDetailContract.SideEffect.HelpRequested)
        }
    }

    private fun start() {
        if (started) return
        started = true
        if (observeJob?.isActive != true) observe()
        refresh()
    }

    private fun observe() {
        observeJob = observeOrder(orderId)
            .onEach { order -> updateUiState { copy(isLoading = false, order = order?.toUi()) } }
            .catch { updateUiState { copy(isLoading = false, error = OrderDetailError.LoadFailed) } }
            .launchIn(viewModelScope)
    }

    private fun refresh() {
        if (refreshJob?.isActive == true) return
        refreshJob = viewModelScope.launch {
            refreshOrder(orderId).fold(
                ifLeft = { error -> updateUiState { copy(isLoading = false, error = error.toUiError()) } },
                ifRight = { updateUiState { copy(error = null) } },
            )
        }
    }

    private fun cancel() {
        viewModelScope.launch {
            cancelOrder(orderId).fold(
                ifLeft = { error -> updateUiState { copy(error = error.toUiError()) } },
                ifRight = { emitSideEffect(OrderDetailContract.SideEffect.Cancelled(orderId.value)) },
            )
        }
    }
}
```

`updateUiState`, `emitSideEffect` and `fold(ifLeft, ifRight)` stand for the project's delegate and `Either` functions.

- One ViewModel per screen, `internal`, `@HiltViewModel`, implementing the MVI contract by delegation. State and effects go only through the delegate. Do not add your own `MutableStateFlow`, `Channel` or `SharedFlow` next to it.
- The ViewModel depends on use cases only. It never receives a repository (not even its domain interface), a data source, a DAO, an API or a `Context`.
- `onAction` is an exhaustive `when` with no `else` branch.
- The constructor, `init` blocks and property initializers start no work: no use case calls, no `launch`, no `launchIn`. Reading route arguments there is fine. Loading starts when the stateful screen sends `Started`. The screen sends it again each time it re-enters composition, for example after a configuration change or when the user navigates back to it, so the ViewModel runs it once per instance and ignores the rest. Keep `started` as a plain field, not in `SavedStateHandle`: the new instance after process death has to start again.
- Offline-first screens observe and refresh separately. `Started` starts the observation, with a `.catch` that turns a local read failure into an error state. `catch` ends the flow, so `Retry` starts the observation again when it is no longer active. Call the refresh use case on `Started` and on `Retry`, and ignore `Retry` while a refresh is still running. Cached content stays on screen while refreshing, and a refresh error is shown next to the content without replacing it.
- Handle every `Either` result. A `Left` updates state or emits an effect; it is never dropped.
- Do not catch `CancellationException`, directly or through `catch (e: Exception)` or `runCatching`. Use cases return `Either`, so expected failures need no try/catch here.
- No navigation, no `NavController`, no Android resources resolved in the ViewModel. Text is resolved from resources in the composable.
- Read route arguments with `savedStateHandle.toRoute<Route>()` (routes and argument rules belong to feature-navigation-compose). When the route has a custom argument type, pass the same map the graph registers: `toRoute<Route>(typeMap = ...)`.
- Use `SavedStateHandle` for anything else only for small, non-sensitive input that must survive process death. Never save PINs, passwords, OTPs, tokens, full card numbers or CVVs there.

## Screens

Every destination has a pair, both `internal`:

```kotlin
@Composable
internal fun OrderDetailScreen(
    onCancelled: (orderId: String) -> Unit,
    onHelpRequested: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: OrderDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.onAction(OrderDetailContract.UiAction.Started)
    }

    CollectSideEffect(viewModel.sideEffect) { effect ->
        when (effect) {
            is OrderDetailContract.SideEffect.Cancelled -> onCancelled(effect.orderId)
            OrderDetailContract.SideEffect.HelpRequested -> onHelpRequested()
        }
    }

    OrderDetailScreenContent(
        state = state,
        onAction = viewModel::onAction,
        modifier = modifier,
    )
}

@Composable
internal fun OrderDetailScreenContent(
    state: OrderDetailContract.UiState,
    modifier: Modifier = Modifier,
    onAction: (OrderDetailContract.UiAction) -> Unit = {},
) {
    // layout
}
```

- `XScreen` is stateful: it resolves the ViewModel, sends `Started` from `LaunchedEffect(viewModel)` when the screen loads data, collects state with `collectAsStateWithLifecycle()` and turns each `SideEffect` into a call to a callback. Its callbacks have no default values, so a missing wiring fails to compile.
- `XScreenContent` is stateless: state in, `onAction` out. It never sends `Started`, so previews and UI tests that target it load nothing.
- Neither receives `NavController` or `NavBackStackEntry`. Do not name composables `XRoute`; `Route` is reserved for navigation routes.
- The `hiltViewModel()` import depends on the project's Hilt version: `androidx.hilt.lifecycle.viewmodel.compose` on Hilt 1.3 or later, `androidx.hilt.navigation.compose` before that. Use the one the project already imports.

## Composables

- `modifier: Modifier = Modifier` is the first optional parameter and is applied once, to the root element.
- Use design system components and tokens. No hardcoded colors, sizes or text styles. If the design system lacks a component, compose the screen from the pieces and tokens it has, and report the missing reusable component instead of creating it inside the feature.
- All user-visible text comes from string resources.
- Accessibility: meaningful icons and images have a `contentDescription` and decorative ones pass `null`; touch targets are at least 48dp; custom controls declare their role and state with `semantics`; information is never conveyed by color alone.
- Lazy lists pass a stable `key` for each item.
- Composables display state and report actions. They do not decide business outcomes or call use cases.
- Do not add `@Immutable` or `@Stable` by reflex. Under strong skipping most classes need nothing. When the task is about performance, follow the jetpack-compose-performance skill.

## Previews

One preview per meaningful state of `XScreenContent`: content, loading, empty and error. Use a `PreviewParameterProvider` when there are several. Previews are `private` and use fake presentation models, never a ViewModel.

## Tests

- ViewModel unit tests with fake use cases: creating the ViewModel calls no use case, `Started` loads once even when sent twice, `Retry` before `Started` leaves a single observation, each action produces the expected state, each effect is emitted once, and each `Left` ends up in state or in an effect. Use the project's main dispatcher rule, and Turbine if the project already has it.
- A Compose UI test on `XScreenContent` when the module already has UI tests.

## Before finishing

Check the code you wrote:

- Presentation imports nothing from the `data` package, and the ViewModel depends on use cases only.
- Contract types, ViewModel and screens are `internal`. No `when` over actions or effects has an `else` branch.
- State changes and effects go through the MVI delegate.
- No work starts in the constructor, `init` or property initializers. On screens that load data, the first load starts on `Started` and runs once per ViewModel; `Retry` can load again.
- Every `Either` result is handled and no `CancellationException` is swallowed.
- Stateful screen: `hiltViewModel()`, `Started` sent from `LaunchedEffect(viewModel)` if the screen loads data, `collectAsStateWithLifecycle()`, effects mapped to callbacks without defaults. Stateless screen: state and `onAction` only.
- Text from resources, design system components, accessibility labels.
- Previews cover each state of the stateless screen.

Then verify:

- Build and test the module, for example `.\gradlew.bat :feature:orders:compileDebugKotlin :feature:orders:testDebugUnitTest`, using the module's real path and variant.
- If Android CLI is installed, render the new previews and look at the result: `android preview render --fqn <fully.qualified.PreviewFunction> --component-tree`. Check the PNG, and check that the component tree has the expected texts and semantics.
- Say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

End the reply with:

- What was created or changed, by file.
- "Changes needed outside this module": each one with the module, the reason and the snippet. Write "None" if there are none.
- Any change to what the screen exposes to navigation (callbacks, their parameters), since the feature graph depends on it.
