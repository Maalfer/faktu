// Vista de panel de control (dashboard anual por trimestres).

import { api } from "../api.js";
import { esc, fmtEUR, fmtDate, estadoBadge, ICONS } from "../ui.js";

export async function renderDashboard(container) {
  container.innerHTML = `<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" id="kpis"></div>
    <div class="mt-6 grid gap-6 lg:grid-cols-3">
      <div class="card p-6 lg:col-span-2" id="chart-card"></div>
      <div class="space-y-4" id="side-recents"></div>
    </div>`;

  let data, tri;
  try {
    [data, tri] = await Promise.all([
      api.get("/dashboard" + (window.faktuYear ? "?year=" + window.faktuYear : "")),
      api.get("/trimestres" + (window.faktuYear ? "?year=" + window.faktuYear : "")),
    ]);
  } catch (e) {
    container.innerHTML = `<div class="card p-8 text-center text-slate-500">${esc(e.message)}</div>`;
    return;
  }
  window.faktuYear = String(data.year);

  renderKPIs(container, data);
  renderChart(container, data);
  renderSide(container, data, tri);
}

function kpiCard({ title, value, sub, tone, icon }) {
  const tones = {
    brand: "bg-brand-50 text-brand-600",
    emerald: "bg-emerald-50 text-emerald-600",
    rose: "bg-rose-50 text-rose-600",
    amber: "bg-amber-50 text-amber-600",
    slate: "bg-slate-100 text-slate-600",
  };
  return `<div class="card p-5">
    <div class="flex items-center justify-between">
      <p class="text-sm font-medium text-slate-500">${esc(title)}</p>
      <span class="flex h-9 w-9 items-center justify-center rounded-xl ${tones[tone] || tones.brand}">${icon || ICONS.facturas}</span>
    </div>
    <p class="mt-2 truncate text-2xl font-extrabold tracking-tight text-slate-900">${value}</p>
    ${sub ? `<p class="mt-1 text-xs text-slate-400">${sub}</p>` : ""}
  </div>`;
}

function renderKPIs(container, data) {
  document.getElementById("kpis").innerHTML = [
    kpiCard({ title: "Facturado", value: fmtEUR(data.total_facturado), sub: `${data.count_facturas} facturas en ${data.year}`, tone: "brand", icon: ICONS.facturas }),
    kpiCard({ title: "Gastos", value: fmtEUR(data.total_gastos), sub: `${data.count_gastos} gastos registrados`, tone: "rose", icon: ICONS.gastos }),
    kpiCard({ title: "Neto", value: fmtEUR(data.total_neto), sub: "Facturado − gastos", tone: "emerald", icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>` }),
    kpiCard({ title: "Pendientes", value: data.pendientes_cobro, sub: "Sin cobrar (emitidas)", tone: "amber", icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>` }),
  ].join("");
}

function renderChart(container, data) {
  const max = Math.max(...data.trimestres.map((q) => Number(q.facturado)), 1);
  const bars = data.trimestres
    .map((q) => {
      const barColor = q.is_current
        ? "bg-gradient-to-t from-brand-600 to-violet-500"
        : "bg-slate-200";
      const h = Math.max(4, (Number(q.facturado) / max) * 130);
      const netoColor = Number(q.neto) >= 0 ? "text-emerald-600" : "text-rose-600";
      return `
      <div class="flex flex-col items-center gap-2">
        <span class="text-[11px] font-bold ${netoColor}">${fmtEUR(q.neto)}</span>
        <div class="flex h-36 w-full items-end justify-center gap-1">
          <div class="rounded-t-lg ${barColor}" style="height:${h}px;width:38px" title="${esc(q.label)} · ${fmtEUR(q.facturado)}"></div>
        </div>
        <div class="flex flex-col items-center">
          <span class="text-sm font-extrabold ${q.is_current ? "text-brand-600" : "text-slate-500"}">${esc(q.label)}</span>
          <span class="text-[10px] text-slate-400">${esc(q.months)}</span>
        </div>
      </div>`;
    })
    .join("");

  document.getElementById("chart-card").innerHTML = `
    <div class="flex items-center justify-between">
      <h2 class="text-base font-bold text-slate-900">Resultado por trimestre · ${esc(data.year)}</h2>
      <div class="flex items-center gap-4 text-xs text-slate-500">
        <span class="flex items-center gap-1.5"><i class="h-2.5 w-2.5 rounded-full bg-brand-600 inline-block"></i>Facturado</span>
        <span class="flex items-center gap-1.5"><i class="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block"></i>Neto</span>
      </div>
    </div>
    <div class="mt-6 flex items-end justify-between gap-2 sm:gap-6">${bars}</div>
    <div class="mt-5 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-4">
      <div><p class="text-[11px] font-semibold uppercase text-slate-400">Base</p><p class="text-sm font-bold text-slate-800">${fmtEUR(data.total_base)}</p></div>
      <div><p class="text-[11px] font-semibold uppercase text-slate-400">IVA</p><p class="text-sm font-bold text-slate-800">${fmtEUR(data.total_iva)}</p></div>
      <div><p class="text-[11px] font-semibold uppercase text-slate-400">Gastos</p><p class="text-sm font-bold text-rose-600">${fmtEUR(data.total_gastos)}</p></div>
      <div><p class="text-[11px] font-semibold uppercase text-slate-400">Neto</p><p class="text-sm font-bold text-emerald-600">${fmtEUR(data.total_neto)}</p></div>
    </div>`;
}

function renderSide(container, data, tri) {
  const current = (tri?.trimestres || []).find((q) => q.is_current);
  if (!current) {
    document.getElementById("side-recents").innerHTML = "";
    return;
  }
  const items = current.facturas.slice(0, 4);

  let html = `
    <div class="card p-5">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-bold text-slate-900">${esc(current.label)} · ${esc(data.year)}</h2>
        <span class="badge badge-current">Actual</span>
      </div>
      <div class="mt-3 grid grid-cols-3 gap-2 text-center">
        <div class="rounded-2xl bg-brand-50 p-3"><p class="text-lg font-extrabold text-brand-700">${fmtEUR(current.facturado)}</p><p class="text-[10px] font-semibold uppercase text-brand-400">Fact.</p></div>
        <div class="rounded-2xl bg-rose-50 p-3"><p class="text-lg font-extrabold text-rose-600">${fmtEUR(current.gastos)}</p><p class="text-[10px] font-semibold uppercase text-rose-400">Gastos</p></div>
        <div class="rounded-2xl bg-emerald-50 p-3"><p class="text-lg font-extrabold text-emerald-600">${fmtEUR(current.neto)}</p><p class="text-[10px] font-semibold uppercase text-emerald-400">Neto</p></div>
      </div>
    </div>`;

  if (items.length) {
    html += `<div class="card p-5">
      <h2 class="mb-3 text-base font-bold text-slate-900">Facturas del trimestre</h2>
      <ul class="divide-y divide-slate-100">
        ${items.map((f) => `
          <li class="flex items-center justify-between gap-3 py-2.5">
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-slate-800">${esc(f.receptor_nombre)}</p>
              <p class="text-xs text-slate-400">${esc(f.numero_completo)} · ${fmtDate(f.fecha_emision)}</p>
            </div>
            <div class="flex items-center gap-2">
              ${estadoBadge(f.estado)}
              <span class="text-sm font-bold text-slate-900">${fmtEUR(f.total)}</span>
            </div>
          </li>`).join("")}
      </ul>
    </div>`;
  }
  document.getElementById("side-recents").innerHTML = html;
}