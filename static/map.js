const map = L.map("map", {
  center: [20, 75],
  zoom: 5,
  zoomControl: true,
});

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors',
}).addTo(map);

const slickLayers = {};
const trackLayers = {};
const shipMarkers = {};
let forecastLayerGroup = L.layerGroup().addTo(map);
let activeSpillId = null;

function makeShipIcon(active = false) {
  const bg = active ? "#10b981" : "#09090b";
  const border = active ? "#10b981" : "#27272a";
  const color = active ? "#000" : "#38bdf8";
  return L.divIcon({
    className: "",
    html: `<div style="
      background:${bg};
      width:28px;height:28px;border-radius:6px;
      display:grid;place-items:center;
      box-shadow:0 0 12px rgba(0,0,0,0.8);
      border:1px solid ${border};
      font-size:12px;color:${color};">
      <i class='fa-solid fa-ship'></i>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function drawSpill(spill) {
  const polygon = L.geoJSON(spill.geometry, {
    style: {
      color: "#f43f5e",
      weight: 1.5,
      fillColor: "#f43f5e",
      fillOpacity: 0.25,
    },
  })
    .bindPopup(`
      <strong style="color:#f43f5e">${spill.name}</strong><br/>
      <small style="color:#a1a1aa">${spill.date_display}</small><br/>
      <b>${spill.area_km2} km²</b> &bull; ${spill.eez}
    `)
    .on("click", () => selectSpill(spill.id))
    .addTo(map);
  slickLayers[spill.id] = polygon;

  const track = L.geoJSON(spill.ship_track, {
    style: {
      color: "#38bdf8",
      weight: 1.5,
      dashArray: "4 4",
      opacity: 0.7,
    },
  }).addTo(map);
  trackLayers[spill.id] = track;

  const [lng, lat] = spill.ship_position;
  const marker = L.marker([lat, lng], { icon: makeShipIcon() })
    .bindPopup(`
      <strong style="color:#38bdf8">${spill.vessel.name}</strong><br/>
      <small style="color:#a1a1aa">${spill.vessel.flag} &bull; ${spill.vessel.type}</small>
    `)
    .on("click", () => selectSpill(spill.id))
    .addTo(map);
  shipMarkers[spill.id] = marker;
}

function renderCard(spill) {
  const card = document.createElement("div");
  card.className = "spill-card";
  card.id = `card-${spill.id}`;
  card.innerHTML = `
    <div class="spill-id">${spill.name.split(' ')[0]} &bull; ${spill.satellite}</div>
    <div class="spill-name">${spill.location}</div>
    <div class="spill-meta">
      <span class="spill-tag area"><i class="fa-solid fa-droplet"></i> ${spill.area_km2} km²</span>
      <span class="spill-tag conf"><i class="fa-solid fa-shield"></i> ${spill.confidence}%</span>
    </div>
  `;
  card.addEventListener("click", () => selectSpill(spill.id));
  document.getElementById("spill-list").appendChild(card);
}

function selectSpill(id) {
  forecastLayerGroup.clearLayers();
  document.getElementById('sidebar').classList.remove('open');
  
  if (activeSpillId) {
    const prevCard = document.getElementById(`card-${activeSpillId}`);
    if (prevCard) prevCard.classList.remove("active");
    if (slickLayers[activeSpillId]) {
      slickLayers[activeSpillId].setStyle({ color: "#f43f5e", weight: 1.5, fillOpacity: 0.25 });
    }
    if (shipMarkers[activeSpillId]) {
      shipMarkers[activeSpillId].setIcon(makeShipIcon(false));
    }
  }

  activeSpillId = id;
  const spill = window._spills.find((s) => s.id === id);
  if (!spill) return;

  slickLayers[id].setStyle({ color: "#10b981", weight: 2, fillOpacity: 0.4 });
  shipMarkers[id].setIcon(makeShipIcon(true));
  document.getElementById(`card-${id}`).classList.add("active");

  const [lng, lat] = spill.center;
  map.flyTo([lat, lng], 7, { duration: 1.2 });
  openDetail(spill);
}

function openDetail(spill) {
  document.getElementById("d-name").textContent = spill.name;
  document.getElementById("d-date").textContent = spill.date_display;
  document.getElementById("d-loc").textContent = spill.location;
  document.getElementById("d-eez").textContent = spill.eez;
  document.getElementById("d-area").textContent = `${spill.area_km2} km² (${spill.length_km} km length)`;
  document.getElementById("d-sat").textContent = `${spill.satellite} / ${spill.orbit_pass}`;
  document.getElementById("d-conf-wrap").innerHTML = `
    <div class="conf-bar-wrap">
      <div class="conf-bar"><div class="conf-bar-fill" style="width:${spill.confidence}%"></div></div>
      <span class="conf-pct">${spill.confidence}%</span>
    </div>`;
  const isConfirmed = spill.status === "Confirmed";
  document.getElementById("d-status").innerHTML = `
    <span class="status-badge ${isConfirmed ? "confirmed" : "investigating"}">
      ${spill.status}
    </span>`;
  document.getElementById("v-name").textContent = spill.vessel.name;
  document.getElementById("v-mmsi").textContent = spill.vessel.mmsi;
  document.getElementById("v-imo").textContent = spill.vessel.imo;
  document.getElementById("v-flag").textContent = spill.vessel.flag;
  document.getElementById("v-type").textContent = spill.vessel.type;
  document.getElementById("v-len").textContent = `${spill.vessel.length_m} m`;
  document.getElementById("detail-panel").classList.add("open");
}

function closeDetail() {
  document.getElementById("detail-panel").classList.remove("open");
  forecastLayerGroup.clearLayers();
  if (activeSpillId) {
    slickLayers[activeSpillId].setStyle({ color: "#f43f5e", weight: 1.5, fillOpacity: 0.25 });
    shipMarkers[activeSpillId].setIcon(makeShipIcon(false));
    const card = document.getElementById(`card-${activeSpillId}`);
    if (card) card.classList.remove("active");
  }
  activeSpillId = null;
}

document.getElementById("btn-drift").addEventListener("click", async () => {
  if (!activeSpillId) return;
  forecastLayerGroup.clearLayers();

  const res = await fetch(`/api/spills/${activeSpillId}/trajectory`);
  const data = await res.json();

  data.forecasts.forEach(fc => {
    L.geoJSON(fc.geometry, {
      style: {
        color: '#fbbf24',
        weight: 1.5,
        dashArray: '5, 5',
        fillColor: '#fbbf24',
        fillOpacity: 0.15
      }
    })
    .bindTooltip(`+${fc.forecast_hour}h Forecast: ${fc.projected_area_km2} sq km`, { sticky: true })
    .addTo(forecastLayerGroup);
  });
});

document.getElementById("btn-report").addEventListener("click", () => {
  if (activeSpillId) {
    window.open(`/api/spills/${activeSpillId}/report`, '_blank');
  }
});

async function loadStats() {
  const res = await fetch("/api/stats");
  const data = await res.json();
  document.getElementById("stat-total").textContent = data.total_spills;
  document.getElementById("stat-area").textContent = data.total_area_km2;
  document.getElementById("stat-conf").textContent = data.avg_confidence + "%";
  document.getElementById("stat-length").textContent = data.total_length_km;
}

async function boot() {
  const res = await fetch("/api/spills");
  const data = await res.json();
  window._spills = data.spills;
  data.spills.forEach((spill) => {
    renderCard(spill);
    drawSpill(spill);
  });
  await loadStats();
  if (data.spills.length > 0) {
    setTimeout(() => selectSpill(data.spills[0].id), 600);
  }
}

boot();