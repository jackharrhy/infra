# Vue 3 CDN Migration Design

## Summary

Replace inline `dangerouslySetInnerHTML` script blocks in Hono JSX admin routes with Vue 3 component apps loaded from CDN. No build step. Server continues to render initial HTML; Vue takes over interactive parts.

## The problem

`campaigns.tsx` has 7 inline script blocks containing ~400 lines of imperative JS:
- Audience mode switching (show/hide form sections)
- From address / from name auto-fill
- From persona selector
- Timezone conversion
- Subscriber picker (search + chip UI)
- Preview panel toggle + width control
- Live preview with debounce fetch
- Image upload modal

These are hard to read, maintain, and test. Logic is scattered, state is implicit in the DOM, and the same patterns are duplicated across create and edit forms.

## Approach: Vue 3 ESM browser build via CDN

```html
<script type="module">
import { createApp, ref, computed } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js';

createApp({
  setup() {
    const audienceMode = ref('list');
    return { audienceMode };
  }
}).mount('#campaign-form');
</script>
```

- **No build step** -- Vue 3's ESM browser build works natively in modern browsers as a module
- **No bundler** -- `import` from CDN URL
- **Progressive** -- only mount Vue on divs that need it, server still renders everything else
- **TypeScript-compatible** -- IDE understands Vue 3 Composition API even in CDN mode
- **15KB gzipped** -- smaller than the inline JS we currently have

## What gets Vue vs what stays server-rendered

| Component | Vue? | Why |
|-----------|------|-----|
| Audience mode switcher | Yes | Reactive show/hide with multiple conditions |
| From persona selector | Yes | Fills multiple fields reactively |
| Timezone input | Yes | Converts local → UTC reactively |
| Subscriber picker | Yes | Search state, selected chips, async fetch |
| Preview panel | Yes | Open/close state, width state, debounced fetch |
| Image upload modal | Yes | File state, async processing, multi-step UI |
| Filter bars (subscribers, campaigns, etc.) | No | Simple form submit, no reactive state needed |
| Tables, pagination | No | Static server-rendered |
| Flash banner auto-dismiss | Yes | Simple but consistent to do in Vue |
| Subscribe page domain hint | Yes | Checkbox state watching |

## Implementation structure

Each interactive page gets one Vue app:

```html
<!-- Server renders the form skeleton -->
<div id="campaign-form" :class is Vue's domain -->
  <!-- v-show, :value, @change, @click etc. in the template -->
</div>

<script type="module">
import { createApp, ref, computed, watch } from 'https://...vue...';
createApp({
  setup() {
    // all the state and logic that was in inline script blocks
  }
}).mount('#campaign-form');
</script>
```

The server still renders initial values as data attributes or inline JSON:
```html
<div id="campaign-form" 
  data-lists='[{"id":1,"slug":"newsletter",...}]'
  data-subscribers='[{"id":1,"email":"..."}]'
  data-initial-audience-mode="list"
>
```

Vue reads these on mount via `el.dataset` -- no script injection for data hydration.

## Pages to migrate

### Priority 1: `campaigns.tsx` (create + edit)
The biggest win. 7 script blocks → 1 Vue app per form.

### Priority 2: `public.tsx`
The subscribe page domain hint (1 small script block).

### Priority 3: `layout.tsx`
The flash auto-dismiss (1 script block, trivial).

## Vue 3 CDN loading

Add to `AdminLayout` `<head>`:
```html
<script type="importmap">
{
  "imports": {
    "vue": "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js"
  }
}
</script>
```

Then in any page:
```html
<script type="module">
import { createApp, ref } from 'vue';
// ...
</script>
```

The importmap means we write `from 'vue'` everywhere instead of the full CDN URL.

## What we do NOT do

- No `.vue` single-file components (requires build step)
- No Vue Router (Hono handles routing)
- No Pinia/Vuex (each app is self-contained, no shared state between pages)
- No JSX in Vue components (use template strings or `h()` if needed)
- No TypeScript in Vue scripts (browser module scripts don't get TS compilation)

## Migration approach

1. Add importmap to `AdminLayout`
2. Migrate `campaigns.tsx` create form to Vue app
3. Migrate `campaigns.tsx` edit form to same Vue app (shared `setup()` function exported from a module)
4. Migrate public subscribe page hint
5. Migrate flash auto-dismiss
6. Remove all `dangerouslySetInnerHTML` script blocks
