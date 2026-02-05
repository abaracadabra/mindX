# mindX Tab System

Tabs are the modular extension point for the mindX UI. One system (the tab registry) handles all tab switching and activation.

## Adding a new tab

1. **DOM**: Add a button with `data-tab="my-tab"` and a content panel with `id="my-tab-tab"` in `app.html` (or inject them via script). The registry shows/hides content by convention: `#${tabId}-tab`.

2. **Registration**: Either:
   - Add an entry to `TabConfig.main`, `TabConfig.core`, `TabConfig.tools`, or `TabConfig.addons` in [tab-config.js](tab-config.js), then ensure `TabConfig.registerAllTabs()` runs (it does when the modular tab system is active), or
   - Call `tabRegistry.registerTab({ id, label, group, onActivate, onDeactivate })` directly (e.g. from your component script).

3. **Behavior**: Provide activation logic via one of:
   - **Component class**: Set `component: 'MyTab'` in TabConfig where `MyTab` is a class extending `TabComponent` (in `components/`) that exposes `initialize()` and `onActivate()`.
   - **Facade**: Set `facade: 'MyTab'` and `facadeMethod: 'load'` in TabConfig; your script exposes `window.MyTab = { load() { ... } }`.
   - **Legacy loader**: Set `legacyLoader: 'loadMyTab'` in TabConfig; app.js exposes `window.loadMyTab`.

Use `TabConfig.addTab(tabConfig)` to add a tab at runtime without editing the main config arrays.
