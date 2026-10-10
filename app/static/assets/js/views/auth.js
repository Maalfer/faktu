// Pantalla de entrada / alta.

import { api } from "../api.js";
import { esc } from "../ui.js";

export async function initAuth() {
  const loginForm = document.getElementById("form-login");
  const registerForm = document.getElementById("form-register");
  const tabLogin = document.getElementById("tab-login");
  const tabRegister = document.getElementById("tab-register");
  const tabsBox = tabLogin?.parentElement;
  const errorBox = document.getElementById("auth-error");

  function showError(msg) {
    if (!msg) { errorBox.classList.add("hidden"); return; }
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function switchTab(register) {
    loginForm.classList.toggle("hidden", register);
    registerForm.classList.toggle("hidden", !register);
    tabLogin.classList.toggle("bg-white", !register);
    tabLogin.classList.toggle("shadow-sm", !register);
    tabLogin.classList.toggle("text-slate-800", !register);
    tabLogin.classList.toggle("text-slate-500", register);
    tabRegister.classList.toggle("bg-white", register);
    tabRegister.classList.toggle("shadow-sm", register);
    tabRegister.classList.toggle("text-slate-800", register);
    tabRegister.classList.toggle("text-slate-500", !register);
    showError("");
  }

  tabLogin.addEventListener("click", () => switchTab(false));
  tabRegister.addEventListener("click", () => switchTab(true));

  async function submit(url, form) {
    showError("");
    const body = Object.fromEntries(new FormData(form).entries());
    try {
      const data = await api.post(url, body);
      api.setToken(data.access_token);
      window.dispatchEvent(new CustomEvent("faktu:login", { detail: data.user }));
    } catch (e) {
      showError(e.message || "Error inesperado");
    }
  }

  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submit("/auth/login", loginForm);
  });
  registerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submit("/auth/register", registerForm);
  });

  setTimeout(() => document.getElementById("login-email")?.focus(), 80);

  // Decide qué mostrar según si la BD ya tiene usuarios.
  let signupOpen = false;
  try {
    const { available } = await api.get("/auth/signup-available");
    signupOpen = available;
  } catch (_) {
    signupOpen = false;
  }

  if (!signupOpen) {
    if (tabsBox) tabsBox.classList.add("hidden");
    if (tabRegister) tabRegister.classList.add("hidden");
    if (registerForm) registerForm.classList.add("hidden");
    if (loginForm) loginForm.classList.remove("hidden");
  }
}
