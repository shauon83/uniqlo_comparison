// Relay between the public page and carts.json on the repo's "carts" branch.
// The GitHub token lives only here (wrangler secret), never in the page.
const MAX_ID = 40, MAX_ITEMS = 200, MAX_QTY = 99, MAX_ENTRIES = 2000, MAX_BYTES = 900_000;
const PID = /^E\d{6}-\d{3}$/, COLOR = /^(\d{2,3})?$/, MAX_SIZE = 20;
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" } });

// IDs are case/space-insensitive so people can recall them; only a salted hash is stored.
export function normId(id) {
  const s = typeof id === "string" ? id.normalize("NFC").trim().toLowerCase() : "";
  return s && s.length <= MAX_ID ? s : null;
}

export function cleanItems(items) {
  if (!Array.isArray(items) || !items.length || items.length > MAX_ITEMS) return null;
  const out = [];
  for (const it of items) {
    if (!it || typeof it.id !== "string" || !PID.test(it.id) || !Number.isInteger(it.qty) || it.qty < 1 || it.qty > MAX_QTY) return null;
    // color/size are optional (older carts have none); "" means not chosen yet
    const color = it.color ?? "", size = it.size ?? "";
    if (typeof color !== "string" || !COLOR.test(color) || typeof size !== "string" || size.length > MAX_SIZE) return null;
    out.push({ id: it.id, qty: it.qty, color, size });
  }
  return out;
}

export async function hashId(id) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("uniqlo-cart:" + id));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${env.REPO}/contents/${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json", "User-Agent": "uniqlo-cart-worker" },
  });
}

async function readCarts(env) {
  const r = await gh(env, `${env.FILE}?ref=${env.BRANCH}`);
  if (r.status === 404) return { data: {}, sha: undefined };
  if (!r.ok) throw new Error(`GitHub 읽기 실패 (${r.status})`);
  const f = await r.json();
  const bytes = Uint8Array.from(atob(f.content.replace(/\n/g, "")), (c) => c.charCodeAt(0));
  return { data: JSON.parse(new TextDecoder().decode(bytes)), sha: f.sha };
}

async function writeCarts(env, data, sha) {
  const bytes = new TextEncoder().encode(JSON.stringify(data, null, 1));
  if (bytes.length > MAX_BYTES) return 413;
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  const r = await gh(env, env.FILE, {
    method: "PUT",
    body: JSON.stringify({ message: "save cart", content: btoa(bin), sha, branch: env.BRANCH }),
  });
  return r.status;
}

async function save(req, env) {
  let body;
  try { body = await req.json(); } catch { return json({ error: "요청 형식이 잘못되었습니다." }, 400); }
  const id = normId(body?.id), items = cleanItems(body?.items);
  if (!id) return json({ error: `아이디는 1~${MAX_ID}자로 입력해 주세요.` }, 400);
  if (!items) return json({ error: `장바구니가 비었거나 형식이 잘못되었습니다. (최대 ${MAX_ITEMS}종, 종류당 ${MAX_QTY}개)` }, 400);
  const key = await hashId(id);
  for (let attempt = 0; attempt < 3; attempt++) { // retry when another save changed the file first
    const { data, sha } = await readCarts(env);
    if (!data[key] && Object.keys(data).length >= MAX_ENTRIES) return json({ error: "저장 공간이 가득 찼습니다." }, 507);
    data[key] = { items, saved_at: new Date().toISOString() };
    const status = await writeCarts(env, data, sha);
    if (status === 200 || status === 201) return json({ ok: true, saved_at: data[key].saved_at });
    if (status === 413) return json({ error: "저장 공간이 가득 찼습니다." }, 507);
    if (status !== 409 && status !== 422) return json({ error: `GitHub 저장 실패 (${status})` }, 502);
  }
  return json({ error: "동시에 저장하는 사람이 많습니다. 잠시 후 다시 시도해 주세요." }, 503);
}

async function load(url, env) {
  const id = normId(url.searchParams.get("id"));
  if (!id) return json({ error: "아이디를 입력해 주세요." }, 400);
  const { data } = await readCarts(env);
  const entry = data[await hashId(id)];
  return entry ? json(entry) : json({ error: "이 아이디로 저장된 장바구니가 없습니다." }, 404);
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    const url = new URL(req.url);
    try {
      if (req.method === "POST" && url.pathname === "/save") return await save(req, env);
      if (req.method === "GET" && url.pathname === "/load") return await load(url, env);
      return json({ error: "없는 주소입니다." }, 404);
    } catch (e) {
      return json({ error: e.message || "서버 오류" }, 500);
    }
  },
};
