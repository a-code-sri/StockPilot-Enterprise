// FreshBasket Online: the shopper's side of the demo. Talks only to the shop server
// (/api, /ws); the shop server talks to StockPilot.
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const view = $("#view");
  const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
  const money = (v) => inr.format(v).replace(".00", "");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function load(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: keep in memory */ }
  }

  const S = {
    config: { shop_name: "FreshBasket", stockpilot_url: "", demo_tools: false, slots: {}, payments: {} },
    fruits: null,          // null = not loaded yet
    fruitsError: "",
    cart: load("fb.cart", {}),        // { itemId: qty }
    orders: load("fb.orders", []),    // [order_id, ...] newest first
    live: false,
    query: "",
  };

  const STATUS = {
    pending: { label: "Order received", icon: "🧾", text: "We've got your order and will start packing it soon." },
    packed: { label: "Packed", icon: "📦", text: "Your fruit is packed and waiting for a rider." },
    out_for_delivery: { label: "On the way", icon: "🛵", text: "Your rider is on the way. Keep your phone handy." },
    delivered: { label: "Delivered", icon: "✅", text: "Delivered. Enjoy your fruit!" },
    failed: { label: "Delivery failed", icon: "⚠️", text: "We couldn't deliver this time. The shop will try again or call you." },
    cancelled: { label: "Cancelled", icon: "✖️", text: "This order was cancelled. Nothing was charged." },
  };
  const STEPS = [["pending", "Placed", "🧾"], ["packed", "Packed", "📦"], ["out_for_delivery", "On the way", "🛵"], ["delivered", "Delivered", "✅"]];

  // ------------------------------------------------------------------ api

  async function api(path, options = {}) {
    const res = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    let body = null;
    try { body = await res.json(); } catch { /* empty */ }
    if (!res.ok) {
      let detail = body && body.detail;
      if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
      throw new Error(detail || `Something went wrong (${res.status}).`);
    }
    return body;
  }

  function toast(text, bad = false) {
    const el = document.createElement("div");
    el.className = "toast" + (bad ? " bad" : "");
    el.textContent = text;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  // ------------------------------------------------------------------ catalogue + cart

  const fruitById = (id) => (S.fruits || []).find((f) => f.id === Number(id));
  const cartLines = () => Object.entries(S.cart)
    .map(([id, qty]) => ({ fruit: fruitById(id), qty }))
    .filter((l) => l.fruit);
  const cartCount = () => cartLines().reduce((n, l) => n + l.qty, 0);
  const cartTotal = () => cartLines().reduce((n, l) => n + l.qty * l.fruit.price, 0);

  async function loadCatalogue({ quiet = false } = {}) {
    const before = new Map((S.fruits || []).map((f) => [f.id, f.available]));
    try {
      S.fruits = await api("/api/catalogue");
      S.fruitsError = "";
    } catch (e) {
      S.fruitsError = e.message;
      if (!S.fruits) S.fruits = [];
    }
    // Keep the basket within what's actually available now.
    const trimmed = [];
    for (const [id, qty] of Object.entries(S.cart)) {
      const f = fruitById(id);
      if (!f) { if (S.fruits.length) delete S.cart[id]; continue; }
      if (qty > f.available) {
        if (f.available > 0) S.cart[id] = f.available; else delete S.cart[id];
        trimmed.push(f.name);
      }
    }
    if (trimmed.length) {
      save("fb.cart", S.cart);
      toast(`Stock changed: we updated ${trimmed.join(", ")} in your basket.`);
    }
    const changed = quiet ? [] : S.fruits.filter((f) => before.has(f.id) && before.get(f.id) !== f.available).map((f) => f.id);
    renderCartButton();
    renderCart();
    if (route().name === "shop") renderShop(changed);
    if (route().name === "checkout") renderCheckout();
  }

  function setQty(id, qty) {
    const f = fruitById(id);
    if (!f) return;
    qty = Math.max(0, Math.min(qty, f.available));
    if (qty === 0) delete S.cart[id]; else S.cart[id] = qty;
    save("fb.cart", S.cart);
    renderCartButton(true);
    renderCart();
    if (route().name === "shop") renderShop();
    if (route().name === "checkout") renderCheckout();
  }

  function stepper(id, qty, max) {
    return `<div class="stepper" data-id="${id}">
      <button type="button" data-step="-1" aria-label="One less">−</button>
      <output aria-live="polite">${qty}</output>
      <button type="button" data-step="1" aria-label="One more" ${qty >= max ? "disabled" : ""}>+</button>
    </div>`;
  }

  // ------------------------------------------------------------------ views

  function route() {
    const h = location.hash.replace(/^#\/?/, "");
    if (h.startsWith("order/")) return { name: "order", id: decodeURIComponent(h.slice(6)) };
    if (h === "orders") return { name: "orders" };
    if (h === "checkout") return { name: "checkout" };
    return { name: "shop" };
  }

  function stockBadge(f) {
    if (f.available === 0) return `<span class="stock out">Sold out</span>`;
    if (f.available <= 5) return `<span class="stock low">Only ${f.available} left</span>`;
    return `<span class="stock ok">In stock</span>`;
  }

  function freshText(f) {
    if (f.fresh_days == null) return "🌿 Farm fresh";
    if (f.fresh_days < 0) return "Past its best, not for sale";
    if (f.fresh_days === 0) return "🌿 Best eaten today";
    return `🌿 Stays fresh ${f.fresh_days} more day${f.fresh_days === 1 ? "" : "s"}`;
  }

  function renderShop(pulseIds = []) {
    const name = esc(S.config.shop_name);
    const head = `
      <section class="hero">
        <div>
          <h1>Fresh fruit at your door, in 2 hours.</h1>
          <p>Hand-picked from mandis and orchards every morning. Order before 6 pm for same-day delivery, and pay when it arrives.</p>
          <div class="hero-perks"><span class="perk">🚚 Free delivery</span><span class="perk">💵 Pay on delivery</span><span class="perk">🔁 Easy cancellation</span></div>
        </div>
        <div class="hero-art" aria-hidden="true">🍎🥭🍌<br>🍇🍉🍓</div>
      </section>
      <div class="toolbar">
        <div><h2>Today at ${name}</h2><small id="stock-note">${S.live ? "Stock updates live." : "Stock refreshes automatically."}</small></div>
        <label class="search"><span class="sr-only" hidden>Search fruit</span>
          <input type="search" id="search" placeholder="Search fruit" value="${esc(S.query)}" aria-label="Search fruit"></label>
      </div>`;

    let body;
    if (S.fruits === null) {
      body = `<div class="grid">${'<div class="skeleton"></div>'.repeat(8)}</div>`;
    } else if (S.fruitsError && !S.fruits.length) {
      body = `<div class="empty"><div class="big">🔌</div><h2>The shop is closed right now</h2>
        <p>${esc(S.fruitsError)}</p><button class="btn btn-ghost" data-retry>Try again</button></div>`;
    } else if (!S.fruits.length) {
      body = `<div class="empty"><div class="big">🧺</div><h2>The shelves are empty</h2>
        <p>Fresh stock arrives soon. ${S.config.demo_tools ? "For the demo, stock the shop with the starter fruits." : ""}</p>
        ${S.config.demo_tools ? '<button class="btn btn-primary" data-stock>🧺 Stock the shop</button>' : ""}</div>`;
    } else {
      const q = S.query.trim().toLowerCase();
      const list = S.fruits.filter((f) => !q || f.name.toLowerCase().includes(q));
      body = list.length ? `<div class="grid">${list.map((f) => {
        const qty = S.cart[f.id] || 0;
        const action = f.available === 0 ? `<button class="btn btn-ghost" disabled>Sold out</button>`
          : qty ? stepper(f.id, qty, f.available)
          : `<button class="btn btn-primary" data-add="${f.id}">Add to basket</button>`;
        return `<article class="card ${f.available === 0 ? "soldout" : ""} ${pulseIds.includes(f.id) ? "pulse" : ""}" data-card="${f.id}">
          <div class="pic" aria-hidden="true">${f.emoji}</div>
          <div class="card-body">
            <h3>${esc(f.name)}</h3>
            <p class="blurb">${esc(f.blurb)}</p>
            <div class="row"><span class="price">${money(f.price)}<small> / ${esc(f.unit)}</small></span>${stockBadge(f)}</div>
            <div class="fresh">${freshText(f)}</div>
            ${action}
          </div></article>`;
      }).join("")}</div>` : `<div class="empty"><div class="big">🔍</div><h2>No fruit matches “${esc(S.query)}”</h2></div>`;
    }
    const focused = document.activeElement && document.activeElement.id === "search";
    view.innerHTML = head + body;
    if (focused) { const s = $("#search"); s.focus(); s.setSelectionRange(s.value.length, s.value.length); }
  }

  function summaryLines(lines) {
    return lines.map((l) => `<div class="line">
      <div class="line-pic" aria-hidden="true">${l.fruit.emoji}</div>
      <div><div class="line-name">${esc(l.fruit.name)}</div><div class="line-sub">${l.qty} × ${money(l.fruit.price)} / ${esc(l.fruit.unit)}</div></div>
      <b>${money(l.qty * l.fruit.price)}</b></div>`).join("");
  }

  function totalsBlock(total) {
    return `<div class="totals">
      <div class="row"><span>Items</span><span>${money(total)}</span></div>
      <div class="row"><span>Delivery</span><span class="free">Free</span></div>
      <div class="row grand"><span>To pay on delivery</span><span>${money(total)}</span></div></div>`;
  }

  function renderCheckout() {
    const lines = cartLines();
    if (S.fruits !== null && !lines.length) {
      view.innerHTML = `<a class="back" href="#/">← Back to shop</a><div class="empty"><div class="big">🛒</div>
        <h2>Your basket is empty</h2><p>Add some fruit first.</p><a class="btn btn-primary" href="#/">Browse fruit</a></div>`;
      return;
    }
    const summary = summaryPanel(lines);
    const existing = view.querySelector("aside.summary");
    if (existing && view.querySelector("form#checkout-form")) {
      existing.innerHTML = summary; // stock or basket changed: keep what the shopper typed
      return;
    }
    const draft = load("fb.customer", {});
    const radio = (name, options, current) => Object.entries(options).map(([k, label], i) => `
      <label class="choice"><input type="radio" name="${name}" value="${k}" ${(current ? current === k : i === 0) ? "checked" : ""}>
      <span><b>${esc(label)}</b></span></label>`).join("");
    view.innerHTML = `
      <a class="back" href="#/">← Keep shopping</a>
      <h1 class="page-title">Checkout</h1>
      <div class="checkout">
        <form id="checkout-form" novalidate>
          <section class="panel"><h2>Delivery details</h2>
            <div class="field-row">
              <div class="field"><label for="f-name">Full name</label><input id="f-name" name="name" autocomplete="name" required minlength="2" maxlength="60" value="${esc(draft.name)}"></div>
              <div class="field"><label for="f-phone">Phone</label><input id="f-phone" name="phone" type="tel" autocomplete="tel" required minlength="6" maxlength="20" value="${esc(draft.phone)}"></div>
            </div>
            <div class="field"><label for="f-address">Address</label><textarea id="f-address" name="address" autocomplete="street-address" required minlength="5" maxlength="300">${esc(draft.address)}</textarea></div>
            <div class="field"><label for="f-note">Note for the rider <span class="fineprint">(optional)</span></label><input id="f-note" name="note" maxlength="200" placeholder="e.g. Ring the bell twice" value="${esc(draft.note)}"></div>
          </section>
          <section class="panel"><h2>Delivery slot</h2><div class="choices">${radio("slot", S.config.slots, draft.slot)}</div></section>
          <section class="panel"><h2>Pay on delivery with</h2><div class="choices inline">${radio("payment", S.config.payments, draft.payment || "upi")}</div>
            <p class="fineprint" style="margin-top:10px">You pay the rider when your fruit arrives. Nothing is charged now.</p></section>
          <div class="error-box" id="checkout-error" hidden></div>
        </form>
        <aside class="panel summary">${summary}</aside>
      </div>`;
  }

  function summaryPanel(lines) {
    return `<h2>Order summary</h2>${summaryLines(lines)}<div style="margin-top:12px">${totalsBlock(cartTotal())}</div>
      <button class="btn btn-primary btn-block" style="margin-top:14px" type="submit" form="checkout-form" id="place-btn">Place order · ${money(cartTotal())}</button>
      <p class="fineprint" style="margin-top:10px">Free cancellation until your order is packed and sent out.</p>`;
  }

  function stepsBlock(status) {
    const idx = STEPS.findIndex(([s]) => s === status);
    const reached = status === "failed" ? 2 : status === "cancelled" ? -1 : idx;
    return `<ol class="steps">${STEPS.map(([s, label, icon], i) => {
      const cls = i < reached ? "done" : i === reached ? (status === "delivered" ? "done" : status === "failed" ? "" : "now") : "";
      return `<li class="${cls}" data-icon="${icon}">${label}</li>`;
    }).join("")}</ol>`;
  }

  const timeFmt = (iso) => new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

  async function renderOrder(id, { flash = false } = {}) {
    if (!view.dataset.order || view.dataset.order !== id) {
      view.dataset.order = id;
      view.innerHTML = `<a class="back" href="#/orders">← My orders</a><div class="skeleton" style="height:220px"></div>`;
    }
    let o;
    try {
      o = await api(`/api/orders/${encodeURIComponent(id)}`);
    } catch (e) {
      view.innerHTML = `<a class="back" href="#/orders">← My orders</a><div class="empty"><div class="big">🔎</div>
        <h2>Couldn't load this order</h2><p>${esc(e.message)}</p><button class="btn btn-ghost" data-reload-order>Try again</button></div>`;
      return;
    }
    if (route().name !== "order" || route().id !== id) return;
    const st = STATUS[o.status] || { label: o.status, icon: "📦", text: "" };
    const banner = o.status === "failed" ? `<div class="banner warn">⚠️ ${st.text}</div>`
      : o.status === "cancelled" ? `<div class="banner bad">✖️ ${st.text}</div>`
      : o.status === "delivered" ? `<div class="banner good">✅ Delivered. Paid ${money(o.total)} by ${esc(o.payment)}.</div>` : "";
    const timeline = [...o.timeline].reverse().map((t) => `<li><span class="dot"></span><div>
      <b>${esc((STATUS[t.status] || {}).label || t.status)}</b><small>${timeFmt(t.at)}${t.remark ? " · " + esc(t.remark) : ""}</small></div></li>`).join("");
    view.innerHTML = `
      <a class="back" href="#/orders">← My orders</a>
      <div class="track-head">
        <div class="track-icon" aria-hidden="true">${st.icon}</div>
        <div><h1>${esc(st.label)}</h1><p>${esc(st.text)}</p>
          <p><span class="order-id">${esc(o.order_id)}</span> · placed ${timeFmt(o.created_at)}</p></div>
      </div>
      <div class="track-grid">
        <div>
          <section class="panel">${stepsBlock(o.status)}${banner}
            <p class="updated">${S.live ? "🟢 This page updates live as the shop works on your order." : "This page refreshes automatically."}</p></section>
          <section class="panel"><h2>Timeline</h2><ol class="timeline">${timeline || "<li>No updates yet.</li>"}</ol></section>
        </div>
        <div>
          <section class="panel"><h2>Items</h2>${summaryLines(o.items.map((it) => ({ fruit: { name: it.name, emoji: it.emoji, price: it.price, unit: it.unit }, qty: it.quantity })))}
            <div style="margin-top:12px">${totalsBlock(o.total)}</div></section>
          <section class="panel"><h2>Delivery</h2><dl class="kv">
            <dt>Name</dt><dd>${esc(o.customer)}</dd><dt>Phone</dt><dd>${esc(o.phone)}</dd>
            <dt>Address</dt><dd>${esc(o.address)}</dd><dt>Slot</dt><dd>${esc(o.slot)}</dd><dt>Payment</dt><dd>${esc(o.payment)} on delivery</dd>
            ${o.note ? `<dt>Note</dt><dd>${esc(o.note)}</dd>` : ""}</dl>
            ${o.can_cancel ? '<button class="btn btn-danger btn-block" style="margin-top:14px" data-cancel>Cancel order</button>' : ""}</section>
        </div>
      </div>`;
    if (flash) $(".track-icon").animate([{ transform: "scale(1)" }, { transform: "scale(1.15)" }, { transform: "scale(1)" }], 500);
  }

  async function renderOrders() {
    if (!S.orders.length) {
      view.innerHTML = `<h1 class="page-title">My orders</h1><div class="empty"><div class="big">🧾</div><h2>No orders yet</h2>
        <p>Orders you place on this device show up here, with live tracking.</p><a class="btn btn-primary" href="#/">Start shopping</a></div>`;
      return;
    }
    view.innerHTML = `<h1 class="page-title">My orders</h1><div class="order-list">${S.orders.map(() => '<div class="skeleton" style="height:82px"></div>').join("")}</div>`;
    const results = await Promise.allSettled(S.orders.map((id) => api(`/api/orders/${encodeURIComponent(id)}`)));
    if (route().name !== "orders") return;
    const rows = results.map((r, i) => {
      if (r.status !== "fulfilled") return "";
      const o = r.value;
      const st = STATUS[o.status] || { label: o.status, icon: "📦" };
      const what = o.items.map((it) => `${it.quantity} ${it.unit} ${it.name}`).join(", ");
      return `<a class="order-row" href="#/order/${encodeURIComponent(S.orders[i])}">
        <div class="line-pic" aria-hidden="true">${o.items[0] ? o.items[0].emoji : "🧺"}</div>
        <div><div class="line-name">${money(o.total)} · <span class="order-id">${esc(o.order_id)}</span></div>
          <div class="line-sub">${esc(what)} · ${timeFmt(o.created_at)}</div></div>
        <span class="badge ${o.status}">${st.icon} ${esc(st.label)}</span></a>`;
    }).join("");
    view.innerHTML = `<h1 class="page-title">My orders</h1><div class="order-list">${rows || '<div class="empty"><h2>Your orders could not be loaded</h2></div>'}</div>`;
  }

  function render() {
    const r = route();
    document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === (r.name === "order" ? "orders" : r.name)));
    if (r.name !== "order") delete view.dataset.order;
    if (r.name === "shop") renderShop();
    else if (r.name === "checkout") renderCheckout();
    else if (r.name === "orders") renderOrders();
    else renderOrder(r.id);
    const c = $("#orders-count");
    c.hidden = !S.orders.length;
    c.textContent = S.orders.length;
  }

  // ------------------------------------------------------------------ basket drawer

  function renderCartButton(bump = false) {
    $("#cart-count").textContent = cartCount();
    if (bump) { const b = $("#cart-btn"); b.classList.remove("bump"); void b.offsetWidth; b.classList.add("bump"); }
  }

  function renderCart() {
    const lines = cartLines();
    $("#cart-body").innerHTML = lines.length ? lines.map((l) => `<div class="line">
        <div class="line-pic" aria-hidden="true">${l.fruit.emoji}</div>
        <div><div class="line-name">${esc(l.fruit.name)}</div><div class="line-sub">${money(l.fruit.price)} / ${esc(l.fruit.unit)}</div></div>
        <div class="line-end"><b>${money(l.qty * l.fruit.price)}</b>${stepper(l.fruit.id, l.qty, l.fruit.available)}</div></div>`).join("")
      : `<div class="empty" style="margin-top:16px"><div class="big">🛒</div><h2>Nothing here yet</h2><p>Add fruit from the shop.</p></div>`;
    $("#cart-foot").innerHTML = lines.length ? `${totalsBlock(cartTotal())}
      <a class="btn btn-primary btn-block" href="#/checkout" data-close-cart>Checkout · ${money(cartTotal())}</a>` : "";
  }

  function openCart(open) {
    $("#cart").classList.toggle("open", open);
    $("#cart").setAttribute("aria-hidden", String(!open));
    $("#cart-btn").setAttribute("aria-expanded", String(open));
    $("#scrim").hidden = !open;
    if (open) $("#cart-close").focus();
  }

  // ------------------------------------------------------------------ live updates

  let ws = null;
  let wsDelay = 1000;
  function setLive(on) {
    S.live = on;
    const el = $("#live");
    el.classList.toggle("on", on);
    el.querySelector("span").textContent = on ? "Live" : "Offline";
    const note = $("#stock-note");
    if (note) note.textContent = on ? "Stock updates live." : "Stock refreshes automatically.";
  }
  function watchOrders() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "watch", orders: S.orders }));
  }
  function connect() {
    ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
    ws.onopen = () => { wsDelay = 1000; watchOrders(); };
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.type === "live") setLive(Boolean(msg.connected));
      else if (msg.type === "catalogue") debounce("catalogue", () => loadCatalogue(), 300);
      else if (msg.type === "order") {
        const st = STATUS[msg.status];
        if (st) toast(`${st.icon} Order ${msg.order_id}: ${st.label}`);
        const r = route();
        if (r.name === "order" && r.id === msg.order_id) renderOrder(msg.order_id, { flash: true });
        if (r.name === "orders") renderOrders();
      }
    };
    ws.onclose = () => {
      setLive(false);
      setTimeout(connect, wsDelay);
      wsDelay = Math.min(wsDelay * 2, 15000);
    };
  }
  const timers = {};
  function debounce(key, fn, ms) { clearTimeout(timers[key]); timers[key] = setTimeout(fn, ms); }

  // ------------------------------------------------------------------ events

  document.addEventListener("click", async (e) => {
    const t = e.target.closest("button, a");
    if (!t) return;
    if (t.dataset.add) { setQty(t.dataset.add, 1); return; }
    if (t.dataset.step) {
      const id = t.closest(".stepper").dataset.id;
      setQty(id, (S.cart[id] || 0) + Number(t.dataset.step));
      return;
    }
    if (t.id === "cart-btn") { openCart(true); return; }
    if (t.id === "cart-close" || "closeCart" in t.dataset) { openCart(false); return; }
    if ("retry" in t.dataset) { S.fruits = null; renderShop(); loadCatalogue({ quiet: true }); return; }
    if ("reloadOrder" in t.dataset) { delete view.dataset.order; render(); return; }
    if ("openGuide" in t.dataset) { $("#guide").showModal(); return; }
    if ("closeGuide" in t.dataset) { $("#guide").close(); return; }
    if (t.id === "demo-close") { $("#demo-bar").hidden = true; save("fb.demoHidden", true); return; }
    if ("cancel" in t.dataset) {
      if (!confirm("Cancel this order?")) return;
      t.disabled = true;
      try {
        await api(`/api/orders/${encodeURIComponent(route().id)}/cancel`, { method: "POST" });
        toast("Your order was cancelled.");
      } catch (err) { toast(err.message, true); }
      renderOrder(route().id);
      return;
    }
    if ("stock" in t.dataset || t.id === "tool-stock") {
      t.disabled = true;
      try {
        const r = await api("/api/demo/stock-shop", { method: "POST" });
        toast(r.added.length ? `Added ${r.added.length} fruits to StockPilot inventory.` : "The shop already has all the starter fruits.");
        loadCatalogue({ quiet: true });
      } catch (err) { toast(err.message, true); }
      t.disabled = false;
      return;
    }
    if (t.id === "tool-shoppers") {
      t.disabled = true;
      try {
        const r = await api("/api/demo/shoppers?count=5", { method: "POST" });
        toast(r.placed.length ? `${r.placed.length} shoppers placed orders. See StockPilot → Delivery.` : "Nothing left in stock to order.");
      } catch (err) { toast(err.message, true); }
      t.disabled = false;
    }
  });

  document.addEventListener("input", (e) => {
    if (e.target.id === "search") { S.query = e.target.value; renderShop(); }
  });

  document.addEventListener("submit", async (e) => {
    if (e.target.id !== "checkout-form") return;
    e.preventDefault();
    const form = e.target;
    const err = $("#checkout-error");
    err.hidden = true;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    const data = Object.fromEntries(new FormData(form));
    save("fb.customer", { name: data.name, phone: data.phone, address: data.address });
    const btn = $("#place-btn");
    btn.disabled = true;
    btn.textContent = "Placing your order…";
    try {
      const order = await api("/api/orders", {
        method: "POST",
        body: JSON.stringify({ ...data, items: cartLines().map((l) => ({ item_id: l.fruit.id, quantity: l.qty })) }),
      });
      S.orders = [order.order_id, ...S.orders.filter((id) => id !== order.order_id)].slice(0, 30);
      save("fb.orders", S.orders);
      S.cart = {};
      save("fb.cart", S.cart);
      renderCartButton();
      renderCart();
      watchOrders();
      toast("🎉 Order placed! We'll start packing it right away.");
      location.hash = `#/order/${encodeURIComponent(order.order_id)}`;
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
      btn.textContent = `Place order · ${money(cartTotal())}`;
      loadCatalogue({ quiet: true });
    }
  });

  $("#scrim").addEventListener("click", () => openCart(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") openCart(false); });
  window.addEventListener("hashchange", () => { openCart(false); render(); view.focus({ preventScroll: true }); window.scrollTo(0, 0); });

  // ------------------------------------------------------------------ start

  (async function start() {
    try { S.config = { ...S.config, ...(await api("/api/config")) }; } catch { /* defaults */ }
    document.title = `${S.config.shop_name} · Fresh fruit, delivered`;
    $("#shop-name").textContent = S.config.shop_name;
    const sp = S.config.stockpilot_url;
    if (sp) {
      $("#stockpilot-link").href = sp;
      document.querySelectorAll("[data-sp]").forEach((a) => { a.href = sp + a.dataset.sp; });
    }
    $("#guide-tools").hidden = !S.config.demo_tools;
    $("#demo-bar").hidden = Boolean(load("fb.demoHidden", false));
    setLive(Boolean(S.config.live));
    render();
    renderCart();
    await loadCatalogue({ quiet: true });
    connect();
    // Safety net if live updates are unavailable.
    setInterval(() => { if (!S.live && route().name === "shop") loadCatalogue(); }, 30000);
    setInterval(() => { if (!S.live && route().name === "order") renderOrder(route().id); }, 20000);
  })();
})();
