(() => {
  const favicon = document.createElement("link");
  favicon.rel = "icon";
  favicon.href = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0d6efd"/><path d="M8 23V9h4l8 8V9h4v14h-4l-8-8v8z" fill="white"/></svg>'
  );
  document.head.appendChild(favicon);

  // Default content is Northstar Foods' demand-planning example. A company
  // preview (examples/theme-gallery/companies/*.html) sets window.THEME_CONTENT
  // before this script loads to swap in its own industry, KPIs, and numbers —
  // the theme (CSS) and content (data) stay independent, same as the real builder.
  const DEFAULTS = {
    customer: "Northstar Foods",
    theme: "Dashboard theme",
    subtitle: "Demand planning command center",
    brandMark: null,
    navLinks: ["Command center", "Scenario modeler", "Cohorts"],
    summary: "A decision-ready view of forecast, inventory risk, and plan performance.",
    filters: [["Period", "FY 2026"], ["Region", "All regions"], ["Channel", "All channels"]],
    decisionPrompt: "Where should we adjust the next demand plan?",
    trajectory: {
      eyebrow: "Demand trajectory",
      title: "Actual vs proposed forecast",
      periods: ["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
      actual: [7.4, 7.9, 8.2, 8.7, 9.1, 9.5, 10.1, 10.6],
      forecast: [7.5, 7.8, 8.4, 8.8, 9.3, 9.9, 10.8, 11.6],
      legendActual: "Actual",
      legendForecast: "Proposed",
      ariaTitle: "Actual and proposed demand by month",
      ariaDesc: "Both series rise, with proposed demand reaching 11.6 million in October.",
    },
    heroKpi: {
      label: "Projected demand", icon: "↗", value: "12.4M", deltaSign: "positive",
      delta: "▲ 8.2%", deltaSub: "vs baseline", ariaLabel: "Projected demand rising",
    },
    kpi2: {
      label: "Forecast accuracy", icon: "◎", value: "91.6%", deltaSign: "positive",
      delta: "▲ 3.1 pts", deltaSub: "vs last cycle", meter: 91.6,
    },
    kpi3: {
      label: "Fill rate", icon: "✓", value: "96.8%", deltaSign: "positive",
      delta: "▲ 1.4 pts", deltaSub: "vs target", meter: 96.8,
    },
    riskKpi: {
      label: "Inventory risk", icon: "!", value: "14", unit: "SKUs",
      delta: "● 5 critical", deltaSub: "next 30 days", critical: 5, total: 14,
      ariaLabel: "Five critical and nine warning SKUs",
    },
    portfolio: {
      eyebrow: "Portfolio mix", title: "Demand by category", cta: "View detail →",
      bars: [
        ["Beverages", 88, "+11.4%"],
        ["Prepared foods", 72, "+7.8%"],
        ["Snacks", 61, "+5.1%"],
        ["Ingredients", 44, "−2.3%"],
      ],
      insightTitle: "Planning signal",
      insightBody: "Beverage demand explains 46% of projected growth. Inventory cover is lowest in Pacific.",
    },
    table: {
      eyebrow: "Operating detail", title: "Regional plan health",
      caption: "Regional forecast performance and risk status",
      columns: ["Region", "Category", "Projected", "vs baseline", "Fill rate", "Status"],
      rows: [
        ["Pacific", "Beverages", "$3.42M", "+12.6%", "98.1%", "On plan"],
        ["Central", "Prepared foods", "$2.88M", "+8.4%", "96.7%", "On plan"],
        ["Northeast", "Snacks", "$2.31M", "+4.9%", "94.2%", "Watch"],
        ["Southeast", "Ingredients", "$1.76M", "−2.3%", "91.8%", "At risk"],
      ],
    },
    footer: { left: "{customer} · Planning workspace", right: "Data through Oct 2026" },
  };

  const c = Object.assign({}, DEFAULTS, window.THEME_CONTENT || {});
  const body = document.body;
  const customer = body.dataset.customer || c.customer;
  const theme = body.dataset.theme || c.theme;
  const subtitle = body.dataset.subtitle || c.subtitle;
  const brandMark = c.brandMark || customer.charAt(0).toUpperCase();

  const points = (series, lo, scale) =>
    series.map((v, i) => `${38 + i * 70},${230 - (v - lo) * scale}`).join(" ");
  const trajVals = [...c.trajectory.actual, ...c.trajectory.forecast];
  const trajMin = Math.min(...trajVals);
  const trajSpan = Math.max(...trajVals) - trajMin || 1;
  const scale = 190 / trajSpan;
  const lo = trajMin - trajSpan * 0.15;

  document.querySelector("#dashboard").innerHTML = `
    <header class="hero">
      <div class="hero__glow" aria-hidden="true"></div>
      <nav class="nav" aria-label="Dashboard navigation">
        <a class="brand" href="#" aria-label="${customer} home">
          <span class="brand__mark" aria-hidden="true">${brandMark}</span>
          <span>${customer}</span>
        </a>
        <div class="nav__links">
          ${c.navLinks.map((label, i) => `<a class="${i === 0 ? "is-active" : ""}" href="#">${label}</a>`).join("")}
        </div>
        <button class="icon-button" aria-label="More options">•••</button>
      </nav>
      <div class="hero__content">
        <div>
          <p class="eyebrow">${theme}</p>
          <h1>${subtitle}</h1>
          <p class="hero__summary">${c.summary}</p>
        </div>
        <div class="hero__actions">
          <span class="freshness"><span class="status-dot"></span> Refreshed 8 min ago</span>
          <button class="button button--ghost">Export</button>
          <button class="button button--primary">New scenario</button>
        </div>
      </div>
    </header>

    <main>
      <section class="filter-row" aria-label="Dashboard filters">
        ${c.filters.map(([label, value]) => `<button class="filter"><span>${label}</span><strong>${value}</strong><i>⌄</i></button>`).join("")}
        <p class="decision-prompt"><span>Decision</span> ${c.decisionPrompt}</p>
      </section>

      <section class="kpi-grid" aria-label="Headline KPIs">
        <article class="kpi kpi--hero">
          <div class="kpi__top"><span class="kpi__label">${c.heroKpi.label}</span><span class="kpi__icon">${c.heroKpi.icon}</span></div>
          <strong class="kpi__value">${c.heroKpi.value}</strong>
          <div class="kpi__delta is-${c.heroKpi.deltaSign}"><span>${c.heroKpi.delta}</span><small>${c.heroKpi.deltaSub}</small></div>
          <svg class="spark" viewBox="0 0 180 40" role="img" aria-label="${c.heroKpi.ariaLabel}">
            <polyline points="2,34 25,30 50,31 75,22 100,24 125,14 150,17 178,5" />
          </svg>
        </article>
        <article class="kpi">
          <div class="kpi__top"><span class="kpi__label">${c.kpi2.label}</span><span class="kpi__icon">${c.kpi2.icon}</span></div>
          <strong class="kpi__value">${c.kpi2.value}</strong>
          <div class="kpi__delta is-${c.kpi2.deltaSign}"><span>${c.kpi2.delta}</span><small>${c.kpi2.deltaSub}</small></div>
          <div class="meter"><span style="width:${c.kpi2.meter}%"></span></div>
        </article>
        <article class="kpi">
          <div class="kpi__top"><span class="kpi__label">${c.kpi3.label}</span><span class="kpi__icon">${c.kpi3.icon}</span></div>
          <strong class="kpi__value">${c.kpi3.value}</strong>
          <div class="kpi__delta is-${c.kpi3.deltaSign}"><span>${c.kpi3.delta}</span><small>${c.kpi3.deltaSub}</small></div>
          <div class="meter"><span style="width:${c.kpi3.meter}%"></span></div>
        </article>
        <article class="kpi kpi--risk">
          <div class="kpi__top"><span class="kpi__label">${c.riskKpi.label}</span><span class="kpi__icon">${c.riskKpi.icon}</span></div>
          <strong class="kpi__value">${c.riskKpi.value} <em>${c.riskKpi.unit}</em></strong>
          <div class="kpi__delta is-negative"><span>${c.riskKpi.delta}</span><small>${c.riskKpi.deltaSub}</small></div>
          <div class="risk-dots" aria-label="${c.riskKpi.ariaLabel}">
            ${Array.from({ length: c.riskKpi.total }, (_, i) => `<span class="${i < c.riskKpi.critical ? "critical" : "warning"}"></span>`).join("")}
          </div>
        </article>
      </section>

      <section class="analysis-grid">
        <article class="panel panel--wide">
          <header class="panel__header">
            <div><p class="eyebrow">${c.trajectory.eyebrow}</p><h2>${c.trajectory.title}</h2></div>
            <div class="legend"><span class="actual">${c.trajectory.legendActual}</span><span class="forecast">${c.trajectory.legendForecast}</span></div>
          </header>
          <svg class="line-chart" viewBox="0 0 570 270" role="img" aria-labelledby="trend-title trend-desc">
            <title id="trend-title">${c.trajectory.ariaTitle}</title>
            <desc id="trend-desc">${c.trajectory.ariaDesc}</desc>
            ${[70, 120, 170, 220].map(y => `<line class="gridline" x1="38" y1="${y}" x2="535" y2="${y}"/>`).join("")}
            <polyline class="area-fill" points="38,230 ${points(c.trajectory.forecast, lo, scale)} 528,230" />
            <polyline class="line line--actual" points="${points(c.trajectory.actual, lo, scale)}" />
            <polyline class="line line--forecast" points="${points(c.trajectory.forecast, lo, scale)}" />
            ${c.trajectory.periods.map((p, i) => `<text x="${38 + i * 70}" y="258">${p}</text>`).join("")}
          </svg>
        </article>

        <article class="panel panel--bars">
          <header class="panel__header">
            <div><p class="eyebrow">${c.portfolio.eyebrow}</p><h2>${c.portfolio.title}</h2></div>
            <button class="text-button">${c.portfolio.cta}</button>
          </header>
          <div class="bar-list">
            ${c.portfolio.bars.map(([label, value, delta], i) => `
              <div class="bar-row">
                <div class="bar-row__meta"><span>${label}</span><strong class="${delta.startsWith("−") || delta.startsWith("-") ? "is-down" : "is-up"}">${delta}</strong></div>
                <div class="bar-track"><span style="width:${value}%" data-index="${i}"></span></div>
              </div>`).join("")}
          </div>
          <aside class="insight">
            <span class="insight__icon">✦</span>
            <div><strong>${c.portfolio.insightTitle}</strong><p>${c.portfolio.insightBody}</p></div>
          </aside>
        </article>
      </section>

      <section class="panel table-panel">
        <header class="panel__header">
          <div><p class="eyebrow">${c.table.eyebrow}</p><h2>${c.table.title}</h2></div>
          <div class="segmented"><button class="is-active">Summary</button><button>Exceptions</button></div>
        </header>
        <div class="table-wrap">
          <table>
            <caption>${c.table.caption}</caption>
            <thead><tr>${c.table.columns.map(h => `<th>${h}</th>`).join("")}</tr></thead>
            <tbody>
              ${c.table.rows.map(row => `<tr>${row.map((cell, i) =>
                i === row.length - 1 ? `<td><span class="badge badge--${cell.toLowerCase().replace(/ /g, "-")}">${cell}</span></td>`
                        : `<td>${cell}</td>`).join("")}</tr>`).join("")}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <footer><span>${c.footer.left.replace("{customer}", customer)}</span><span>${c.footer.right}</span></footer>
  `;
})();
