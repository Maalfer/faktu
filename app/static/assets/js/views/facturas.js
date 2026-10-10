// Vista de facturas: listado por trimestres + alta/edición.

import { api, downloadPdf } from "../api.js";
import {
  closeModal, confirmAction, esc, estadoBadge, fmtDate, fmtEUR, fmtNum, ICONS, openModal, quarterBadge, toast, todayISO,
} from "../ui.js";

export async function renderFacturas(container) {
  container.innerHTML = `<div class="flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">Ingresos</h1>
        <p class="mt-1 text-sm text-slate-500">Emite, edita y descarga las facturas de tus ingresos por trimestre</p>
      </div>
      <button class="btn-primary" id="btn-nueva-factura">${ICONS.plus}<span class="hidden sm:inline">Nueva factura</span></button>
    </div>
    <div class="mt-6" id="facturas-content"></div>`;

  document.getElementById("btn-nueva-factura").onclick = () => openFacturaForm();
  await loadFacturas(container);
}

async function loadFacturas(container) {
  const content = document.getElementById("facturas-content");
  content.innerHTML = spinner();
  let data;
  try {
    data = await api.get("/trimestres" + (window.faktuYear ? "?year=" + window.faktuYear : ""));
  } catch (e) {
    content.innerHTML = errorCard(e.message);
    return;
  }
  window.faktuYear = String(data.year);

  // Tabs de años
  const tabs = data.years.map((y) =>
    `<button data-year="${y}" class="year-tab rounded-xl px-4 py-2 text-sm font-bold transition ${
      y === data.year ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
    }">${y}</button>`).join("");

  content.innerHTML = `
    <div class="mb-5 flex flex-wrap gap-2">${tabs}</div>
    <div class="mb-4 flex flex-wrap gap-3">
      <div class="card flex items-center gap-2 px-4 py-3">
        <span class="text-lg font-extrabold text-brand-600">${countFacturas(data)}</span>
        <span class="text-sm text-slate-500">facturas</span>
      </div>
      <div class="card flex-1 min-w-[180px] px-4 py-3">
        <p class="text-[11px] font-semibold uppercase text-slate-400">Total emitido ${esc(data.year)}</p>
        <p class="text-xl font-extrabold text-brand-600">${fmtEUR(sumRemaining(data))}</p>
      </div>
    </div>
    <div class="space-y-3">${data.trimestres.map((q) => quarterSection(q, data)).join("")}</div>`;

  content.querySelectorAll(".year-tab").forEach((b) =>
    b.addEventListener("click", () => {
      window.faktuYear = b.dataset.year;
      loadFacturas(container);
    }));

  // Acordeón
  content.querySelectorAll("[data-accordion]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const body = document.getElementById(btn.dataset.accordion);
      body.classList.toggle("open");
      btn.querySelector(".chevron").classList.toggle("rotate-180");
    });
  });

  // Acciones
  content.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => delFactura(b.dataset.del, b.dataset.num, container)));
  content.querySelectorAll("[data-pdf]").forEach((b) =>
    b.addEventListener("click", () => getPdf(b.dataset.pdf, b.dataset.num)));
  content.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openFacturaForm(Number(b.dataset.edit))));
  content.querySelectorAll("[data-ver]").forEach((b) =>
    b.addEventListener("click", () => openFacturaForm(Number(b.dataset.ver))));
}

function sumRemaining(data) {
  return data.trimestres
    .filter((q) => q.is_current || q.is_past)
    .reduce((s, q) => s + Number(q.datos.total_facturado), 0);
}

function countFacturas(data) {
  return data.trimestres
    .filter((q) => q.is_current || q.is_past)
    .reduce((s, q) => s + q.datos.num_facturas, 0);
}

function quarterSection(q, data) {
  const open = q.is_current;
  return `
    <section class="card overflow-hidden">
      <button data-accordion="${esc(`qb-${data.year}-${q.num}`)}" aria-expanded="${open}" class="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition hover:bg-slate-50 sm:px-5">
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
              ${q.datos.num_facturas} factura${q.datos.num_facturas !== 1 ? "s" : ""} ·
              <span class="font-semibold text-brand-600">${fmtEUR(q.datos.total_facturado)}</span>
              ${q.datos.num_gastos ? ` · ${q.datos.num_gastos} gasto${q.datos.num_gastos !== 1 ? "s" : ""} · <span class="font-semibold text-rose-500">${fmtEUR(q.datos.total_gastos)}</span>` : ""}
            </p>
          </div>
        </div>
        <svg class="chevron h-5 w-5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
      </button>
      <div id="${esc(`qb-${data.year}-${q.num}`)}" class="quarter-body ${open ? "open" : ""}">
        <div>
          <div class="px-4 pb-4 sm:px-5">
            ${q.facturas.length === 0
              ? emptyQuarter(q.is_future, "ingresos")
              : `<ul class="grid gap-3 sm:grid-cols-2">${q.facturas.map(facturaCard).join("")}</ul>`}
          </div>
        </div>
      </div>
    </section>`;
}

function facturaCard(f) {
  return `
    <li class="group rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:shadow-cardhover">
      <div class="flex items-start justify-between gap-2">
        <div>
          <p class="font-extrabold text-slate-900">${esc(f.numero_completo)}</p>
          ${estadoBadge(f.estado)}
        </div>
        <span class="badge badge-current hidden sm:inline-flex">T${trimetreFrom(f.fecha_emision)}</span>
      </div>
      <p class="mt-2 truncate text-sm font-medium text-slate-600">${esc(f.receptor_nombre)}</p>
      <p class="text-xs text-slate-400">${fmtDate(f.fecha_emision)}</p>
      <div class="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
        <strong class="text-base font-extrabold text-slate-900">${fmtEUR(f.total)}</strong>
        <div class="flex items-center gap-1 opacity-60 transition group-hover:opacity-100">
          <button class="icon-btn" data-ver="${f.id}" title="Ver / editar">${ICONS.edit}</button>
          <button class="icon-btn" data-pdf="${f.id}" data-num="${esc(f.numero_completo)}" title="Descargar PDF">${ICONS.pdf}</button>
          <button class="icon-btn text-rose-500 hover:bg-rose-50 hover:text-rose-600" data-del="${f.id}" data-num="${esc(f.numero_completo)}" title="Eliminar">${ICONS.trash}</button>
        </div>
      </div>
    </li>`;
}

function trimetreFrom(iso) {
  const m = Number(String(iso).slice(5, 7));
  return Math.ceil(m / 3);
}

function emptyQuarter(future, kind) {
  return `<div class="rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
    ${future ? "Trimestre pendiente" : `Sin ${kind} en este trimestre`}</div>`;
}

const spinner = () => `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;
const errorCard = (m) => `<div class="card p-8 text-center text-slate-500">${esc(m)}</div>`;

async function delFactura(id, num, container) {
  const ok = await confirmAction({
    title: `¿Eliminar ${num}?`,
    message: "Se eliminará la factura y todas sus líneas. Esta acción no se puede deshacer.",
  });
  if (!ok) return;
  try {
    await api.del(`/facturas/${id}`);
    toast("Factura eliminada");
    loadFacturas(container);
  } catch (e) {
    toast(e.message, "error");
  }
}

async function getPdf(id, num) {
  try {
    await downloadPdf(`/facturas/${id}/pdf`, `factura_${num.replace(/\W+/g, "-")}.pdf`);
  } catch (e) {
    toast(e.message, "error");
  }
}

// ── Formulario ──────────────────────────────────────────────────────────

let facturaCache = null; // para no recargar datos en cada edición

export async function openFacturaForm(id = null) {
  facturaCache = { config: null, clientes: [], factura: null, nextNumero: "" };
  const [config, clientes] = await Promise.all([
    api.get("/config"),
    api.get("/clientes"),
  ]);
  facturaCache.config = config;
  facturaCache.clientes = clientes;

  if (id) {
    facturaCache.factura = await api.get(`/facturas/${id}`);
  } else {
    const year = new Date().getFullYear();
    const nn = await api.get(`/facturas/next-numero?year=${year}`);
    facturaCache.nextNumero = nn.numero;
  }

  renderFacturaForm();
}

function renderFacturaForm() {
  const c = facturaCache;
  const f = c.factura;
  const cfg = c.config;
  const year = new Date().getFullYear();
  const numero = f ? f.numero : c.nextNumero;

  const clienteOptions = c.clientes.map((cl) =>
    `<option value="${cl.id}">${esc(cl.nombre)}${cl.nif ? ` · ${esc(cl.nif)}` : ""}</option>`).join("");
  const metodos = (cfg.metodos_cobro || []).map((m) =>
    `<option ${f && f.metodo_cobro === m ? "selected" : ""}>${esc(m)}</option>`).join("");

  const emisor = f || cfg;
  const receptor = f || {};

  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">${f ? "Editar factura" : "Nueva factura"}</h2>
        <button class="icon-btn" onclick="window.__closeModal()">✕</button>
      </div>

      <form id="factura-form" class="space-y-6">
        <!-- Datos básicos -->
        <section class="space-y-4">
          <h3 class="text-sm font-bold uppercase tracking-wide text-brand-600">Datos de la factura</h3>
          <div class="grid gap-4 sm:grid-cols-3">
            <div>
              <label class="label">Número *</label>
              <input class="input font-mono" name="numero" required value="${esc(numero)}">
            </div>
            <div>
              <label class="label">Serie</label>
              <input class="input" name="serie" value="${esc(f?.serie || cfg.serie_por_defecto || "")}" placeholder="p.ej. F-">
            </div>
            <div>
              <label class="label">Fecha emisión *</label>
              <input class="input" type="date" name="fecha_emision" required value="${f ? f.fecha_emision : todayISO()}">
            </div>
          </div>
          <div class="grid gap-4 sm:grid-cols-3">
            <div>
              <label class="label">Estado</label>
              <select class="input" name="estado">
                ${["emitida", "pagada", "borrador"].map((e) => `<option value="${e}" ${(!f && e === "emitida") || f?.estado === e ? "selected" : ""}>${e === "emitida" ? "Emitida" : e === "pagada" ? "Pagada" : "Borrador"}</option>`).join("")}
              </select>
            </div>
            <div>
              <label class="label">IVA %</label>
              <input class="input" type="number" step="0.01" min="0" max="100" name="iva_porcentaje" value="${f ? f.iva_porcentaje : cfg.iva_por_defecto ?? 21}">
            </div>
            <div>
              <label class="label">IRPF %</label>
              <input class="input" type="number" step="0.01" min="0" max="100" name="irpf_porcentaje" value="${f ? f.irpf_porcentaje : cfg.irpf_por_defecto ?? 0}">
            </div>
          </div>
        </section>

        <!-- Cliente / receptor -->
        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold uppercase tracking-wide text-brand-600">Cliente / Receptor</h3>
            ${c.clientes.length ? `<label class="text-xs font-semibold text-slate-500">Cliente guardado:
              <select class="input mt-1 !w-auto" id="cliente-select">
                <option value="">— Elegir cliente —</option>${clienteOptions}
              </select></label>` : ""}
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div><label class="label">Nombre / Empresa *</label><input class="input" name="receptor_nombre" required value="${esc(receptor.receptor_nombre || "")}"></div>
            <div><label class="label">NIF / CIF</label><input class="input" name="receptor_nif" value="${esc(receptor.receptor_nif || "")}"></div>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div><label class="label">Dirección</label><input class="input" name="receptor_direccion" value="${esc(receptor.receptor_direccion || "")}"></div>
            <div class="grid grid-cols-2 gap-4">
              <div><label class="label">CP</label><input class="input" name="receptor_cp" value="${esc(receptor.receptor_cp || "")}"></div>
              <div><label class="label">Ciudad</label><input class="input" name="receptor_ciudad" value="${esc(receptor.receptor_ciudad || "")}"></div>
            </div>
          </div>
        </section>

        <!-- Líneas -->
        <section>
          <h3 class="text-sm font-bold uppercase tracking-wide text-brand-600">Líneas</h3>
          <div id="lineas-wrapper" class="mt-3 space-y-2"></div>
          <button type="button" id="add-linea" class="btn-soft mt-3">${ICONS.plus} Añadir línea</button>
          <div class="mt-4 ml-auto w-full max-w-xs space-y-1 rounded-2xl bg-slate-50 p-4 text-sm">
            <div class="flex justify-between text-slate-500"><span>Base imponible</span><strong id="sum-base">0,00 €</strong></div>
            <div class="flex justify-between text-slate-500"><span id="label-iva">IVA (21%)</span><strong id="sum-iva">0,00 €</strong></div>
            <div id="irpf-row" class="flex justify-between text-slate-500" style="display:none"><span id="label-irpf">IRPF</span><strong id="sum-irpf">0,00 €</strong></div>
            <div class="flex justify-between border-t border-slate-200 pt-2 text-base font-extrabold text-slate-900"><span>TOTAL</span><span id="sum-total">0,00 €</span></div>
          </div>
        </section>

        <!-- Emisor -->
        <section class="space-y-3">
          <h3 class="text-sm font-bold uppercase tracking-wide text-brand-600">Tus datos (emisor)</h3>
          <div class="grid gap-4 sm:grid-cols-2">
            <div><label class="label">Nombre / Empresa *</label><input class="input" name="emisor_nombre" required value="${esc(emisor.emisor_nombre || "")}"></div>
            <div><label class="label">NIF / CIF *</label><input class="input" name="emisor_nif" required value="${esc(emisor.emisor_nif || "")}"></div>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div><label class="label">Dirección</label><input class="input" name="emisor_direccion" value="${esc(emisor.emisor_direccion || "")}"></div>
            <div class="grid grid-cols-3 gap-3">
              <div><label class="label">CP</label><input class="input" name="emisor_cp" value="${esc(emisor.emisor_cp || "")}"></div>
              <div class="col-span-2"><label class="label">Ciudad</label><input class="input" name="emisor_ciudad" value="${esc(emisor.emisor_ciudad || "")}"></div>
            </div>
          </div>
          <div class="grid gap-4 sm:grid-cols-3">
            <div><label class="label">Email</label><input class="input" type="email" name="emisor_email" value="${esc(emisor.emisor_email || "")}"></div>
            <div><label class="label">Teléfono</label><input class="input" name="emisor_telefono" value="${esc(emisor.emisor_telefono || "")}"></div>
            <div><label class="label">País</label><input class="input" name="emisor_pais" value="${esc(emisor.emisor_pais || "España")}"></div>
          </div>
        </section>

        <!-- Extras -->
        <section class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label">Método de cobro</label>
            <input class="input" name="metodo_cobro" list="metodos-list" value="${esc(f?.metodo_cobro || "")}" placeholder="Transferencia">
            <datalist id="metodos-list">${metodos}</datalist>
          </div>
          <div>
            <label class="label">Notas</label>
            <textarea class="input" name="notas" rows="2">${esc(f?.notas || "")}</textarea>
          </div>
        </section>

        <div class="sticky bottom-0 -mx-5 border-t border-slate-100 bg-white px-5 py-4 sm:-mx-7 sm:px-7">
          <div class="flex justify-end gap-2">
            <button type="button" class="btn-ghost" id="cancel-form">Cancelar</button>
            <button type="submit" class="btn-primary">${f ? "Guardar cambios" : "Crear factura"}</button>
          </div>
        </div>
      </form>
    </div>`, { wide: true });

  document.getElementById("cancel-form").onclick = closeModal;
  window.__closeModal = closeModal;

  // Líneas
  const initial = f ? f.lineas : [{ concepto: "", cantidad: 1, precio_unitario: 0 }];
  initial.forEach((l, i) => addLineaRow(l, i));
  document.getElementById("add-linea").onclick = () => addLineaRow({});

  // Cliente -> autocompletar receptor
  const sel = document.getElementById("cliente-select");
  if (sel) {
    sel.addEventListener("change", () => {
      const cl = c.clientes.find((x) => String(x.id) === sel.value);
      if (!cl) return;
      for (const field of ["nombre", "nif", "direccion", "cp", "ciudad", "provincia", "pais"]) {
        const el = form.elements[`receptor_${field}`];
        if (el) el.value = cl[field] || "";
      }
    });
  }

  const form = document.getElementById("factura-form");
  form.addEventListener("submit", submitFactura);

  // Recalcula totales en vivo
  form.addEventListener("input", (e) => {
    if (["iva_porcentaje", "irpf_porcentaje"].includes(e.target.name)) updateTotals();
  });
  updateTotals();
}

function addLineaRow(linea = {}, idx = null) {
  const wrap = document.getElementById("lineas-wrapper");
  const row = document.createElement("div");
  row.className = "flex items-center gap-2 rounded-2xl bg-slate-50 p-2";
  row.dataset.row = idx ?? null;
  row.innerHTML = `
    <input class="input flex-1 min-w-0" name="l-concepto" placeholder="Concepto" value="${esc(linea.concepto || "")}">
    <input class="input w-16 text-right" type="number" name="l-cantidad" min="0" step="0.01" value="${linea.cantidad ?? 1}">
    <input class="input w-24 text-right" type="number" name="l-precio" min="0" step="0.01" value="${linea.precio_unitario ?? 0}">
    <span class="w-20 text-right text-sm font-bold text-slate-700 l-importe">0,00 €</span>
    <button type="button" class="icon-btn !h-8 !w-8 text-rose-500 hover:bg-rose-50 l-del">${ICONS.trash}</button>`;
  row.querySelector(".l-del").onclick = () => {
    row.remove();
    updateTotals();
  };
  row.querySelectorAll('[name="l-cantidad"], [name="l-precio"]').forEach((i) =>
    i.addEventListener("input", () => {
      row.dataset.dirty = "1";
      updateTotals();
    }));
  // numeración de filas
  wrap.appendChild(row);
  updateTotals();
}

function getLineas() {
  const rows = [...document.querySelectorAll("#lineas-wrapper > div")];
  return rows
    .map((r, i) => {
      const concepto = r.querySelector('[name="l-concepto"]').value.trim();
      const cantidad = parseFloat(r.querySelector('[name="l-cantidad"]').value) || 0;
      const precio = parseFloat(r.querySelector('[name="l-precio"]').value) || 0;
      return { concepto, cantidad, precio_unitario: precio, orden: i };
    })
    .filter((l) => l.concepto && l.cantidad > 0);
}

function updateTotals() {
  const iva = parseFloat(document.getElementById("factura-form").elements["iva_porcentaje"].value) || 0;
  const irpf = parseFloat(document.getElementById("factura-form").elements["irpf_porcentaje"].value) || 0;

  const rows = [...document.querySelectorAll("#lineas-wrapper > div")];
  let base = 0;
  rows.forEach((r) => {
    const cantidad = parseFloat(r.querySelector('[name="l-cantidad"]').value) || 0;
    const precio = parseFloat(r.querySelector('[name="l-precio"]').value) || 0;
    const imp = cantidad * precio;
    base += imp;
    r.querySelector(".l-importe").textContent = fmtEUR(imp);
  });

  const cuotaIva = base * iva / 100;
  const cuotaIrpf = base * irpf / 100;
  document.getElementById("sum-base").textContent = fmtEUR(base);
  document.getElementById("label-iva").textContent = `IVA (${fmtNum(iva)}%)`;
  document.getElementById("sum-iva").textContent = fmtEUR(cuotaIva);
  const irpfRow = document.getElementById("irpf-row");
  irpfRow.style.display = irpf > 0 ? "flex" : "none";
  document.getElementById("label-irpf").textContent = `IRPF (${fmtNum(irpf)}%)`;
  document.getElementById("sum-irpf").textContent = fmtEUR(cuotaIrpf);
  document.getElementById("sum-total").textContent = fmtEUR(base + cuotaIva - cuotaIrpf);
}

async function submitFactura(e) {
  e.preventDefault();
  const form = e.target;
  const lineas = getLineas();
  if (lineas.length === 0) {
    toastSimple("Añade al menos una línea con concepto e importe", true);
    return;
  }

  const data = {
    numero: form.elements.numero.value.trim(),
    serie: form.elements.serie.value.trim(),
    fecha_emision: form.elements.fecha_emision.value,
    cliente_id: document.getElementById("cliente-select")?.value ? Number(document.getElementById("cliente-select").value) : null,
    estado: form.elements.estado.value,
    iva_porcentaje: parseFloat(form.elements.iva_porcentaje.value) || 0,
    irpf_porcentaje: parseFloat(form.elements.irpf_porcentaje.value) || 0,
    metodo_cobro: form.elements.metodo_cobro.value.trim(),
    notas: form.elements.notas.value,
    lineas,
  };
  for (const p of ["receptor", "emisor"]) {
    for (const field of ["nombre", "nif", "direccion", "cp", "ciudad", "provincia", "pais", "email", "telefono"]) {
      data[`${p}_${field}`] = form.elements[`${p}_${field}`]?.value?.trim() || "";
    }
  }

  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = "Guardando…";
  try {
    if (facturaCache.factura) {
      await api.put(`/facturas/${facturaCache.factura.id}`, data);
      toast("Factura actualizada");
    } else {
      await api.post("/facturas", data);
      toast("Factura creada");
    }
    closeModal();
    renderFacturas(document.getElementById("view"));
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    btn.textContent = facturaCache.factura ? "Guardar cambios" : "Crear factura";
  }
}

