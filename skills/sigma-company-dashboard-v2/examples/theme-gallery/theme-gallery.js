(() => {
  const favicon = document.createElement("link");
  favicon.rel = "icon";
  favicon.href = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0d6efd"/><path d="M8 23V9h4l8 8V9h4v14h-4l-8-8v8z" fill="white"/></svg>'
  );
  document.head.appendChild(favicon);

  const body = document.body;
  const customer = body.dataset.customer || "Northstar Foods";
  const theme = body.dataset.theme || "Dashboard theme";
  const subtitle = body.dataset.subtitle || "Demand planning command center";

  const periods = ["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"];
  const actual = [7.4, 7.9, 8.2, 8.7, 9.1, 9.5, 10.1, 10.6];
  const forecast = [7.5, 7.8, 8.4, 8.8, 9.3, 9.9, 10.8, 11.6];

  const points = (series) =>
    series.map((v, i) => `${38 + i * 70},${230 - (v - 6.5) * 38}`).join(" ");

  const bars = [
    ["Beverages", 88, "+11.4%"],
    ["Prepared foods", 72, "+7.8%"],
    ["Snacks", 61, "+5.1%"],
    ["Ingredients", 44, "−2.3%"],
  ];

  const rows = [
    ["Pacific", "Beverages", "$3.42M", "+12.6%", "98.1%", "On plan"],
    ["Central", "Prepared foods", "$2.88M", "+8.4%", "96.7%", "On plan"],
    ["Northeast", "Snacks", "$2.31M", "+4.9%", "94.2%", "Watch"],
    ["Southeast", "Ingredients", "$1.76M", "−2.3%", "91.8%", "At risk"],
  ];

  document.querySelector("#dashboard").innerHTML = `
    <header class="hero">
      <div class="hero__glow" aria-hidden="true"></div>
      <nav class="nav" aria-label="Dashboard navigation">
        <a class="brand" href="#" aria-label="${customer} home">
          <span class="brand__mark" aria-hidden="true">N</span>
          <span>${customer}</span>
        </a>
        <div class="nav__links">
          <a class="is-active" href="#">Command center</a>
          <a href="#">Scenario modeler</a>
          <a href="#">Cohorts</a>
        </div>
        <button class="icon-button" aria-label="More options">•••</button>
      </nav>
      <div class="hero__content">
        <div>
          <p class="eyebrow">${theme}</p>
          <h1>${subtitle}</h1>
          <p class="hero__summary">A decision-ready view of forecast, inventory risk, and plan performance.</p>
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
        <button class="filter"><span>Period</span><strong>FY 2026</strong><i>⌄</i></button>
        <button class="filter"><span>Region</span><strong>All regions</strong><i>⌄</i></button>
        <button class="filter"><span>Channel</span><strong>All channels</strong><i>⌄</i></button>
        <p class="decision-prompt"><span>Decision</span> Where should we adjust the next demand plan?</p>
      </section>

      <section class="kpi-grid" aria-label="Headline KPIs">
        <article class="kpi kpi--hero">
          <div class="kpi__top"><span class="kpi__label">Projected demand</span><span class="kpi__icon">↗</span></div>
          <strong class="kpi__value">12.4M</strong>
          <div class="kpi__delta is-positive"><span>▲ 8.2%</span><small>vs baseline</small></div>
          <svg class="spark" viewBox="0 0 180 40" role="img" aria-label="Projected demand rising">
            <polyline points="2,34 25,30 50,31 75,22 100,24 125,14 150,17 178,5" />
          </svg>
        </article>
        <article class="kpi">
          <div class="kpi__top"><span class="kpi__label">Forecast accuracy</span><span class="kpi__icon">◎</span></div>
          <strong class="kpi__value">91.6%</strong>
          <div class="kpi__delta is-positive"><span>▲ 3.1 pts</span><small>vs last cycle</small></div>
          <div class="meter"><span style="width:91.6%"></span></div>
        </article>
        <article class="kpi">
          <div class="kpi__top"><span class="kpi__label">Fill rate</span><span class="kpi__icon">✓</span></div>
          <strong class="kpi__value">96.8%</strong>
          <div class="kpi__delta is-positive"><span>▲ 1.4 pts</span><small>vs target</small></div>
          <div class="meter"><span style="width:96.8%"></span></div>
        </article>
        <article class="kpi kpi--risk">
          <div class="kpi__top"><span class="kpi__label">Inventory risk</span><span class="kpi__icon">!</span></div>
          <strong class="kpi__value">14 <em>SKUs</em></strong>
          <div class="kpi__delta is-negative"><span>● 5 critical</span><small>next 30 days</small></div>
          <div class="risk-dots" aria-label="Five critical and nine warning SKUs">
            ${Array.from({ length: 14 }, (_, i) => `<span class="${i < 5 ? "critical" : "warning"}"></span>`).join("")}
          </div>
        </article>
      </section>

      <section class="analysis-grid">
        <article class="panel panel--wide">
          <header class="panel__header">
            <div><p class="eyebrow">Demand trajectory</p><h2>Actual vs proposed forecast</h2></div>
            <div class="legend"><span class="actual">Actual</span><span class="forecast">Proposed</span></div>
          </header>
          <svg class="line-chart" viewBox="0 0 570 270" role="img" aria-labelledby="trend-title trend-desc">
            <title id="trend-title">Actual and proposed demand by month</title>
            <desc id="trend-desc">Both series rise, with proposed demand reaching 11.6 million in October.</desc>
            ${[70, 120, 170, 220].map(y => `<line class="gridline" x1="38" y1="${y}" x2="535" y2="${y}"/>`).join("")}
            <polyline class="area-fill" points="38,230 ${points(forecast)} 528,230" />
            <polyline class="line line--actual" points="${points(actual)}" />
            <polyline class="line line--forecast" points="${points(forecast)}" />
            ${periods.map((p, i) => `<text x="${38 + i * 70}" y="258">${p}</text>`).join("")}
          </svg>
        </article>

        <article class="panel panel--bars">
          <header class="panel__header">
            <div><p class="eyebrow">Portfolio mix</p><h2>Demand by category</h2></div>
            <button class="text-button">View detail →</button>
          </header>
          <div class="bar-list">
            ${bars.map(([label, value, delta], i) => `
              <div class="bar-row">
                <div class="bar-row__meta"><span>${label}</span><strong class="${delta.startsWith("−") ? "is-down" : "is-up"}">${delta}</strong></div>
                <div class="bar-track"><span style="width:${value}%" data-index="${i}"></span></div>
              </div>`).join("")}
          </div>
          <aside class="insight">
            <span class="insight__icon">✦</span>
            <div><strong>Planning signal</strong><p>Beverage demand explains 46% of projected growth. Inventory cover is lowest in Pacific.</p></div>
          </aside>
        </article>
      </section>

      <section class="panel table-panel">
        <header class="panel__header">
          <div><p class="eyebrow">Operating detail</p><h2>Regional plan health</h2></div>
          <div class="segmented"><button class="is-active">Summary</button><button>Exceptions</button></div>
        </header>
        <div class="table-wrap">
          <table>
            <caption>Regional forecast performance and risk status</caption>
            <thead><tr><th>Region</th><th>Category</th><th>Projected</th><th>vs baseline</th><th>Fill rate</th><th>Status</th></tr></thead>
            <tbody>
              ${rows.map(row => `<tr>${row.map((cell, i) =>
                i === 5 ? `<td><span class="badge badge--${cell.toLowerCase().replace(" ", "-")}">${cell}</span></td>`
                        : `<td>${cell}</td>`).join("")}</tr>`).join("")}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <footer><span>${customer} · Planning workspace</span><span>Data through Oct 2026</span></footer>
  `;
})();
