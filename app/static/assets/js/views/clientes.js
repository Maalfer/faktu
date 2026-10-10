// Vista de clientes (receptores guardados).

import { api } from "../api.js";
import { closeModal, confirmAction, esc, fmtEUR, ICONS, openModal, toast } from "../ui.js";

export async function renderClientes(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">Clientes</h1>
        <p class="mt-1 text-sm text-slate-500">Tus clientes habituales para rellenar las facturas en un clic</p>
      </div>
      <button class="btn-primary" id="btn-nuevo-cliente">${ICONS.plus}<span class="hidden sm:inline">Nuevo cliente</span></button>
    </div>
    <div class="mt-6" id="clientes-content"></div>`;

  document.getElementById("btn-nuevo-cliente").onclick = () => openClienteForm();
  await loadClientes(container);
}

async function loadClientes(container) {
  const content = document.getElementById("clientes-content");
  content.innerHTML = `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;
  let clientes;
  try {
    clientes = await api.get("/clientes");
  } catch (e) {
    content.innerHTML = `<div class="card p-8 text-center text-slate-500">${esc(e.message)}</div>`;
    return;
  }

  if (clientes.length === 0) {
    content.innerHTML = `
      <div class="card flex flex-col items-center px-6 py-16 text-center">
        <span class="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-brand-50 text-brand-500">${ICONS.clientes}</span>
        <p class="text-lg font-bold text-slate-900">Sin clientes todavía</p>
        <p class="mt-1 max-w-sm text-sm text-slate-500">Guarda tus clientes más frecuentes y rellena sus datos al crear una factura con un solo clic.</p>
        <button class="btn-primary mt-6" id="empty-new">${ICONS.plus} Crear cliente</button>
      </div>`;
    document.getElementById("empty-new").onclick = () => openClienteForm();
    return;
  }

  content.innerHTML = `
    <div class="card overflow-hidden">
      <div class="hidden grid-cols-12 gap-3 border-b border-slate-100 bg-slate-50 px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-slate-400 sm:grid-col-none md:grid">
        <div class="col-span-4">Cliente</div>
        <div class="col-span-3">NIF / CIF</div>
        <div class="col-span-2">Ciudad</div>
        <div class="col-span-2 text-right">Facturado</div>
        <div class="col-span-1 text-right">Acciones</div>
      </div>
      <ul class="divide-y divide-slate-100">
        ${clientes.map(clienteRow).join("")}
      </ul>
    </div>`;

  content.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openClienteForm(Number(b.dataset.edit))));
  content.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => delCliente(b.dataset.del, b.dataset.nombre, container)));
}

function clienteRow(c) {
  return `
    <li class="grid grid-cols-1 items-center gap-2 px-5 py-3.5 transition hover:bg-slate-50 md:grid-cols-12">
      <div class="col-span-4 min-w-0">
        <p class="truncate font-semibold text-slate-800">${esc(c.nombre)}</p>
        <p class="truncate text-xs text-slate-400">${c.email ? esc(c.email) : c.direccion ? esc(c.direccion) : ""}</p>
      </div>
      <p class="col-span-3 text-sm text-slate-600">${esc(c.nif || "—")}</p>
      <p class="col-span-2 text-sm text-slate-600">${esc(c.ciudad || "—")}</p>
      <p class="col-span-2 text-right text-sm font-bold text-brand-600">${fmtEUR(c.total_facturado)}</p>
      <div class="col-span-1 flex justify-end gap-1">
        <button class="icon-btn" data-edit="${c.id}" title="Editar">${ICONS.edit}</button>
        <button class="icon-btn text-rose-500 hover:bg-rose-50" data-del="${c.id}" data-nombre="${esc(c.nombre)}" title="Eliminar">${ICONS.trash}</button>
      </div>
    </li>`;
}

async function delCliente(id, nombre, container) {
  const ok = await confirmAction({
    title: "¿Eliminar cliente?",
    message: `Se eliminará «${nombre}». Sus facturas se conservarán.`,
  });
  if (!ok) return;
  try {
    await api.del(`/clientes/${id}`);
    toast("Cliente eliminado");
    loadClientes(container);
  } catch (e) {
    toast(e.message, "error");
  }
}

let clienteCache = null;

export async function openClienteForm(id = null) {
  clienteCache = { cliente: id ? await api.get(`/clientes/${id}`) : null };
  const c = clienteCache.cliente;

  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">${c ? "Editar cliente" : "Nuevo cliente"}</h2>
        <button class="icon-btn" id="cliente-close">✕</button>
      </div>
      <form id="cliente-form" class="space-y-4">
        <div class="grid gap-4 sm:grid-cols-2">
          <div><label class="label">Nombre / Empresa *</label><input class="input" name="nombre" required value="${esc(c?.nombre || "")}"></div>
          <div><label class="label">NIF / CIF</label><input class="input" name="nif" value="${esc(c?.nif || "")}"></div>
        </div>
        <div>
          <label class="label">Dirección</label>
          <input class="input" name="direccion" value="${esc(c?.direccion || "")}">
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div><label class="label">CP</label><input class="input" name="cp" value="${esc(c?.cp || "")}"></div>
          <div class="col-span-1"><label class="label">Ciudad</label><input class="input" name="ciudad" value="${esc(c?.ciudad || "")}"></div>
          <div><label class="label">País</label><input class="input" name="pais" value="${esc(c?.pais || "España")}"></div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div><label class="label">Email</label><input class="input" type="email" name="email" value="${esc(c?.email || "")}"></div>
          <div><label class="label">Teléfono</label><input class="input" name="telefono" value="${esc(c?.telefono || "")}"></div>
        </div>
        <div>
          <label class="label">Notas</label>
          <textarea class="input" name="notas" rows="2">${esc(c?.notas || "")}</textarea>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" id="cliente-cancel">Cancelar</button>
          <button type="submit" class="btn-primary">${c ? "Guardar cambios" : "Crear cliente"}</button>
        </div>
      </form>
    </div>`);

  document.getElementById("cliente-close").onclick = closeModal;
  document.getElementById("cliente-cancel").onclick = closeModal;
  document.getElementById("cliente-form").addEventListener("submit", submitCliente);
}

async function submitCliente(e) {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form).entries());
  Object.keys(data).forEach((k) => (data[k] = data[k].trim()));
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  try {
    if (clienteCache.cliente) {
      await api.put(`/clientes/${clienteCache.cliente.id}`, data);
      toast("Cliente actualizado");
    } else {
      await api.post("/clientes", data);
      toast("Cliente creado");
    }
    closeModal();
    renderClientes(document.getElementById("view"));
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
  }
}