#!/usr/bin/env python3
"""Fetch the in-force consolidated law of Liechtenstein from LILEX (www.gesetze.li).

Step 1: list every text in force (search by LR-number prefix 0..9, "geltend").
Step 2: for each text, fetch the overview page (current version + validity dates) and
        the HTML text of that version.  Everything is cached under _raw/li/.
"""
import concurrent.futures as cf
import datetime
import html
import json
import os
import re
import sys
import time

import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
BASE = "https://www.gesetze.li"
RAW = os.environ.get("LI_RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "li"))
RAW = os.path.abspath(RAW)
HDRS = {"User-Agent": UA}


def get(url, binary=False, tries=5):
    for i in range(tries):
        try:
            # stateless requests (no cookie jar), like a plain command-line client
            r = requests.get(url, headers=HDRS, timeout=120)
            if r.status_code == 200:
                return r.content if binary else r.content.decode("utf-8", "replace")
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr)
        except requests.TooManyRedirects as e:
            print("REDIRECT-LOOP, backing off", url, file=sys.stderr)
            time.sleep(120 * (i + 1))
            continue
        except requests.RequestException as e:
            print("ERR", e, url, file=sys.stderr)
        time.sleep(5 * (i + 1))
    print("FAILED", url, file=sys.stderr)
    return None


def list_texts(date):
    out = {}
    for prefix in "0123456789":
        url = (f"{BASE}/konso/suche?search_text=&search_loc=&lrnr={prefix}&lgblid_von="
               f"&observe_date={date}&compl_list=1&rechts_gebiet=0")
        t = get(url)
        n = re.search(r"Es wurden <span>(\d+)</span>", t)
        rows = re.findall(r"<tr>\s*<td>([\d.]+)</td>\s*<td[^>]*>([^<]*)</td>\s*<td>\s*"
                          r"<a href=\"/konso/(\d+)\?[^\"]*\">(.*?)</a>", t, re.S)
        print(prefix, n and n.group(1), len(rows), file=sys.stderr)
        for lgbl, lr, lid, title in rows:
            if not lr.strip().startswith(prefix):
                continue
            out[lid] = {"lgbl": lgbl, "lr": lr.strip(), "id": lid,
                        "title": html.unescape(re.sub(r"\s+", " ", title)).strip()}
        time.sleep(1)
    return list(out.values())


def fetch_one(it):
    d = os.path.join(RAW, "texts")
    meta_f = os.path.join(d, it["id"] + ".page.html")
    if not os.path.exists(meta_f):
        t = get(f"{BASE}/konso/{it['id']}")
        if not t:
            return it["id"]
        open(meta_f, "w").write(t)
        time.sleep(0.5)
    page = open(meta_f).read()
    m = re.search(r'<option selected="selected" value="(\d+)">([^<]*)</option>', page)
    ver = m.group(1) if m else None
    txt_f = os.path.join(d, f"{it['id']}.v{ver}.html")
    if not os.path.exists(txt_f):
        url = f"{BASE}/konso/html/{it['id']}" + (f"?version={ver}" if ver else "")
        t = get(url, binary=True)
        if not t:
            return it["id"]
        open(txt_f, "wb").write(t)
        time.sleep(0.5)
    return it["id"]


def main():
    os.makedirs(os.path.join(RAW, "texts"), exist_ok=True)
    date = datetime.date.today().strftime("%d.%m.%Y")
    idx = os.path.join(RAW, "index.json")
    if not os.path.exists(idx):
        items = list_texts(date)
        json.dump({"date": date, "items": items}, open(idx, "w"), ensure_ascii=False, indent=0)
    items = json.load(open(idx))["items"]
    print(len(items), "texts", file=sys.stderr)
    done = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for _ in ex.map(fetch_one, items):
            done += 1
            if done % 200 == 0:
                print("fetched", done, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
