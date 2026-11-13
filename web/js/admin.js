"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const money = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(v / 100);
const decimal = (cents) => (cents / 100).toFixed(2);
const cents = (str) => Math.round(Number(str) * 100);
const imageSrc = (url) => /^\/(images|uploads)\//.test(url || "") && !url.includes("..") ? url : "/images/logo.png";
const STATUSES = { new: "Yeni", confirmed: "Onaylandı", preparing: "Hazırlanıyor", on_the_way: "Yolda", delivered: "Teslim Edildi", cancelled: "İptal Edildi" };
const NEXT = { new: ["confirmed", "cancelled"], confirmed: ["preparing", "cancelled"], preparing: ["on_the_way", "cancelled"], on_the_way: ["delivered", "cancelled"], delivered: [], cancelled: [] };
const SECTIONS = { overview: ["Genel Bakış", "İşletmenizin son durumuna göz atın."], products: ["Ürün Yönetimi", "Ürün ekle, fiyat değiştir, görsel yükle ve stok durumunu yönet."], categories: ["Kategoriler", "Menünüzün kategori yapısını düzenleyin."], orders: ["Siparişler", "Siparişlerinizi anlık listeleyin ve süreçleri yönetin."], messages: ["Mesajlar", "Müşterilerinizin sizinle iletişime geçmek için gönderdiği mesajlar."], settings: ["Site Ayarları", "İşletmenize ait metin, görsel ve sipariş ayarlarını değiştirin."] };
let csrfToken = "";
let activeSection = "overview";
let products = [];
let categories = [];
let orders = [];
let messages = [];
let settings = {};
let toastTimeout;
let previousNewOrderCount = null;

function toast(message) {
  const el = $("#toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toastTimeout); toastTimeout = setTimeout(() => el.classList.remove("show"), 4000);
}

async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.body && typeof options.body === "string") headers["Content-Type"] = "application/json";
  if (csrfToken && options.method && options.method.toUpperCase() !== "GET") headers["X-CSRF-Token"] = csrfToken;
  const response = await fetch(path, { credentials: "same-origin", ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/admin/login") showLogin();
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((e) => e.msg).join("; ") : "İşlem tamamlanamadı");
  }
  return data;
}

function showLogin() { csrfToken = ""; $("#admin-app").hidden = true; $("#login-screen").hidden = false; }
function showAdmin() { $("#login-screen").hidden = true; $("#admin-app").hidden = false; navigate("overview"); }

async function handleLogin(event) {
  event.preventDefault();
  const button = $("#login-button"); button.disabled = true;
  try {
    const data = Object.fromEntries(new FormData(event.target));
    const response = await api("/api/admin/login", { method: "POST", body: JSON.stringify(data) });
    csrfToken = response.csrf_token;
    event.target.reset();
    showAdmin();
    toast("Yönetim paneline hoş geldiniz");
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
}

async function navigate(section) {
  activeSection = section;
  $$(".panel-section").forEach((el) => { el.hidden = el.id !== `section-${section}`; });
  $$("#admin-nav [data-section]").forEach((el) => el.classList.toggle("selected", el.dataset.section === section));
  const [title, subtitle] = SECTIONS[section];
  $("#page-title").textContent = title;
  $("#page-subtitle").textContent = subtitle;
  $("#breadcrumb-title").textContent = title;
  $("#sidebar").classList.remove("open");
  try {
    switch (section) {
      case "overview": await loadDashboard(); break;
      case "products": await loadProducts(); break;
      case "categories": await loadCategories(); break;
      case "orders": await loadOrders(); break;
      case "messages": await loadMessages(); break;
      case "settings": await loadSettings(); break;
    }
  } catch (error) { toast(error.message); }
}

function statusPill(status) {
  const variant = { delivered: "green", confirmed: "green", new: "orange", preparing: "orange", cancelled: "red", on_the_way: "orange" }[status] || "";
  return `<span class="status-pill ${variant}">${esc(STATUSES[status] || status)}</span>`;
}

function shortDate(value) {
  return new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" }).format(new Date(value));
}

async function loadDashboard() {
  const data = await api("/api/admin/dashboard");
  if (previousNewOrderCount !== null && data.new_orders > previousNewOrderCount) {
    $("#admin-live-notice").hidden = false;
    toast(`${data.new_orders - previousNewOrderCount} yeni sipariş geldi!`);
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Pideci · Yeni sipariş", {body: "Yeni siparişleriniz var. Yönetim paneline bakın."});
    }
  }
  previousNewOrderCount = data.new_orders;
  const stats = [
    ["Aktif Ürün", data.active_products, "fa-utensils", "Menüde görünen ürün"],
    ["Yeni Sipariş", data.new_orders, "fa-bag-shopping", "Onay bekleyen sipariş"],
    ["Teslim Edilen Ciro", money(data.delivered_revenue_cents), "fa-wallet", "Teslim edilen siparişler"],
    ["Okunmamış Mesaj", data.unread_messages, "fa-envelope", "İletişim talepleri"],
  ];
  $("#stats-grid").innerHTML = stats.map(([label, value, icon, desc]) => `<div class="stat-card"><div class="stat-header"><span>${label}</span><span class="stat-icon"><i class="fas ${icon}"></i></span></div><strong>${esc(value)}</strong><small>${desc}</small></div>`).join("");
  $("#recent-orders").innerHTML = data.recent_orders.length ? data.recent_orders.map((order) => `<div class="order-card"><div class="order-top"><div><h3>${esc(order.code)} · ${esc(order.customer_name)}</h3><small>${shortDate(order.created_at)}</small></div>${statusPill(order.status)}</div><div class="order-bottom"><span class="order-items">${order.items.map((x) => `${x.quantity}× ${esc(x.name)}`).join(" · ")}</span><b>${money(order.total_cents)}</b></div></div>`).join("") : '<p class="empty-state">Henüz sipariş bulunmuyor.</p>';
}

async function loadProducts() {
  [products, categories] = await Promise.all([api("/api/admin/products"), api("/api/admin/categories")]);
  const select = $("#admin-category-filter");
  const selected = select.value;
  select.innerHTML = '<option value="all">Tüm Kategoriler</option>' + categories.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  select.value = [...select.options].some((o) => o.value === selected) ? selected : "all";
  renderProducts();
}
function renderProducts() {
  const query = $("#admin-product-search").value.trim().toLocaleLowerCase("tr-TR");
  const category = $("#admin-category-filter").value;
  const status = $("#admin-status-filter").value;
  const rows = products.filter((p) => (p.name.toLocaleLowerCase("tr-TR").includes(query) || p.category.toLocaleLowerCase("tr-TR").includes(query)) &&
    (category === "all" || String(p.category_id) === category) &&
    (status === "all" || status === "active" && p.is_active || status === "inactive" && !p.is_active || status === "out" && !p.in_stock || status === "campaign" && p.old_price_cents > p.price_cents));
  $("#product-count").textContent = `${rows.length} ürün`;
  $("#products-table").innerHTML = rows.length ? rows.map((p) => `<tr>
    <td><div class="product-cell"><img src="${esc(imageSrc(p.image_url))}" alt=""><div><strong>${esc(p.name)}</strong><small>${esc(p.description || p.serving_info)}</small></div></div></td>
    <td>${esc(p.category)}</td><td><strong>${money(p.price_cents)}</strong>${p.old_price_cents ? `<br><small style="text-decoration:line-through;color:#999">${money(p.old_price_cents)}</small>` : ""}</td>
    <td>${p.badge ? `<span class="status-pill tag">${esc(p.badge)}</span>` : '<span class="muted">—</span>'}</td>
    <td>${p.in_stock ? '<span class="status-pill green">Stokta</span>' : '<span class="status-pill red">Tükendi</span>'}</td>
    <td>${p.is_active ? '<span class="status-pill green">Yayında</span>' : '<span class="status-pill">Arşivde</span>'}</td>
    <td><div class="row-actions"><button type="button" class="icon-button" title="Düzenle" data-edit-product="${p.id}"><i class="fas fa-pen"></i></button><button type="button" class="icon-button danger" title="Arşivle" data-archive-product="${p.id}" ${p.is_active ? "" : "disabled"}><i class="fas fa-box-archive"></i></button></div></td>
   </tr>`).join("") : '<tr><td colspan="7" class="empty-state">Ürün bulunamadı.</td></tr>';
}

function openProduct(id = null) {
  const form = $("#product-form");
  form.reset();
  const product = id ? products.find((p) => p.id === Number(id)) : null;
  $("#product-dialog-title").textContent = product ? "Ürünü Düzenle" : "Yeni Ürün Ekle";
  $("#product-category").innerHTML = categories.map((c) => `<option value="${c.id}">${esc(c.name)}${c.is_active ? "" : " (Pasif)"}</option>`).join("");
  if (!categories.length) { toast("Önce kategori eklemeniz gerekiyor"); return; }
  form.elements.id.value = product?.id || "";
  form.elements.name.value = product?.name || "";
  form.elements.category_id.value = product?.category_id || categories[0].id;
  form.elements.position.value = product?.position ?? (products.length + 1);
  form.elements.price.value = product ? decimal(product.price_cents) : "";
  form.elements.old_price.value = product?.old_price_cents ? decimal(product.old_price_cents) : "";
  form.elements.description.value = product?.description || "";
  form.elements.serving_info.value = product?.serving_info || "";
  form.elements.badge.value = product?.badge || "";
  form.elements.is_active.checked = product?.is_active ?? true;
  form.elements.in_stock.checked = product?.in_stock ?? true;
  form.elements.is_featured.checked = product?.is_featured ?? false;
  $("#product-image-file").value = "";
  $("#product-image-preview").src = imageSrc(product?.image_url);
  $("#product-dialog").showModal();
}

async function uploadFile(file) {
  if (!file) return null;
  if (file.size > 5 * 1024 * 1024) throw new Error("Görsel boyutu 5 MB'dan küçük olmalı");
  const body = new FormData(); body.append("file", file);
  const result = await api("/api/admin/uploads", { method: "POST", body });
  return result.url;
}

async function saveProduct(event) {
  event.preventDefault();
  const button = $("#save-product"); button.disabled = true;
  const form = event.target;
  const id = form.elements.id.value;
  const previous = id ? products.find((p) => p.id === Number(id)) : null;
  try {
    const image_url = await uploadFile($("#product-image-file").files[0]) || previous?.image_url || "";
    const payload = {
      name: form.elements.name.value.trim(), category_id: Number(form.elements.category_id.value),
      position: Number(form.elements.position.value), price_cents: cents(form.elements.price.value),
      old_price_cents: form.elements.old_price.value ? cents(form.elements.old_price.value) : null,
      description: form.elements.description.value, serving_info: form.elements.serving_info.value,
      badge: form.elements.badge.value,
      image_url, is_active: form.elements.is_active.checked,
      in_stock: form.elements.in_stock.checked, is_featured: form.elements.is_featured.checked,
    };
    await api(id ? `/api/admin/products/${id}` : "/api/admin/products", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    $("#product-dialog").close();
    toast("Ürün başarıyla kaydedildi");
    await loadProducts();
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
}

async function archiveProduct(id) {
  const product = products.find((p) => p.id === Number(id));
  if (!product || !confirm(`“${product.name}” siteden kaldırılsın mı? Sipariş geçmişi silinmez.`)) return;
  try { await api(`/api/admin/products/${id}`, { method: "DELETE" }); toast("Ürün arşivlendi"); await loadProducts(); }
  catch (error) { toast(error.message); }
}

async function loadCategories() { categories = await api("/api/admin/categories"); renderCategories(); }
function renderCategories() {
  $("#categories-table").innerHTML = categories.length ? categories.map((cat) => `<tr>
    <td><strong>${esc(cat.name)}</strong></td><td>${cat.position}</td>
    <td>${cat.is_active ? '<span class="status-pill green">Aktif</span>' : '<span class="status-pill">Pasif</span>'}</td>
    <td><div class="row-actions"><button type="button" class="icon-button" data-edit-category="${cat.id}" title="Düzenle"><i class="fas fa-pen"></i></button><button type="button" class="icon-button danger" data-delete-category="${cat.id}" title="Sil"><i class="fas fa-trash"></i></button></div></td>
    </tr>`).join("") : '<tr><td colspan="4" class="empty-state">Kategori bulunamadı.</td></tr>';
}
function openCategory(id = null) {
  const form = $("#category-form"); form.reset();
  const category = categories.find((c) => c.id === Number(id));
  $("#category-dialog-title").textContent = category ? "Kategoriyi Düzenle" : "Yeni Kategori";
  form.elements.id.value = category?.id || "";
  form.elements.name.value = category?.name || "";
  form.elements.position.value = category?.position ?? (categories.length + 1);
  form.elements.is_active.checked = category?.is_active ?? true;
  $("#category-dialog").showModal();
}
async function saveCategory(event) {
  event.preventDefault();
  const form = event.target; const id = form.elements.id.value;
  const data = { name: form.elements.name.value.trim(), position: Number(form.elements.position.value), is_active: form.elements.is_active.checked };
  try { await api(id ? `/api/admin/categories/${id}` : "/api/admin/categories", { method: id ? "PUT" : "POST", body: JSON.stringify(data) }); $("#category-dialog").close(); toast("Kategori kaydedildi"); await loadCategories(); }
  catch (error) { toast(error.message); }
}
async function deleteCategory(id) {
  const category = categories.find((c) => c.id === Number(id));
  if (!category || !confirm(`“${category.name}” kategorisini silmek istiyor musunuz?`)) return;
  try { await api(`/api/admin/categories/${id}`, { method: "DELETE" }); toast("Kategori silindi"); await loadCategories(); }
  catch (error) { toast(error.message); }
}

async function loadOrders() { orders = await api("/api/admin/orders"); renderOrders(); }
function renderOrders() {
  const filter = $("#order-filter").value;
  const rows = orders.filter((o) => filter === "all" || o.status === filter);
  $("#order-count").textContent = `${rows.length} sipariş`;
  $("#orders-list").innerHTML = rows.length ? rows.map((o) => `<article class="order-card">
    <div class="order-top"><div><h3>${esc(o.code)} · ${esc(o.customer_name)}</h3><small>${shortDate(o.created_at)}</small></div>${statusPill(o.status)}</div>
    <div class="order-meta"><span><i class="fas fa-phone"></i> ${esc(o.phone)}</span><span><i class="fas fa-location-dot"></i> ${esc(o.address)}</span><span>Kapıda Nakit</span></div>
    ${o.note ? `<div class="order-items"><b>Not:</b> ${esc(o.note)}</div>` : ""}
    <div class="order-items">${o.items.map((item) => `${item.quantity}× ${esc(item.name)} (${money(item.line_total_cents)})`).join(" · ")}</div>
    <div class="order-bottom"><div><b>${money(o.total_cents)}</b><small style="display:block;color:#999">${money(o.subtotal_cents)} + ${money(o.delivery_fee_cents)} teslimat</small></div>
      ${NEXT[o.status].length ? `<select aria-label="Sipariş durumunu güncelle" data-order-status="${o.id}"><option value="">Durum Güncelle...</option>${NEXT[o.status].map((next) => `<option value="${next}">${esc(STATUSES[next])}</option>`).join("")}</select>` : '<span class="status-pill">Sipariş tamamlandı</span>'}</div></article>`).join("") : '<p class="empty-state">Bu filtrede sipariş bulunamadı.</p>';
}
async function updateOrderStatus(id, status) {
  if (!status) return;
  if (status === "cancelled" && !confirm("Bu sipariş iptal edilsin mi?")) { renderOrders(); return; }
  try { await api(`/api/admin/orders/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); toast("Sipariş durumu güncellendi"); await loadOrders(); }
  catch (error) { toast(error.message); await loadOrders(); }
}

async function loadMessages() { messages = await api("/api/admin/messages"); renderMessages(); }
function renderMessages() {
  $("#messages-list").innerHTML = messages.length ? messages.map((m) => `<article class="message-card ${m.is_read ? "" : "unread"}">
   <div class="message-top"><div><h3>${esc(m.name)} ${m.is_read ? "" : '<span class="status-pill orange">Yeni</span>'}</h3><small>${esc(m.email)} ${m.phone ? " · " + esc(m.phone) : ""}</small></div><small>${shortDate(m.created_at)}</small></div>
   <p>${esc(m.message)}</p><button type="button" class="secondary-button" data-toggle-message="${m.id}" data-read="${m.is_read ? "false" : "true"}">${m.is_read ? "Okunmadı Yap" : "Okundu İşaretle"}</button></article>`).join("") : '<p class="empty-state">Henüz mesaj yok.</p>';
}
async function markMessage(id, isRead) {
  try { await api(`/api/admin/messages/${id}`, { method: "PATCH", body: JSON.stringify({ is_read: isRead }) }); await loadMessages(); }
  catch (error) { toast(error.message); }
}

async function loadSettings() {
  settings = await api("/api/admin/settings");
  const form = $("#settings-form");
  for (const [key, value] of Object.entries(settings)) {
    if (key.endsWith("_cents") || key.endsWith("_url")) continue;
    if (!form.elements[key]) continue;
    if (form.elements[key].type === "checkbox") form.elements[key].checked = value;
    else form.elements[key].value = value;
  }
  form.elements.instagram_url.value = settings.instagram_url || "";
  form.elements.facebook_url.value = settings.facebook_url || "";
  form.elements.delivery_fee.value = decimal(settings.delivery_fee_cents);
  form.elements.min_order.value = decimal(settings.min_order_cents);
  $$("#settings-form input[type=file]").forEach((el) => { el.value = ""; });
  $("#hero-preview").src = imageSrc(settings.hero_image_url);
  $("#logo-preview").src = imageSrc(settings.logo_url);
  $("#about-preview").src = imageSrc(settings.about_image_url);
}
async function saveSettings(event) {
  event.preventDefault(); const button = $("#save-settings"); button.disabled = true;
  const form = event.target;
  try {
    const next = {
      ...settings, business_name: form.elements.business_name.value, phone: form.elements.phone.value,
      address: form.elements.address.value, opening_hours: form.elements.opening_hours.value,
      instagram_url: form.elements.instagram_url.value, facebook_url: form.elements.facebook_url.value,
      delivery_areas: form.elements.delivery_areas.value, hero_title: form.elements.hero_title.value,
      hero_text: form.elements.hero_text.value, about_title: form.elements.about_title.value,
      about_text: form.elements.about_text.value, delivery_fee_cents: cents(form.elements.delivery_fee.value),
      min_order_cents: cents(form.elements.min_order.value), ordering_enabled: form.elements.ordering_enabled.checked,
    };
    const imageFields = [ ["#hero-file", "hero_image_url"], ["#logo-file", "logo_url"], ["#about-file", "about_image_url"] ];
    for (const [selector, key] of imageFields) {
      const newUrl = await uploadFile($(selector).files[0]);
      if (newUrl) next[key] = newUrl;
    }
    await api("/api/admin/settings", { method: "PUT", body: JSON.stringify(next) });
    toast("Site ayarları başarıyla kaydedildi"); await loadSettings();
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
}

function bindEvents() {
  $("#today-label").textContent = new Intl.DateTimeFormat("tr-TR", { dateStyle: "long" }).format(new Date());
  $("#login-form").onsubmit = handleLogin;
  $("#sidebar-toggle").onclick = () => $("#sidebar").classList.toggle("open");
  $("#logout-btn").onclick = async () => { try { await api("/api/admin/logout", { method: "POST" }); } catch {} showLogin(); };
  $("#new-product").onclick = () => openProduct();
  $("#product-form").onsubmit = saveProduct;
  $("#new-category").onclick = () => openCategory();
  $("#category-form").onsubmit = saveCategory;
  $("#refresh-orders").onclick = loadOrders;
  $("#refresh-messages").onclick = loadMessages;
  $("#notifications-enable").onclick = async () => {
    if (!("Notification" in window)) { toast("Tarayıcınız bildirim desteklemiyor"); return; }
    const permission = await Notification.requestPermission();
    toast(permission === "granted" ? "Bildirimler etkinleştirildi" : "Bildirim izni verilmedi");
  };
  $("#settings-form").onsubmit = saveSettings;
  $("#admin-product-search").oninput = renderProducts;
  $("#admin-category-filter").onchange = renderProducts;
  $("#admin-status-filter").onchange = renderProducts;
  $("#order-filter").onchange = renderOrders;
  for (const [inputId, previewId] of [["#hero-file", "#hero-preview"], ["#logo-file", "#logo-preview"], ["#about-file", "#about-preview"]]) {
    $(inputId).onchange = (event) => {
      const file = event.target.files[0]; if (!file) return;
      const url = URL.createObjectURL(file);
      const image = $(previewId);
      image.onload = () => URL.revokeObjectURL(url);
      image.src = url;
    };
  }
  $("#product-image-file").onchange = (event) => {
    const file = event.target.files[0]; if (!file) return;
    const url = URL.createObjectURL(file);
    const image = $("#product-image-preview");
    image.onload = () => URL.revokeObjectURL(url);
    image.src = url;
  };
  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-section]");
    if (nav) navigate(nav.dataset.section);
    const editP = event.target.closest("[data-edit-product]");
    if (editP) openProduct(editP.dataset.editProduct);
    const archive = event.target.closest("[data-archive-product]");
    if (archive) archiveProduct(archive.dataset.archiveProduct);
    const editC = event.target.closest("[data-edit-category]");
    if (editC) openCategory(editC.dataset.editCategory);
    const removeC = event.target.closest("[data-delete-category]");
    if (removeC) deleteCategory(removeC.dataset.deleteCategory);
    const message = event.target.closest("[data-toggle-message]");
    if (message) markMessage(message.dataset.toggleMessage, message.dataset.read === "true");
    if (event.target.closest("[data-close-dialog]")) event.target.closest("dialog").close();
  });
  document.addEventListener("change", (event) => {
    const status = event.target.closest("[data-order-status]");
    if (status) updateOrderStatus(status.dataset.orderStatus, status.value);
  });
}

async function init() {
  bindEvents();
  try { const me = await api("/api/admin/me"); csrfToken = me.csrf_token; showAdmin(); }
  catch { showLogin(); }
  // Keep the order queue current while the management panel is open.
  setInterval(() => {
    if ($("#admin-app").hidden || document.visibilityState !== "visible") return;
    // Poll incoming orders from any panel section; never claim background notifications.
    loadDashboard().catch((error) => toast(error.message));
    if (activeSection === "orders") loadOrders().catch((error) => toast(error.message));
  }, 25_000);
}
init();
