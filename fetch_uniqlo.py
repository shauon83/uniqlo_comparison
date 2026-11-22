"""Fetch the full Uniqlo JP + KR online catalogs and embed them into uniqlo.html.

Usage:  python fetch_uniqlo.py          (re-run any time to refresh prices)
        python fetch_uniqlo.py --embed-only   (rebuild html from uniqlo_raw.json)
        add --suggest to write match_candidates.tsv (name translation + photo) for new review
Products are matched across countries by productId (e.g. E469740-000), plus the
human-reviewed pairs in uniqlo_matches.json for items that use different codes per country.
"""
import json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).parent
HTML = HERE / "uniqlo.html"
RAW = HERE / "uniqlo_raw.json"
STORES = {"jp": "https://www.uniqlo.com/jp/api/commerce/v5/ja/products",
          "kr": "https://www.uniqlo.com/kr/api/commerce/v5/ko/products"}
PAGE, DELAY = 100, 0.6  # polite: sequential requests with a pause


def get(store, **params):
    url = STORES[store] + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            time.sleep(DELAY)
            if d.get("status") != "ok":
                raise RuntimeError(d.get("error"))
            return d["result"]
        except Exception as e:  # retry transient failures, then give up loudly
            if attempt == 2:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(3)


def item_info(store, it, gender, klass):
    main = (it.get("images") or {}).get("main") or {}
    rep = it.get("representativeColorDisplayCode")
    img = (main.get(rep) or next(iter(main.values()), {})).get("image", "")
    p = it.get("prices") or {}
    base = (p.get("base") or {}).get("value")
    promo = (p.get("promo") or {}).get("value")
    flags = [f.get("name", "") for f in ((it.get("representative") or {}).get("flags") or {}).get("priceFlags", [])]
    lang = "ja" if store == "jp" else "ko"
    return {"id": it["productId"], "name": it.get("name", ""), "gender": gender, "class": klass,
            "base": base, "sale": promo if promo is not None else base, "image": img,
            "rating": (it.get("rating") or {}).get("average"), "reviews": (it.get("rating") or {}).get("count"),
            "flags": [f for f in flags if f],
            "url": f"https://www.uniqlo.com/{store}/{lang}/products/{it['productId']}/{it.get('priceGroup', '00')}"}


def fetch_store(store):
    first = get(store, q="ヒートテック" if store == "jp" else "히트텍", limit=1, offset=0)
    genders = first["aggregations"]["tree"]["genders"]
    out = {}
    for g in genders:
        tree = get(store, path=g["id"], limit=1, offset=0)["aggregations"]["tree"]
        # class-level first (gives the category); then the plain gender list catches leftovers
        for klass in tree["classes"] + [None]:
            path = f"{g['id']},{klass['id']}" if klass else str(g["id"])
            offset = 0
            while True:
                res = get(store, path=path, limit=PAGE, offset=offset)
                for it in res["items"]:
                    if it["productId"] not in out:
                        out[it["productId"]] = item_info(store, it, g["name"].title(), klass["name"] if klass else "")
                offset += PAGE
                if offset >= res["pagination"]["total"] or not res["items"]:
                    break
            print(f"  {store} {g['name']:<6} {klass['name'] if klass else '(all)'}: {len(out)} total", flush=True)
    return out


HASH_CACHE = HERE / "uniqlo_imghash.json"


def dhash(url, cache):
    """64-bit difference hash of a small grayscale thumbnail; cached by URL."""
    if url not in cache:
        from io import BytesIO
        from PIL import Image
        req = urllib.request.Request(url + "?width=150", headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                im = Image.open(BytesIO(r.read())).convert("L").resize((9, 8), Image.LANCZOS)
            px = list(im.getdata())
            cache[url] = sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])
        except Exception as e:
            print("  image skipped:", url, e)
            cache[url] = None
        time.sleep(0.1)
    return cache[url]


def code_matches(jp, kr):
    # same product sometimes carries a -001 suffix in JP but -000 in KR
    return {pid: (pid if pid in kr else pid[:-3] + "000") for pid in jp if pid in kr or pid[:-3] + "000" in kr}


def suggest(jp, kr, reviewed):
    """Write candidate pairs (name translation score + photo distance) for human review into uniqlo_matches.json.
    shortcut: photo hashes use only the representative colour, which often differs by country, so they rank but never decide."""
    from name_match import similarity
    code = code_matches(jp, kr)
    used = set(code.values()) | set(reviewed.values())
    jp_only = [j for pid, j in jp.items() if pid not in code and pid not in reviewed and j["image"]]
    kr_only = [k for pid, k in kr.items() if pid not in used and k["image"] and not k["name"].startswith("GU")]
    cache = json.loads(HASH_CACHE.read_text()) if HASH_CACHE.exists() else {}
    rows = []
    for j in jp_only:
        for k in kr_only:
            if j["gender"] != k["gender"] or (s := similarity(j["name"], k["name"])) < 0.6:
                continue
            hj, hk = dhash(j["image"], cache), dhash(k["image"], cache)
            d = bin(hj ^ hk).count("1") if hj is not None and hk is not None else 64
            rows.append((-s, d, j["id"], j["name"], k["id"], k["name"]))
    HASH_CACHE.write_text(json.dumps(cache))
    rows.sort()
    out = HERE / "match_candidates.tsv"
    out.write_text("".join(f"{-s:.2f}\t{d}\t{a}\t{an}\t{b}\t{bn}\n" for s, d, a, an, b, bn in rows), encoding="utf-8")
    print(f"{len(rows)} candidates -> {out.name}; add confirmed pairs to {MATCHES.name}")


MATCHES = HERE / "uniqlo_matches.json"


def build(jp, kr):
    code_match = code_matches(jp, kr)
    reviewed = json.loads(MATCHES.read_text(encoding="utf-8"))["pairs"] if MATCHES.exists() else {}
    reviewed = {a: b for a, b in reviewed.items() if a in jp and b in kr and a not in code_match}
    print(f"matched by code {len(code_match)}, by reviewed name/photo {len(reviewed)}")
    products = []
    for pid, j in jp.items():
        kid = code_match.get(pid) or reviewed.get(pid)
        k = kr.get(kid) if kid else None
        products.append({
            "id": pid, "name_jp": j["name"], "name_kr": k["name"] if k else "",
            "gender": j["gender"], "class_jp": j["class"], "class_kr": k["class"] if k else "",
            "image": j["image"] or (k or {}).get("image", ""),
            "jp_price": j["base"], "jp_sale_price": j["sale"], "jp_link": j["url"], "jp_flags": j["flags"],
            "kr_price": k["base"] if k else None, "kr_sale_price": k["sale"] if k else None,
            "kr_link": k["url"] if k else None, "kr_flags": k["flags"] if k else [],
            "rating": j["rating"], "reviews": j["reviews"], "is_jp_exclusive": k is None,
            "kr_id": kid if k else None, "match": ("code" if pid in code_match else "reviewed") if k else None,
        })
    return [p for p in products if p["jp_price"]]


def embed(products, fetched_at, stats):
    html = HTML.read_text(encoding="utf-8")
    block = ("/*DATA-START*/\nconst FETCHED_AT = " + json.dumps(fetched_at) + ";\nconst STATS = " + json.dumps(stats)
             + ";\nconst PRODUCTS = "
             + json.dumps(products, ensure_ascii=False, separators=(",", ":")) + ";\n/*DATA-END*/")
    new, n = re.subn(r"/\*DATA-START\*/.*?/\*DATA-END\*/", lambda _: block, html, flags=re.S)
    if n != 1:
        sys.exit("uniqlo.html is missing the /*DATA-START*/ ... /*DATA-END*/ markers")
    HTML.write_text(new, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    if "--embed-only" in sys.argv:
        raw = json.loads(RAW.read_text(encoding="utf-8"))
    else:
        raw = {"fetched_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST"),
               "jp": fetch_store("jp"), "kr": fetch_store("kr")}
        RAW.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    if "--suggest" in sys.argv:
        suggest(raw["jp"], raw["kr"], json.loads(MATCHES.read_text(encoding="utf-8"))["pairs"] if MATCHES.exists() else {})
    products = build(raw["jp"], raw["kr"])
    assert products and len({p["id"] for p in products}) == len(products), "empty or duplicate catalog"
    matched_kr = {p["kr_id"] for p in products if p["kr_id"]}
    same = sum(not p["is_jp_exclusive"] for p in products)
    # counted on the JP side (JP code basis); several JP variants may map to one KR product
    stats = {"jp": len(products), "kr": len(raw["kr"]), "common": same, "jp_only": len(products) - same,
             "kr_only": len(raw["kr"]) - len(matched_kr), "kr_matched": len(matched_kr)}
    if "--no-embed" not in sys.argv:
        embed(products, raw["fetched_at"], stats)
    print(stats)
