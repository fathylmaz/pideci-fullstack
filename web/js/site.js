"use strict";

const $ = (selector) => document.querySelector(selector);
const money = (cents) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(cents / 100);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const validImage = (url) => /^\/(images|uploads)\/[^?#]*$/u.test(url || "") && !url.includes("..");
const imageSrc = (url) => validImage(url) ? url : "/images/logo.png";
const state = { products: [], categories: [], settings: {}, categoryId: "all", search: "", sort: "default", limit: 12, cart: loadCart() };
let toastTimeout;
let lastOrderCode = "";
const ORDER_LABELS = {new:"Alındı / Değerlendiriliyor", confirmed:"Onaylandı", preparing:"Hazırlanıyor", on_the_way:"Yolda", delivered:"Teslim Edildi", cancelled:"İptal Edildi"};

function loadCart() {
  try {
    const value = JSON.parse(localStorage.getItem("pideci_cart") || "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([k, v]) => /^\d+$/.test(k) && Number.isInteger(v) && v > 0 && v <= 30));
  } catch { return {}; }
}

function notify(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3800);
}

async function jsonFetch(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((item) => item.msg).join(". ") : "İstek tamamlanamadı";
    throw new Error(message);
  }
  return data;
}

function setText(selector, value) {
  const node = $(selector);
  if (node) node.textContent = value;
}

function configureSite(settings) {
  state.settings = settings;
  document.title = `${settings.business_name} | Fırından Sofranıza`;
  setText("#hero-title", settings.hero_title);
  setText("#hero-text", settings.hero_text);
  setText("#about-title", settings.about_title);
  setText("#about-text", settings.about_text);
  setText("#footer-name", settings.business_name);
  setText("#contact-phone", settings.phone || "İşletme tarafından eklenecek");
  setText("#contact-address", settings.address || "İşletme tarafından eklenecek");
  setText("#contact-hours", settings.opening_hours);
  if (validImage(settings.logo_url)) {
    $("#site-logo").src = settings.logo_url;
    $("#footer-logo").src = settings.logo_url;
  }
  if (validImage(settings.about_image_url)) $("#about-image").src = settings.about_image_url;
  if (validImage(settings.hero_image_url)) $(".home").style.backgroundImage = `url("${encodeURI(settings.hero_image_url).replace(/"/g, "%22")}")`;
  const instagram = $("#instagram-link");
  if (/^https:\/\/(www\.)?instagram\.com\//.test(settings.instagram_url || "")) {
    instagram.href = settings.instagram_url;
    instagram.hidden = false;
  } else instagram.hidden = true;
  const facebook = $("#facebook-link");
  if (/^https:\/\/(www\.|m\.)?facebook\.com\//.test(settings.facebook_url || "")) {
    facebook.href = settings.facebook_url; facebook.hidden = false;
  } else facebook.hidden = true;
  const areas = (settings.delivery_areas || "").split(/[\n,]/).map((x) => x.trim()).filter(Boolean);
  const areaField = $("#delivery-area-field");
  const areaSelect = $("#delivery-area-select");
  areaField.hidden = areas.length === 0;
  areaSelect.required = areas.length > 0;
  areaSelect.replaceChildren(new Option("Bölge seçin", ""), ...areas.map((area) => new Option(area, area)));
  $("#delivery-areas-info").hidden = areas.length === 0;
  setText("#contact-delivery-areas", areas.join(" · "));
}

const categoryIcons = {"Pide": "fa-fire-flame-curved", "Lahmacun": "fa-pizza-slice", "Çorba": "fa-bowl-food", "Tatlı": "fa-cake-candles", "İçecek": "fa-mug-hot", "Yan Ürünler": "fa-seedling"};
const badgeIcons = {"Yeni":"fa-sparkles", "Popüler":"fa-heart", "Şefin Seçimi":"fa-star", "Kampanya":"fa-tag", "Acılı":"fa-pepper-hot", "Vejetaryen":"fa-leaf", "Tatlı Molası":"fa-cookie-bite"};

function renderCategories() {
  const chips = $("#category-chips");
  chips.replaceChildren();
  [{ id: "all", name: "Tümü" }, ...state.categories].forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip" + (String(state.categoryId) === String(category.id) ? " active" : "");
    const icon = category.id === "all" ? "fa-layer-group" : (categoryIcons[category.name] || "fa-utensils");
    button.innerHTML = `<i class="fas ${icon}" aria-hidden="true"></i> ${esc(category.name)}`;
    button.onclick = () => { state.categoryId = category.id; state.limit = 12; renderCategories(); renderProducts(); };
    chips.append(button);
  });
}

function productBadge(product) {
  if (!product.badge) return "";
  const value = product.badge;
  const css = value === "Kampanya" ? "sale" : value === "Yeni" ? "new" : value === "Vejetaryen" ? "green" : "";
  return `<span class="food-badge ${css}"><i class="fas ${badgeIcons[value] || "fa-tag"}"></i> ${esc(value)}</span>`;
}

function menuCard(product) {
  const outOfStock = !product.in_stock;
  const original = product.old_price_cents && product.old_price_cents > product.price_cents ? `<del>${money(product.old_price_cents)}</del>` : "";
  const discount = original ? `<span class="discount-tag">%${Math.round((1-product.price_cents/product.old_price_cents)*100)} indirim</span>` : "";
  return `<article class="box food-card"><div class="food-photo">
    <img loading="lazy" decoding="async" src="${esc(imageSrc(product.image_url))}" alt="${esc(product.name)}">
    ${productBadge(product)} ${outOfStock ? '<span class="sold-out">Tükendi</span>' : ""}
    </div><div class="food-info"><span class="menu-category">${esc(product.category)}</span>
    <h3>${esc(product.name)}</h3>
    <p class="product-description">${esc(product.description || product.serving_info || "Özenle hazırlanır.")}</p>
    <div class="food-price"><strong>${money(product.price_cents)}</strong>${original}${discount}</div></div>
    <div class="food-actions"><button class="btn add-to-cart" type="button" data-id="${product.id}" ${outOfStock ? "disabled" : ""}>
    ${outOfStock ? "Tükendi" : '<i class="fas fa-cart-plus"></i> Sepete Ekle'}</button></div></article>`;
}

function featuredCard(product) {
  return `<article class="box featured-card"><div class="featured-photo"><img loading="lazy" decoding="async" src="${esc(imageSrc(product.image_url))}" alt="${esc(product.name)}">${productBadge(product)}</div>
    <div class="featured-details"><span class="title">${esc(product.category)}</span><h3 class="name">${esc(product.name)}</h3>
    <p>${esc(product.description || "Taş fırından sofranıza.")}</p>
    <div class="featured-bottom"><strong>${money(product.price_cents)}</strong><button type="button" class="add-to-cart" data-id="${product.id}" ${product.in_stock ? "" : "disabled"} aria-label="${esc(product.name)} sepete ekle"><i class="fas fa-cart-plus"></i> Sepete Ekle</button></div></div></article>`;
}

function renderDeals() {
  const deals = state.products.filter((p) => p.in_stock && p.old_price_cents && p.old_price_cents > p.price_cents).slice(0, 3);
  $("#deals").hidden = deals.length === 0;
  $("#deals-grid").innerHTML = deals.map((p) => `<article class="deal-card"><img loading="lazy" src="${esc(imageSrc(p.image_url))}" alt="${esc(p.name)}"><div class="deal-content"><span><i class="fas fa-tag"></i> Menü Fırsatı</span><h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><div><del>${money(p.old_price_cents)}</del><strong>${money(p.price_cents)}</strong></div><button type="button" class="add-to-cart" data-id="${p.id}"><i class="fas fa-cart-plus"></i> Sepete Ekle</button></div></article>`).join("");
}

function renderPairings() {
  const dessert = state.products.filter((p) => p.category === "Tatlı" && p.in_stock).slice(0, 2);
  const drinks = state.products.filter((p) => p.category === "İçecek" && p.in_stock).slice(0, 2);
  $("#pairings-grid").innerHTML = [...dessert, ...drinks].map((p) => `<article class="pairing-card"><img loading="lazy" decoding="async" src="${esc(imageSrc(p.image_url))}" alt="${esc(p.name)}"><div><small>${esc(p.category)}</small><h3>${esc(p.name)}</h3><b>${money(p.price_cents)}</b></div><button type="button" class="add-to-cart" data-id="${p.id}" title="${esc(p.name)} sepete ekle" aria-label="${esc(p.name)} sepete ekle"><i class="fas fa-plus"></i></button></article>`).join("");
}

function renderProducts() {
  const query = state.search.toLocaleLowerCase("tr-TR");
  const products = state.products.filter((p) => (state.categoryId === "all" || String(state.categoryId) === String(p.category_id)) &&
    (p.name.toLocaleLowerCase("tr-TR").includes(query) || p.category.toLocaleLowerCase("tr-TR").includes(query) || p.description.toLocaleLowerCase("tr-TR").includes(query)));
  if (state.sort === "price-asc") products.sort((a,b) => a.price_cents-b.price_cents);
  if (state.sort === "price-desc") products.sort((a,b) => b.price_cents-a.price_cents);
  if (state.sort === "name") products.sort((a,b) => a.name.localeCompare(b.name,"tr"));
  const shown = products.slice(0,state.limit);
  $("#menu-grid").innerHTML = shown.length ? shown.map(menuCard).join("") : '<p class="empty-state">Aradığınız ürün bulunamadı.</p>';
  setText("#menu-meta", `${products.length} lezzet · ${shown.length} ürün gösteriliyor`);
  $("#show-more").hidden = shown.length >= products.length;
  const featured = state.products.filter((p) => p.is_featured && p.in_stock).slice(0, 4);
  $("#featured-grid").innerHTML = featured.length ? featured.map(featuredCard).join("") : '<p class="empty-state">Öne çıkan ürünler yakında burada olacak.</p>';
  renderDeals();
  renderPairings();
}

function setCart(productId, quantity) {
  const product = state.products.find((p) => p.id === Number(productId));
  if (!product || !product.in_stock) { notify("Bu ürün şu anda satışta değil."); return; }
  if (quantity <= 0) delete state.cart[productId];
  else state.cart[productId] = Math.min(quantity, 30);
  if (Object.values(state.cart).reduce((total, qty) => total + qty, 0) > 60) {
    if (quantity > 0) state.cart[productId] -= 1;
    if (state.cart[productId] <= 0) delete state.cart[productId];
    notify("Bir siparişte en fazla 60 ürün olabilir.");
  }
  localStorage.setItem("pideci_cart", JSON.stringify(state.cart));
  renderCart();
}

function calculateCart() {
  let subtotal = 0;
  let count = 0;
  const lines = [];
  for (const [id, qty] of Object.entries(state.cart)) {
    const product = state.products.find((p) => p.id === Number(id));
    if (!product || !product.in_stock) continue;
    subtotal += product.price_cents * qty;
    count += qty;
    lines.push({ product, qty });
  }
  return { subtotal, count, lines };
}

function renderCart() {
  const { subtotal, count, lines } = calculateCart();
  // Clean stale items (deleted, archived or out of stock) from persistent cart.
  const validIds = new Set(lines.map((line) => String(line.product.id)));
  let changed = false;
  Object.keys(state.cart).forEach((id) => { if (!validIds.has(id)) { delete state.cart[id]; changed = true; } });
  if (changed) localStorage.setItem("pideci_cart", JSON.stringify(state.cart));
  setText("#cart-count", count);
  $("#cart-items").innerHTML = lines.length ? lines.map(({ product, qty }) =>
    `<div class="cart-item"><img src="${esc(imageSrc(product.image_url))}" alt="${esc(product.name)}">
      <div class="cart-item-info"><strong>${esc(product.name)}</strong><small>${money(product.price_cents * qty)}</small>
      <div class="quantity-control"><button data-cart-minus="${product.id}" type="button" aria-label="Bir adet azalt">−</button><span>${qty}</span>
      <button data-cart-plus="${product.id}" type="button" aria-label="Bir adet artır">+</button>
      <button data-cart-remove="${product.id}" type="button" aria-label="Ürünü kaldır"><i class="fas fa-trash"></i></button></div></div></div>`).join("") : '<p class="empty-state" style="color:#555">Sepetin henüz boş. Menümüzden lezzet seçebilirsin.</p>';
  const delivery = state.settings.delivery_fee_cents || 0;
  const minimum = state.settings.min_order_cents || 0;
  setText("#cart-subtotal", money(subtotal));
  setText("#cart-delivery", money(lines.length ? delivery : 0));
  setText("#cart-total", money(subtotal + (lines.length ? delivery : 0)));
  setText("#min-order-note", !state.settings.ordering_enabled ? "Online sipariş şu an kapalı." : subtotal > 0 && subtotal < minimum ? `Minimum sipariş tutarı: ${money(minimum)}` : "");
  $("#checkout-open").disabled = count === 0 || subtotal < minimum || !state.settings.ordering_enabled;
}

function openCart() {
  $("#cart-backdrop").hidden = false;
  $("#cart-drawer").classList.add("open");
  $("#cart-drawer").setAttribute("aria-hidden", "false");
  $("#close-cart").focus();
}
function closeCart(restoreFocus = true) {
  $("#cart-backdrop").hidden = true;
  $("#cart-drawer").classList.remove("open");
  $("#cart-drawer").setAttribute("aria-hidden", "true");
  if (restoreFocus) $("#cart-btn").focus();
}

async function submitOrder(event) {
  event.preventDefault();
  const button = $("#order-submit");
  button.disabled = true;
  const data = Object.fromEntries(new FormData(event.target).entries());
  data.items = calculateCart().lines.map(({ product, qty }) => ({ product_id: product.id, quantity: qty }));
  try {
    const order = await jsonFetch("/api/public/orders", { method: "POST", body: JSON.stringify(data) });
    state.cart = {};
    localStorage.removeItem("pideci_cart");
    renderCart();
    $("#checkout-dialog").close();
    event.target.reset();
    closeCart();
    lastOrderCode = order.code;
    setText("#receipt-code", order.code);
    setText("#receipt-summary", `Toplam: ${money(order.total_cents)}`);
    $("#receipt-dialog").showModal();
  } catch (error) { notify(error.message); } finally { button.disabled = false; }
}

async function submitOrderStatus(event) {
  event.preventDefault();
  const button = $("#status-check");
  const result = $("#status-result");
  button.disabled = true;
  try {
    const data = new FormData(event.target);
    const query = new URLSearchParams({code: String(data.get("code") || ""), phone: String(data.get("phone") || "")});
    const status = await jsonFetch(`/api/public/orders/status?${query}`);
    result.hidden = false;
    result.textContent = `${status.code} · ${ORDER_LABELS[status.status] || status.status} · ${money(status.total_cents)}`;
  } catch(error) {
    result.hidden = false; result.textContent = error.message;
  } finally { button.disabled = false; }
}

async function submitContact(event) {
  event.preventDefault();
  const button = event.target.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const data = Object.fromEntries(new FormData(event.target).entries());
    await jsonFetch("/api/public/messages", { method: "POST", body: JSON.stringify(data) });
    event.target.reset();
    notify("Mesajınız işletmeye iletildi. Teşekkür ederiz!");
  } catch (error) { notify(error.message); } finally { button.disabled = false; }
}

function bindEvents() {
  $("#search-btn").onclick = () => { $("#menu").scrollIntoView({ behavior: "smooth" }); $("#product-search").focus(); };
  $("#cart-btn").onclick = openCart;
  $("#close-cart").onclick = closeCart;
  $("#cart-backdrop").onclick = closeCart;
  $("#checkout-open").onclick = () => { closeCart(false); $("#checkout-dialog").showModal(); };
  $("#checkout-close").onclick = () => $("#checkout-dialog").close();
  $("#checkout-form").onsubmit = submitOrder;
  $("#status-form").onsubmit = submitOrderStatus;
  $("#receipt-close").onclick = () => $("#receipt-dialog").close();
  $("#copy-order-code").onclick = async () => {
    try { await navigator.clipboard.writeText(lastOrderCode); notify("Sipariş kodu kopyalandı"); }
    catch { notify(`Sipariş kodunuz: ${lastOrderCode}`); }
  };
  $("#contact-form").onsubmit = submitContact;
  $("#product-search").oninput = (event) => { state.search = event.target.value.trim(); state.limit = 12; renderProducts(); };
  $("#product-sort").onchange = (event) => { state.sort = event.target.value; state.limit = 12; renderProducts(); };
  $("#show-more").onclick = () => { state.limit += 12; renderProducts(); };
  $("#menu-btn").onclick = () => {
    const open = $("#site-nav").classList.toggle("open");
    $("#menu-btn").setAttribute("aria-expanded", String(open));
  };
  $("#site-nav").onclick = (event) => { if (event.target.closest("a")) { $("#site-nav").classList.remove("open"); $("#menu-btn").setAttribute("aria-expanded", "false"); } };
  document.addEventListener("click", (event) => {
    const add = event.target.closest("[data-id].add-to-cart");
    if (add) { const id = add.dataset.id; setCart(id, (state.cart[id] || 0) + 1); notify("Ürün sepetine eklendi"); }
    const minus = event.target.closest("[data-cart-minus]");
    const plus = event.target.closest("[data-cart-plus]");
    const remove = event.target.closest("[data-cart-remove]");
    if (minus) setCart(minus.dataset.cartMinus, (state.cart[minus.dataset.cartMinus] || 0) - 1);
    if (plus) setCart(plus.dataset.cartPlus, (state.cart[plus.dataset.cartPlus] || 0) + 1);
    if (remove) setCart(remove.dataset.cartRemove, 0);
  });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && $("#cart-drawer").classList.contains("open")) closeCart(); });
}

async function init() {
  setText("#year", new Date().getFullYear());
  bindEvents();
  try {
    const [settings, categories, products] = await Promise.all([
      jsonFetch("/api/public/settings"), jsonFetch("/api/public/categories"), jsonFetch("/api/public/products"),
    ]);
    configureSite(settings);
    state.categories = categories;
    state.products = products;
    renderCategories();
    renderProducts();
    renderCart();
  } catch (error) {
    $("#menu-grid").innerHTML = '<p class="empty-state">Menü yüklenemedi. Sayfayı yenileyerek tekrar deneyin.</p>';
    notify("Sunucuyla bağlantı kurulamadı: " + error.message);
  }
}
init();
