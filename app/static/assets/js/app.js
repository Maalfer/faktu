// Faktu — SPA principal: estado, navegación y enrutado.

import { api } from "./api.js";
import { esc, ICONS } from "./ui.js";
import { initAuth } from "./views/auth.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderFacturas, openFacturaForm } from "./views/facturas.js";
import { renderGastos, openGastoForm } from "./views/gastos.js";
import { renderClientes } from "./views/clientes.js";
import { renderConfig } from "./views/configuracion.js";

const ROUTES = [
  { id: "dashboard", label: "Panel", icon: ICONS.dashboard, render: renderDashboard, title: "Panel" },
  { id: "facturas", label: "Facturas", icon: ICONS.facturas, render: renderFacturas, title: "Facturas", fab: "newInvoice" },
  { id: "gastos", label: "Gastos", icon: ICONS.gastos, render: renderGastos, title: "Gastos", fab: "newGasto" },
  { id: "clientes", label: "Clientes", icon: ICONS.clientes, render: renderClientes, title: "Clientes" },
  { id: "ajustes", label: "Ajustes", icon: ICONS.ajustes, render: renderConfig, title: "Ajustes" },
];

let currentView = "";

const viewEl = () => document.getElementById("view");

function showApp() {
  document.getElementById("auth-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  loadUserInfo();
}

function showAuth() {
  document.getElementById("app").classList.add("hidden");
  document.getElementById("auth-screen").classList.remove("hidden");
}

function loadUserInfo() {
  api
    .get("/auth/me")
    .then((u) => {
      window.faktuUser = u;
      const who = document.getElementById("side-user");
      if (who) who.textContent = u.full_name || u.email;
    })
    .catch(() => {});
}

function buildNav() {
  const side = document.getElementById("side-nav");
  const mobile = document.getElementById("mobile-nav");
  side.innerHTML = ROUTES.map(
    (r) => `<a href="#/${r.id}" class="nav-item" data-nav="${r.id}">${r.icon}<span>${r.label}</span></a>`
  ).join("");
  mobile.innerHTML = ROUTES.map(
    (r) => `<a href="#/${r.id}" class="nav-item-mobile" data-nav="${r.id}">${r.icon}<span>${r.label}</span></a>`
  ).join("");
}

function setActiveNav(id) {
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const active = a.dataset.nav === id;
    a.classList.toggle("nav-item-active", active && a.classList.contains("nav-item"));
    a.classList.toggle("nav-item-mobile-active", active && a.classList.contains("nav-item-mobile"));
  });
}

async function router() {
  const hash = location.hash.replace(/^#\/?/, "");
  const route = ROUTES.find((r) => r.id === hash) || ROUTES[0];
  currentView = route.id;

  document.getElementById("mobile-title").textContent = route.title;
  setActiveNav(route.id);

  const fab = document.getElementById("fab");
  if (route.fab) {
    document.body.classList.add("show-fab");
    fab.onclick = () => {
      if (route.fab === "newInvoice") openFacturaForm();
      else openGastoForm();
    };
  } else {
    document.body.classList.remove("show-fab");
    fab.onclick = null;
  }

  viewEl().scrollTop = 0;
  window.scrollTo(0, 0);
  await route.render(viewEl());
}

async function bootstrap() {
  initAuth();
  buildNav();

  if (api.getToken()) {
    showApp();
  } else {
    showAuth();
  }

  window.addEventListener("hashchange", router);
  window.addEventListener("faktu:login", () => {
    showApp();
    if (!location.hash) location.hash = "#/dashboard";
    router();
  });
  window.addEventListener("faktu:logout", () => {
    showAuth();
    location.hash = "";
    currentView = "";
  });

  document.getElementById("logout-btn").addEventListener("click", () => {
    api.clearToken();
    window.dispatchEvent(new CustomEvent("faktu:logout"));
  });

  const menuBtn = document.getElementById("user-menu-btn");
  menuBtn.addEventListener("click", () => {
    const u = window.faktuUser;
    const msg = u ? `${u.full_name || ""} · ${u.email}` : "No identificado";
    (async () => {
      const mod = await import("./ui.js");
      mod.toast(msg, "info");
    })();
  });

  if (location.hash.startsWith("#/")) router();
}

bootstrap();

export { viewEl };