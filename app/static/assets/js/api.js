// Cliente ligero para la API REST de Faktu.

const TOKEN_KEY = "faktu_token";

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Error inesperado");
    this.status = status;
    this.detail = detail;
  }
}

export const api = {
  base: "/api/v1",

  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  async request(method, path, body, isForm = false) {
    const headers = {};
    const token = this.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let payload;
    if (body !== undefined && !isForm) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    } else if (isForm) {
      payload = body; // FormData
    }

    const res = await fetch(this.base + path, { method, headers, body: payload });
    if (res.status === 204) return null;

    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) data = await res.json();

    if (!res.ok) {
      if (res.status === 401 && !path.startsWith("/auth/login")) {
        this.clearToken();
        window.location.hash = "";
        window.dispatchEvent(new CustomEvent("faktu:logout"));
      }
      const detail = data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || "Campo inválido").join(" · ")
        : detail;
      throw new ApiError(res.status, msg);
    }
    return data;
  },

  get(p) { return this.request("GET", p); },
  post(p, b) { return this.request("POST", p, b); },
  put(p, b) { return this.request("PUT", p, b); },
  del(p) { return this.request("DELETE", p); },
  upload(p, file) {
    const fd = new FormData();
    fd.append("archivo", file);
    return this.request("POST", p, fd, true);
  },
};

export function downloadUrl(path) {
  const token = api.getToken();
  return token ? `${api.base}${path}` : api.base + path;
}

export async function downloadFile(url, fallbackName = "descarga") {
  const token = api.getToken();
  const res = await fetch(api.base + url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "No se pudo descargar");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

export function downloadPdf(url, fallbackName = "descarga.pdf") {
  return downloadFile(url, fallbackName);
}

export async function fileObjectUrl(path) {
  const token = api.getToken();
  const res = await fetch(api.base + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "No se pudo leer el archivo");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}