// node test.mjs — runs the worker against an in-memory fake of the GitHub contents API
import assert from "node:assert/strict";
import worker, { normId, cleanItems } from "./worker.js";

assert.equal(normId("  SungEun "), "sungeun");
assert.equal(normId(""), null);
assert.equal(normId("x".repeat(41)), null);
assert.deepEqual(cleanItems([{ id: "E469871-000", qty: 2 }]), [{ id: "E469871-000", qty: 2, color: "", size: "" }]);
assert.deepEqual(cleanItems([{ id: "E469871-000", qty: 1, color: "09", size: "M" }]), [{ id: "E469871-000", qty: 1, color: "09", size: "M" }]);
assert.equal(cleanItems([{ id: "E469871-000", qty: 1, color: "<b>" }]), null);
assert.equal(cleanItems([{ id: "E469871-000", qty: 1, size: "x".repeat(21) }]), null);
assert.equal(cleanItems([{ id: "<img>", qty: 1 }]), null);
assert.equal(cleanItems([{ id: "E469871-000", qty: 0 }]), null);
assert.equal(cleanItems([]), null);

let file = null, sha = 0, conflictOnce = true;
globalThis.fetch = async (url, init = {}) => {
  if (!init.method) return file ? new Response(JSON.stringify({ content: file, sha: String(sha) })) : new Response("{}", { status: 404 });
  const b = JSON.parse(init.body);
  if (conflictOnce && file) { conflictOnce = false; sha++; return new Response("{}", { status: 409 }); }
  if (file && b.sha !== String(sha)) return new Response("{}", { status: 409 });
  assert.equal(b.branch, "carts");
  file = b.content; sha++;
  return new Response("{}", { status: 200 });
};
const env = { REPO: "o/r", BRANCH: "carts", FILE: "carts.json", GITHUB_TOKEN: "t" };
const call = (path, body) => worker.fetch(new Request("https://w" + path, body ? { method: "POST", body: JSON.stringify(body) } : {}), env);

assert.equal((await call("/load?id=성은")).status, 404);
assert.equal((await call("/save", { id: "성은", items: [{ id: "E469871-000", qty: 2 }] })).status, 200);
assert.equal((await call("/save", { id: "other", items: [{ id: "E479224-000", qty: 1 }] })).status, 200); // hits one 409, retries
assert.equal((await call("/save", { id: "bad", items: [{ id: "x", qty: 1 }] })).status, 400);
const r = await call("/load?id=%20성은%20");
assert.equal(r.status, 200);
assert.deepEqual((await r.json()).items, [{ id: "E469871-000", qty: 2, color: "", size: "" }]);
const stored = new TextDecoder().decode(Uint8Array.from(atob(file), (c) => c.charCodeAt(0)));
assert.ok(!stored.includes("성은") && Object.keys(JSON.parse(stored)).length === 2, "only hashes stored");
console.log("worker tests OK");
