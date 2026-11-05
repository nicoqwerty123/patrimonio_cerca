// Avisos: consulta periódicamente las alertas que ya corresponde mostrar y las presenta como notificaciones.
(() => {
  const csrf = document.querySelector('meta[name="csrf"]').content;
  const caja = document.getElementById("avisos");
  const insignia = document.getElementById("insignia");
  const mostrados = new Set();

  const post = (url, datos) =>
    fetch(url, {
      method: "POST",
      headers: {"X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams(datos),
    });

  function aviso(p) {
    const el = document.createElement("div");
    el.className = "aviso-flotante";
    const t = document.createElement("a");
    t.href = p.url;
    t.textContent = p.titulo;
    const m = document.createElement("p");
    m.textContent = p.mensaje;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "enlace";
    b.textContent = "Entendido";
    b.addEventListener("click", () => {
      post(window.URLS.leer, {id: p.id});
      el.remove();
      if (insignia && !caja.children.length) insignia.hidden = true;
    });
    el.append(t, m, b);
    caja.append(el);
  }

  async function revisar() {
    try {
      const res = await fetch(window.URLS.pendientes);
      const {pendientes} = await res.json();
      pendientes.filter((p) => !mostrados.has(p.id)).forEach((p) => { mostrados.add(p.id); aviso(p); });
      if (insignia) {
        insignia.textContent = pendientes.length;
        insignia.hidden = pendientes.length === 0;
      }
    } catch (e) { /* sin conexión: se reintenta en el próximo ciclo */ }
  }

  const todas = document.getElementById("form-leer-todas");
  if (todas) {
    todas.addEventListener("submit", async (e) => {
      e.preventDefault();
      await post(window.URLS.leer, {todas: 1});
      location.reload();
    });
  }

  revisar();
  setInterval(revisar, 60000);
})();
