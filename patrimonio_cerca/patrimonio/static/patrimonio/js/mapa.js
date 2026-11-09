(() => {
  const SANTIAGO = {lat: -33.4489, lng: -70.6693};
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const csrf = document.querySelector('meta[name="csrf"]').content;
  const cfg = window.CFG;
  const tiles = JSON.parse(document.getElementById("tiles-cfg").textContent);

  let centro = {...SANTIAGO, nombre: "Santiago centro"};
  let radio = cfg.radio;
  const marcadores = new Map();
  let circulo = null;

  const mapa = L.map("mapa").setView([centro.lat, centro.lng], 14);
  L.tileLayer(tiles.url, {maxZoom: 19, attribution: tiles.attr}).addTo(mapa);

  // Los marcadores cercanos se agrupan para que no se tapen entre sí.
  const capa = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 38,
    iconCreateFunction: (c) => L.divIcon({className: "", html: `<span class="cluster">${c.getChildCount()}</span>`, iconSize: [34, 34]}),
  });
  mapa.addLayer(capa);
  const capaYo = L.layerGroup().addTo(mapa);

  const distancia = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1).replace(".", ",")} km`);
  const icono = (r) => L.divIcon({
    className: "",
    html: `<span class="pin ${esc(r.tipo)}" style="--c:${esc(r.color)}"></span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
  const categoriasSel = () => [...document.querySelectorAll(".chip[aria-pressed='true']")].map((c) => c.dataset.id).join(",");

  function guardarPosicion(extra = {}) {
    fetch(cfg.ubic, {
      method: "POST",
      headers: {"X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({radio, ...extra}),
    });
  }

  function aviso(texto) {
    const a = $("#aviso");
    a.textContent = texto || "";
    a.hidden = !texto;
  }

  function contador(total) {
    const b = document.getElementById("insignia-ruta");
    if (b) { b.textContent = total; b.hidden = !total; }
  }

  // ---- datos ----
  async function cargar() {
    const p = new URLSearchParams({
      lat: centro.lat, lng: centro.lng, radio,
      gratis: $("#f-gratis").checked ? 1 : 0,
      pase: $("#f-pase").checked ? 1 : 0,
      abierto: $("#f-abierto").checked ? 1 : 0,
      categorias: categoriasSel(),
      tipo: $("#f-tipo").value,
      orden: $("#f-orden").value,
    });
    try {
      const res = await fetch(`${cfg.api}?${p}`);
      pintar((await res.json()).resultados);
    } catch (e) {
      aviso("No pudimos cargar los resultados. Revisa tu conexión e inténtalo de nuevo.");
    }
  }

  function pintar(lista) {
    capa.clearLayers();
    capaYo.clearLayers();
    marcadores.clear();
    if (circulo) circulo.remove();
    circulo = L.circle([centro.lat, centro.lng], {radius: radio * 1000, color: "#1f4e8c", weight: 1, fillOpacity: 0.04, interactive: false}).addTo(mapa);
    L.circleMarker([centro.lat, centro.lng], {radius: 6, color: "#fff", weight: 2, fillColor: "#1d2a33", fillOpacity: 1, interactive: false}).addTo(capaYo);

    const ol = $("#lista");
    ol.innerHTML = "";
    $("#titulo-lista").textContent = `Cerca de ${centro.nombre}`;
    $("#conteo").textContent = lista.length ? `${lista.length} ${lista.length === 1 ? "resultado" : "resultados"}` : "";
    $("#vacio").hidden = lista.length > 0;
    $("#vacio-radio").textContent = radio;
    $("#btn-ampliar").hidden = radio >= 10;
    $("#resumen").hidden = true;

    lista.forEach((r) => {
      const m = L.marker([r.lat, r.lng], {icon: icono(r), title: r.titulo});
      m.on("click", () => seleccionar(r));
      capa.addLayer(m);
      marcadores.set(r.id, m);

      const meta = [esc(r.categoria), esc(r.costo)];
      if (r.pase) meta.push("pase cultural");
      if (r.estado) meta.push(esc(r.estado_texto).toLowerCase());
      if (r.abierto === true) meta.push('<span class="abierto">abierto ahora</span>');
      if (r.abierto === false) meta.push('<span class="cerrado-txt">cerrado ahora</span>');

      const li = document.createElement("li");
      li.innerHTML = `
        <button type="button" class="item" data-id="${r.id}">
          <span class="pin ${esc(r.tipo)} chico" style="--c:${esc(r.color)}"></span>
          <span class="item-texto">
            <span class="item-titulo">${esc(r.titulo)}</span>
            <span class="item-meta">${meta.join(" · ")}</span>
          </span>
          <span class="item-dist">${distancia(r.distancia)}</span>
        </button>`;
      li.querySelector("button").addEventListener("click", () => seleccionar(r, true));
      ol.append(li);
    });

    mapa.fitBounds(circulo.getBounds(), {padding: [20, 20]});
  }

  function seleccionar(r, centrar) {
    if (window.innerWidth <= 860 && typeof mostrarVistaMapa === "function") {
      mostrarVistaMapa(true);
    }
    if (centrar && marcadores.has(r.id)) {
      capa.zoomToShowLayer(marcadores.get(r.id), () => mapa.panTo([r.lat, r.lng]));
    }
    document.querySelectorAll(".item.activo").forEach((e) => e.classList.remove("activo"));
    const fila = document.querySelector(`.item[data-id="${r.id}"]`);
    if (fila) { fila.classList.add("activo"); fila.scrollIntoView({block: "nearest"}); }

    const box = $("#resumen");
    box.hidden = false;
    box.innerHTML = `
      <button type="button" class="cerrar" aria-label="Cerrar resumen">×</button>
      <h3>${esc(r.titulo)}</h3>
      <p class="resumen-meta">${esc(r.categoria)} · a ${distancia(r.distancia)}</p>
      <ul class="etiquetas">
        <li class="${r.gratis ? "ok" : ""}">${esc(r.costo)}</li>
        ${r.pase ? '<li class="pase">Acepta pase cultural</li>' : ""}
        ${r.estado ? `<li class="estado-${esc(r.estado)}">${esc(r.estado_texto)}</li>` : ""}
        ${r.abierto === true ? '<li class="ok">Abierto ahora</li>' : ""}
        ${r.abierto === false ? '<li class="cerrado">Cerrado ahora</li>' : ""}
      </ul>
      <p>${r.fechas ? esc(r.fechas) + " · " : ""}${esc(r.horario)}</p>
      <p>${esc(r.direccion)}, ${esc(r.comuna)}</p>
      <div class="acciones">
        <a class="boton" href="${esc(r.url)}">Ver ficha completa</a>
        <button type="button" class="secundario" id="btn-fav">${r.fav ? "Quitar de mi ruta" : "Guardar en mi ruta"}</button>
      </div>`;
    box.querySelector(".cerrar").addEventListener("click", () => { box.hidden = true; });
    box.querySelector("#btn-fav").addEventListener("click", async (e) => {
      const res = await fetch(cfg.fav.replace("/0/", `/${r.id}/`), {
        method: "POST",
        headers: {"X-CSRFToken": csrf, "X-Requested-With": "fetch"},
      });
      const d = await res.json();
      r.fav = d.fav;
      e.target.textContent = r.fav ? "Quitar de mi ruta" : "Guardar en mi ruta";
      contador(d.total);
    });
  }

  // ---- ubicación y búsqueda ----
  function usarUbicacion() {
    if (!navigator.geolocation) { aviso("Tu navegador no permite obtener la ubicación. Busca por comuna o dirección."); return; }
    aviso("Buscando tu ubicación…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        centro = {lat: pos.coords.latitude, lng: pos.coords.longitude, nombre: "tu ubicación"};
        aviso("");
        guardarPosicion({lat: centro.lat, lng: centro.lng});
        cargar();
      },
      () => aviso("No pudimos obtener tu ubicación. Revisa el permiso del navegador o busca por comuna o dirección."),
      {enableHighAccuracy: true, timeout: 10000}
    );
  }

  $("#form-buscar").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = $("#q").value.trim();
    if (!q) return;
    const res = await fetch(`${cfg.buscar}?q=${encodeURIComponent(q)}`);
    const d = await res.json();
    if (!d.ok) { aviso("No encontramos ese lugar. Prueba con el nombre de una comuna, como Providencia o Valparaíso."); return; }
    aviso("");
    centro = {lat: d.lat, lng: d.lng, nombre: d.nombre};
    guardarPosicion({lat: d.lat, lng: d.lng});
    cargar();
  });

  $("#btn-ubicacion").addEventListener("click", usarUbicacion);

  // ---- filtros ----
  let espera;
  $("#radio").addEventListener("input", (e) => {
    radio = Number(e.target.value);
    $("#radio-valor").textContent = `${radio} km`;
    clearTimeout(espera);
    espera = setTimeout(() => { guardarPosicion(); cargar(); }, 250);
  });
  ["#f-gratis", "#f-pase", "#f-abierto", "#f-tipo", "#f-orden"].forEach((s) => $(s).addEventListener("change", cargar));
  document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => {
    c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
    cargar();
  }));

  $("#btn-ampliar").addEventListener("click", () => {
    radio = 10;
    $("#radio").value = 10;
    $("#radio-valor").textContent = "10 km";
    guardarPosicion();
    cargar();
  });
  $("#btn-limpiar").addEventListener("click", () => {
    ["#f-gratis", "#f-pase", "#f-abierto"].forEach((s) => { $(s).checked = false; });
    $("#f-tipo").value = "";
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
    cargar();
  });

  // ---- permiso inicial (pantalla 1 del diseño) ----
  const dlg = $("#permiso");
  const cerrarDialogo = () => { sessionStorage.setItem("decidido", "1"); dlg.close(); };
  $("#permitir").addEventListener("click", () => { cerrarDialogo(); usarUbicacion(); });
  $("#omitir").addEventListener("click", () => { cerrarDialogo(); aviso("Mostrando Santiago centro. Busca una comuna o usa tu ubicación cuando quieras."); });

  // ---- alternador móvil mapa / lista ----
  const btnToggle = document.getElementById("btn-toggle-vista");
  const visor = document.getElementById("contenido-principal");
  const icoVista = document.getElementById("ico-vista");
  const txtVista = document.getElementById("txt-vista");
  let viendoMapa = false;

  function mostrarVistaMapa(activar) {
    viendoMapa = activar;
    if (!visor) return;
    if (viendoMapa) {
      visor.classList.add("movil-modo-mapa");
      if (icoVista) icoVista.textContent = "📋";
      if (txtVista) txtVista.textContent = "Ver Lista y Filtros";
      setTimeout(() => { mapa.invalidateSize(); }, 200);
    } else {
      visor.classList.remove("movil-modo-mapa");
      if (icoVista) icoVista.textContent = "🗺️";
      if (txtVista) txtVista.textContent = "Ver Mapa";
    }
  }

  if (btnToggle) {
    btnToggle.addEventListener("click", () => mostrarVistaMapa(!viendoMapa));
  }

  cargar();
  if (!sessionStorage.getItem("decidido") && typeof dlg.showModal === "function") dlg.showModal();
})();
