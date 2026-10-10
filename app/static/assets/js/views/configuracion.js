// Vista de ajustes: datos del emisor y valores por defecto.

import { api } from "../api.js";
import { closeModal, confirmAction, esc, fmtDate, ICONS, openModal, toast } from "../ui.js";

export async function renderConfig(container) {
  container.innerHTML = `<div class="flex justify-center py-16"><div class="h-9 w-9 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div></div>`;

  let cfg, me, tokens;
  try {
    [cfg, me, tokens] = await Promise.all([
      api.get("/config"),
      api.get("/auth/me"),
      api.get("/api-tokens"),
    ]);
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
            <div class="flex items-start justify-between gap-2">
              <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">${ICONS.key} Token API / IA</h2>
              <button class="btn-soft text-xs" id="new-token">${ICONS.plus} Crear token</button>
            </div>
            <p class="mt-2 text-xs text-slate-500">
              Genera un token personal para que Claude u otra IA gestione tu cuenta con
              <code class="rounded bg-slate-100 px-1 py-0.5">Authorization: Bearer fkt_…</code>.
              Se muestra una sola vez; guárdalo bien.
            </p>
            <div id="tokens-list" class="mt-4 space-y-2"></div>
          </div>

          <div class="card p-6">
            <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Métodos de cobro</h2>
            <p class="mt-1 text-xs text-slate-500">Uno por línea (p.ej. Transferencia, Tarjeta…).</p>
            <div id="metodos-wrap" class="mt-3 space-y-2"></div>
            <button type="button" class="btn-soft mt-3" id="add-metodo">${ICONS.plus} Añadir método</button>
          </div>
        </div>
      </div>

      <div class="card mt-5 p-6">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="text-sm font-bold uppercase tracking-wide text-brand-600">Exportar todos mis datos (CSV)</h2>
            <p class="mt-2 max-w-2xl text-sm text-slate-500">
              Genera un archivo ZIP con el <strong>100% de la información</strong> de tu cuenta de
              todos los años: clientes, facturas con sus líneas, gastos, libro de conceptos,
              configuración del emisor y tokens de API (sin secretos). Útil para copias de
              seguridad o para llevarte los datos a otra herramienta.
            </p>
          </div>
          <button class="btn-primary shrink-0" id="export-data">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="mr-1"><path d="M5 20h14v-2H5v2zm7-18a1 1 0 0 1 1 1v9.59l3.3-3.3 1.4 1.42-5.7 5.7-5.7-5.7 1.4-1.42 3.3 3.3V3a1 1 0 0 1 1-1z"/></svg>
            Exportar ZIP
          </button>
        </div>
        <details class="mt-4 text-xs text-slate-500">
          <summary class="cursor-pointer font-semibold text-slate-600">¿Qué incluye el ZIP?</summary>
          <ul class="mt-2 space-y-1 pl-4 list-disc">
            <li><code>clientes.csv</code> — todos tus clientes con NIF, dirección y notas.</li>
            <li><code>facturas.csv</code> — cada factura con datos emisor/receptor, IVA/IRPF, base imponible, cuotas, total, trimestre, estado y método de cobro.</li>
            <li><code>lineas_factura.csv</code> — líneas de cada factura (concepto, cantidad, precio, importe) unidas por <code>factura_id</code>.</li>
            <li><code>gastos.csv</code> — gastos con categoría, proveedor, fecha, trimestre y ruta del adjunto.</li>
            <li><code>conceptos.csv</code> — libro de conceptos por trimestre (ingresos y gastos).</li>
            <li><code>configuracion.csv</code> — datos del emisor y preferencias por defecto.</li>
            <li><code>api_tokens.csv</code> — tokens con prefijo, fechas de uso y revocación (sin secretos).</li>
            <li><code>README.txt</code> — descripción de columnas y fecha de generación.</li>
          </ul>
        </details>
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

  // Tokens de API
  renderTokens(tokens);

  document.getElementById("new-token").onclick = () => openCreateToken(container);

  // Exportación completa
  document.getElementById("export-data").onclick = async () => downloadExport();
}

async function downloadExport() {
  try {
    const token = api.getToken();
    if (!token) {
      toast("No hay sesión activa", "error");
      return;
    }
    const btn = document.getElementById("export-data");
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = "Generando…";
    const res = await fetch(api.base + "/export", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const dispo = res.headers.get("content-disposition") || "";
    const m = dispo.match(/filename="?([^";]+)"?/);
    const filename = m ? m[1] : `faktu-export-${new Date().toISOString().slice(0, 10)}.zip`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    toast("Exportación lista", "success");
  } catch (e) {
    toast(`Error al exportar: ${e.message}`, "error");
  } finally {
    const btn = document.getElementById("export-data");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="mr-1"><path d="M5 20h14v-2H5v2zm7-18a1 1 0 0 1 1 1v9.59l3.3-3.3 1.4 1.42-5.7 5.7-5.7-5.7 1.4-1.42 3.3 3.3V3a1 1 0 0 1 1-1z"/></svg>
        Exportar ZIP
      `;
    }
  }
}

function renderTokens(tokens) {
  const list = document.getElementById("tokens-list");
  if (!tokens.length) {
    list.innerHTML = `<p class="text-xs text-slate-400">No tienes tokens. Crea uno para empezar.</p>`;
    return;
  }
  list.innerHTML = tokens
    .map((t) => {
      const live = !t.revoked_at;
      const used = t.last_used_at ? `usado ${fmtDate(t.last_used_at)}` : "nunca usado";
      return `
        <div class="flex items-center justify-between gap-2 rounded-xl border ${live ? "border-slate-200 bg-white" : "border-rose-200 bg-rose-50"} px-3 py-2">
          <div class="min-w-0">
            <p class="truncate text-sm font-bold text-slate-800">${esc(t.name || "sin nombre")}</p>
            <p class="truncate font-mono text-xs text-slate-500">fkt_<strong class="text-brand-600">${esc(t.prefix)}</strong>••••••••••</p>
            <p class="text-[11px] text-slate-400">creado ${fmtDate(t.created_at)} · ${used}${!live ? " · revocado" : ""}</p>
          </div>
          ${live
            ? `<button class="icon-btn text-rose-500 hover:bg-rose-50" data-revoke="${t.id}" title="Revocar">${ICONS.trash}</button>`
            : ""}
        </div>`;
    })
    .join("");

  list.querySelectorAll("[data-revoke]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const ok = await confirmAction({
        title: "¿Revocar este token?",
        message: "Dejará de funcionar inmediatamente. Esta acción no se puede deshacer.",
      });
      if (!ok) return;
      try {
        await api.del(`/api-tokens/${btn.dataset.revoke}`);
        toast("Token revocado");
        const fresh = await api.get("/api-tokens");
        renderTokens(fresh);
      } catch (e) {
        toast(e.message, "error");
      }
    }),
  );
}

function openCreateToken(container) {
  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">Nuevo token de API</h2>
        <button class="icon-btn" id="tok-close">✕</button>
      </div>
      <form id="tok-form" class="space-y-4">
        <div>
          <label class="label">Etiqueta (para identificar el dispositivo o IA)</label>
          <input class="input" name="name" placeholder="p. ej. Claude Desktop" maxlength="80">
        </div>
        <p class="text-xs text-slate-500">
          El token se mostrará <strong>una sola vez</strong>. Cópialo y guárdalo en un lugar seguro
          (gestor de contraseñas). Para revocar el acceso basta con borrarlo desde aquí.
        </p>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" id="tok-cancel">Cancelar</button>
          <button type="submit" class="btn-primary">Crear token</button>
        </div>
      </form>
    </div>`);

  document.getElementById("tok-close").onclick = closeModal;
  document.getElementById("tok-cancel").onclick = closeModal;
  document.getElementById("tok-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = new FormData(e.target).get("name")?.toString().trim() || "";
    try {
      const created = await api.post("/api-tokens", { name });
      closeModal();
      // Refresca la lista debajo del modal antes de mostrar el secreto.
      const fresh = await api.get("/api-tokens");
      renderTokens(fresh);
      showCreatedToken(created);
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

function showCreatedToken(created) {
  openModal(`
    <div class="p-5 sm:p-7">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900">Tu token, cópialo ya</h2>
        <button class="icon-btn" id="tok-close">✕</button>
      </div>
      <p class="text-sm text-slate-600">
        Por seguridad <strong>solo se muestra una vez</strong>. Pégalo donde lo necesites
        (Claude, scripts, Postman…) antes de cerrar esta ventana.
      </p>
      <div class="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-4">
        <p class="select-all break-all text-center font-mono text-base font-bold tracking-wider text-slate-900 sm:text-lg" id="tok-secret">${esc(created.token)}</p>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <button class="btn-primary" id="tok-copy">${ICONS.copy} Copiar al portapapeles</button>
        <a class="btn-ghost text-xs" href="/docs" target="_blank" rel="noopener">Ver documentación API</a>
      </div>
      <details class="mt-4 text-xs text-slate-500">
        <summary class="cursor-pointer font-semibold text-slate-600">Cómo usarlo (ejemplo curl)</summary>
        <pre class="mt-2 overflow-x-auto rounded-lg bg-slate-100 p-3 text-[11px] leading-snug text-slate-800"><code>curl https://tu-dominio/api/v1/facturas \\\\
  -H "Authorization: Bearer ${esc(created.token)}"</code></pre>
      </details>
      <div class="mt-6 flex justify-end">
        <button class="btn-primary" id="tok-done">Listo, lo he guardado</button>
      </div>
    </div>`);

  document.getElementById("tok-close").onclick = closeModal;
  document.getElementById("tok-done").onclick = closeModal;
  document.getElementById("tok-copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(created.token);
      toast("Token copiado", "success");
    } catch (_) {
      const el = document.getElementById("tok-secret");
      const r = document.createRange();
      r.selectNodeContents(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      toast("Selecciona y copia manualmente", "info");
    }
  };
}
