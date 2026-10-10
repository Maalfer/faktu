// Utilidades de UI compartidas.

export const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

export function fmtEUR(n) {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(Number(n) || 0);
}

export function fmtNum(n) {
  return new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(n) || 0);
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = String(iso).slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function todayISO() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export function toast(msg, type = "success") {
  const root = document.getElementById("toast-root");
  const colors = {
    success: "bg-slate-900 text-white",
    error: "bg-rose-600 text-white",
    info: "bg-brand-600 text-white",
  };
  const icons = {
    success: `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
    error: `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm4.3 14.3a1 1 0 0 1-1.41 0L12 13.41 9.11 16.3a1 1 0 0 1-1.41-1.41L10.59 12 7.7 9.11a1 1 0 0 1 1.41-1.41L12 10.59l2.89-2.89a1 1 0 0 1 1.41 1.41L13.41 12l2.89 2.89a1 1 0 0 1 0 1.41z"/></svg>`,
    info: `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M11 7h2v2h-2zm0 4h2v6h-2zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg>`,
  };
  const el = document.createElement("div");
  el.className = `flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-2xl animate-toastIn ${colors[type] || colors.success}`;
  el.innerHTML = `${icons[type] || ""}<span>${esc(msg)}</span>`;
  root.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity .3s, transform .3s";
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    setTimeout(() => el.remove(), 320);
  }, 2600);
}

// ── Modal ────────────────────────────────────────────────────────────────

export function openModal(html, { wide = false } = {}) {
  const root = document.getElementById("modal-root");
  const panel = document.getElementById("modal-panel");
  panel.className = `relative z-10 max-h-[92dvh] w-full overflow-y-auto rounded-t-3xl bg-white shadow-2xl animate-fadeUp sm:mx-4 sm:rounded-3xl ${wide ? "sm:max-w-3xl" : "sm:max-w-2xl"}`;
  panel.innerHTML = html;
  root.classList.remove("hidden");
  root.classList.add("flex");
  document.body.style.overflow = "hidden";
  const backdrop = document.getElementById("modal-backdrop");
  backdrop.onclick = closeModal;
  document.addEventListener("keydown", escKey);
  return panel;
}

export function closeModal() {
  const root = document.getElementById("modal-root");
  root.classList.add("hidden");
  root.classList.remove("flex");
  document.body.style.overflow = "";
  document.removeEventListener("keydown", escKey);
}

function escKey(e) {
  if (e.key === "Escape") closeModal();
}

// ── Confirm ──────────────────────────────────────────────────────────────

export function confirmAction({ title, message, danger = true, confirmText = "Eliminar" }) {
  return new Promise((resolve) => {
    openModal(`
      <div class="p-6">
        <div class="flex items-start gap-4">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${danger ? "bg-rose-100 text-rose-600" : "bg-brand-100 text-brand-600"}">
            ${danger
              ? `<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`
              : `<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`}
          </div>
          <div class="flex-1">
            <h3 class="text-lg font-bold text-slate-900">${esc(title)}</h3>
            <p class="mt-1 text-sm text-slate-500">${esc(message)}</p>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-2">
          <button class="btn-ghost" id="confirm-cancel">Cancelar</button>
          <button class="${danger ? "btn-danger" : "btn-primary"}" id="confirm-ok">${esc(confirmText)}</button>
        </div>
      </div>`);
    document.getElementById("confirm-cancel").onclick = () => { closeModal(); resolve(false); };
    document.getElementById("confirm-ok").onclick = () => { closeModal(); resolve(true); };
  });
}

// ── Badges de estado ─────────────────────────────────────────────────────

export const ESTADOS = {
  borrador: "Borrador",
  emitida: "Emitida",
  pagada: "Pagada",
};

export function estadoBadge(estado) {
  return `<span class="badge badge-${esc(estado)}">${esc(ESTADOS[estado] || estado)}</span>`;
}

export function quarterBadge(q, info = {}) {
  const current = info.current ?? info.is_current;
  const future = info.future ?? info.is_future;
  const past = info.past ?? info.is_past;
  if (current) return `<span class="badge badge-current">Trimestre actual</span>`;
  if (future) return `<span class="badge badge-future">Próximo</span>`;
  if (past) return `<span class="badge badge-past">Histórico</span>`;
  return "";
}

// Iconos SVG reutilizables
export const ICONS = {
  dashboard: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>`,
  facturas: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm10 9H8v2h8v-2zm0 4H8v2h8v-2z"/></svg>`,
  gastos: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm6 10.5c0 .83-.67 1.5-1.5 1.5H14c-.55 0-1-.45-1-1V9c0-.55.45-1 1-1h4.5c.83 0 1.5.67 1.5 1.5v3zM5 6.5C5 5.67 5.67 5 6.5 5H10c.55 0 1 .45 1 1v4c0 .55-.45 1-1 1H5.5C4.67 11 4 10.33 4 9.5v-3zM6.5 19C5.67 19 5 18.33 5 17.5v-3c0-.83.67-1.5 1.5-1.5H10c.55 0 1 .45 1 1v4c0 .55-.45 1-1 1H6.5zm9.5-8h4v3c0 .83-.67 1.5-1.5 1.5H14c-.55 0-1-.45-1-1V12c0-.55.45-1 1-1z"/></svg>`,
  clientes: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>`,
  trimestres: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/></svg>`,
  ajustes: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94c.04-.3.06-.61.06-.94s-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>`,
  plus: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>`,
  pdf: `<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zm-8 2V5h2v6h1.17L12 13.17 9.83 11H11zm-6 7h14v2H5v-2z"/></svg>`,
  edit: `<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`,
  trash: `<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`,
  download: `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zm-8 2V5h2v6h1.17L12 13.17 9.83 11H11zm-6 7h14v2H5v-2z"/></svg>`,
  copy: `<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>`,
  key: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12.65 10a3.99 3.99 0 0 0-3.93 3.91c0 .27.03.54.07.8l-4.43 4.43 1.41 1.41 4.43-4.43c.26.04.53.07.8.07A3.91 3.91 0 0 0 12.65 10zm0 6a2 2 0 1 1 0-4 2 2 0 0 1 0 4zM21 7l-1.41-1.41-4.43 4.43A3.99 3.99 0 0 0 12.65 9.99c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4c0-.27-.03-.54-.07-.8L19.59 9 21 7.59V7z"/></svg>`,
};