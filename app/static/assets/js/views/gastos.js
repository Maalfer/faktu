// Vista de gastos: listado por trimestres + alta/edición + archivo adjunto.

import { api, fileObjectUrl } from "../api.js";
import {
  closeModal, confirmAction, esc, fmtDate, fmtEUR, ICONS, openModal, quarterBadge, toast, todayISO,
} from "../ui.js";

const CATEGORIAS = ["Varios", "Material", "Transporte", "Hostelería", "Alojamiento", "Software", "Formación", "Mercadotecnia"];

export async function renderGastos(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">Gastos</h1>
        <p class="mt-1 text-sm text-slate-500">Controla tus gastos deducibles agrupados por trimestre</p>
      </div>
      <button class="btn-primary" id="btn-nuevo-gasto">${ICONS.plus}<span class="hidden sm:inline">Nuevo gasto</span></button>
    </div>
    <div class="mt-6" id="gastos-content"></div>`;

  document.getElementById("btn-nuevo-gasto").onclick = () => openGastoForm();
  await loadGastos(container);
}

async function loadGastos(container) {
  const content = document.getElementById("gastos-content");
  content.innerHTML = `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;
  let data;
  try {
    data = await api.get("/trimestres?year=" + (window.faktuYear || ""));
  } catch (e) {
    content.innerHTML = `<div class="card p-8 text-center text-slate-500">${esc(e.message)}</div>`;
    return;
  }
  window.faktuYear = String(data.year);

  const tabs = data.years.map((y) =>
    `<button data-year="${y}" class="year-tab rounded-xl px-4 py-2 text-sm font-bold transition ${
      y === data.year ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
    }">${y}</button>`).join("");

  const totalGastos = data.trimestres.reduce((s, q) => s + Number(q.datos.total_gastos), 0);

  content.innerHTML = `
    <div class="mb-5 flex flex-wrap gap-2">${tabs}</div>
    <div class="card mb-4 max-w-md px-4 py-3">
      <p class="text-[11px] font-semibold uppercase text-slate-400">Total gastos ${esc(data.year)}</p>
      <p class="text-xl font-extrabold text-rose-600">${fmtEUR(totalGastos)}</p>
    </div>
    <div class="space-y-3">${data.trimestres.map((q) => quarterSection(q, data)).join("")}</div>`;

  content.querySelectorAll(".year-tab").forEach((b) =>
    b.addEventListener("click", () => {
      window.faktuYear = b.dataset.year;
      loadGastos(container);
    }));

  content.querySelectorAll("[data-file]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        const url = await fileObjectUrl(`/gastos/${btn.dataset.file}/archivo`);
        const a = document.createElement("a");
        a.href = url;
        a.download = "archivo";
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
      } catch (e) {
        toast(e.message, "error");
      }
    }));

  content.querySelectorAll("[data-accordion]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const body = document.getElementById(btn.dataset.accordion);
      body.classList.toggle("open");
      btn.querySelector(".chevron").classList.toggle("rotate-180");
    });
  });

  content.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => delGasto(b.dataset.del, b.dataset.nombre, container)));
  content.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openGastoForm(Number(b.dataset.edit))));
}

function quarterSection(q, data) {
  const open = q.is_current;
  return `
    <section class="card overflow-hidden">
      <button data-accordion="${esc(`gb-${data.year}-${q.num}`)}" aria-expanded="${open}" class="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition hover:bg-slate-50 sm:px-5">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-2xl font-extrabold ${
            q.is_current ? "bg-rose-600 text-white" : q.is_future ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"
          }">T${q.num}</span>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900">${esc(q.months)}</span>
              ${quarterBadge(q.num, q)}
            </div>
            <p class="text-xs text-slate-500">
              ${q.datos.num_gastos} gasto${q.datos.num_gastos !== 1 ? "s" : ""} ·
              <span class="font-semibold text-rose-600">${fmtEUR(q.datos.total_gastos)}</span>
              ${q.datos.num_facturas ? ` · facturado <span class="font-semibold text-brand-600">${fmtEUR(q.datos.total_facturado)}</span>` : ""}
            </p>
          </div>
        </div>
        <svg class="chevron h-5 w-5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
      </button>
      <div id="${esc(`gb-${data.year}-${q.num}`)}" class="quarter-body ${open ? "open" : ""}">
        <div>
          <div class="px-4 pb-4 sm:px-5">
            ${q.gastos.length === 0
              ? `<div class="rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">${q.is_future ? "Trimestre pendiente" : "Sin gastos en este trimestre"}</div>`
              : `<ul class="grid gap-3 sm:grid-cols-2">${q.gastos.map(gastoCard).join("")}</ul>`}
          </div>
        </div>
      </div>
    </section>`;
}

function gastoCard(g) {
  return `
    <li class="group rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition hover:border-rose-200 hover:shadow-cardhover">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <p class="truncate font-bold text-slate-900">${esc(g.concepto)}</p>
          ${g.proveedor ? `<p class="truncate text-xs text-slate-400">${esc(g.proveedor)}</p>` : ""}
        </div>
        <span class="badge bg-rose-50 text-rose-600 ring-1 ring-rose-100">${esc(g.categoria)}</span>
      </div>
      <div class="mt-3 flex items-end justify-between">
        <div>
          <p class="font-extrabold text-rose-600">${fmtEUR(g.importe)}</p>
          <p class="text-xs text-slate-400">${fmtDate(g.fecha)}</p>
        </div>
        <div class="flex items-center gap-1 opacity-60 transition group-hover:opacity-100">
          ${g.archivo ? `<button class="icon-btn" data-file="${g.id}" title="Descargar archivo">${ICONS.download}</button>` : ""}
          <button class="icon-btn" data-edit="${g.id}" title="Editar">${ICONS.edit}</button>
          <button class="icon-btn text-rose-500 hover:bg-rose-50 hover:text-rose-600" data-del="${g.id}" data-nombre="${esc(g.concepto)}" title="Eliminar">${ICONS.trash}</button>
        </div>
      </div>
    </li>`;
}

async function delGasto(id, nombre, container) {
  const ok = await confirmAction({
    title: "¿Eliminar gasto?",
    message: `Se eliminará «${nombre}». Esta acción no se puede deshacer.`,
  });
  if (!ok) return;
  try {
    await api.del(`/gastos/${id}`);
    toast("Gasto eliminado");
    loadGastos(container);
  } catch (e) {
    toast(e.message, "error");
  }
}

// ── Formulario ──────────────────────────────────────────────────────────

let gastoCache = null;

export async function openGastoForm(id = null) {
  gastoCache = { gasto: id ? await api.get(`/gastos/${id}`) : null };

  const g = gastoCache.gasto;
  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">${g ? "Editar gasto" : "Nuevo gasto"}</h2>
        <button class="icon-btn" id="gasto-close">✕</button>
      </div>
      <form id="gasto-form" class="space-y-4">
        <div>
          <label class="label">Concepto *</label>
          <input class="input" name="concepto" required value="${esc(g?.concepto || "")}" placeholder="p.ej. Material de oficina">
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label">Categoría</label>
            <select class="input" name="categoria">
              ${CATEGORIAS.map((c) => `<option ${g?.categoria === c || (!g && c === "Varios") ? "selected" : ""}>${c}</option>`).join("")}
            </select>
          </div>
          <div>
            <label class="label">Fecha *</label>
            <input class="input" type="date" name="fecha" required value="${g?.fecha || todayISO()}">
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label">Importe (€) *</label>
            <input class="input" type="number" step="0.01" min="0.01" name="importe" required value="${g?.importe ?? ""}" placeholder="0,00">
          </div>
          <div>
            <label class="label">Proveedor</label>
            <input class="input" name="proveedor" value="${esc(g?.proveedor || "")}" placeholder="Empresa o tienda">
          </div>
        </div>
        <div>
          <label class="label">Notas</label>
          <textarea class="input" name="notas" rows="2" placeholder="Opcional">${esc(g?.notas || "")}</textarea>
        </div>
        ${g
          ? `<div>
              <label class="label">Archivo adjunto ${g.archivo ? "(ya existe uno)" : ""}</label>
              <input class="input file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-brand-700" type="file" name="archivo" accept="image/*,.pdf">
              ${g.archivo ? `<p class="mt-1 text-xs text-slate-400">Subir otro reemplazará el actual.</p>` : ""}
            </div>`
          : ""}
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" id="gasto-cancel">Cancelar</button>
          <button type="submit" class="btn-primary">${g ? "Guardar cambios" : "Crear gasto"}</button>
        </div>
      </form>
    </div>`);

  document.getElementById("gasto-close").onclick = closeModal;
  document.getElementById("gasto-cancel").onclick = closeModal;
  document.getElementById("gasto-form").addEventListener("submit", submitGasto);

  // descarga de archivos
  document.querySelectorAll("[data-file]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      try {
        const url = await fileObjectUrl(`/gastos/${btn.dataset.file}/archivo`);
        const a = document.createElement("a");
        a.href = url;
        a.download = "archivo";
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
      } catch (e) {
        toast(e.message, "error");
      }
    }));
}

async function submitGasto(e) {
  e.preventDefault();
  const form = e.target;
  const data = {
    concepto: form.elements.concepto.value.trim(),
    categoria: form.elements.categoria.value,
    fecha: form.elements.fecha.value,
    importe: parseFloat(form.elements.importe.value),
    proveedor: form.elements.proveedor.value.trim(),
    notas: form.elements.notas.value.trim(),
  };
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = "Guardando…";
  try {
    let gasto;
    if (gastoCache.gasto) {
      gasto = await api.put(`/gastos/${gastoCache.gasto.id}`, data);
    } else {
      gasto = await api.post("/gastos", data);
    }
    const file = form.elements.archivo?.files?.[0];
    if (file) await api.upload(`/gastos/${gasto.id}/archivo`, file);
    toast(gastoCache.gasto ? "Gasto actualizado" : "Gasto creado");
    closeModal();
    renderGastos(document.getElementById("view"));
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    btn.textContent = gastoCache.gasto ? "Guardar cambios" : "Crear gasto";
  }
}