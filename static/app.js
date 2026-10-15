const CATEGORIES = {church: "храм", museum: "музей", monument: "памятник", park: "парк",
  square: "площадь", building: "здание", lost: "исчезнувший объект", other: "другое"};
const CRED = {confirmed: "подтверждено", from_words: "со слов", requires_check: "требует проверки"};
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

const map = L.map("map").setView([56.1385, 47.245], 14);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  {attribution: "© OpenStreetMap"}).addTo(map);
const layer = L.layerGroup().addTo(map);

let category = "", year = 2026, timer;

async function loadPlaces() {
  const q = new URLSearchParams({year});
  if (category) q.set("category", category);
  const data = await (await fetch("/api/places/?" + q)).json();
  layer.clearLayers();
  data.features.forEach(f => {
    const [lon, lat] = f.geometry.coordinates;
    L.marker([lat, lon]).addTo(layer).on("click", () => showCard(f.id));
  });
}

async function showCard(id) {
  const f = await (await fetch(`/api/places/${id}/`)).json();
  const p = f.properties;
  const list = (items, fn) => items.length ? `<ul>${items.map(fn).join("")}</ul>` : "";
  document.getElementById("card").innerHTML = `
    <h2>${esc(p.name_ru)}</h2>
    ${p.name_cv ? `<p>${esc(p.name_cv)}</p>` : ""}
    <p><span class="badge ${esc(p.credibility)}">${CRED[p.credibility] || ""}</span>
       ${esc(CATEGORIES[p.category] || "")}${p.year_from ? ", с " + esc(p.year_from) + " г." : ""}</p>
    ${p.address ? `<p class="hint">${esc(p.address)}</p>` : ""}
    <p>${esc(p.description_ru)}</p>
    <p><a href="/places/${esc(f.id)}/suggest/">Предложить правку</a></p>
    ${p.events.length ? "<h3>События</h3>" + list(p.events,
      e => `<li><b>${esc(e.start_year ?? "")}</b> ${esc(e.title_ru)}</li>`) : ""}
    ${p.people.length ? "<h3>Люди</h3>" + list(p.people,
      x => `<li>${esc(x.full_name)} (${esc(x.birth_year ?? "?")}–${esc(x.death_year ?? "?")})</li>`) : ""}
    <h3>Старые фото</h3>
    <div id="photos"><p class="hint">Ищем фото на PastVu…</p></div>
    <h3>Источники</h3>
    ${p.sources.length ? list(p.sources,
      s => `<li>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>` : esc(s.title)}</li>`)
      : `<p class="hint">Источников пока нет.</p>`}`;
  loadPhotos(id);
}

function yearLabel(ph) {
  if (!ph.year) return "";
  return ph.year2 && ph.year2 !== ph.year ? `${ph.year}–${ph.year2}` : String(ph.year);
}

async function loadPhotos(id) {
  const box = document.getElementById("photos");
  try {
    const data = await (await fetch(`/api/places/${id}/photos/`)).json();
    if (!data.photos.length) {
      box.innerHTML = `<p class="hint">${esc(data.error || "Старых фото рядом не найдено.")}</p>`;
      return;
    }
    box.innerHTML = `<div class="gallery">` + data.photos.map((ph, i) =>
      `<button type="button" class="thumb" data-i="${i}" title="${esc(ph.title)}">
         <img src="${esc(ph.thumb)}" alt="${esc(ph.title)}" loading="lazy">
         <span>${esc(yearLabel(ph))}</span></button>`).join("") + `</div>
      <p class="hint">Фото: <a href="https://pastvu.com" target="_blank" rel="noopener">PastVu</a>.
      Права принадлежат авторам, подробности на странице фото.</p>`;
    box.querySelectorAll(".thumb").forEach(b =>
      b.onclick = () => openPhoto(data.photos[+b.dataset.i]));
  } catch {
    box.innerHTML = `<p class="hint">Не удалось загрузить фото.</p>`;
  }
}

function openPhoto(ph) {
  document.getElementById("photo-img").src = ph.image;
  document.getElementById("photo-img").alt = ph.title;
  document.getElementById("photo-cap").textContent =
    [yearLabel(ph), ph.title].filter(Boolean).join(". ");
  document.getElementById("photo-link").href = ph.url;
  document.getElementById("photo-dlg").showModal();
}
document.getElementById("photo-close").onclick =
  () => document.getElementById("photo-dlg").close();

function drawFilters() {
  const box = document.getElementById("filters");
  box.innerHTML = "";
  [["", "все"], ...Object.entries(CATEGORIES)].forEach(([key, label]) => {
    const b = document.createElement("button");
    b.textContent = label;
    if (key === category) b.className = "on";
    b.onclick = () => { category = key; drawFilters(); loadPlaces(); };
    box.append(b);
  });
}

document.getElementById("year").oninput = e => {
  year = +e.target.value;
  document.getElementById("year-out").textContent = year;
  clearTimeout(timer);
  timer = setTimeout(loadPlaces, 200);
};

drawFilters();
loadPlaces();