const CATEGORIES = {church: "храм", museum: "музей", monument: "памятник", park: "парк",
  square: "площадь", building: "здание", lost: "исчезнувший объект", other: "другое"};
const CRED = {confirmed: "подтверждено", from_words: "со слов", requires_check: "требует проверки"};
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";

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

async function post(id, action, body) {
  const r = await fetch(`/api/places/${id}/${action}/`, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()},
    body: JSON.stringify(body)});
  return r.ok;
}

function yearLabel(ph) {
  if (!ph.year) return "";
  return ph.year2 && ph.year2 !== ph.year ? `${ph.year}–${ph.year2}` : String(ph.year);
}

function thumbHtml(ph, i, extra = "") {
  return `<div class="thumb-wrap">
    <button type="button" class="thumb" data-i="${i}" title="${esc(ph.title)}">
      <img src="${esc(ph.thumb)}" alt="${esc(ph.title)}" loading="lazy">
      <span>${esc(yearLabel(ph))}</span></button>${extra}</div>`;
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
        e => `<li><b>${esc(e.start_year ?? "")}</b> <a href="/events/${esc(e.id)}/">${esc(e.title_ru)}</a></li>`) : ""}
    ${p.people.length ? "<h3>Люди</h3>" + list(p.people,
        x => `<li><a href="/people/${esc(x.id)}/">${esc(x.full_name)}</a> (${esc(x.birth_year ?? "?")}–${esc(x.death_year ?? "?")})</li>`) : ""}
    <h3>Старые фото</h3>
    <div id="pinned"></div>
    <div id="nearby"><p class="hint">Ищем фото на PastVu…</p></div>
    <h3>Источники</h3>
    ${p.sources.length ? list(p.sources,
      s => `<li>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>` : esc(s.title)}</li>`)
      : `<p class="hint">Источников пока нет.</p>`}`;
  drawPinned(id, p.pinned_photos);
  loadNearby(id, p.pinned_photos);
}

function drawPinned(id, photos) {
  const box = document.getElementById("pinned");
  if (!photos.length) { box.innerHTML = ""; return; }
  box.innerHTML = `<p class="hint">Проверено модератором:</p><div class="gallery">` +
    photos.map((ph, i) => thumbHtml(ph, i, IS_STAFF
      ? `<button type="button" class="mini" data-unpin="${ph.cid}">Открепить</button>` : "")).join("") +
    `</div>` + (photos.length >= 2 ? `<p><button type="button" id="cmp-open">Сравнить фото</button></p>` : "");
  box.querySelectorAll(".thumb").forEach(b => b.onclick = () => openPhoto(photos[+b.dataset.i]));
  box.querySelectorAll("[data-unpin]").forEach(b => b.onclick = async () => {
    await post(id, "unpin_photo", {cid: +b.dataset.unpin});
    showCard(id);
  });
  const c = document.getElementById("cmp-open");
  if (c) c.onclick = () => openCompare(photos);
}

async function loadNearby(id, pinned) {
  const box = document.getElementById("nearby");
  const have = new Set(pinned.map(p => p.cid));
  try {
    const data = await (await fetch(`/api/places/${id}/photos/`)).json();
    const photos = data.photos.filter(ph => !have.has(ph.cid));
    if (!photos.length) {
      box.innerHTML = `<p class="hint">${esc(data.error || (pinned.length ? "" : "Старых фото рядом не найдено."))}</p>`;
      return;
    }
    box.innerHTML = `<p class="hint">Найдено рядом на PastVu (могут относиться к соседним зданиям):</p>
      <div class="gallery">` + photos.map((ph, i) => thumbHtml(ph, i, IS_STAFF
        ? `<button type="button" class="mini" data-pin="${i}">Закрепить</button>` : "")).join("") + `</div>
      <p class="hint">Фото: <a href="https://pastvu.com" target="_blank" rel="noopener">PastVu</a>.
      Права принадлежат авторам, подробности на странице фото.</p>`;
    box.querySelectorAll(".thumb").forEach(b => b.onclick = () => openPhoto(photos[+b.dataset.i]));
    box.querySelectorAll("[data-pin]").forEach(b => b.onclick = async () => {
      const ph = photos[+b.dataset.pin];
      await post(id, "pin_photo", {cid: ph.cid, file: ph.file, title: ph.title, year: ph.year, year2: ph.year2});
      showCard(id);
    });
  } catch {
    box.innerHTML = `<p class="hint">Не удалось загрузить фото.</p>`;
  }
}

function openPhoto(ph) {
  document.getElementById("photo-img").src = ph.image;
  document.getElementById("photo-img").alt = ph.title;
  document.getElementById("photo-cap").textContent = [yearLabel(ph), ph.title].filter(Boolean).join(". ");
  document.getElementById("photo-link").href = ph.url;
  document.getElementById("photo-dlg").showModal();
}
document.getElementById("photo-close").onclick = () => document.getElementById("photo-dlg").close();

// Сравнение двух фото со шторкой
const cmpA = document.getElementById("cmp-a"), cmpB = document.getElementById("cmp-b");
const imgA = document.getElementById("cmp-img-a"), imgB = document.getElementById("cmp-img-b");
const range = document.getElementById("cmp-range");
const clip = () => { imgA.style.clipPath = `inset(0 ${100 - range.value}% 0 0)`; };
range.oninput = clip;
function openCompare(photos) {
  const opts = photos.map((ph, i) =>
    `<option value="${i}">${esc(yearLabel(ph) || "без даты")} ${esc(ph.title.slice(0, 40))}</option>`).join("");
  cmpA.innerHTML = cmpB.innerHTML = opts;
  cmpA.value = "0";
  cmpB.value = String(photos.length - 1);
  const update = () => {
    imgA.src = photos[+cmpA.value].image;
    imgB.src = photos[+cmpB.value].image;
  };
  cmpA.onchange = cmpB.onchange = update;
  update();
  range.value = 50;
  clip();
  document.getElementById("cmp-dlg").showModal();
}
document.getElementById("cmp-close").onclick = () => document.getElementById("cmp-dlg").close();

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
async function openFromUrl() {
  const id = new URLSearchParams(location.search).get("place");
  if (!id) return;
  const r = await fetch(`/api/places/${id}/`);
  if (!r.ok) return;
  const f = await r.json();
  const [lon, lat] = f.geometry.coordinates;
  map.setView([lat, lon], 17);
  showCard(id);
}
openFromUrl();