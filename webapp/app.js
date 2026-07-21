import { createApp, ref, computed, onMounted } from "vue";
import {
  CdxButton, CdxIcon, CdxInfoChip, CdxSelect, CdxSearchInput,
  CdxTabs, CdxTab, CdxMessage, CdxProgressIndicator, CdxToggleSwitch,
} from "@wikimedia/codex";
import {
  cdxIconHistory, cdxIconEdit, cdxIconLinkExternal, cdxIconRobot,
  cdxIconImage, cdxIconInfoFilled, cdxIconChart, cdxIconAlert,
} from "@wikimedia/codex-icons";

const App = {
  components: {
    CdxButton, CdxIcon, CdxInfoChip, CdxSelect, CdxSearchInput,
    CdxTabs, CdxTab, CdxMessage, CdxProgressIndicator, CdxToggleSwitch,
  },
  setup() {
    const data = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const query = ref("");
    const bandFilter = ref("all");
    const sortKey = ref("urgency");
    const activeTab = ref("articles");
    const needsReviewOnly = ref(false);

    // Scan panel state
    const scanCategory = ref("");
    const scanLimit = ref(30);
    const scanRecursive = ref(false);
    const scanning = ref(false);
    const scanError = ref(null);

    onMounted(async () => {
      try {
        const res = await fetch("./data.json");
        if (res.ok) {
          data.value = await res.json();
          if (!scanCategory.value && data.value.category) {
            scanCategory.value = data.value.category;
          }
        }
      } catch (e) {
        // no data.json yet — scan panel prompts the user
      } finally {
        loading.value = false;
      }
    });

    async function scan() {
      const cat = scanCategory.value.trim();
      if (!cat || scanning.value) return;
      scanning.value = true;
      scanError.value = null;
      error.value = null;
      data.value = null;
      try {
        const params = new URLSearchParams({
          category: cat,
          limit: String(scanLimit.value),
          recursive: String(scanRecursive.value),
        });
        const res = await fetch("/api/scan?" + params);
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Scan failed");
        data.value = json;
      } catch (e) {
        scanError.value = e.message;
      } finally {
        scanning.value = false;
      }
    }

    const bandFilterItems = [
      { value: "all", label: "Any age" },
      { value: "RED", label: "Updated > 3 years ago" },
      { value: "ORANGE", label: "Updated 18-36 months ago" },
      { value: "YELLOW", label: "Updated 6-18 months ago" },
      { value: "GREEN", label: "Updated < 6 months ago" },
    ];
    const BAND_ORDER = { RED: 0, ORANGE: 1, YELLOW: 2, GREEN: 3 };
    const sortItems = [
      { value: "urgency", label: "Urgency (needs update first, then oldest)" },
      { value: "priority", label: "Priority (evidence + traffic + age)" },
      { value: "age", label: "Oldest first" },
      { value: "views", label: "Most viewed" },
      { value: "title", label: "Title (A-Z)" },
    ];

    const articles = computed(() => {
      if (!data.value) return [];
      let list = data.value.articles.slice();
      if (needsReviewOnly.value) list = list.filter((a) => a.recommend_update);
      if (bandFilter.value !== "all") {
        list = list.filter((a) => a.band === bandFilter.value);
      }
      const q = query.value.trim().toLowerCase();
      if (q) list = list.filter((a) => a.title.toLowerCase().includes(q));
      const cmp = {
        urgency: (a, b) => (b.recommend_update - a.recommend_update) || BAND_ORDER[a.band] - BAND_ORDER[b.band] || b.priority - a.priority,
        priority: (a, b) => b.priority - a.priority,
        age: (a, b) => b.days_since_substantive - a.days_since_substantive,
        views: (a, b) => b.pageviews_60d - a.pageviews_60d,
        title: (a, b) => a.title.localeCompare(b.title),
      }[sortKey.value];
      return list.sort(cmp);
    });

    const images = computed(() => (data.value ? data.value.images : []));
    const needsUpdate = computed(() =>
      data.value ? (data.value.needs_update_count || 0) : 0);

    const distSegments = computed(() => {
      if (!data.value) return [];
      const b = data.value.bands;
      const total = Math.max(1, data.value.article_count);
      return ["GREEN", "YELLOW", "ORANGE", "RED"]
        .map((k) => ({ band: k, pct: (100 * (b[k] || 0)) / total }))
        .filter((s) => s.pct > 0);
    });

    function formatAge(days) {
      if (days < 60) return Math.round(days) + " days";
      const months = days / 30.44;
      if (months < 24) return Math.round(months) + " months";
      return (days / 365.25).toFixed(1) + " years";
    }
    function open(url) { window.open(url, "_blank", "noopener"); }

    return {
      data, loading, error, query, bandFilter, sortKey, activeTab,
      needsReviewOnly, bandFilterItems, sortItems, articles, images,
      needsUpdate, distSegments, formatAge, open,
      scanCategory, scanLimit, scanRecursive, scanning, scanError, scan,
      iconHistory: cdxIconHistory, iconEdit: cdxIconEdit,
      iconExternal: cdxIconLinkExternal, iconRobot: cdxIconRobot,
      iconImage: cdxIconImage, iconInfo: cdxIconInfoFilled,
      iconChart: cdxIconChart, iconAlert: cdxIconAlert,
    };
  },
  template: `
  <div class="cfr-header">
    <div class="mark"><cdx-icon :icon="iconHistory" size="medium" /></div>
    <div>
      <h1>Content Freshness Radar</h1>
      <div class="sub" v-if="data">
        Category <strong>{{ data.category }}</strong> on {{ data.wiki }}
        &middot; {{ data.article_count }} articles &middot; generated {{ data.generated_at }}
      </div>
      <div class="sub" v-else>Surfacing content that shows evidence of being outdated</div>
    </div>
  </div>

  <div class="cfr-wrap">

    <!-- Scan panel -->
    <div class="cfr-scan-panel">
      <div class="cfr-scan-row">
        <div class="cfr-scan-field grow">
          <label class="cfr-field-label">Wikipedia category</label>
          <input
            class="cfr-input"
            v-model="scanCategory"
            placeholder='e.g. Demographics of Asia'
            :disabled="scanning"
            @keydown.enter="scan"
          />
        </div>
        <div class="cfr-scan-field">
          <label class="cfr-field-label">Limit</label>
          <input
            class="cfr-input cfr-input-sm"
            type="number"
            v-model.number="scanLimit"
            min="5"
            max="100"
            :disabled="scanning"
          />
        </div>
        <div class="cfr-scan-field" style="align-self:flex-end;padding-bottom:6px">
          <cdx-toggle-switch v-model="scanRecursive">Subcategories</cdx-toggle-switch>
        </div>
        <div class="cfr-scan-field" style="align-self:flex-end">
          <cdx-button
            action="progressive"
            weight="primary"
            :disabled="scanning || !scanCategory.trim()"
            @click="scan"
          >
            {{ scanning ? 'Scanning…' : 'Scan' }}
          </cdx-button>
        </div>
      </div>
      <cdx-message
        v-if="scanError"
        type="error"
        :allow-user-dismiss="true"
        @user-dismissed="scanError = null"
        style="margin-top:10px"
      >
        {{ scanError }}
      </cdx-message>
    </div>

    <!-- Scanning in progress -->
    <div v-if="scanning" class="cfr-scanning-state">
      <cdx-progress-indicator>
        Scanning Category:{{ scanCategory }}… this may take a minute.
      </cdx-progress-indicator>
    </div>

    <!-- Initial data.json load -->
    <cdx-progress-indicator v-else-if="loading">Loading data...</cdx-progress-indicator>

    <!-- No data yet (first visit, no data.json) -->
    <div v-else-if="!data" class="cfr-empty-state">
      Enter a Wikipedia category above and click <strong>Scan</strong> to get started.
    </div>

    <template v-else>
      <cdx-message type="notice" :fade-in="true">
        <strong>Age is a lens, not a verdict.</strong> A page untouched for years
        may simply be complete (history, mathematics). We only recommend an update
        where there is concrete <em>evidence</em> - the article's own
        “as of YYYY” data is old, or the community already tagged it.
        Colour bands below just describe how long since the last real edit.
      </cdx-message>

      <!-- Headline: the actionable number -->
      <div class="cfr-headline">
        <div class="big">{{ needsUpdate }}</div>
        <div>
          <div class="cfr-headline-t">pages show evidence of outdated content</div>
          <div class="cfr-muted">out of {{ data.article_count }} scanned &middot;
            these are the ones actually worth a look</div>
        </div>
      </div>

      <!-- Freshness (age) distribution - descriptive only -->
      <div class="cfr-lenslabel">Last-edit age (descriptive lens)</div>
      <div class="cfr-bandgrid">
        <div v-for="k in ['GREEN','YELLOW','ORANGE','RED']" :key="k" class="cfr-bandcard" :class="k">
          <div class="n">{{ data.bands[k] || 0 }}</div>
          <div class="l">{{ k === 'GREEN' ? '< 6 mo' : k === 'YELLOW' ? '6-18 mo' : k === 'ORANGE' ? '18-36 mo' : '> 3 yr' }}</div>
        </div>
      </div>
      <div class="cfr-distbar">
        <span v-for="s in distSegments" :key="s.band" :class="s.band" :style="{ width: s.pct + '%' }"></span>
      </div>

      <!-- Controls -->
      <div class="cfr-controls">
        <div class="grow">
          <label class="cfr-field-label">Search articles</label>
          <cdx-search-input v-model="query" placeholder="Filter by title..." />
        </div>
        <div>
          <label class="cfr-field-label">Last-edit age</label>
          <cdx-select v-model:selected="bandFilter" :menu-items="bandFilterItems" />
        </div>
        <div>
          <label class="cfr-field-label">Sort by</label>
          <select class="cfr-input" v-model="sortKey">
            <option v-for="s in sortItems" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div style="padding-bottom:4px">
          <cdx-toggle-switch v-model="needsReviewOnly">Only pages with update evidence</cdx-toggle-switch>
        </div>
      </div>

      <cdx-tabs v-model:active="activeTab" :framed="true">
        <cdx-tab name="articles" label="Articles">
          <table class="cfr-table">
            <thead>
              <tr>
                <th>Article</th>
                <th>Evidence of outdated content</th>
                <th>Last real edit</th>
                <th>Age since last edit</th>
                <th>Views (60d)</th>
                <th>Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in articles" :key="a.pageid" :class="{ 'cfr-row-flag': a.recommend_update }">
                <td>
                  <a class="cfr-title-link" :href="a.url" target="_blank" rel="noopener">
                    {{ a.title }} <cdx-icon :icon="iconExternal" size="x-small" />
                  </a>
                  <div class="cfr-summary">{{ a.last_substantive_summary }}</div>
                  <div v-if="a.skipped_recent_days > 30" class="cfr-botnote">
                    <cdx-icon :icon="iconRobot" size="x-small" />
                    {{ Math.round(a.skipped_recent_days) }} recent days were minor/bot/revert edits
                  </div>
                </td>
                <td>
                  <template v-if="a.recommend_update">
                    <div v-for="e in a.evidence" :key="e" class="cfr-evidence">
                      <cdx-icon :icon="iconAlert" size="x-small" /> {{ e }}
                    </div>
                  </template>
                  <div v-else class="cfr-muted">
                    <span class="cfr-pill" :class="a.band" style="opacity:.85">{{ a.band_desc }}</span>
                    <div style="margin-top:3px">no staleness signals</div>
                  </div>
                  <div v-if="a.volatility_factors && a.volatility_factors.length" class="cfr-botnote">
                    <cdx-icon :icon="iconChart" size="x-small" />
                    {{ a.volatility_factors.join(' · ') }}
                  </div>
                </td>
                <td class="cfr-num">{{ a.last_substantive_edit }}</td>
                <td class="cfr-num">{{ formatAge(a.days_since_substantive) }}</td>
                <td class="cfr-num">{{ a.pageviews_60d.toLocaleString() }}</td>
                <td class="cfr-num"><strong>{{ a.priority }}</strong></td>
                <td>
                  <cdx-button
                    v-if="a.recommend_update"
                    action="progressive" weight="primary"
                    @click="open(a.edit_url)">
                    <cdx-icon :icon="iconEdit" /> Review &amp; update
                  </cdx-button>
                  <cdx-button v-else weight="quiet" @click="open(a.url)">
                    View
                  </cdx-button>
                </td>
              </tr>
              <tr v-if="articles.length === 0">
                <td colspan="7" class="cfr-muted" style="text-align:center;padding:24px">
                  No articles match the current filters.
                </td>
              </tr>
            </tbody>
          </table>
        </cdx-tab>

        <cdx-tab name="images" label="Images (experimental)">
          <cdx-message type="warning" :allow-user-dismiss="false" style="margin-bottom:12px">
            <strong>Experimental &amp; low-signal.</strong> Upload age barely
            correlates with whether an image needs updating - the vast majority of
            images, photos, screenshots and charts never do (a Windows 98
            screenshot or a 1990s economic graph is correctly old). Reliably
            telling which need a refresh needs a model that understands the image
            and how it is used. Shown here only for exploration.
          </cdx-message>
          <div v-if="images.length === 0" class="cfr-muted" style="padding:24px;text-align:center">
            No images scored. Re-run the pipeline with the <code>--images</code> flag.
          </div>
          <div class="cfr-imggrid">
            <div v-for="img in images" :key="img.file" class="cfr-imgcard">
              <div class="thumb" :style="{ backgroundImage: 'url(' + img.url + ')' }"></div>
              <div class="body">
                <div class="fname">{{ img.file.replace('File:', '') }}</div>
                <div class="cfr-muted">
                  Last re-uploaded {{ img.last_reupload }} &middot; {{ formatAge(img.days_since_reupload) }} old
                </div>
                <div class="cfr-muted">Used on: {{ img.used_on.join(', ') }}</div>
                <cdx-button size="small" @click="open(img.descriptionurl)">
                  <cdx-icon :icon="iconImage" /> View file
                </cdx-button>
              </div>
            </div>
          </div>
        </cdx-tab>
      </cdx-tabs>

      <div class="cfr-foot">
        Content Freshness Radar &middot; built with the
        <a href="https://doc.wikimedia.org/codex/main/" target="_blank" rel="noopener">Codex</a>
        design system &middot; data from the MediaWiki API
      </div>
    </template>
  </div>
  `,
};

createApp(App).mount("#app");
