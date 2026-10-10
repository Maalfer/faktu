// Vista de ajustes: datos del emisor y valores por defecto.

import { api } from "../api.js";
import { esc, ICONS, toast } from "../ui.js";

export async function renderConfig(container) {
  container.innerHTML = `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;

  let cfg, me;
  try {
    [cfg, me] = await Promise.all([api.get("/config"), api.get("/auth/me")]);
  } catch (e) {
    container.innerHTML = `<div class="card p-8 text-center text-slate-500">${esc(e.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <div>
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">Ajustes</h1>
      <p class="mt-1 text-sm text-slate-500">Tus datos de facturación y preferencias por defecto</p>

      <div class="mt-6 grid gap-5 lg:grid-cols-3">
        <form id="config-form" class="card space-y-4 p-6 lg:col-span-2">
          <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Datos de facturación</h2>
          <div class="grid gap-4 sm:grid-cols-2">
            <div><label class="label">Nombre / Empresa</label><input class="input" name="emisor_nombre" value="${esc(cfg.emisor_nombre)}"></div>
            <div><label class="label">NIF / CIF</label><input class="input" name="emisor_nif" value="${esc(cfg.emisor_nif)}"></div>
          </div>
          <div>
            <label class="label">Dirección</label>
            <input class="input" name="emisor_direccion" value="${esc(cfg.emisor_direccion)}">
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div><label class="label">CP</label><input class="input" name="emisor_cp" value="${esc(cfg.emisor_cp)}"></div>
            <div><label class="label">Ciudad</label><input class="input" name="emisor_ciudad" value="${esc(cfg.emisor_ciudad)}"></div>
            <div><label class="label">Provincia</label><input class="input" name="emisor_provincia" value="${esc(cfg.emisor_provincia)}"></div>
          </div>
          <div class="grid gap-4 sm:grid-cols-3">
            <div><label class="label">Email</label><input class="input" type="email" name="emisor_email" value="${esc(cfg.emisor_email)}"></div>
            <div><label class="label">Teléfono</label><input class="input" name="emisor_telefono" value="${esc(cfg.emisor_telefono)}"></div>
            <div><label class="label">País</label><input class="input" name="emisor_pais" value="${esc(cfg.emisor_pais)}"></div>
          </div>

          <div class="border-t border-slate-100 pt-4">
            <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Por defecto</h2>
            <div class="mt-4 grid gap-4 sm:grid-cols-3">
              <div><label class="label">Serie</label><input class="input" name="serie_por_defecto" value="${esc(cfg.serie_por_defecto)}" placeholder="p.ej. F-"></div>
              <div><label class="label">IVA %</label><input class="input" type="number" step="0.01" min="0" max="100" name="iva_por_defecto" value="${cfg.iva_por_defecto}"></div>
              <div><label class="label">IRPF %</label><input class="input" type="number" step="0.01" min="0" max="100" name="irpf_por_defecto" value="${cfg.irpf_por_defecto}"></div>
            </div>
          </div>

          <div class="flex justify-end">
            <button class="btn-primary" type="submit">Guardar ajustes</button>
          </div>
        </form>

        <div class="space-y-5">
          <div class="card p-6">
            <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Cuenta</h2>
            <div class="mt-3 space-y-2">
              <p class="text-sm font-semibold text-slate-800">${esc(me.full_name || "Sin nombre")}</p>
              <p class="text-sm text-slate-500">${esc(me.email)}</p>
            </div>
          </div>
          <div class="card p-6">
            <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Métodos de cobro</h2>
            <p class="mt-1 text-xs text-slate-500">Uno por línea (p.ej. Transferencia, Tarjeta…).</p>
            <div id="metodos-wrap" class="mt-3 space-y-2"></div>
            <button type="button" class="btn-soft mt-3" id="add-metodo">${ICONS.plus} Añadir método</button>
          </div>
        </div>
      </div>
    </div>`;

  // Métodos de cobro
  const wrap = document.getElementById("metodos-wrap");
  function renderMetodos() {
    wrap.innerHTML = (cfg.metodos_cobro || [])
      .map((m, i) => `
        <div class="flex items-center gap-2">
          <input class="input" data-m="metodo" value="${esc(m)}">
          <button type="button" class="icon-btn text-rose-500 hover:bg-rose-50" data-m-del="${i}">${ICONS.trash}</button>
        </div>`).join("");
    wrap.querySelectorAll("[data-m-del]").forEach((btn) =>
      btn.addEventListener("click", () => {
        cfg.metodos_cobro.splice(Number(btn.dataset.mDel), 1);
        renderMetodos();
      }));
  }
  renderMetodos();
  document.getElementById("add-metodo").onclick = () => {
    cfg.metodos_cobro.push("");
    renderMetodos();
  };

  const form = document.getElementById("config-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    Object.keys(data).forEach((k) => (data[k] = typeof data[k] === "string" ? data[k].trim() : data[k]));
    const metodos = [...wrap.querySelectorAll("[data-m=metodo]")].map((i) => i.value.trim()).filter(Boolean);
    data.metodos_cobro = metodos;
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = "Guardando…";
    try {
      await api.put("/config", data);
      toast("Ajustes guardados");
      renderConfig(container);
    } catch (err) {
      toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = "Guardar ajustes";
    }
  });
}