"use strict";

const FRONTEND_DATA = __FRONTEND_DATA_JSON__;

let artifactSortKey = "created_at";
let artifactSortDirection = -1;

function text(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (Array.isArray(value)) {
    return value.length ? value.map(text).join("；") : "-";
  }
  if (typeof value === "object") {
    const items = Object.entries(value).map(([key, item]) => `${key}=${text(item)}`);
    return items.length ? items.join("；") : "-";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
  }
  return String(value);
}

function field(artifact, key) {
  if (!artifact) {
    return undefined;
  }
  if (Object.prototype.hasOwnProperty.call(artifact, key)) {
    return artifact[key];
  }
  return artifact.summary ? artifact.summary[key] : undefined;
}

function renderDefinitionList(elementId, artifact, keys) {
  const element = document.getElementById(elementId);
  element.innerHTML = "";
  if (!artifact) {
    element.appendChild(row("状态", "未发现"));
    return;
  }
  keys.forEach(([label, key]) => element.appendChild(row(label, field(artifact, key))));
  element.appendChild(row("output path", artifact.path));
}

function row(label, value) {
  const fragment = document.createDocumentFragment();
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = label;
  dd.textContent = text(value);
  fragment.appendChild(dt);
  fragment.appendChild(dd);
  return fragment;
}

function renderOverview() {
  const data = FRONTEND_DATA;
  document.getElementById("generated-at").textContent = text(data.generated_at);
  document.getElementById("metric-artifacts").textContent = text(data.summary.artifact_count);
  document.getElementById("metric-pipeline").textContent = text(field(data.latest_pipeline, "status"));
  document.getElementById("metric-backtest").textContent = [
    `收益 ${text(field(data.latest_backtest, "total_return"))}`,
    `回撤 ${text(field(data.latest_backtest, "max_drawdown"))}`,
    `sharpe ${text(field(data.latest_backtest, "sharpe"))}`,
  ].join(" / ");
  document.getElementById("metric-walkforward").textContent = text(field(data.latest_walkforward, "fold_count"));
  document.getElementById("metric-candidates").textContent = text(field(data.latest_candidate_selection, "total_candidates"));
  document.getElementById("metric-warnings").textContent = text(data.warning_items.length);
}

function renderDetails() {
  renderDefinitionList("pipeline-detail", FRONTEND_DATA.latest_pipeline, [
    ["market_regime", "market_regime"],
    ["buy_count", "buy_count"],
    ["watch_count", "watch_count"],
    ["block_count", "block_count"],
    ["high_risk_count", "high_risk_count"],
  ]);
  renderDefinitionList("backtest-detail", FRONTEND_DATA.latest_backtest, [
    ["total_return", "total_return"],
    ["max_drawdown", "max_drawdown"],
    ["sharpe", "sharpe"],
    ["trade_count", "trade_count"],
    ["final_equity", "final_equity"],
  ]);
  renderDefinitionList("sweep-detail", FRONTEND_DATA.latest_sweep, [
    ["sweep_name", "sweep_name"],
    ["total_variants", "total_variants"],
    ["success_count", "success_count"],
    ["failed_count", "failed_count"],
  ]);
  const walkforward = FRONTEND_DATA.latest_walkforward;
  const stability = walkforward && walkforward.summary ? walkforward.summary.stability_metrics || {} : {};
  if (walkforward) {
    walkforward.summary.positive_return_ratio = stability.positive_return_ratio;
    walkforward.summary.mean_total_return = stability.mean_total_return;
    walkforward.summary.worst_max_drawdown = stability.worst_max_drawdown;
  }
  renderDefinitionList("walkforward-detail", walkforward, [
    ["fold_count", "fold_count"],
    ["success_count", "success_count"],
    ["positive_return_ratio", "positive_return_ratio"],
    ["mean_total_return", "mean_total_return"],
    ["worst_max_drawdown", "worst_max_drawdown"],
    ["overfit warnings", "overfit_warnings"],
  ]);
}

function renderCandidates() {
  const body = document.getElementById("candidate-body");
  body.innerHTML = "";
  const candidates = FRONTEND_DATA.top_candidates || [];
  if (!candidates.length) {
    appendEmptyRow(body, 5, "未发现候选配置评分结果");
    return;
  }
  candidates.forEach((candidate) => {
    const tr = document.createElement("tr");
    ["candidate_id", "name", "recommendation", "total_score", "filter_reasons"].forEach((key) => {
      const td = document.createElement("td");
      td.textContent = text(candidate[key]);
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function renderExperiments() {
  const body = document.getElementById("experiment-body");
  body.innerHTML = "";
  const experiments = (FRONTEND_DATA.recent_experiments || []).slice(0, 20);
  if (!experiments.length) {
    appendEmptyRow(body, 5, "未发现 experiment 记录");
    return;
  }
  experiments.forEach((experiment) => {
    const tr = document.createElement("tr");
    ["command", "status", "data_version", "config_hash", "tags"].forEach((key) => {
      const td = document.createElement("td");
      td.textContent = text(experiment[key]);
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function renderWarnings() {
  const list = document.getElementById("warning-list");
  list.innerHTML = "";
  const warnings = FRONTEND_DATA.warning_items || [];
  if (!warnings.length) {
    const item = document.createElement("li");
    item.textContent = "当前没有 warning。";
    list.appendChild(item);
    return;
  }
  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = `[${text(warning.artifact_type)}] ${text(warning.name)}：${text(warning.message)} (${text(warning.path)})`;
    list.appendChild(item);
  });
}

function setupExplorer() {
  const filter = document.getElementById("artifact-type-filter");
  const types = Array.from(new Set((FRONTEND_DATA.artifacts || []).map((artifact) => artifact.artifact_type))).sort();
  filter.innerHTML = "";
  const all = document.createElement("option");
  all.value = "";
  all.textContent = "全部类型";
  filter.appendChild(all);
  types.forEach((type) => {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    filter.appendChild(option);
  });
  document.getElementById("artifact-search").addEventListener("input", renderArtifacts);
  filter.addEventListener("change", renderArtifacts);
  document.querySelectorAll(".sort-button").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sort;
      if (artifactSortKey === key) {
        artifactSortDirection *= -1;
      } else {
        artifactSortKey = key;
        artifactSortDirection = key === "created_at" ? -1 : 1;
      }
      renderArtifacts();
    });
  });
  renderArtifacts();
}

function renderArtifacts() {
  const body = document.getElementById("artifact-body");
  const query = document.getElementById("artifact-search").value.trim().toLowerCase();
  const type = document.getElementById("artifact-type-filter").value;
  body.innerHTML = "";
  const artifacts = (FRONTEND_DATA.artifacts || [])
    .filter((artifact) => !type || artifact.artifact_type === type)
    .filter((artifact) => {
      if (!query) {
        return true;
      }
      return [artifact.artifact_id, artifact.artifact_type, artifact.name, artifact.status, artifact.path, text(artifact.summary)]
        .join(" ")
        .toLowerCase()
        .includes(query);
    })
    .sort(compareArtifacts);
  if (!artifacts.length) {
    appendEmptyRow(body, 5, "未发现匹配 artifact");
    return;
  }
  artifacts.forEach((artifact) => {
    const tr = document.createElement("tr");
    tr.className = "artifact-row";
    ["created_at", "artifact_type", "name", "status", "path"].forEach((key) => {
      const td = document.createElement("td");
      td.textContent = text(artifact[key]);
      tr.appendChild(td);
    });
    const detail = document.createElement("tr");
    detail.className = "artifact-summary hidden";
    const detailCell = document.createElement("td");
    detailCell.colSpan = 5;
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(artifact.summary || {}, null, 2);
    detailCell.appendChild(pre);
    detail.appendChild(detailCell);
    tr.addEventListener("click", () => detail.classList.toggle("hidden"));
    body.appendChild(tr);
    body.appendChild(detail);
  });
}

function compareArtifacts(left, right) {
  const a = text(left[artifactSortKey]);
  const b = text(right[artifactSortKey]);
  return a.localeCompare(b) * artifactSortDirection;
}

function appendEmptyRow(body, columns, message) {
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = columns;
  td.className = "empty";
  td.textContent = message;
  tr.appendChild(td);
  body.appendChild(tr);
}

renderOverview();
renderDetails();
renderCandidates();
renderExperiments();
renderWarnings();
setupExplorer();
