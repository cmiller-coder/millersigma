---
name: sigma-plugin-patterns
description: >-
  Proven architectural patterns and practical recipes for Sigma Computing
  plugins — the JSON settings pattern for rich configuration beyond the
  editor panel, and other reusable flows for state, config, and interaction.
  Use alongside sigma-plugin-development when structuring how a plugin
  stores settings or orchestrates workbook interactions.
---

# Sigma Plugin Common Patterns & Flows

This skill covers proven patterns and architectural approaches for building Sigma plugins. It complements the core Sigma Plugin Development skill with practical recipes for common needs.

---

## The JSON Settings Pattern

### The Problem

Sigma's editor panel (`configureEditorPanel`) provides basic controls — element selectors, column pickers, toggles, dropdowns, and text fields. But these controls have limited UI customization. For plugins that need rich configuration (color pickers, nested options, conditional settings, layout builders, etc.), the editor panel is too restrictive.

### The Solution

Use a single `text` type config field as a **JSON storage layer**. The plugin reads/writes a serialized JSON object to this field, and provides its own custom settings UI within the plugin itself.

This gives you:
- Full control over the settings UI (any HTML/CSS/JS you want)
- Arbitrarily complex nested configuration
- Settings that persist with the workbook
- A single source of truth stored in Sigma's config system

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Sigma Editor Panel                             │
│  ┌───────────────────────────────────────────┐  │
│  │ source:     [Element Selector]            │  │
│  │ dataColumn: [Column Selector]             │  │
│  │ config:     [Hidden/Raw JSON text field]  │  │  ← JSON lives here
│  │ editMode:   [Toggle]                      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Plugin (iframe)                                │
│  ┌───────────────────────────────────────────┐  │
│  │  Custom Settings Dialog/Panel             │  │  ← Your UI reads/writes
│  │  ┌─────────────────────────────────┐      │  │     the JSON config
│  │  │ Title: [________]               │      │  │
│  │  │ Theme: [Light ▼]               │      │  │
│  │  │ Colors: [🎨] [🎨] [🎨]          │      │  │
│  │  │ Layout: [Grid ▼]              │      │  │
│  │  │ [Save]  [Cancel]               │      │  │
│  │  └─────────────────────────────────┘      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Implementation

#### 1. Reserve a text field in the editor panel config

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'dataColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Column' },
  { name: 'config', type: 'text', label: 'Settings Config (JSON)', defaultValue: '{}' },
  { name: 'editMode', type: 'toggle', label: 'Edit Mode' }
]);
```

The `config` field stores the entire settings object as a JSON string. The `editMode` toggle controls whether the plugin shows the settings UI.

#### 2. Define your settings shape

```javascript
// Define defaults — these are used when no saved config exists
const DEFAULT_SETTINGS = {
  title: 'My Plugin',
  backgroundColor: '#ffffff',
  textColor: '#000000',
  layout: 'grid',
  itemsPerPage: 10,
  showLabels: true,
  styling: {
    theme: 'light',
    borderRadius: '8px',
    fontSize: '14px'
  }
};
```

Keep defaults comprehensive. Every setting should have a sensible default so the plugin works immediately without configuration.

#### 3. Load settings from the config field

```javascript
function loadSettings(configString) {
  if (!configString || !configString.trim()) {
    return { ...DEFAULT_SETTINGS };
  }

  try {
    const parsed = JSON.parse(configString);
    // Merge with defaults so new settings added later get their defaults
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch (err) {
    console.error('Invalid config JSON:', err);
    return { ...DEFAULT_SETTINGS };
  }
}
```

**Always merge with defaults** using spread. This ensures forward compatibility — when you add new settings fields in a future version, existing workbooks that don't have those fields will pick up the defaults automatically rather than breaking.

For nested settings, use deep merge:
```javascript
const newSettings = {
  ...DEFAULT_SETTINGS,
  ...parsed,
  styling: {
    ...DEFAULT_SETTINGS.styling,
    ...(parsed.styling || {})
  }
};
```

#### 4. Save settings back to Sigma

```javascript
function saveSettings(settingsObject) {
  const json = JSON.stringify(settingsObject, null, 2);
  client.config.set({ config: json });
}
```

`client.config.set()` writes the JSON string back to the `config` text field. Sigma persists this with the workbook.

#### 5. Gate the settings UI behind edit mode

Only show the settings interface when `editMode` is toggled on in the editor panel. This way end users viewing the workbook don't see configuration UI — only editors do.

```javascript
// React example
if (config.editMode) {
  // Render settings button / panel
}

// Plain JS example
if (config.editMode) {
  document.getElementById('settings-btn').style.display = 'block';
}
```

### Complete Flow

```
Editor toggles "Edit Mode" ON
  → Plugin shows Settings button
    → User clicks Settings
      → Plugin opens custom settings dialog
        → User modifies settings (colors, layout, options, etc.)
          → User clicks Save
            → Plugin serializes settings to JSON
              → client.config.set({ config: jsonString })
                → Sigma persists the JSON in the workbook
                  → Plugin re-renders with new settings

Later, when workbook loads:
  → useConfig() returns the saved config string
    → Plugin parses JSON
      → Plugin renders with saved settings
```

### Tips for the Settings Pattern

- **Validate on load, not on save** — always wrap `JSON.parse` in try/catch when reading. Assume the stored string could be malformed.
- **Merge with defaults** — never replace defaults entirely with parsed config. Always spread defaults first, then overlay saved values. This handles version upgrades gracefully.
- **Use `null, 2` in stringify** — the pretty-printed JSON is visible in the editor panel text field. Readable JSON helps with debugging.
- **Keep the config field labeled clearly** — users may see the raw JSON in the editor panel. A label like "Settings Config (JSON)" tells them not to hand-edit it.
- **Consider a reset mechanism** — provide a "Reset to Defaults" button in your settings UI that writes the default settings back.

---

## Edit Mode Pattern

### Purpose

Sigma plugins often need two modes: a **view mode** for consumers and an **edit mode** for workbook builders. The edit mode toggle is the standard way to handle this.

### Setup

```javascript
client.config.configureEditorPanel([
  // ... other config
  { name: 'editMode', type: 'toggle', label: 'Edit Mode' }
]);
```

### Usage

```javascript
const config = useConfig();

// Only show editing controls when edit mode is on
if (config.editMode) {
  // Show: settings buttons, drag handles, add/remove controls, etc.
}
```

### What Edit Mode Enables

- Settings button/panel
- Inline editing (rename titles, reorder items)
- Debug information (data counts, column IDs)
- Configuration wizards
- Any UI that workbook builders need but viewers should not see

---

## Variable + Action Trigger Pattern

### Purpose

When a plugin needs to communicate a user action back to the workbook (e.g., "the user clicked row 5" or "the user selected Category X"), use the combination of a control variable and an action trigger.

### Setup

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'selectedValue', type: 'variable', label: 'Selected Value' },
  { name: 'onSelect', type: 'action-trigger', label: 'On Select Action' }
]);
```

### Implementation

```javascript
// React
const [selectedValue, setSelectedValue] = useVariable(config.selectedValue || '');
const triggerOnSelect = useActionTrigger(config.onSelect || '');

async function handleItemClick(value) {
  // Step 1: Set the variable (so the workbook knows WHAT was selected)
  await setSelectedValue(value);

  // Step 2: Trigger the action (so the workbook knows to REACT)
  if (triggerOnSelect) {
    await triggerOnSelect();
  }
}
```

### Why Both?

- The **variable** carries the data (what was selected, what value changed)
- The **action trigger** signals the event (something happened, react now)

The workbook builder connects these in Sigma:
1. The variable feeds into a filter or control
2. The action trigger refreshes elements, navigates pages, or runs workflows

### Multiple Variables

For plugins that need to pass multiple pieces of information:

```javascript
client.config.configureEditorPanel([
  { name: 'selectedId', type: 'variable', label: 'Selected ID' },
  { name: 'selectedName', type: 'variable', label: 'Selected Name' },
  { name: 'selectedCategory', type: 'variable', label: 'Selected Category' },
  { name: 'onSelect', type: 'action-trigger', label: 'On Select' }
]);

// Set all variables, then trigger once
async function handleSelection(item) {
  await setSelectedId(item.id);
  await setSelectedName(item.name);
  await setSelectedCategory(item.category);
  if (triggerOnSelect) await triggerOnSelect();
}
```

### Dual-Variable Pattern for Context Actions

When a user action needs both a value and a label (e.g., for context menus or drill-downs):

```javascript
client.config.configureEditorPanel([
  { name: 'contextValue', type: 'variable', label: 'Context Menu Value' },
  { name: 'contextLabel', type: 'variable', label: 'Context Menu Label' },
  { name: 'onContextAction', type: 'action-trigger', label: 'On Context Action' }
]);

async function handleContextMenu(item) {
  await setContextValue(item.id);           // The data value
  await setContextLabel(item.displayName);   // Human-readable label
  if (triggerContextAction) await triggerContextAction();
}
```

### Write-Only Variable Pattern

When the plugin only writes to a variable and never reads it:

```javascript
const [, setSelectedValue] = useVariable(config.selectedValue || '');
// Destructure with leading comma to discard the getter
```

---

## Dynamic Editor Panel Reconfiguration

### Purpose

Sometimes the editor panel needs to show different fields depending on the current configuration state. For example, a "Enable Writeback" toggle should reveal variable and action-trigger fields only when enabled.

### Implementation

```javascript
const buildEditorPanelConfig = (enableWriteback = false) => {
  const baseConfig = [
    { name: 'source', type: 'element' },
    { name: 'categoryColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Category' },
    { name: 'enableWriteback', type: 'toggle', label: 'Enable Writeback' },
    { name: 'config', type: 'text', label: 'Settings Config (JSON)', defaultValue: '{}' },
    { name: 'editMode', type: 'toggle', label: 'Edit Mode' }
  ];

  if (enableWriteback) {
    baseConfig.push(
      { name: 'selectedID', type: 'variable', label: 'Selected ID Variable' },
      { name: 'selectedCategory', type: 'variable', label: 'Selected Category Variable' },
      { name: 'updateCategory', type: 'action-trigger', label: 'Update Category' }
    );
  }

  return baseConfig;
};

// Initial configuration
client.config.configureEditorPanel(buildEditorPanelConfig());

function App() {
  const config = useConfig();

  // Reconfigure when the toggle changes
  useEffect(() => {
    client.config.configureEditorPanel(buildEditorPanelConfig(config.enableWriteback));
  }, [config.enableWriteback]);

  // ...
}
```

This pattern lets you keep the editor panel clean — users only see fields relevant to their current configuration choices.

---

## Variable Value Unwrapping

### The Problem

Variable values from `useVariable()` can sometimes arrive as objects rather than plain values, depending on the variable type and SDK version:

```javascript
// May be a simple string
"some value"

// Or an object with a value property
{ value: "some value" }

// Or nested
{ defaultValue: { value: "some value" } }
```

### Defensive Unwrapping

```javascript
function unwrapVariable(variableValue) {
  if (variableValue === null || variableValue === undefined) return null;

  // Object with .value
  if (typeof variableValue === 'object') {
    if (variableValue.value !== undefined) return variableValue.value;
    if (variableValue.defaultValue?.value !== undefined) return variableValue.defaultValue.value;
    return null;
  }

  // Primitive value
  return variableValue;
}

const [rawValue] = useVariable(config.selectedValue || '');
const actualValue = unwrapVariable(rawValue);
```

**Date variables** may have an additional nesting level with a timestamp:

```javascript
// Date variable structure
{ defaultValue: { value: { date: 1737936000000 } } }  // milliseconds timestamp

function unwrapDateVariable(variableValue) {
  const unwrapped = unwrapVariable(variableValue);
  if (unwrapped && typeof unwrapped === 'object' && unwrapped.date) {
    const date = new Date(unwrapped.date);
    // Account for timezone offset if needed
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() + offset);
  }
  return unwrapped ? new Date(unwrapped) : null;
}
```

Always use defensive unwrapping when reading variable values, especially for variables bound to text area controls, date pickers, or complex workbook elements.

---

## Action Effect Pattern (Workbook → Plugin)

### Purpose

When the workbook needs to tell the plugin to do something (the reverse of action triggers). For example, an external button in Sigma tells the plugin to reset, refresh, or change state.

### Setup

```javascript
client.config.configureEditorPanel([
  { name: 'onReset', type: 'action-effect', label: 'Reset Plugin' }
]);
```

### Implementation

```javascript
import { useActionEffect } from '@sigmacomputing/plugin';

useActionEffect(config.onReset || '', () => {
  // This callback runs when the workbook triggers the action
  resetPluginState();
  clearSelection();
});
```

---

## LLM/AI Integration Pattern

### Purpose

Plugins can orchestrate AI workflows by combining variables (for prompts/responses) with action triggers (to invoke Sigma actions that call LLMs).

### Setup

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'aiPrompt', type: 'variable', allowedTypes: ['text'], label: 'AI Prompt Variable' },
  { name: 'aiResponse', type: 'variable', allowedTypes: ['text'], label: 'AI Response Variable' },
  { name: 'aiAction', type: 'action-trigger', label: 'Run AI Action' }
]);
```

### Implementation

```javascript
const [aiPrompt, setAiPrompt] = useVariable(config.aiPrompt || '');
const [aiResponse, setAiResponse] = useVariable(config.aiResponse || '');
const triggerAiAction = useActionTrigger(config.aiAction || '');

async function askAI(question) {
  // 1. Set the prompt
  await setAiPrompt(question);

  // 2. Trigger the Sigma action (which calls the LLM)
  if (triggerAiAction) {
    await triggerAiAction();
  }

  // 3. Watch for response changes via useEffect or subscription
}

// Watch for response updates
useEffect(() => {
  if (aiResponse) {
    // Process the AI response
    // May need to unwrap: response could be a string or { value: "..." }
    const text = typeof aiResponse === 'object' ? aiResponse.value : aiResponse;
    handleAIResponse(text);
  }
}, [aiResponse]);
```

---

## Multi-Column Data Pattern

### Selecting Multiple Columns

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'columns', type: 'column', source: 'source', allowMultiple: true, label: 'Data Columns' }
]);
```

With `allowMultiple: true`, the config value may be an array of column IDs or a single ID. Always handle both:

```javascript
const columnIds = Array.isArray(config.columns) ? config.columns : [config.columns].filter(Boolean);
```

### Multiple Named Columns

For plugins that need specific columns for specific roles (e.g., a chart needing X axis, Y axis, and label):

```javascript
client.config.configureEditorPanel([
  { name: 'source', type: 'element' },
  { name: 'xAxis', type: 'column', source: 'source', allowMultiple: false, label: 'X Axis' },
  { name: 'yAxis', type: 'column', source: 'source', allowMultiple: false, label: 'Y Axis' },
  { name: 'labelColumn', type: 'column', source: 'source', allowMultiple: false, label: 'Labels' },
  { name: 'tooltipColumns', type: 'column', source: 'source', allowMultiple: true, label: 'Tooltip Fields' }
]);
```

Each column config entry independently references the same source element but serves a different purpose in the plugin.

### Using Column Type Metadata for Auto-Detection

```javascript
const columns = useElementColumns(config.source || '');
const columnInfo = columns[config.xAxis];

// Auto-detect time series based on column type
const isTimeSeries = /date|time/i.test(columnInfo?.columnType || '');

// Use format metadata for display
if (columnInfo?.format?.format) {
  // columnInfo.format.format contains d3-format or d3-time-format strings
  // e.g., "$,.2f" for currency, "%Y-%m-%d" for dates
}
```

---

## Data Transformation Patterns

### Column-Oriented to Row-Oriented

Sigma provides data as columns. Many UI libraries expect rows.

```javascript
function toRows(sigmaData, columnIds, columns) {
  const rowCount = sigmaData[columnIds[0]]?.length || 0;
  const rows = [];

  for (let i = 0; i < rowCount; i++) {
    const row = {};
    for (const colId of columnIds) {
      // Use display name as key for readability
      const name = columns[colId]?.name || colId;
      row[name] = sigmaData[colId][i];
    }
    rows.push(row);
  }

  return rows;
}
```

### Filtering Null Values

```javascript
const cleanValues = sigmaData[columnId].filter(v => v !== null);
```

### Aggregating Data

```javascript
const numbers = sigmaData[columnId].filter(v => typeof v === 'number');
const sum = numbers.reduce((a, b) => a + b, 0);
const avg = numbers.length > 0 ? sum / numbers.length : 0;
const min = Math.min(...numbers);
const max = Math.max(...numbers);
```

### Type-Safe Value Handling

Sigma columns can contain mixed types. Defensive type checking is important:

```javascript
const value = sigmaData[columnId][i];

if (typeof value === 'number') {
  // Numeric processing
} else if (typeof value === 'string') {
  // String processing
} else if (typeof value === 'boolean') {
  // Convert to string if needed: String(value)
} else {
  // null — skip or use default
}
```

### Date Normalization

Dates from Sigma may arrive as ISO strings, numeric timestamps (seconds or milliseconds), or Date objects. See the **Date and Time Handling** section in the core Sigma Plugin Development skill for a defensive `parseDate()` function that handles all formats.

---

## Graceful Loading Pattern

Plugins render before configuration is complete. Always handle partial config states:

```javascript
function render(config, data, columns) {
  // State 1: No data source selected
  if (!config.source) {
    return showMessage('Select a data source to get started.');
  }

  // State 2: Source selected but no column chosen
  if (!config.dataColumn) {
    return showMessage('Select a data column to display.');
  }

  // State 3: Column selected but no data available
  const columnData = data[config.dataColumn];
  if (!columnData || columnData.length === 0) {
    return showMessage('No data available for the selected column.');
  }

  // State 4: Everything ready — render the full plugin
  return renderPlugin(data, columns, config);
}
```

This creates a smooth experience where the plugin guides the editor through setup rather than showing errors or blank screens.

---

## Vanilla JavaScript Plugin Pattern

### When to Use

For lightweight plugins that don't need a framework, or when bundle size must be minimal. The subscription-based API works with any approach: vanilla JS, jQuery, Web Components, etc.

### Structure

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/@sigmacomputing/plugin"></script>
</head>
<body>
  <div id="app"></div>
  <script>
    const { client } = sigmaComputing.plugin;

    client.config.configureEditorPanel([
      { name: 'source', type: 'element' },
      { name: 'column', type: 'column', source: 'source', allowMultiple: false, label: 'Column' }
    ]);

    let currentConfig = null;
    let unsubData = null;
    let unsubCols = null;

    client.config.subscribe((config) => {
      currentConfig = config;

      // Clean up previous subscriptions
      if (unsubData) unsubData();
      if (unsubCols) unsubCols();

      if (!config.source) {
        document.getElementById('app').textContent = 'Select a data source.';
        return;
      }

      unsubCols = client.elements.subscribeToElementColumns(config.source, (columns) => {
        // Store column metadata for rendering
        window._columns = columns;
      });

      unsubData = client.elements.subscribeToElementData(config.source, (data) => {
        render(data, window._columns, config);
      });
    });

    function render(data, columns, config) {
      if (!config.column || !data[config.column]) {
        document.getElementById('app').textContent = 'Select a column.';
        return;
      }
      const values = data[config.column];
      const colName = columns?.[config.column]?.name || config.column;
      document.getElementById('app').innerHTML =
        `<h2>${values.length} rows from "${colName}"</h2>`;
    }
  </script>
</body>
</html>
```

### Key Differences from React Approach

| Aspect | React Hooks | Vanilla JS |
|--------|-------------|------------|
| Config access | `useConfig()` | `client.config.subscribe(cb)` or `client.config.getKey(name)` |
| Data access | `useElementData(id)` | `client.elements.subscribeToElementData(id, cb)` |
| Column metadata | `useElementColumns(id)` | `client.elements.subscribeToElementColumns(id, cb)` |
| Cleanup | Automatic (hook lifecycle) | Manual (call returned unsubscribe function) |
| Editor panel | `client.config.configureEditorPanel()` or `useEditorPanelConfig()` | `client.config.configureEditorPanel()` only |
| Config write | `client.config.set()` | `client.config.set()` or `client.config.setKey()` |

