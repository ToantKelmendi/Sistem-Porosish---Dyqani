/**
 * Gjendja e ndarë mes dyqanit (klienti) dhe panelit të operacioneve.
 *
 * Në sistemin real këtë rol e mbajnë orders_db + inventory_db; në shfletues e
 * imitojmë me localStorage, që të dy faqet të shohin të njëjtat të dhëna dhe
 * veprimi i klientit të shfaqet menjëherë në panel — pikërisht si event-i
 * `order.created` që kalon nga një shërbim në tjetrin.
 */

const KEY = "spdd.state.v1";
const CHANNEL = "spdd.state";

/** Katalogu fillestar — analogu i tabelës `products` në inventory_db. */
export const PRODUCTS = [
  { id: 1, name: 'Laptop 14"', category: "Kompjuterë", price: 500, stock: 8,
    image: "assets/products/laptop.jpg",
    blurb: "Procesor 8-bërthama, 16 GB RAM, SSD 512 GB. Garanci 24 mujore." },
  { id: 2, name: 'Monitor 27"', category: "Periferike", price: 220, stock: 3,
    image: "assets/products/monitor.jpg",
    blurb: "Panel IPS 2560×1440, 100 Hz, mbajtëse e rregullueshme në lartësi." },
  { id: 3, name: "Tastierë mekanike", category: "Periferike", price: 95, stock: 0,
    image: "assets/products/tastiere.jpg",
    blurb: "Switch-e lineare, shtresë alumini, ndriçim RGB. Layout shqip." },
  { id: 4, name: "Maus optik", category: "Periferike", price: 25, stock: 42,
    image: "assets/products/maus.jpg",
    blurb: "Sensor 12 000 DPI, gjashtë butona, ndriçim i anës." },
  { id: 5, name: "Kufje me mikrofon", category: "Audio", price: 65, stock: 14,
    image: "assets/products/kufje.jpg",
    blurb: "Mikrofon me shuarje zhurme, jastëkë të butë, kontroll në kabllo." },
  { id: 6, name: "Disk SSD 1 TB", category: "Ruajtje", price: 110, stock: 6,
    image: "assets/products/ssd.jpg",
    blurb: "I jashtëm, rezistent ndërsa lëviz, lexim deri 1 050 MB/s." },
  { id: 7, name: "Kamerë web HD", category: "Video", price: 48, stock: 1,
    image: "assets/products/kamera.jpg",
    blurb: "1080p, fokus automatik, mikrofon i integruar, mbajtëse universale." },
];

const SEED_ORDERS = [
  { id: 5, customer: "Elira Berisha", email: "elira@example.com", productId: 2,
    productName: 'Monitor 27"', qty: 1, unitPrice: 220, status: "reserved",
    created: "09:12", source: "dyqani" },
  { id: 6, customer: "Genc Dema", email: "genc@example.com", productId: 3,
    productName: "Tastierë mekanike", qty: 2, unitPrice: 95, status: "failed",
    created: "09:31", source: "dyqani" },
];

const SEED_EVENTS = [
  { kind: "warn", label: "Porosia nuk u plotësua", detail: "Porosia 6 — stok i pamjaftueshëm",
    tech: "order.stock_failed · inventory-service", time: "09:31" },
  { kind: "info", label: "Porosi e re e pranuar", detail: "Porosia 6 — 2 × Tastierë mekanike",
    tech: "order.created · order-service", time: "09:31" },
  { kind: "ok", label: "Stoku u rezervua", detail: 'Porosia 5 — 1 × Monitor 27"',
    tech: "order.stock_reserved · inventory-service", time: "09:12" },
];

export function defaultState() {
  return {
    products: PRODUCTS.map((p) => Object.assign({}, p)),
    orders: SEED_ORDERS.map((o) => Object.assign({}, o)),
    events: SEED_EVENTS.map((e) => Object.assign({}, e)),
    nextOrderId: 7,
    session: null,
    rev: 0,
  };
}

/** Lexon gjendjen; kthen atë fillestare nëse nuk ekziston ose është e korruptuar. */
export function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.products) || !Array.isArray(parsed.orders)) return defaultState();
    // Gjendja e ruajtur mban vetëm atë që ndryshon (stoku). Përshkrimi, fotoja
    // dhe kategoria vijnë gjithmonë nga katalogu, që përditësimet e katalogut
    // të mos kërkojnë pastrim të localStorage-it te përdoruesi.
    const merged = Object.assign(defaultState(), parsed);
    merged.products = merged.products.map((p) => {
      const catalog = PRODUCTS.find((c) => c.id === p.id);
      return catalog ? Object.assign({}, catalog, { stock: p.stock }) : p;
    });
    return merged;
  } catch (err) {
    return defaultState();
  }
}

/** Ruan gjendjen dhe njofton faqet e tjera (BroadcastChannel + event storage). */
export function save(state) {
  const next = Object.assign({}, state, { rev: (state.rev || 0) + 1 });
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
    if (typeof BroadcastChannel === "function") {
      const ch = new BroadcastChannel(CHANNEL);
      ch.postMessage({ rev: next.rev });
      ch.close();
    }
  } catch (err) {
    /* kuota e plotë ose modaliteti privat — faqja vazhdon me gjendjen në memorie */
  }
  return next;
}

/** Regjistron një dëgjues për ndryshime nga faqja tjetër. Kthen funksionin e ndalimit. */
export function subscribe(onChange) {
  const onStorage = (e) => { if (e.key === KEY) onChange(load()); };
  window.addEventListener("storage", onStorage);
  let ch = null;
  if (typeof BroadcastChannel === "function") {
    ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = () => onChange(load());
  }
  return () => {
    window.removeEventListener("storage", onStorage);
    if (ch) ch.close();
  };
}

export function stamp() {
  const d = new Date();
  return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
}

/**
 * Kontrolli i stokut — i njëjti rregull që zbaton `inventory-service/app/consumer.py`:
 * rezervimi bëhet vetëm nëse sasia e kërkuar ekziston plotësisht.
 */
export function resolveStock(state, orderId) {
  const order = state.orders.find((o) => o.id === orderId);
  if (!order) return state;
  const product = state.products.find((p) => p.id === order.productId);
  const ok = product && product.stock >= order.qty;
  return Object.assign({}, state, {
    products: ok
      ? state.products.map((p) => (p.id === order.productId ? Object.assign({}, p, { stock: p.stock - order.qty }) : p))
      : state.products,
    orders: state.orders.map((o) => (o.id === orderId ? Object.assign({}, o, { status: ok ? "reserved" : "failed" }) : o)),
    events: [{
      kind: ok ? "ok" : "warn",
      label: ok ? "Stoku u rezervua" : "Porosia nuk u plotësua",
      detail: ok ? "Porosia " + orderId + " — " + order.qty + " × " + order.productName
                 : "Porosia " + orderId + " — stok i pamjaftueshëm",
      tech: (ok ? "order.stock_reserved" : "order.stock_failed") + " · inventory-service (ack)",
      time: stamp(),
    }].concat(state.events).slice(0, 16),
  });
}

/** Kthimi i produktit: stoku rikthehet dhe porosia shënohet e kthyer. */
export function returnOrder(state, orderId) {
  const order = state.orders.find((o) => o.id === orderId);
  if (!order || order.status !== "reserved") return state;
  return Object.assign({}, state, {
    products: state.products.map((p) => (p.id === order.productId ? Object.assign({}, p, { stock: p.stock + order.qty }) : p)),
    orders: state.orders.map((o) => (o.id === orderId ? Object.assign({}, o, { status: "returned" }) : o)),
    events: [{
      kind: "info", label: "Kthim i pranuar",
      detail: "Porosia " + orderId + " — " + order.qty + " × " + order.productName + " u kthye në stok",
      tech: "order.returned · inventory-service", time: stamp(),
    }].concat(state.events).slice(0, 16),
  });
}
