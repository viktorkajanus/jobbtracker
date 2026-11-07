"use strict";

const CITIES = ["Stockholm", "Gothenburg"];
const ABROAD = ["London", "Frankfurt", "Amsterdam", "Zurich", "Oslo", "Copenhagen", "Helsinki"];
const TYPES = ["Internship", "Graduate", "Thesis", "Junior"];
const AREAS = ["IB", "PE", "M&A", "Consulting", "Audit", "Supply chain", "Strategy", "Analytics", "Finance", "General"];
const STATUSES = ["", "Interested", "Applied", "Hidden"];
const NEW_DAYS = 3;
const SOON_DAYS = 7;

const FILTER_KEY = "jobbtracker.filters.v1";
// Marks keep a snapshot of the job and a status history, so a future application
// pipeline view can show them even after the ad itself has expired.
const MARKS_KEY = "jobbtracker.marks.v1";

const store = {
  read(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  },
  write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage unavailable: keep working in memory */
    }
  },
};

const defaultFilters = () => ({
  cities: [], types: [], areas: [], period: "", status: "active", q: "",
  sort: { key: "deadline", dir: 1 },
});

const state = {
  data: { jobs: [], sources: [], manual: [], generated: null },
  filters: { ...defaultFilters(), ...store.read(FILTER_KEY, {}) },
  marks: store.read(MARKS_KEY, {}),
};

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const areasOf = (job) => (job.areas.length ? job.areas : ["General"]);
const statusOf = (job) => state.marks[job.id]?.status || "";
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);

function saveFilters() {
  store.write(FILTER_KEY, state.filters);
}

function setStatus(job, status) {
  const now = new Date().toISOString();
  const prev = state.marks[job.id];
  if (!status && !prev) return;
  const history = [...(prev?.history || []), { status, at: now }];
  state.marks[job.id] = {
    status,
    updated: now,
    history,
    job: { company: job.company, title: job.title, cities: job.cities, deadline: job.deadline,
           apply_url: job.apply_url, ad_url: job.ad_url, type: job.type },
  };
  store.write(MARKS_KEY, state.marks);
}

// --- Filtering and sorting --------------------------------------------------

function matches(job, f, ignore) {
  if (ignore !== "cities" && f.cities.length && !job.cities.some((c) => f.cities.includes(c))) return false;
  if (ignore !== "types" && f.types.length && !f.types.includes(job.type)) return false;
  if (ignore !== "areas" && f.areas.length && !areasOf(job).some((a) => f.areas.includes(a))) return false;
  if (f.period === "none" && job.period) return false;
  if (f.period && f.period !== "none" && job.period !== f.period) return false;
  const s = statusOf(job);
  if (f.status === "active" && s === "Hidden") return false;
  if (f.status === "none" && s) return false;
  if (!["active", "none", "all"].includes(f.status) && s !== f.status) return false;
  if (f.q) {
    const hay = `${job.company} ${job.title}`.toLowerCase();
    if (!f.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}

function sortValue(job, key) {
  const v = job[key];
  if (Array.isArray(v)) return (key === "areas" ? areasOf(job) : v).join(", ");
  return v ?? null;
}

function sorted(jobs) {
  const { key, dir } = state.filters.sort;
  return [...jobs].sort((a, b) => {
    const x = sortValue(a, key), y = sortValue(b, key);
    if (x === y) return a.company.localeCompare(b.company);
    if (x === null) return 1; // unknown values always last
    if (y === null) return -1;
    return String(x).localeCompare(String(y), "sv") * dir;
  });
}

// --- Rendering --------------------------------------------------------------

function chip(label, pressed, count, extraClass = "") {
  const c = count === undefined ? "" : `<span class="count">${count}</span>`;
  return `<button type="button" class="chip ${extraClass}" aria-pressed="${pressed}" data-value="${esc(label)}">${esc(label)}${c}</button>`;
}

function countBy(field, values) {
  const pool = state.data.jobs.filter((j) => matches(j, state.filters, field));
  const get = field === "areas" ? areasOf : (j) => (field === "cities" ? j.cities : [j[field.slice(0, -1)]]);
  return Object.fromEntries(values.map((v) => [v, pool.filter((j) => get(j).includes(v)).length]));
}

function renderChips() {
  const f = state.filters;
  const cityCounts = countBy("cities", [...CITIES, ...ABROAD]);
  const abroadOn = ABROAD.every((c) => f.cities.includes(c));
  const abroadCount = state.data.jobs.filter((j) => matches(j, f, "cities") && j.cities.some((c) => ABROAD.includes(c))).length;
  $("#city-chips").innerHTML =
    CITIES.map((c) => chip(c, f.cities.includes(c), cityCounts[c])).join("") +
    chip("Abroad", abroadOn, abroadCount) +
    ABROAD.map((c) => chip(c, f.cities.includes(c), cityCounts[c], "sub-chip")).join("");

  const typeCounts = countBy("types", TYPES);
  $("#type-chips").innerHTML = TYPES.map((t) => chip(t, f.types.includes(t), typeCounts[t])).join("");

  const areaCounts = countBy("areas", AREAS);
  $("#area-chips").innerHTML = AREAS.filter((a) => areaCounts[a] || f.areas.includes(a))
    .map((a) => chip(a, f.areas.includes(a), areaCounts[a])).join("");
}

function renderPeriods() {
  const periods = [...new Set(state.data.jobs.map((j) => j.period).filter(Boolean))].sort((a, b) => {
    const ya = a.match(/\d{4}/)?.[0] || "", yb = b.match(/\d{4}/)?.[0] || "";
    return ya.localeCompare(yb) || a.localeCompare(b);
  });
  const sel = $("#period");
  sel.innerHTML = `<option value="">Any period</option>` +
    periods.map((p) => `<option>${esc(p)}</option>`).join("") +
    `<option value="none">Not specified</option>`;
  sel.value = state.filters.period;
}

function fmtDate(d) {
  return d ? esc(d) : `<span class="muted">-</span>`;
}

function row(job) {
  const today = state.data.generated || new Date().toISOString().slice(0, 10);
  const isNew = job.first_seen && daysBetween(job.first_seen, today) < NEW_DAYS;
  const soon = job.deadline && daysBetween(today, job.deadline) <= SOON_DAYS;
  const status = statusOf(job);
  const options = STATUSES.map((s) => `<option value="${s}" ${s === status ? "selected" : ""}>${s || "-"}</option>`).join("");
  const sameLink = job.apply_url === job.ad_url;
  return `<tr class="status-${esc(status) || "none"}" data-id="${esc(job.id)}">
    <td class="company" data-label="Company">${esc(job.company)}${isNew ? '<span class="badge new">New</span>' : ""}</td>
    <td class="role" data-label="Role">${esc(job.title)}</td>
    <td data-label="Type">${esc(job.type)}</td>
    <td data-label="Area">${esc(areasOf(job).join(", "))}</td>
    <td data-label="Location">${esc(job.cities.join(", "))}</td>
    <td class="nowrap" data-label="Period">${job.period ? esc(job.period) : '<span class="muted">Not specified</span>'}</td>
    <td class="nowrap ${soon ? "soon" : ""}" data-label="Deadline">${fmtDate(job.deadline)}</td>
    <td class="nowrap" data-label="Posted">${fmtDate(job.posted || job.first_seen)}</td>
    <td class="links" data-label="Links">
      <a href="${esc(job.apply_url)}" target="_blank" rel="noopener">Apply</a>${sameLink ? "" :
      `<a href="${esc(job.ad_url)}" target="_blank" rel="noopener">Original ad</a>`}
    </td>
    <td data-label="Status"><select aria-label="Status for ${esc(job.title)}">${options}</select></td>
  </tr>`;
}

function render() {
  const f = state.filters;
  renderChips();
  const jobs = sorted(state.data.jobs.filter((j) => matches(j, f)));
  $("#jobs tbody").innerHTML = jobs.map(row).join("");
  $("#empty").hidden = jobs.length > 0;
  $("#summary").textContent = `${jobs.length} of ${state.data.jobs.length} jobs`;
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.setAttribute("aria-sort", th.dataset.sort === f.sort.key ? (f.sort.dir > 0 ? "ascending" : "descending") : "none");
  });
  $("#search").value = f.q;
  $("#status-filter").value = f.status;
  saveFilters();
}

function renderStatic() {
  const { manual, sources, generated } = state.data;
  $("#manual-list").innerHTML = [...manual].sort((a, b) => a.name.localeCompare(b.name))
    .map((m) => `<li><a href="${esc(m.careers_url)}" target="_blank" rel="noopener">${esc(m.name)}</a> <span class="muted">${esc(m.segment)}</span></li>`)
    .join("");
  const ok = sources.filter((s) => s.ok).length;
  const failed = sources.filter((s) => !s.ok).map((s) => s.name);
  $("#foot").innerHTML = `Updated ${esc(generated || "never")} · ${ok} of ${sources.length} sources fetched` +
    (failed.length ? ` · Unavailable this run: ${esc(failed.join(", "))}` : "") +
    ` · Sources: Arbetsförmedlingen JobTech and company career sites.`;
}

// --- Events -----------------------------------------------------------------

function toggle(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function bind() {
  $("#city-chips").addEventListener("click", (e) => {
    const v = e.target.closest(".chip")?.dataset.value;
    if (!v) return;
    const f = state.filters;
    if (v === "Abroad") {
      const allOn = ABROAD.every((c) => f.cities.includes(c));
      f.cities = allOn ? f.cities.filter((c) => !ABROAD.includes(c)) : [...new Set([...f.cities, ...ABROAD])];
    } else {
      f.cities = toggle(f.cities, v);
    }
    render();
  });
  for (const [id, field] of [["#type-chips", "types"], ["#area-chips", "areas"]]) {
    $(id).addEventListener("click", (e) => {
      const v = e.target.closest(".chip")?.dataset.value;
      if (!v) return;
      state.filters[field] = toggle(state.filters[field], v);
      render();
    });
  }
  $("#period").addEventListener("change", (e) => { state.filters.period = e.target.value; render(); });
  $("#status-filter").addEventListener("change", (e) => { state.filters.status = e.target.value; render(); });
  $("#search").addEventListener("input", (e) => { state.filters.q = e.target.value.trim(); render(); });
  $("#reset").addEventListener("click", () => {
    state.filters = defaultFilters();
    renderPeriods();
    render();
  });
  $("#jobs thead").addEventListener("click", (e) => {
    const key = e.target.closest("th[data-sort]")?.dataset.sort;
    if (!key) return;
    const s = state.filters.sort;
    state.filters.sort = { key, dir: s.key === key ? -s.dir : 1 };
    render();
  });
  $("#jobs tbody").addEventListener("change", (e) => {
    if (e.target.tagName !== "SELECT") return;
    const id = e.target.closest("tr").dataset.id;
    const job = state.data.jobs.find((j) => j.id === id);
    setStatus(job, e.target.value);
    render();
  });
}

async function init() {
  bind();
  try {
    const res = await fetch("data/jobs.json", { cache: "no-cache" });
    state.data = await res.json();
  } catch (err) {
    $("#summary").textContent = "Could not load job data.";
    return;
  }
  renderPeriods();
  renderStatic();
  render();
}

init();
