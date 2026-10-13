#!/usr/bin/env python3
"""Convert the LILEX HTML cached by li_fetch.py into Markdown files in the repository."""
import datetime
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter

from bs4 import BeautifulSoup, NavigableString, Tag

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = os.path.abspath(os.environ.get("LI_RAW", os.path.join(REPO, "..", "_raw", "li")))
BASE = "https://www.gesetze.li"
RETRIEVED = os.environ.get("LI_RETRIEVED", datetime.date.today().isoformat())

MONTHS = {m: i + 1 for i, m in enumerate(
    ["januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september",
     "oktober", "november", "dezember"])}
MONTHS["jänner"] = 1
MONTHS["maerz"] = 3

PARA = {"ab", "abs", "abge", "zust", "inkr", "inkrfl", "urkund", "geschehen", "folgen", "zent",
        "vorbehaltland", "vorbehalttit", "vom", "htit1", "htit2", "htit3", "unterschrift", "ort",
        "fuerst", "regierung", "sig", "unt", "udat", "gezr", "gez", "dat", "gezf", "inheintrag", "beitritt"}
LIST = {"gbst", "bst1", "bst2", "bst3", "bst4", "ziff", "ziff1", "ziff2", "ziff3", "strich", "strich1",
        "strich2", "roem", "lit", "aufz", "aufz1", "aufz2"}
unknown = Counter()


def slugify(s, maxlen=60):
    s = s.replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen].rstrip("-") or "text"


def parse_date(s):
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zäÄ]+)\s+(\d{4})", s)
    if m and m.group(2).lower() in MONTHS:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


def dmy(s):
    m = re.match(r"\s*(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def doc_type(lr, title):
    if lr.startswith("0"):
        return "treaty"
    if lr == "101":
        return "constitution"
    t = title.lower()
    if re.search(r"gesetzbuch|strafprozessordnung|zivilprozessordnung|jurisdiktionsnorm|exekutionsordnung|"
                 r"personen- und gesellschaftsrecht|^sachenrecht|^strafgesetzbuch", t):
        return "code"
    if t.startswith("verfassungsgesetz") or "hausgesetz" in t:
        return "constitutional_act"
    if "verordnung" in t.split(" vom")[0] or t.startswith("verordnung"):
        return "ordinance"
    if t.startswith("kundmachung"):
        return "announcement"
    if t.startswith("finanzbeschluss") or t.startswith("beschluss") or "landtagsbeschluss" in t:
        return "resolution"
    if "gesetz" in t.split(" vom")[0] or t.startswith("gesetz") or "ordnung" in t.split(" vom")[0]:
        return "act"
    return "other"


def esc(s):
    return s


def inline(node):
    """Render inline content of a node to Markdown text."""
    return inline_nodes(node.children)


def inline_nodes(children):
    out = []
    for c in children:
        if isinstance(c, NavigableString):
            out.append(str(c))
            continue
        if not isinstance(c, Tag):
            continue
        n = c.name
        if n == "div" or n == "table":
            continue  # handled by block renderer
        if n == "a":
            href = c.get("href") or ""
            if href.startswith("#fn"):
                num = c.get_text(strip=True)
                out.append(f"[^{num}]")
            elif href.startswith("#") or not href:
                out.append(inline(c))
            else:
                url = href if href.startswith("http") else BASE + href if href.startswith("/") else href
                txt = inline(c).strip()
                out.append(f"[{txt}]({url})" if txt else "")
        elif n == "sup":
            t = inline(c).strip()
            out.append(f"<sup>{t}</sup>" if t else "")
        elif n == "sub":
            t = inline(c).strip()
            out.append(f"<sub>{t}</sub>" if t else "")
        elif n in ("b", "strong"):
            t = inline(c).strip()
            out.append(f"**{t}**" if t else "")
        elif n in ("i", "em"):
            t = inline(c).strip()
            out.append(f"*{t}*" if t else "")
        elif n == "u":
            out.append(inline(c))
        elif n == "br":
            out.append("\n")
        elif n == "img":
            src = c.get("src") or ""
            src = re.sub(r"^(\.\./)+", "/", src)
            url = src if src.startswith("http") else BASE + (src if src.startswith("/") else "/" + src)
            out.append(f"[Bild: {url}]({url})")
        else:
            out.append(inline(c))
    return "".join(out)


def clean(t):
    t = t.replace("\xa0", " ").replace("\t", " ")
    t = re.sub(r"[ \r\f\v]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    return t.strip()


def para(t):
    t = clean(t)
    if not t:
        return None
    # keep Markdown from turning leading numbers / symbols into lists or headings
    t = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", t)
    t = re.sub(r"^([#>+\-*])(\s)", r"\\\1\2", t)
    return t.replace("\n", "  \n")


def table_md(tb):
    rows = []
    for tr in tb.find_all("tr"):
        if tr.find_parent("table") is not tb:
            continue
        cells = []
        for td in tr.find_all(["td", "th"], recursive=False):
            parts = []
            blocks = td.find_all("div", recursive=True)
            if blocks:
                for d in td.find_all("div"):
                    if d.find("div"):
                        txt = clean(inline(d))
                    else:
                        txt = clean(inline(d))
                    if txt:
                        parts.append(txt)
            else:
                txt = clean(inline(td))
                if txt:
                    parts.append(txt)
            cell = "<br>".join(p.replace("\n", "<br>") for p in parts).replace("|", "\\|")
            cells.append(cell)
            for _ in range(int(td.get("colspan", 1) or 1) - 1):
                cells.append("")
        if any(cells):
            rows.append(cells)
    if not rows:
        return None
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


class Doc:
    def __init__(self, art_level):
        self.out = []
        self.notes = []
        self.pending = {}
        self.art_level = art_level

    def add(self, s):
        if s:
            self.out.append(s)

    def block(self, el):
        for c in el.children:
            if isinstance(c, NavigableString):
                t = para(str(c))
                if t:
                    self.add(t)
                continue
            if not isinstance(c, Tag):
                continue
            if c.name == "table":
                if "Landesgesetzblatt" in c.get_text() and c.find("col") and len(c.find_all("tr")) <= 4:
                    continue  # LGBl header
                t = table_md(c)
                self.add(t)
                continue
            if c.name in ("hr", "script", "style", "link", "meta", "col"):
                continue
            if c.name == "a" and not c.get("href"):
                continue
            if c.name != "div":
                t = para(inline(c))
                if t:
                    self.add(t)
                continue
            self.div(c)

    def div(self, d):
        cls = (d.get("class") or [""])[0]
        if cls == "fntext":
            a = d.find("a")
            num = a.get_text(strip=True) if a else str(len(self.notes) + 1)
            if a:
                a.extract()
            self.notes.append(f"[^{num}]: {clean(inline(d))}")
            return
        m = re.match(r"tit(\d)(m?)$", cls)
        if m or cls in ("tits", "tit1ue", "titpraeambel"):
            lvl = min(6, (int(m.group(1)) if m else 1) + 1)
            txt = clean(inline(d)).replace("\n", " ")
            if m and m.group(2):
                self.pending[lvl] = txt
                return
            label = self.pending.pop(lvl, None)
            if label and txt:
                txt = f"{label} — {txt}"
            elif label:
                txt = label
            if txt:
                self.add("#" * lvl + " " + txt)
            return
        # flush a dangling tit*m label
        for lvl in sorted(self.pending):
            self.add("#" * lvl + " " + self.pending.pop(lvl))
        if cls == "art":
            label = ""
            for c in list(d.children):
                if isinstance(c, Tag) and c.name == "div":
                    break
                if isinstance(c, Tag) and c.name == "a" and not c.get("href"):
                    c.extract()
                    continue
                label += inline_nodes([c])
                c.extract()
            label = clean(label).replace("\n", " ")
            if label:
                h = "#" * min(6, self.art_level)
                self.add(f"{h} {label}" if self.art_level <= 6 else f"**{label}**")
            self.block(d)
            return
        if cls == "sacht":
            t = clean(inline(d)).replace("\n", " ")
            if t:
                self.add(f"*{t}*")
            return
        if cls in ("einl", "") or d.find("div", recursive=False) is not None and cls not in PARA | LIST:
            if cls not in ("einl", ""):
                unknown[cls] += 1
            # text before first child div
            self.block(d)
            return
        if cls not in PARA | LIST:
            unknown[cls] += 1
        # paragraph possibly containing nested list divs
        head = []
        rest = []
        seen_div = False
        for c in d.children:
            if isinstance(c, Tag) and c.name in ("div", "table"):
                seen_div = True
            (rest if seen_div else head).append(c)
        t = para(inline_nodes(head))
        if t:
            self.add(t)
        for c in rest:
            if isinstance(c, Tag) and c.name == "div":
                self.div(c)
            elif isinstance(c, Tag) and c.name == "table":
                self.add(table_md(c))
            else:
                t = para(inline_nodes([c]))
                if t:
                    self.add(t)


def convert(it, page_html, text_html):
    soup = BeautifulSoup(text_html, "lxml")
    body = soup.body or soup
    hdr = body.get_text(" ", strip=True)[:400]
    m = re.search(r"Jahrgang (\d{4})\s+Nr\.\s*([\w.]+)\s+ausgegeben am ([^\n]+?\d{4})", hdr)
    lgbl = f"LGBl. {m.group(1)} Nr. {m.group(2)}" if m else f"LGBl. {it['lgbl']}"
    issued = parse_date(m.group(3)) if m else None
    max_tit = 1
    for d in body.find_all("div", class_=re.compile(r"^tit\d")):
        mm = re.match(r"tit(\d)", d["class"][0])
        max_tit = max(max_tit, int(mm.group(1)) + 1)
    if body.find("div", class_="tits"):
        max_tit = max(max_tit, 2)
    doc = Doc(max_tit + 1)
    doc.block(body)
    # versions
    ver = re.search(r'<option selected="selected" value="(\d+)">([^<]*)</option>', page_html or "")
    vfrom = dmy(ver.group(2)) if ver else None
    title = it["title"]
    date = parse_date(title.split("(")[0]) or issued
    meta = {
        "title": title,
        "identifier": f"LR {it['lr']}",
        "lgbl": lgbl,
        "type": doc_type(it["lr"], title),
        "jurisdiction": "li",
        "language": "de",
    }
    if date:
        meta["date"] = date
    if issued:
        meta["published"] = issued
    if vfrom:
        meta["last_amended"] = vfrom
        meta["version"] = int(ver.group(1))
    meta["status"] = "in_force"
    meta["source"] = f"{BASE}/konso/{it['id']}"
    meta["retrieved"] = RETRIEVED
    fm = ["---"]
    for k, v in meta.items():
        if isinstance(v, int):
            fm.append(f"{k}: {v}")
        elif k in ("date", "published", "last_amended", "retrieved") or k in ("status", "type", "jurisdiction", "language"):
            fm.append(f"{k}: {v}")
        else:
            fm.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
    fm.append("---")
    body_md = "\n\n".join(x for x in doc.out if x)
    parts = ["\n".join(fm), f"# {title}", body_md]
    if doc.notes:
        parts.append("---\n\n" + "\n\n".join(doc.notes))
    return "\n\n".join(p for p in parts if p).rstrip() + "\n"


def rel_path(it, used):
    lr = it["lr"]
    if lr.startswith("0"):
        segs = lr.split(".")
        d = ["0"]
        if len(segs) > 1:
            d.append("0." + segs[1][:1])
            if len(segs[1]) >= 2:
                d.append("0." + segs[1][:2])
            if segs[1] == "110" and len(segs) >= 3:
                # EEA: >1,400 texts (Joint Committee decisions 0.110.0NN.x) -> one more level
                d.append(".".join(segs[:3]))
    else:
        d = [lr[0]]
        head = lr.split(".")[0]
        if len(head) >= 2:
            d.append(head[:2])
    title = it["title"]
    abbr = re.findall(r"[;,(]\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöü\-]*[A-ZÄÖÜ][A-Za-zÄÖÜäöü\-]*)\)\s*$", title)
    slug = slugify(abbr[0]) if abbr and len(abbr[0]) <= 15 else slugify(title, 60)
    name = f"{lr}-{slug}"
    if name in used:
        name = f"{lr}-{it['lgbl']}-{slug}"
    used.add(name)
    return os.path.join(*d, name + ".md")


def main():
    idx = json.load(open(os.path.join(RAW, "index.json")))
    items = idx["items"]
    tdir = os.path.join(RAW, "texts")
    for top in "0123456789":
        p = os.path.join(REPO, top)
        if os.path.isdir(p):
            shutil.rmtree(p)
    used = set()
    stats = Counter()
    missing = []
    for it in sorted(items, key=lambda i: (i["lr"], i["lgbl"])):
        pf = os.path.join(tdir, it["id"] + ".page.html")
        if not os.path.exists(pf):
            missing.append(it)
            continue
        page = open(pf, encoding="utf-8", errors="replace").read()
        ver = re.search(r'<option selected="selected" value="(\d+)">', page)
        tf = os.path.join(tdir, f"{it['id']}.v{ver.group(1) if ver else None}.html")
        if not os.path.exists(tf) or os.path.getsize(tf) == 0:
            missing.append(it)
            continue
        raw = open(tf, "rb").read().decode("utf-8", "replace")
        md = convert(it, page, raw)
        rp = rel_path(it, used)
        fp = os.path.join(REPO, rp)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w", encoding="utf-8").write(md)
        stats[re.search(r"^type: (\S+)", md, re.M).group(1)] += 1
        stats["landesrecht" if not it["lr"].startswith("0") else "staatsvertraege"] += 1
    print(dict(stats), file=sys.stderr)
    print("missing", len(missing), [m["id"] for m in missing[:20]], file=sys.stderr)
    print("unknown classes", unknown.most_common(40), file=sys.stderr)


if __name__ == "__main__":
    main()
