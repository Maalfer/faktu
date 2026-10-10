// Vista de trimestres: libro de conceptos de ingreso/gasto por trimestre + export Excel.

import { api, downloadFile } from "../api.js";
import {
  closeModal, confirmAction, esc, fmtEUR, fmtNum, ICONS, openModal, quarterBadge, toast,
} from "../ui.js";

export async function renderTrimestres(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">Trimestres</h1>
        <p class="mt-1 text-sm text-slate-500">Libro automático con tus ingresos y gastos de cada trimestre; añade a mano solo lo que no tenga factura. Exportable a Excel</p>
      </div>
      <button class="btn-primary" id="btn-export">${ICONS.download}<span class="hidden sm:inline">Exportar Excel</span></button>
    </div>
    <div class="mt-6" id="trimestres-content"></div>`;

  document.getElementById("btn-export").onclick = () => exportExcel();
  await loadTrimestres(container);
}

async function loadTrimestres(container) {
  const content = document.getElementById("trimestres-content");
  content.innerHTML = spinner();
  let data;
  try {
    data = await api.get("/conceptos" + (window.faktuYear ? "?year=" + window.faktuYear : ""));
  } catch (e) {
    content.innerHTML = errorCard(e.message);
    return;
  }
  window.faktuYear = String(data.year);

  const tabs = data.years.map((y) =>
    `<button data-year="${y}" class="year-tab rounded-xl px-4 py-2 text-sm font-bold transition ${
      y === data.year ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
    }">${y}</button>`).join("");

  content.innerHTML = `
    <div class="mb-5 flex flex-wrap gap-2">${tabs}</div>
    <div class="mb-4 grid gap-3 sm:grid-cols-3">
      <div class="card px-4 py-3">
        <p class="text-[11px] font-semibold uppercase text-slate-400">Ingresos ${esc(data.year)}</p>
        <p class="text-xl font-extrabold text-brand-600">${fmtEUR(data.total_ingresos)}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="text-[11px] font-semibold uppercase text-slate-400">Gastos ${esc(data.year)}</p>
        <p class="text-xl font-extrabold text-rose-600">${fmtEUR(data.total_gastos)}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="text-[11px] font-semibold uppercase text-slate-400">Neto ${esc(data.year)}</p>
        <p class="text-xl font-extrabold ${Number(data.total_neto) >= 0 ? "text-emerald-600" : "text-rose-600"}">${fmtEUR(data.total_neto)}</p>
      </div>
    </div>
    <div class="space-y-3">${data.trimestres.map((q) => quarterSection(q, data)).join("")}</div>`;

  content.querySelectorAll(".year-tab").forEach((b) =>
    b.addEventListener("click", () => {
      window.faktuYear = b.dataset.year;
      loadTrimestres(container);
    }));

  content.querySelectorAll("[data-accordion]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const body = document.getElementById(btn.dataset.accordion);
      body.classList.toggle("open");
      btn.querySelector(".chevron").classList.toggle("rotate-180");
    });
  });

  content.querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", () => openConceptoForm({
      tipo: b.dataset.add, year: Number(b.dataset.year), trimestre: Number(b.dataset.trimestre),
    })));
  content.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openConceptoForm({ id: Number(b.dataset.edit) })));
  content.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => delConcepto(b.dataset.del, b.dataset.nombre, container)));
}

function quarterSection(q, data) {
  const open = q.is_current;
  const netoColor = Number(q.neto) >= 0 ? "text-emerald-600" : "text-rose-600";
  return `
    <section class="card overflow-hidden">
      <button data-accordion="${esc(`tb-${data.year}-${q.num}`)}" aria-expanded="${open}" class="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition hover:bg-slate-50 sm:px-5">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-2xl font-extrabold ${
            q.is_current ? "bg-brand-600 text-white" : q.is_future ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"
          }">T${q.num}</span>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900">${esc(q.months)}</span>
              ${quarterBadge(q.num, q)}
            </div>
            <p class="text-xs text-slate-500">
              <span class="font-semibold text-brand-600">${fmtEUR(q.total_ingresos)}</span> ingresos ·
              <span class="font-semibold text-rose-500">${fmtEUR(q.total_gastos)}</span> gastos ·
              <span class="font-semibold ${netoColor}">${fmtEUR(q.neto)}</span> neto
            </p>
          </div>
        </div>
        <svg class="chevron h-5 w-5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
      </button>
      <div id="${esc(`tb-${data.year}-${q.num}`)}" class="quarter-body ${open ? "open" : ""}">
        <div>
          <div class="grid gap-4 px-4 pb-4 sm:grid-cols-2 sm:px-5">
            ${sideColumn("ingreso", "Ingresos", q.ingresos, q.total_ingresos, q, data, "brand")}
            ${sideColumn("gasto", "Gastos", q.gastos, q.total_gastos, q, data, "rose")}
          </div>
        </div>
      </div>
    </section>`;
}

function sideColumn(tipo, title, items, total, q, data, tone) {
  const toneText = tone === "brand" ? "text-brand-600" : "text-rose-600";
  const toneBtn = tone === "brand" ? "text-brand-600 hover:bg-slate-50" : "text-rose-600 hover:bg-rose-50";
  return `
    <div class="rounded-2xl border border-slate-100 bg-slate-50 p-3">
      <div class="mb-2 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="text-sm font-bold text-slate-700">${title}</h3>
          <span class="text-sm font-extrabold ${toneText}">${fmtEUR(total)}</span>
        </div>
        <button class="icon-btn ${toneBtn}" data-add="${tipo}" data-year="${data.year}" data-trimestre="${q.num}" title="Añadir ${tipo} manual (lo demás se calcula solo)">${ICONS.plus}</button>
      </div>
      ${items.length === 0
        ? `<div class="rounded-xl border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-slate-400">Sin ${title.toLowerCase()}</div>`
        : `<ul class="space-y-2">${items.map((c) => conceptoRow(c, tone)).join("")}</ul>`}
    </div>`;
}

function conceptoRow(c, tone) {
  const ivaBadge = c.iva == null
    ? `<span class="badge bg-slate-100 text-slate-500">N/A</span>`
    : `<span class="badge bg-slate-100 text-slate-500">${fmtNum(c.iva)}%</span>`;
  return `
    <li class="group flex items-center justify-between gap-2 rounded-xl bg-white px-3 py-2 shadow-sm ring-1 ring-slate-200">
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-slate-800">${esc(c.concepto)}</p>
        <div class="mt-1 flex items-center gap-1.5">
          <span class="text-xs font-bold ${tone === "brand" ? "text-brand-600" : "text-rose-600"}">${fmtEUR(c.importe)}</span>
          ${ivaBadge}
          ${c.auto ? `<span class="badge bg-brand-50 text-brand-600" title="Calculado automáticamente desde ${c.origen === "factura" ? "Ingresos" : "Gastos"}">auto</span>` : ""}
        </div>
        ${c.notas ? `<p class="mt-1 truncate text-[11px] text-slate-400" title="${esc(c.notas)}">${esc(c.notas)}</p>` : ""}
      </div>
      ${c.auto
        ? `<a class="icon-btn !h-8 !w-8 opacity-60 transition group-hover:opacity-100" href="#/${c.origen === "factura" ? "ingresos" : "gastos"}" title="Se edita en ${c.origen === "factura" ? "Ingresos" : "Gastos"}">${ICONS.edit}</a>`
        : `<div class="flex items-center gap-1 opacity-60 transition group-hover:opacity-100">
        <button class="icon-btn !h-8 !w-8" data-edit="${c.id}" title="Editar">${ICONS.edit}</button>
        <button class="icon-btn !h-8 !w-8 text-rose-500 hover:bg-rose-50 hover:text-rose-600" data-del="${c.id}" data-nombre="${esc(c.concepto)}" title="Eliminar">${ICONS.trash}</button>
      </div>`}
    </li>`;
}

const spinner = () => `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;
const errorCard = (m) => `<div class="card p-8 text-center text-slate-500">${esc(m)}</div>`;

async function exportExcel() {
  const year = window.faktuYear || new Date().getFullYear();
  try {
    await downloadFile(`/conceptos/export?year=${year}`, `Trimestres_${year}.xlsx`);
    toast("Excel exportado");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function delConcepto(id, nombre, container) {
  const ok = await confirmAction({
    title: "¿Eliminar concepto?",
    message: `Se eliminará «${nombre}». Esta acción no se puede deshacer.`,
  });
  if (!ok) return;
  try {
    await api.del(`/conceptos/${id}`);
    toast("Concepto eliminado");
    loadTrimestres(container);
  } catch (e) {
    toast(e.message, "error");
  }
}

// ── Formulario ──────────────────────────────────────────────────────────

let conceptoCache = null;

export async function openConceptoForm({ id = null, tipo = "ingreso", year = null, trimestre = null } = {}) {
  const existing = id ? await api.get(`/conceptos/${id}`) : null;
  const c = existing || {
    tipo,
    year: year || Number(window.faktuYear) || new Date().getFullYear(),
    trimestre: trimestre || 1,
    concepto: "",
    importe: "",
    iva: tipo === "ingreso" ? 21 : null,
  };
  conceptoCache = { id, orden: c.orden ?? 0 };

  const esIngreso = c.tipo === "ingreso";
  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">${id ? "Editar" : "Nuevo"} ${esIngreso ? "ingreso" : "gasto"}</h2>
        <button class="icon-btn" id="concepto-close">✕</button>
      </div>
      <form id="concepto-form" class="space-y-4">
        <div>
          <label class="label">Concepto *</label>
          <input class="input" name="concepto" required value="${esc(c.concepto || "")}" placeholder="p.ej. Ventas Academia">
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label">Importe ${esIngreso ? "sin IVA " : ""}(€) *</label>
            <input class="input" type="number" step="0.01" min="0.01" name="importe" required value="${c.importe ?? ""}" placeholder="0,00">
          </div>
          ${esIngreso
            ? `<div>
                <label class="label">IVA % (vacío = N/A)</label>
                <input class="input" type="number" step="0.01" min="0" max="100" name="iva" value="${c.iva ?? ""}" placeholder="21">
              </div>`
            : `<div>
                <label class="label">Tipo</label>
                <input class="input" value="Gasto" disabled>
              </div>`}
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label">Trimestre</label>
            <select class="input" name="trimestre">
              ${[1, 2, 3, 4].map((t) => `<option value="${t}" ${Number(c.trimestre) === t ? "selected" : ""}>T${t}</option>`).join("")}
            </select>
          </div>
          <div>
            <label class="label">Año</label>
            <input class="input" type="number" name="year" min="2000" max="2100" value="${c.year}">
          </div>
        </div>
        <div>
          <label class="label">Notas</label>
          <input class="input" name="notas" maxlength="500" value="${esc(c.notas || "")}" placeholder="Opcional">
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" id="concepto-cancel">Cancelar</button>
          <button type="submit" class="btn-primary">${id ? "Guardar cambios" : "Crear"}</button>
        </div>
      </form>
    </div>`);

  document.getElementById("concepto-close").onclick = closeModal;
  document.getElementById("concepto-cancel").onclick = closeModal;
  document.getElementById("concepto-form").addEventListener("submit", (e) => submitConcepto(e, c.tipo));
}

async function submitConcepto(e, tipo) {
  e.preventDefault();
  const form = e.target;
  const ivaRaw = form.elements.iva?.value?.trim();
  const data = {
    year: parseInt(form.elements.year.value, 10),
    trimestre: parseInt(form.elements.trimestre.value, 10),
    tipo,
    concepto: form.elements.concepto.value.trim(),
    importe: parseFloat(form.elements.importe.value),
    iva: ivaRaw === "" || ivaRaw == null ? null : parseFloat(ivaRaw),
    orden: conceptoCache.orden ?? 0,
    notas: form.elements.notas.value.trim(),
  };
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = "Guardando…";
  try {
    if (conceptoCache.id) {
      await api.put(`/conceptos/${conceptoCache.id}`, data);
      toast("Concepto actualizado");
    } else {
      await api.post("/conceptos", data);
      toast("Concepto creado");
    }
    closeModal();
    renderTrimestres(document.getElementById("view"));
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    btn.textContent = conceptoCache.id ? "Guardar cambios" : "Crear";
  }
}
