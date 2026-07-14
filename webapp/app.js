import { createApp, ref, computed, onMounted } from "vue";
import {
  CdxButton, CdxIcon, CdxInfoChip, CdxSelect, CdxSearchInput,
  CdxTabs, CdxTab, CdxThumbnail, CdxMessage, CdxProgressIndicator,
} from "@wikimedia/codex";
import {
  cdxIconHistory, cdxIconEdit, cdxIconLinkExternal, cdxIconRobot,
  cdxIconImage, cdxIconArticles, cdxIconInfoFilled, cdxIconChart,
} from "@wikimedia/codex-icons";

const BAND_ORDER = { RED: 0, ORANGE: 1, YELLOW: 2, GREEN: 3 };

const App = {
  components: {
    CdxButton, CdxIcon, CdxInfoChip, CdxSelect, CdxSearchInput,
    CdxTabs, CdxTab, CdxThumbnail, CdxMessage, CdxProgressIndicator,
  },
  setup() {
    const data = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const query = ref("");
    const bandFilter = ref("all");
    const sortKey = ref("priority");
    const activeTab = ref("articles");

    onMounted(async () => {
      try {
        const res = await fetch("./data.json");
        if (!res.ok) throw new Error("HTTP " + res.status);
        data.value = await res.json();
      } catch (e) {
        error.value = "Could not load data.json. Run the pipeline first: " +
          "python3 run_pipeline.py --category \"...\" --images";
      } finally {
        loading.value = false;
      }
    });

    const bandFilterItems = [
      { value: "all", label: "All freshness bands" },
      { value: "RED", label: "Red - outdated (>3y)" },
      { value: "ORANGE", label: "Orange - stale (18-36m)" },
      { value: "YELLOW", label: "Yellow - aging (6-18m)" },
      { value: "GREEN", label: "Green - fresh (<6m)" },
    ];
    const sortItems = [
      { value: "priority", label: "Priority (needs attention)" },
      { value: "age", label: "Oldest first" },
      { value: "views", label: "Most viewed" },
      { value: "title", label: "Title (A-Z)" },
    ];

    const articles = computed(() => {
      if (!data.value) return [];
      let list = data.value.articles.slice();
      if (bandFilter.value !== "all") {
        list = list.filter((a) => a.band === bandFilter.value);
      }
      const q = query.value.trim().toLowerCase();
      if (q) list = list.filter((a) => a.title.toLowerCase().includes(q));
      const cmp = {
        priority: (a, b) => b.priority - a.priority,
        age: (a, b) => b.days_since_substantive - a.days_since_substantive,
        views: (a, b) => b.pageviews_60d - a.pageviews_60d,
        title: (a, b) => a.title.localeCompare(b.title),
      }[sortKey.value];
      return list.sort(cmp);
    });

    const images = computed(() => (data.value ? data.value.images : []));

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
      bandFilterItems, sortItems, articles, images, distSegments,
      formatAge, open, BAND_ORDER,
      iconHistory: cdxIconHistory, iconEdit: cdxIconEdit,
      iconExternal: cdxIconLinkExternal, iconRobot: cdxIconRobot,
      iconImage: cdxIconImage, iconArticles: cdxIconArticles,
      iconInfo: cdxIconInfoFilled, iconChart: cdxIconChart,
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
      <div class="sub" v-else>Making content obsolescence visible</div>
    </div>
  </div>

  <div class="cfr-wrap">
    <cdx-progress-indicator v-if="loading">Loading data...</cdx-progress-indicator>
    <cdx-message v-else-if="error" type="error" :allow-user-dismiss="false">
      {{ error }}
    </cdx-message>

    <template v-else>
      <cdx-message type="notice" :fade-in="true">
        Articles are scored by their <strong>last substantive edit</strong> - minor,
        bot and revert edits are ignored so a page that only gets automated touches
        still surfaces as outdated. Sort by <em>priority</em> to find high-traffic
        pages that haven't truly been updated in years.
      </cdx-message>

      <!-- Band summary -->
      <div class="cfr-bandgrid">
        <div v-for="k in ['GREEN','YELLOW','ORANGE','RED']" :key="k" class="cfr-bandcard" :class="k">
          <div class="n">{{ data.bands[k] || 0 }}</div>
          <div class="l">{{ k }}</div>
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
          <label class="cfr-field-label">Freshness</label>
          <cdx-select v-model:selected="bandFilter" :menu-items="bandFilterItems" />
        </div>
        <div>
          <label class="cfr-field-label">Sort by</label>
          <cdx-select v-model:selected="sortKey" :menu-items="sortItems" />
        </div>
      </div>

      <cdx-tabs v-model:active="activeTab" :framed="true">
        <cdx-tab name="articles" label="Articles">
          <table class="cfr-table">
            <thead>
              <tr>
                <th>Article</th>
                <th>Freshness</th>
                <th>Last real edit</th>
                <th>Age</th>
                <th>Views (60d)</th>
                <th>Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in articles" :key="a.pageid">
                <td>
                  <a class="cfr-title-link" :href="a.url" target="_blank" rel="noopener">
                    {{ a.title }} <cdx-icon :icon="iconExternal" size="x-small" />
                  </a>
                  <div class="cfr-summary">{{ a.last_substantive_summary }}</div>
                  <div v-if="a.skipped_recent_days > 30" class="cfr-botnote">
                    <cdx-icon :icon="iconRobot" size="x-small" />
                    {{ Math.round(a.skipped_recent_days) }} recent days were minor/bot/revert edits
                  </div>
                  <div v-if="a.volatility_factors && a.volatility_factors.length" class="cfr-botnote">
                    <cdx-icon :icon="iconChart" size="x-small" />
                    {{ a.volatility_factors.join(' \u00b7 ') }}
                  </div>
                </td>
                <td>
                  <span class="cfr-pill" :class="a.band">{{ a.band }}</span>
                  <div v-if="a.dated_since" style="margin-top:4px">
                    <cdx-info-chip status="error">data as of {{ a.dated_since }}</cdx-info-chip>
                  </div>
                  <div v-if="a.community_flagged" style="margin-top:4px">
                    <cdx-info-chip status="warning">Community-flagged</cdx-info-chip>
                  </div>
                </td>
                <td class="cfr-num">{{ a.last_substantive_edit }}</td>
                <td class="cfr-num">{{ formatAge(a.days_since_substantive) }}</td>
                <td class="cfr-num">{{ a.pageviews_60d.toLocaleString() }}</td>
                <td class="cfr-num">
                  <strong>{{ a.priority }}</strong>
                  <div v-if="a.volatility > 1" class="cfr-muted">&times;{{ a.volatility }} volatility</div>
                </td>
                <td>
                  <div class="cfr-actions">
                    <cdx-button
                      :action="a.band === 'RED' || a.band === 'ORANGE' ? 'progressive' : 'default'"
                      :weight="a.band === 'RED' ? 'primary' : 'normal'"
                      @click="open(a.edit_url)">
                      <cdx-icon :icon="iconEdit" /> Update
                    </cdx-button>
                  </div>
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

        <cdx-tab name="images" label="Images & graphics">
          <div v-if="images.length === 0" class="cfr-muted" style="padding:24px;text-align:center">
            No images scored. Re-run the pipeline with the <code>--images</code> flag.
          </div>
          <div class="cfr-imggrid">
            <div v-for="img in images" :key="img.file" class="cfr-imgcard">
              <div class="thumb" :style="{ backgroundImage: 'url(' + img.url + ')' }"></div>
              <div class="body">
                <div class="fname">{{ img.file.replace('File:', '') }}</div>
                <div>
                  <span class="cfr-pill" :class="img.band">{{ img.band }}</span>
                  <cdx-info-chip v-if="img.is_screenshot" status="notice" style="margin-left:4px">
                    screenshot
                  </cdx-info-chip>
                  <cdx-info-chip v-else-if="img.kind === 'graphic'" status="notice" style="margin-left:4px">
                    graphic
                  </cdx-info-chip>
                </div>
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
