---
name: sigma-plugin-development
description: >-
  Comprehensive reference for building Sigma Computing plugins with the
  @sigmacomputing/plugin SDK — editor-panel configuration, reading element
  data, control variables, action triggers/effects, environment/style/
  lifecycle, and hosting. Use when building, configuring, or debugging a
  custom Sigma plugin in any framework (React, Vue, Svelte, vanilla JS).
  Pair with sigma-plugin-patterns for higher-level architectural recipes.
---

# Sigma Plugin Development

This skill provides comprehensive guidance for building Sigma Computing plugins. Sigma plugins are custom web applications embedded within Sigma workbooks that can read data, interact with workbook elements, and respond to user actions.

## Overview

A Sigma plugin is any web application hosted at a URL that uses the `@sigmacomputing/plugin` SDK to communicate with a Sigma workbook. Plugins can be built with any web technology (React, Vue, Svelte, plain JavaScript/HTML, etc.) — the SDK is framework-agnostic.

**SDK Package:** `@sigmacomputing/plugin` (npm)

---

## Plugin Architecture

### How It Works

1. A plugin is a web page loaded inside an iframe within a Sigma workbook
2. The plugin communicates with Sigma via the `@sigmacomputing/plugin` SDK
3. The workbook editor configures the plugin through an **Editor Panel** (defined by the plugin)
4. Data flows from Sigma elements into the plugin; the plugin can write back via **control variables** and **action triggers**

### Initialization

The plugin must configure its editor panel before any rendering. There are two approaches:

**Classic (module-level, works with any framework or vanilla JS):**
```javascript
import { client } from '@sigmacomputing/plugin';

client.config.configureEditorPanel([
  // ... configuration entries
]);
```
This must execute once when the script loads. In React, place it at the top level of the module outside any component.

**React Hook (inside a component):**
```javascript
import { useEditorPanelConfig } from '@sigmacomputing/plugin';

function App() {
  useEditorPanelConfig([
    // ... configuration entries
  ]);
  // ...
}
```
`useEditorPanelConfig` is a newer React-specific alternative that can be called inside a component.

---

## Editor Panel Configuration

The editor panel defines what controls appear in the Sigma workbook's plugin configuration sidebar. Each entry has a `name` (used as the key to retrieve the value) and a `type`.

### Available Configuration Types

#### `element` — Data Source Selector
Lets the workbook editor select a Sigma element (table, visualization, etc.) as the plugin's data source.

```javascript
{ name: 'source', type: 'element' }
```

#### `column` — Column Selector
Lets the editor pick a column from a previously selected element. Must reference a `source` element by name.

```javascript
{
  name: 'dataColumn',
  type: 'column',
  source: 'source',            // References the 'source' element config entry
  allowMultiple: false,         // true to allow selecting multiple columns
  allowedTypes: ['number'],     // Optional: restrict to specific column types
  label: 'Data Column'          // Display label in the editor panel
}
```

**Properties:**
- `source` (required) — name of the element config entry this column belongs to
- `allowMultiple` — when `true`, returns `string[]`; when `false`, returns `string`. Handle both: `Array.isArray(config.columns) ? config.columns : [config.columns].filter(Boolean)`
- `allowedTypes` — restrict which column types can be selected. ValueType values: `'boolean'`, `'datetime'`, `'number'`, `'integer'`, `'text'`, `'variant'`, `'link'`, `'error'`
- `label` — display label in the editor panel

#### `text` — Text Input
A free-form text field. Useful for JSON configuration strings or simple text settings.

```javascript
{
  name: 'config',
  type: 'text',
  label: 'Settings Config (JSON)',
  defaultValue: '{}',           // Optional default value
  placeholder: 'Enter value',   // Optional placeholder text
  multiline: true,              // Optional: enables multi-line text area
  secure: false                 // Optional: password masking, prevents plaintext in query strings
}
```

#### `toggle` — Boolean Toggle
A simple on/off switch.

```javascript
{ name: 'editMode', type: 'toggle', label: 'Edit Mode' }
```

#### `checkbox` — Checkbox
A boolean input, similar to toggle but renders as a checkbox.

```javascript
{ name: 'showLabels', type: 'checkbox', label: 'Show Labels' }
```

#### `radio` — Radio Buttons
Multiple options rendered as radio buttons.

```javascript
{
  name: 'chartType',
  type: 'radio',
  values: ['bar', 'line', 'scatter'],   // Array of selectable options
  singleLine: true,                      // Optional: render inline instead of stacked
  label: 'Chart Type'
}
```

#### `dropdown` — Dropdown Selector
A dropdown with predefined values.

```javascript
{
  name: 'percentile',
  type: 'dropdown',
  source: 'source',
  values: [0.25, 0.5, 0.75, 0.95],    // Array of selectable options
  width: 200                            // Optional: custom width
}
```

#### `color` — Color Picker
A color picker input.

```javascript
{ name: 'accentColor', type: 'color', label: 'Accent Color' }
```

#### `variable` — Control Variable
Binds the plugin to a Sigma workbook control variable. This enables bidirectional data flow — the plugin can read and write the variable's value, and other workbook elements can react to changes.

```javascript
{
  name: 'selectedValue',
  type: 'variable',
  label: 'Selected Value Variable',
  allowedTypes: ['text']              // Optional: restrict variable ControlType
}
```

**ControlType values:** `'boolean'`, `'date'`, `'number'`, `'text'`, `'text-list'`, `'number-list'`, `'date-list'`, `'number-range'`, `'date-range'`

#### `interaction` — Cross-Element Selection Binding
Binds to selection state across workbook elements. Enables selection-driven interactivity.

```javascript
{
  name: 'selection',
  type: 'interaction',
  label: 'Selection Binding'
}
```

#### `action-trigger` — Action Trigger (Outbound)
Binds to a Sigma workbook action. The plugin can trigger this action programmatically (e.g., to refresh data, navigate, filter, etc.).

```javascript
{
  name: 'onValueSelect',
  type: 'action-trigger',
  label: 'On Value Select Action'
}
```

#### `action-effect` — Action Effect (Inbound)
Registers a callback that Sigma can invoke. This is the reverse of `action-trigger` — the workbook triggers the plugin rather than the plugin triggering the workbook.

```javascript
{
  name: 'onExternalAction',
  type: 'action-effect',
  label: 'Handle External Action'
}
```

#### `url-parameter` — URL State Synchronization
Binds to URL parameters, enabling deep linking and state sharing via URL.

```javascript
{
  name: 'filterParam',
  type: 'url-parameter',
  label: 'Filter URL Parameter'
}
```

#### `group` — Logical Grouping
Groups related config entries together in the editor panel.

```javascript
{
  name: 'advancedSettings',
  type: 'group',
  source: 'source'
}
```

### Full Configuration Example

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'dataColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Data Column' },
  { name: 'measure', type: 'column', source: 'source', allowedTypes: ['number', 'integer'], label: 'Measure' },
  { name: 'percentile', type: 'dropdown', source: 'source', values: [0.25, 0.5, 0.75, 0.95] },
  { name: 'config', type: 'text', label: 'Settings Config (JSON)', defaultValue: '{}' },
  { name: 'editMode', type: 'toggle', label: 'Edit Mode' },
  { name: 'selectedValue', type: 'variable', label: 'Selected Value Variable' },
  { name: 'onValueSelect', type: 'action-trigger', label: 'On Value Select Action' },
  { name: 'onExternalAction', type: 'action-effect', label: 'Handle External Action' }
]);
```

### Config Entry Properties Reference

| Property | Type | Applicable To | Description |
|----------|------|---------------|-------------|
| `name` | `string` | All | Unique key to retrieve this value from config |
| `type` | `string` | All | One of: `element`, `column`, `text`, `toggle`, `checkbox`, `radio`, `dropdown`, `color`, `variable`, `interaction`, `action-trigger`, `action-effect`, `url-parameter`, `group` |
| `source` | `string` | `column`, `dropdown`, `group` | Name of the element config entry to reference |
| `allowMultiple` | `boolean` | `column` | Whether multiple columns can be selected |
| `allowedTypes` | `string[]` | `column`, `variable` | For columns: ValueType values. For variables: ControlType values |
| `label` | `string` | All except `element` | Display label shown in the editor panel |
| `defaultValue` | `string` | `text`, `toggle` | Default value for the field |
| `placeholder` | `string` | `text` | Placeholder text shown when empty |
| `multiline` | `boolean` | `text` | Enables multi-line text area |
| `secure` | `boolean` | `text` | Password masking; prevents plaintext in query strings |
| `values` | `any[]` | `dropdown`, `radio` | Array of selectable options |
| `width` | `number` | `dropdown` | Custom width in pixels |
| `singleLine` | `boolean` | `radio` | Render options inline instead of stacked |
| `description` | `string` | All | Tooltip/helper text shown in the editor panel |

---

## Reading Configuration

### React Hook

```javascript
import { useConfig } from '@sigmacomputing/plugin';

const config = useConfig();
// config.source       — element ID string (or undefined)
// config.dataColumn   — column ID string (or undefined if single), string[] if allowMultiple
// config.config       — text field value string
// config.editMode     — boolean
// config.selectedValue    — variable reference ID
// config.onValueSelect   — action trigger reference ID
```

### Plain JavaScript (Subscription & Getter Pattern)

For non-React usage, the SDK provides subscription-based and direct access:

```javascript
import { client } from '@sigmacomputing/plugin';

// Subscribe to all config changes
client.config.subscribe((config) => {
  // Called whenever any config value changes
  const source = config.source;
  const dataColumn = config.dataColumn;
  // ... use values
});

// Get a specific config value directly
const currentSource = client.config.getKey('source');
```

---

## Accessing Data

### Data Structure

Data from Sigma elements is **column-oriented**. Each column is an array of values keyed by the column ID:

```typescript
// The shape of data returned from Sigma
{
  [columnId: string]: (string | number | boolean | null)[]
}
```

**Example data object:**
```javascript
{
  "col-abc123": ["Alice", "Bob", "Charlie"],     // Text column
  "col-def456": [100, 200, 300],                  // Numeric column
  "col-ghi789": [true, false, true],               // Boolean column
  "col-jkl012": [null, "2025-01-15", "2025-03-20"] // Date column (string format)
}
```

Key characteristics:
- Data is organized by **columns**, not rows
- Column keys are internal IDs (not display names) — use column metadata to get display names
- Each column array has the same length (one entry per row)
- Values can be `string`, `number`, `boolean`, or `null`
- Date/datetime values may arrive as ISO strings, numeric timestamps (seconds or milliseconds), or Date objects depending on the source

### React Hooks

```javascript
import { useElementData, useElementColumns } from '@sigmacomputing/plugin';

const sigmaData = useElementData(config.source || '');
const columns = useElementColumns(config.source || '');

// Access a specific column's data
const columnValues = sigmaData[config.dataColumn];  // Array of values
const rowCount = columnValues?.length || 0;
```

### Plain JavaScript (Subscription Pattern)

```javascript
// Subscribe to data updates (returns an unsubscribe function)
const unsubData = client.elements.subscribeToElementData(config.source, (data) => {
  // data is the column-oriented object: { [columnId]: value[] }
  const values = data[config.dataColumn];
  render(values);
});

// Subscribe to column metadata updates
const unsubCols = client.elements.subscribeToElementColumns(config.source, (columns) => {
  // columns: { [columnId]: { name, columnType, id, format? } }
  updateColumnNames(columns);
});

// Clean up when done
unsubData();
unsubCols();
```

### Column Metadata

The column metadata object provides rich information about each column:

```javascript
columns[columnId] = {
  name: string,          // Human-readable display name
  columnType: string,    // Data type: 'text', 'number', 'integer', 'datetime', 'date', 'boolean', 'binary'
  id: string,            // Column identifier
  format?: {             // Optional format specification
    type: string,        // Format category
    format: string       // Format string (d3-format for numbers, d3-time-format for dates)
                         // Examples: "$,.2f" (currency), ",.0f" (integer with commas), "%Y-%m-%d" (date)
  }
}
```

**Column types observed across plugins:** `'text'`, `'number'`, `'integer'`, `'datetime'`, `'date'`, `'boolean'`, `'binary'`, `'string'`

**Format types for the `format.type` property:** `'number'`, `'currency'`, `'percent'`, `'date'`, `'auto'`, `'compact'`
- `number` — numeric format (the `format.format` string controls decimals, prefix, suffix via d3-format)
- `currency` — currency format (auto-adds `$` prefix)
- `percent` — percentage format (auto-adds `%` suffix)
- `date` — date format (`format.format` contains a d3-time-format string like `"%Y-%m-%d"`)
- `auto` — auto-detected format
- `compact` — compact notation (e.g., `1.2K`, `3.4M`)

### Working with the Data

Since data is column-oriented, to iterate by row you index into each column array:

```javascript
const names = sigmaData['col-name'];
const values = sigmaData['col-value'];

for (let i = 0; i < names.length; i++) {
  console.log(`Row ${i}: name=${names[i]}, value=${values[i]}`);
}
```

To convert to row-oriented data:

```javascript
const columnIds = Object.keys(sigmaData);
const rowCount = sigmaData[columnIds[0]]?.length || 0;
const rows = [];

for (let i = 0; i < rowCount; i++) {
  const row = {};
  for (const colId of columnIds) {
    row[colId] = sigmaData[colId][i];
  }
  rows.push(row);
}
```

---

## Date and Time Handling

Sigma can return date/datetime values in multiple formats depending on the source. A defensive parsing approach is recommended:

```javascript
function parseDate(value) {
  if (value === null || value === undefined) return null;

  // Already a Date object
  if (value instanceof Date) {
    return isNaN(value.getTime()) ? null : value;
  }

  // Numeric timestamp (could be seconds or milliseconds)
  if (typeof value === 'number') {
    // Timestamps under ~10 billion are seconds; above are milliseconds
    const ms = value < 10000000000 ? value * 1000 : value;
    const date = new Date(ms);
    return isNaN(date.getTime()) ? null : date;
  }

  // String — try ISO parse first, then fallback
  if (typeof value === 'string') {
    const date = new Date(value);
    return isNaN(date.getTime()) ? null : date;
  }

  return null;
}
```

**Formatting dates for variable writeback:**
```javascript
// Sigma text variables expect YYYY-MM-DD format
const formatted = date.toISOString().split('T')[0];  // "2025-07-18"
await setDateVariable(formatted);
```

**Using column format metadata:**
The `format.format` property on column metadata contains d3-time-format strings (e.g., `"%Y-%m-%d"`) that can be used with d3-time-format or similar libraries.

---

## Control Variables

Control variables provide **bidirectional data binding** between the plugin and the Sigma workbook. Other workbook elements (filters, tables, charts) can listen to these variables.

### React Hook

```javascript
import { useVariable } from '@sigmacomputing/plugin';

// Returns a tuple: [currentValue, setterFunction]
const [selectedValue, setSelectedValue] = useVariable(config.selectedValue || '');

// Read the current value
console.log(selectedValue);

// Write a new value (async)
await setSelectedValue('new value');

// Write-only pattern (discard the getter)
const [, setSelectedValue] = useVariable(config.selectedValue || '');

// Range variables support multiple arguments
await setRangeVariable(startValue, endValue);
```

### Variable Type Coercion

Text variables require explicit `String()` coercion. Use empty string `''` instead of `null` when unsetting:

```javascript
await setSelectedValue(String(someValue));  // Ensure string type
await setSelectedValue('');                  // Clear the variable
```

### Use Cases

- Plugin sets a variable → a Sigma filter reacts, filtering a table
- Plugin reads a variable set by a Sigma control → displays corresponding data
- Passing selected items, search terms, or calculated values back to the workbook

---

## Action Triggers and Action Effects

### Action Triggers (Plugin → Workbook)

Action triggers let the plugin invoke Sigma workbook actions (e.g., refresh data, navigate to a page, trigger a workflow).

```javascript
import { useActionTrigger } from '@sigmacomputing/plugin';

// Returns an async function (or null if not configured)
const triggerAction = useActionTrigger(config.onValueSelect || '');

// Trigger the action
if (triggerAction) {
  await triggerAction();
}
```

### Action Effects (Workbook → Plugin)

Action effects let the workbook invoke a callback inside the plugin. This is the reverse direction — useful for the workbook to tell the plugin to do something.

```javascript
import { useActionEffect } from '@sigmacomputing/plugin';

// Register a callback that Sigma will invoke
useActionEffect(config.onExternalAction || '', () => {
  // This runs when the workbook triggers the action effect
  refreshChart();
  resetSelection();
});
```

### Combining Variables and Actions

A common pattern is to set a control variable and then trigger an action, so the workbook can react to the new value:

```javascript
async function handleUserSelection(value) {
  // 1. Set the control variable with the selected value
  await setSelectedValue(value);

  // 2. Trigger the workbook action (e.g., refresh, navigate)
  if (triggerAction) {
    await triggerAction();
  }
}
```

This pattern enables plugins to drive complex workbook interactions — for example, clicking an item in the plugin filters a dashboard table and refreshes a chart.

---

## Persisting Plugin Settings

Plugins can store custom configuration (settings, theme preferences, layout options) by writing JSON to a `text` type config field. For a detailed walkthrough of this pattern including default merging, edit mode gating, and deep merge strategies, see the **JSON Settings Pattern** in the Sigma Plugin Patterns skill.

### Saving Settings

```javascript
const settingsObject = {
  title: 'My Plugin',
  backgroundColor: '#ffffff',
  customOption: true
};

// Serialize and save to the workbook
// Note: client.config.set() performs a shallow merge with the current config object
client.config.set({ config: JSON.stringify(settingsObject, null, 2) });

// Or update a single key directly
client.config.setKey('config', JSON.stringify(settingsObject, null, 2));
```

### Loading Settings

```javascript
const config = useConfig();

if (config.config?.trim()) {
  try {
    const settings = JSON.parse(config.config);
    // Always merge with defaults for forward compatibility
    const merged = { ...DEFAULT_SETTINGS, ...settings };
  } catch (err) {
    console.error('Invalid config JSON:', err);
    // Fall back to defaults
  }
}
```

Settings stored this way are persisted with the workbook — they survive page refreshes and are shared with anyone viewing the workbook.

---

## Environment, Style, and Lifecycle

### Detecting the Sigma Environment

```javascript
// Returns 'author' | 'viewer' | 'explorer'
const env = client.sigmaEnv;

if (env === 'author') {
  // Workbook is in edit mode — show editing UI
} else if (env === 'viewer') {
  // Read-only viewer — hide editing controls
}
```

This is useful as an alternative (or complement) to the `editMode` toggle — `sigmaEnv` reflects the actual Sigma session context rather than a user-configured toggle.

### Plugin Styles

Sigma can push style information to the plugin (e.g., workbook theme colors):

```javascript
// React: not yet available as a hook — use client API
const style = await client.style.get();

// Subscribe to style changes
client.style.subscribe((pluginStyle) => {
  // Apply workbook theme colors to your plugin
});
```

### Loading State

Show a loading indicator within the Sigma element while your plugin initializes:

```javascript
client.setLoadingState(true);
// ... load data, initialize chart ...
client.setLoadingState(false);
```

### URL Parameters

Plugins can read and write URL parameters for deep linking:

```javascript
// Get current value
const filterValue = client.getUrlParameter('filterParam');

// Set value (updates the URL)
client.setUrlParameter('filterParam', 'category-A');

// Subscribe to changes
client.subscribeToUrlParameter('filterParam', (value) => {
  applyFilter(value);
});
```

---

## SDK API Reference

### React Hooks

```javascript
import {
  client,                // Main SDK client object
  useConfig,             // Get editor panel config (all values)
  useEditorPanelConfig,  // Define editor panel (alternative to client.config.configureEditorPanel)
  useElementData,        // Subscribe to element data
  useElementColumns,     // Get column metadata
  useVariable,           // Read/write control variables
  useActionTrigger,      // Trigger workbook actions (plugin → workbook)
  useActionEffect        // Receive workbook actions (workbook → plugin)
} from '@sigmacomputing/plugin';
```

### Client API (Vanilla JavaScript)

```javascript
import { client } from '@sigmacomputing/plugin';

// --- Environment ---
client.sigmaEnv                                                 // 'author' | 'viewer' | 'explorer'

// --- Configuration ---
client.config.configureEditorPanel(entries)                     // Define editor panel UI
client.config.get()                                             // Get full config object
client.config.getKey(name)                                      // Get a specific config value
client.config.set(config)                                       // Shallow merge with current config
client.config.setKey(name, value)                               // Write a single config value
client.config.subscribe(callback)                               // Subscribe to config changes, returns unsubscribe fn

// --- Element Data ---
client.elements.getElementColumns(configId)                     // Returns Promise<columns>
client.elements.subscribeToElementData(sourceId, callback)      // Subscribe to data, returns unsubscribe fn
client.elements.subscribeToElementColumns(sourceId, callback)   // Subscribe to columns, returns unsubscribe fn

// --- Variables ---
client.getVariable(configId)                                    // Get static variable snapshot
client.setVariable(configId, ...values)                         // Set variable value(s)
client.subscribeToWorkbookVariable(configId, callback)          // Monitor variable changes

// --- Actions ---
client.triggerAction(configId)                                  // Execute an action trigger
client.registerEffect(configId, callback)                       // Register an action effect handler

// --- Interactions ---
client.getInteraction(configId)                                 // Get selection state → WorkbookSelection[]
client.setInteraction(configId, elementId, selection)            // Set selection state

// --- URL Parameters ---
client.getUrlParameter(configId)                                // Get current URL parameter value
client.setUrlParameter(configId, value)                         // Set URL parameter
client.subscribeToUrlParameter(configId, callback)              // Monitor URL parameter changes

// --- Style ---
client.style.get()                                              // Returns Promise<PluginStyle>
client.style.subscribe(callback)                                // Subscribe to style changes

// --- Lifecycle ---
client.setLoadingState(boolean)                                 // Show/hide loading indicator
client.destroy()                                                // Cleanup all subscribers
```

### Hook Reference

| Hook | Returns | Description |
|------|---------|-------------|
| `useConfig()` | `object` | Current editor panel config as key-value object |
| `useEditorPanelConfig(entries)` | `void` | Define editor panel (React alternative to `client.config.configureEditorPanel`) |
| `useElementData(sourceId)` | `{ [colId]: value[] }` | Column-oriented data from the specified element |
| `useElementColumns(sourceId)` | `{ [colId]: ColumnInfo }` | Column metadata (name, columnType, format) |
| `useVariable(variableId)` | `[value, setValue]` | Bidirectional variable binding; setter is async |
| `useActionTrigger(triggerId)` | `function \| null` | Async function to trigger a workbook action |
| `useActionEffect(effectId, callback)` | `void` | Registers callback invoked by workbook action |

---

## Building a Plugin

### Minimal Plain JavaScript Plugin

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/@sigmacomputing/plugin"></script>
</head>
<body>
  <div id="app">Loading...</div>
  <script>
    const { client } = sigmaComputing.plugin;

    // 1. Define what the editor panel shows
    client.config.configureEditorPanel([
      { name: 'source', type: 'element' },
      { name: 'dataColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Column' }
    ]);

    // 2. Subscribe to data changes
    let unsubData = null;

    client.config.subscribe((config) => {
      if (!config.source || !config.dataColumn) {
        document.getElementById('app').textContent = 'Select a data source and column.';
        return;
      }

      // Clean up previous subscription
      if (unsubData) unsubData();

      // Subscribe to element data
      unsubData = client.elements.subscribeToElementData(config.source, (data) => {
        const values = data[config.dataColumn];
        if (values) {
          document.getElementById('app').textContent = `${values.length} rows loaded`;
        }
      });
    });
  </script>
</body>
</html>
```

### React Plugin Structure

```
my-plugin/
  package.json          # Must include @sigmacomputing/plugin dependency
  public/
    index.html          # Standard HTML shell with a root div
  src/
    index.js            # Mount your app to the DOM
    App.js              # Main plugin component
```

```javascript
// App.js
import { client, useConfig, useElementData, useElementColumns } from '@sigmacomputing/plugin';

// Configure editor panel at module level
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'dataColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Column' }
]);

function App() {
  const config = useConfig();
  const data = useElementData(config.source || '');
  const columns = useElementColumns(config.source || '');

  if (!config.source) return <p>Select a data source.</p>;
  if (!config.dataColumn) return <p>Select a column.</p>;

  const values = data[config.dataColumn] || [];
  const colName = columns[config.dataColumn]?.name || config.dataColumn;

  return (
    <div>
      <h1>{values.length} rows from "{colName}"</h1>
      <ul>
        {values.map((v, i) => <li key={i}>{String(v)}</li>)}
      </ul>
    </div>
  );
}

export default App;
```

---

## Registering, Hosting, and Development

### Registering a Plugin in Sigma

1. Build your plugin and host it at a publicly accessible URL (or localhost for development)
2. In Sigma, go to **Administration > Plugins**
3. Click **Add Plugin** and enter the URL
4. The plugin becomes available to add to any workbook
5. In a workbook, add the plugin element and configure it via the editor panel

### Local Development

Run your plugin locally and register `http://localhost:3000` (or your dev server port) as the plugin URL in Sigma. Changes hot-reload in the workbook. The default Vite dev server runs on `http://localhost:5173`.

### Production Hosting

Any static hosting works: Vercel, Netlify, S3 + CloudFront, GitHub Pages, etc. The plugin just needs to be a publicly accessible URL serving your HTML/JS/CSS.

### Build Considerations

- The plugin runs in an iframe — bundle everything needed (no reliance on the parent page)
- Keep bundle size small for fast load times inside workbooks
- CORS is typically not an issue since the SDK handles communication via postMessage
- For vanilla JS plugins, you can use a CDN-hosted SDK to avoid any build step entirely

---

## Data Type Reference

### Config Values by Type

| Config Type | Value in `useConfig()` |
|-------------|----------------------|
| `element` | `string` (element ID) or `undefined` |
| `column` (`allowMultiple: false`) | `string` (column ID) or `undefined` |
| `column` (`allowMultiple: true`) | `string[]` (array of column IDs) |
| `text` | `string` |
| `toggle` | `boolean` |
| `checkbox` | `boolean` |
| `radio` | The selected value from the `values` array |
| `dropdown` | The selected value from the `values` array |
| `color` | `string` (color value) |
| `variable` | `string` (variable reference ID) |
| `interaction` | `string` (interaction reference ID) |
| `action-trigger` | `string` (action reference ID) |
| `action-effect` | `string` (action effect reference ID) |
| `url-parameter` | `string` (URL parameter reference ID) |

### Element Data Values

Each column in the data object is an array. Individual values are one of:

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text values, dates as ISO strings | `"Hello"`, `"2025-01-15"` |
| `number` | Numeric values, integers, decimals, timestamps | `42`, `3.14`, `1737936000` |
| `boolean` | True/false values | `true`, `false` |
| `null` | Missing or empty values | `null` |

### Column Metadata (ColumnInfo)

```javascript
columns[columnId] = {
  name: string,          // Human-readable display name
  columnType: string,    // 'text' | 'number' | 'integer' | 'datetime' | 'date' | 'boolean' | 'binary'
  id: string,            // Column identifier
  format?: {
    type: string,        // Format category
    format: string       // d3-format string (numbers) or d3-time-format string (dates)
  }
}
```

---

## Tips and Best Practices

- **Always call `configureEditorPanel` at module level** (or use `useEditorPanelConfig` inside a component) — before any rendering or component lifecycle
- **Handle missing config gracefully** — users configure plugins incrementally; your plugin will render before all fields are set
- **Use control variables for output** — when your plugin needs to pass data back to the workbook, use variables rather than trying to modify elements directly
- **Combine variables + actions** — set a variable then trigger an action for the most responsive workbook interactions
- **Persist settings as JSON** — use a `text` config field to store serialized settings that survive page refreshes
- **Column IDs vs. display names** — always use `useElementColumns` to resolve human-readable names; never assume the column ID is the display name
- **Data is column-oriented** — if you need row-oriented access, transpose it yourself
- **Handle date formats defensively** — dates may arrive as strings, numbers (seconds or ms timestamps), or Date objects
- **Use `allowedTypes` on columns** — restrict column selection to appropriate types (e.g., `['number', 'integer']` for numeric-only fields)
- **The plugin runs in an iframe** — standard web security restrictions apply; the plugin cannot access the parent Sigma page directly
- **Subscriptions return unsubscribe functions** — in vanilla JS plugins, always clean up subscriptions when the source changes
