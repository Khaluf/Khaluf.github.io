"""Fetch Google Scholar metrics and write metrics.json.
Uses SerpAPI if the SERPAPI_KEY secret is set (reliable), otherwise the free `scholarly` library.
Never overwrites metrics.json with empty/invalid data."""
import json, os, sys, datetime

AUTHOR_ID = "Z8lBRZkAAAAJ"
OUT = os.path.join(os.path.dirname(__file__), "..", "metrics.json")


def via_serpapi(key):
    import requests
    r = requests.get("https://serpapi.com/search.json", params={
        "engine": "google_scholar_author", "author_id": AUTHOR_ID, "api_key": key, "hl": "en"}, timeout=60)
    r.raise_for_status()
    table = r.json()["cited_by"]["table"]
    vals = {}
    for row in table:
        (name, d), = row.items()
        since_key = next(k for k in d if k.startswith("since_"))
        vals[name] = (d["all"], d[since_key])
        vals["since"] = int(since_key.split("_")[1])
    ppy, start = {}, 0
    while True:
        a = requests.get("https://serpapi.com/search.json", params={
            "engine": "google_scholar_author", "author_id": AUTHOR_ID, "api_key": key,
            "hl": "en", "num": 100, "start": start}, timeout=60).json().get("articles", [])
        for art in a:
            y = str(art.get("year") or "").strip()
            if y.isdigit():
                ppy[y] = ppy.get(y, 0) + 1
        if len(a) < 100:
            break
        start += 100
    return {"pubs_per_year": dict(sorted(ppy.items())), "citations": vals["citations"][0], "citations_since": vals["citations"][1],
            "h_index": vals["h_index"][0], "h_index_since": vals["h_index"][1],
            "i10_index": vals["i10_index"][0], "i10_index_since": vals["i10_index"][1],
            "since": vals["since"]}


def via_scholarly():
    from scholarly import scholarly
    a = scholarly.fill(scholarly.search_author_id(AUTHOR_ID), sections=["basics", "indices", "publications"])
    ppy = {}
    for p in a.get("publications", []):
        y = str(p.get("bib", {}).get("pub_year") or "").strip()
        if y.isdigit():
            ppy[y] = ppy.get(y, 0) + 1
    return {"pubs_per_year": dict(sorted(ppy.items())), "citations": a["citedby"], "citations_since": a["citedby5y"],
            "h_index": a["hindex"], "h_index_since": a["hindex5y"],
            "i10_index": a["i10index"], "i10_index_since": a["i10index5y"],
            "since": datetime.date.today().year - 5}


def main():
    key = os.environ.get("SERPAPI_KEY")
    try:
        m = via_serpapi(key) if key else via_scholarly()
    except Exception as e:
        print("Fetch failed, keeping previous metrics:", e)
        return 0
    if not m.get("citations"):
        print("Empty result, keeping previous metrics")
        return 0
    m["updated"] = datetime.date.today().isoformat()
    with open(OUT, "w") as f:
        json.dump(m, f, indent=2)
    print("Updated:", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
