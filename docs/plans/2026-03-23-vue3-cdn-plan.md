# Vue 3 CDN Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all `dangerouslySetInnerHTML` script blocks in admin routes with Vue 3 Composition API apps loaded from CDN, using an importmap for clean imports.

**Architecture:** Add importmap + Vue CDN to AdminLayout. For each complex page, replace inline script blocks with a `<script type="module">` block that mounts a Vue 3 `createApp`. Server renders initial HTML and passes data via `data-*` attributes. Vue reads these on mount and manages all reactive state.

**Tech Stack:** Vue 3 ESM browser build (unpkg CDN), importmap, existing Hono JSX server rendering.

**Design doc:** `docs/plans/2026-03-23-vue3-cdn-design.md`

**IMPORTANT:** Vue template directives (`v-show`, `v-if`, `@click`, `:value`) go directly in the Hono JSX HTML attributes. The server renders the initial HTML with these attributes; Vue picks them up on mount. Since Hono JSX uses `class` not `className`, and Vue uses the same convention, this works naturally.

---

### Task 1: Add Vue 3 importmap to AdminLayout

**Files:**
- Modify: `src/routes/admin/layout.tsx`

**Step 1:** Add importmap to `<head>` before the stylesheet link:

```tsx
<script type="importmap" dangerouslySetInnerHTML={{ __html: JSON.stringify({
  imports: {
    "vue": "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js"
  }
}) }} />
```

**Step 2:** Add the same importmap to the public layout (`src/routes/public.tsx`) and the design page (`src/routes/admin/design.tsx`) since they also have inline scripts.

**Step 3:** Verify the admin login page still loads (importmap shouldn't break anything).

**Step 4:** Commit: `git commit -m "add Vue 3 importmap to admin and public layouts"`

---

### Task 2: Migrate campaign create form to Vue 3

**Files:**
- Modify: `src/routes/admin/campaigns.tsx`

**Step 1:** Read the 7 script blocks in the campaign create form carefully. Understand every piece of state:
- `audienceMode` (string: list/all/tag/specific)
- `fromPersonaId` (string: "" or list id)
- `fromAddress`, `fromName` (strings)
- `scheduledAtLocal`, `scheduledAt` (strings, local vs UTC)
- `pendingMap` (object: uuid -> dataUri)
- `selected` subscribers (Set of ids)
- Preview panel: `panelOpen` (bool), `previewWidth` (number|null)
- Image modal: `modalOpen`, `currentFile`, `processedData`
- `previewTimer` (debounce)

**Step 2:** Change the create form's `<div class="max-w-2xl">` wrapper to:

```html
<div id="campaign-create" class="max-w-2xl"
  data-lists={JSON.stringify(allLists.map(l => ({ id: l.id, slug: l.slug, name: l.name, fromAddress: l.fromAddress, fromName: l.name, fromDomain: l.fromDomain })))}
  data-all-subscribers={JSON.stringify(allSubscribers.map(s => ({ id: s.id, email: s.email, firstName: s.firstName, lastName: s.lastName })))}
>
```

**Step 3:** Replace ALL `v-show`, `@change`, `:value` etc. with Vue directives directly in the JSX. Key conversions:

For audience mode switcher (currently `display:none` JS-toggled):
```html
<!-- OLD: class with JS toggling display -->
<div data-audience="tag" class="mb-4 hidden">

<!-- NEW: Vue v-show -->
<div v-show="audienceMode === 'tag'" class="mb-4">
```

For select elements:
```html
<!-- OLD: has "selected" prop from server, then JS reads value -->
<select id="audienceMode" name="audienceMode">

<!-- NEW: Vue v-model -->
<select v-model="audienceMode" name="audienceMode">
```

**Step 4:** Add a single `<script type="module">` after the form:

```html
<script type="module" dangerouslySetInnerHTML={{ __html: `
import { createApp, ref, computed, watch, nextTick } from 'vue';

createApp({
  setup() {
    const el = document.getElementById('campaign-create');
    const lists = JSON.parse(el.dataset.lists);
    const allSubscribers = JSON.parse(el.dataset.allSubscribers);

    // Audience
    const audienceMode = ref('list');

    // From
    const fromPersonaId = ref('');
    const fromAddress = ref('');
    const fromName = ref('');

    watch(fromPersonaId, (id) => {
      if (!id) return;
      const list = lists.find(l => String(l.id) === id);
      if (list) {
        fromAddress.value = list.fromAddress || (list.slug + '@' + list.fromDomain);
        fromName.value = list.name;
      }
    });

    watch(fromAddress, (addr) => {
      if (!fromName.value && addr) {
        fromName.value = addr.split('@')[0] || '';
      }
    });

    // Schedule
    const scheduledAtLocal = ref('');
    const scheduledAt = ref('');
    const scheduledAtUtcLabel = computed(() => {
      if (!scheduledAt.value) return '';
      return 'UTC: ' + new Date(scheduledAt.value).toUTCString();
    });

    watch(scheduledAtLocal, (val) => {
      if (val) {
        scheduledAt.value = new Date(val).toISOString();
      } else {
        scheduledAt.value = '';
      }
    });

    // Subscriber picker
    const subscriberSearch = ref('');
    const selectedIds = ref([]);
    const pendingImagesJson = ref('{}');
    const pendingMap = {};

    const searchResults = computed(() => {
      if (!subscriberSearch.value) return [];
      const q = subscriberSearch.value.toLowerCase();
      return allSubscribers.filter(s => {
        if (selectedIds.value.includes(s.id)) return false;
        const name = [s.firstName || '', s.lastName || ''].join(' ').trim();
        return s.email.toLowerCase().includes(q) || name.toLowerCase().includes(q);
      }).slice(0, 10);
    });

    function addSubscriber(s) {
      if (!selectedIds.value.includes(s.id)) selectedIds.value = [...selectedIds.value, s.id];
      subscriberSearch.value = '';
    }

    function removeSubscriber(id) {
      selectedIds.value = selectedIds.value.filter(i => i !== id);
    }

    const selectedSubscribers = computed(() =>
      selectedIds.value.map(id => allSubscribers.find(s => s.id === id)).filter(Boolean)
    );

    // Preview panel
    const previewPanelOpen = ref(false);
    const previewWidth = ref(null);
    const previewWidthLabel = computed(() => previewWidth.value ? previewWidth.value + 'px' : '');

    function setPreviewWidth(w) { previewWidth.value = w; }
    function togglePreviewPanel() {
      previewPanelOpen.value = !previewPanelOpen.value;
      document.body.style.overflow = previewPanelOpen.value ? 'hidden' : '';
      if (previewPanelOpen.value) updatePreview();
    }

    // Live preview
    let previewTimer = null;
    function updatePreview() {
      const body = document.getElementById('bodyMarkdown')?.value;
      if (!body?.trim()) return;
      const subject = document.getElementById('subject')?.value;
      clearTimeout(previewTimer);
      previewTimer = setTimeout(() => {
        fetch('/admin/campaigns/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bodyMarkdown: body, subject: subject || 'Preview', listName: 'Preview' })
        })
        .then(r => r.text())
        .then(html => {
          const frame = document.getElementById('previewFrame');
          if (frame) frame.srcdoc = html;
        });
      }, 500);
    }

    // Image upload
    const imageModalOpen = ref(false);
    const imageModalName = ref('');
    const imageModalSize = ref('');
    const imageEmbedLabel = ref('Embed in email');
    const imageS3Label = ref('Host on S3');
    let processedData = null;

    function formatBytes(b) {
      if (b < 1024) return b + ' B';
      if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
      return (b / 1024 / 1024).toFixed(1) + ' MB';
    }

    function handleImageFile(file) {
      if (!file || !file.type.startsWith('image/')) return;
      const formData = new FormData();
      formData.append('image', file);
      fetch('/admin/campaigns/upload-image', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
          processedData = data;
          imageModalName.value = file.name;
          imageModalSize.value = 'Original: ' + formatBytes(data.originalSizeBytes) + ' → ' + formatBytes(data.sizeBytes) + ' WebP (' + data.width + '×' + data.height + ')';
          imageEmbedLabel.value = 'Embed in email (' + formatBytes(data.sizeBytes) + ' inline, always displays)';
          imageS3Label.value = 'Host on S3 (tiny email, uploads on save)';
          imageModalOpen.value = true;
        })
        .catch(() => alert('Failed to process image'));
    }

    function embedImage() {
      if (!processedData) return;
      insertAtCursor('\\n![image](' + processedData.dataUri + ')\\n');
      imageModalOpen.value = false;
    }

    function s3Image() {
      if (!processedData) return;
      const uuid = crypto.randomUUID();
      pendingMap[uuid] = processedData.dataUri;
      pendingImagesJson.value = JSON.stringify(pendingMap);
      insertAtCursor('\\n<!-- s3-pending:' + uuid + ' -->\\n');
      imageModalOpen.value = false;
    }

    function insertAtCursor(text) {
      const ta = document.getElementById('bodyMarkdown');
      if (!ta) return;
      const start = ta.selectionStart, end = ta.selectionEnd;
      ta.value = ta.value.slice(0, start) + text + ta.value.slice(end);
      ta.selectionStart = ta.selectionEnd = start + text.length;
      ta.dispatchEvent(new Event('input'));
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && previewPanelOpen.value) togglePreviewPanel();
    });

    // Textarea input → live preview
    nextTick(() => {
      const ta = document.getElementById('bodyMarkdown');
      const subj = document.getElementById('subject');
      if (ta) ta.addEventListener('input', updatePreview);
      if (subj) subj.addEventListener('input', updatePreview);

      // Drag-drop on image zone
      const zone = document.getElementById('imageDropZone');
      const fileInput = document.getElementById('imageFileInput');
      if (zone && fileInput) {
        zone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => fileInput.files[0] && handleImageFile(fileInput.files[0]));
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('border-blue-400', 'bg-blue-50'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('border-blue-400', 'bg-blue-50'));
        zone.addEventListener('drop', e => {
          e.preventDefault();
          zone.classList.remove('border-blue-400', 'bg-blue-50');
          if (e.dataTransfer.files[0]) handleImageFile(e.dataTransfer.files[0]);
        });
      }
    });

    return {
      audienceMode, fromPersonaId, fromAddress, fromName,
      scheduledAtLocal, scheduledAt, scheduledAtUtcLabel,
      subscriberSearch, selectedIds, selectedSubscribers, searchResults, addSubscriber, removeSubscriber, pendingImagesJson,
      previewPanelOpen, previewWidth, previewWidthLabel, setPreviewWidth, togglePreviewPanel,
      imageModalOpen, imageModalName, imageModalSize, imageEmbedLabel, imageS3Label, embedImage, s3Image,
    };
  }
}).mount('#campaign-create');
`}} />
```

**Step 5:** Update the HTML template to use Vue directives. Key changes:
- `<div id="campaign-create" ...>` becomes the Vue mount point
- All `data-audience="..."` hidden divs → `v-show="audienceMode === '...'"` 
- The `fromPersona` select → `v-model="fromPersonaId"`
- `fromAddress` input → `v-model="fromAddress"`
- `fromName` input → `v-model="fromName"`
- `scheduledAtLocal` input → `v-model="scheduledAtLocal"`
- `scheduledAt` hidden input → `:value="scheduledAt"`
- UTC label → `{{ scheduledAtUtcLabel }}`
- `pendingImagesJson` → `:value="pendingImagesJson"`
- Subscriber search → `v-model="subscriberSearch"`, search results from `searchResults`
- Selected subscriber chips → `v-for="s in selectedSubscribers"`
- `subscriberIds` hidden → `:value="selectedIds.join(',')"`
- Preview toggle button → `@click="togglePreviewPanel()"`
- Preview panel → `v-show="previewPanelOpen"`
- Width buttons → `@click="setPreviewWidth(375)"` etc.
- Image drop zone handlers remain on DOM (wired in nextTick)
- Image modal → `v-show="imageModalOpen"`

**Step 6:** Remove ALL 7 `dangerouslySetInnerHTML` script blocks from the create form.

**Step 7:** Run `bun test`, start the app and manually verify:
- Audience mode switching works
- From persona auto-fills address/name
- Timezone converts correctly
- Subscriber picker search + chips work
- Preview panel opens/closes, width presets work
- Image drop zone works

**Step 8:** Commit: `git commit -m "migrate campaign create form to Vue 3 CDN"`

---

### Task 3: Migrate campaign edit form to Vue 3

**Files:**
- Modify: `src/routes/admin/campaigns.tsx`

Same as Task 2 but for the edit form (`#campaign-edit`). Extract the shared `setup()` logic into a reusable function at the top of the script block, pre-populating with existing campaign values from data attributes:

```javascript
data-initial-audience-mode={currentAudienceMode}
data-initial-from-address={campaign.fromAddress}
data-initial-from-name={campaign.fromName ?? ""}
data-initial-scheduled-at={campaign.scheduledAt ?? ""}
data-initial-subscriber-ids={JSON.stringify(currentSubscriberIds)}
```

In setup(), read these and use them as initial `ref()` values.

Remove the 3 script blocks from the edit form.

Commit: `git commit -m "migrate campaign edit form to Vue 3 CDN"`

---

### Task 4: Migrate public subscribe page hint

**Files:**
- Modify: `src/routes/public.tsx`

The multi-domain checkbox hint is currently a `<script>` block. Convert to Vue:

```html
<div id="subscribe-form" data-multiple-domains={multipleDomains ? "true" : "false"}>
  <!-- form content with v-show and @change directives -->
</div>
<script type="module">
import { createApp, ref, computed } from 'vue';
createApp({
  setup() {
    const selectedDomains = ref(new Set());
    const showHint = computed(() => selectedDomains.value.size > 1);
    function onListChange(domain, checked) {
      if (checked) selectedDomains.value.add(domain);
      else selectedDomains.value.delete(domain);
      selectedDomains.value = new Set(selectedDomains.value); // trigger reactivity
    }
    return { showHint, onListChange };
  }
}).mount('#subscribe-form');
</script>
```

The list checkboxes get `@change="onListChange(domain, $event.target.checked)"` and the hint div gets `v-show="showHint"`.

Commit: `git commit -m "migrate subscribe page multi-domain hint to Vue 3"`

---

### Task 5: Migrate flash auto-dismiss

**Files:**
- Modify: `src/routes/admin/layout.tsx`

The current flash auto-dismiss uses a `dangerouslySetInnerHTML` script. Convert to a small inline Vue app:

```html
{flash && (
  <div id="flash-banner">
    <div v-show="visible" class="...">
      <span>{{ message }}</span>
      <button @click="visible = false">×</button>
    </div>
  </div>
)}
<script type="module" dangerouslySetInnerHTML={{ __html: `
import { createApp, ref, onMounted } from 'vue';
createApp({
  setup() {
    const visible = ref(true);
    const message = ${JSON.stringify(flash)};
    onMounted(() => setTimeout(() => { visible.value = false; }, 3000));
    return { visible, message };
  }
}).mount('#flash-banner');
` }} />
```

Commit: `git commit -m "migrate flash auto-dismiss to Vue 3"`

---

### Task 6: Verify and clean up

**Step 1:** Run `bun test` -- all 100 tests must pass.

**Step 2:** Check for any remaining `dangerouslySetInnerHTML` script blocks:
```bash
grep -rn "dangerouslySetInnerHTML" src/routes/ --include="*.tsx"
```
Expected: only the importmap and any data-injection scripts (not logic scripts).

**Step 3:** Do a manual smoke test of all Vue-powered pages.

**Step 4:** Docker build: `docker build -t lists:test .`

**Step 5:** Push: `git push origin main`
