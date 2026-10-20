#!/usr/bin/env python3
"""Télécharge la dernière archive XML de la table CIQUAL (ANSES), trouvée via data.gouv.fr."""
import json
import sys
import urllib.request

API = "https://www.data.gouv.fr/api/1/datasets/?q=ciqual&page_size=20"
# Si data.gouv.fr ne répond pas : la table 2020, toujours en ligne chez l'ANSES.
SECOURS = "https://ciqual.anses.fr/cms/sites/default/files/inline-files/XML_2020_07_07.zip"
AGENT = {"User-Agent": "gb-aliments (https://github.com/gb7878w/gb-aliments)"}


def lire(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120) as r:
        return r.read()


def candidats():
    donnees = json.loads(lire(API))
    for jeu in donnees.get("data", []):
        if "ciqual" not in (jeu.get("title") or "").lower():
            continue
        for r in jeu.get("resources", []):
            texte = f"{r.get('title', '')} {r.get('url', '')}".lower()
            if "xml" in texte and (r.get("format", "").lower() == "zip" or r.get("url", "").lower().endswith(".zip")):
                yield r.get("last_modified") or r.get("created_at") or "", r["url"]


def main() -> None:
    sortie = sys.argv[1]
    urls = []
    try:
        urls = [u for _, u in sorted(candidats(), reverse=True)]
    except Exception as e:  # noqa: BLE001
        print(f"data.gouv.fr injoignable ({e}), on prend la table 2020", file=sys.stderr)
    urls.append(SECOURS)
    for url in urls:
        try:
            octets = lire(url)
        except Exception as e:  # noqa: BLE001
            print(f"Échec {url} : {e}", file=sys.stderr)
            continue
        if octets[:2] == b"PK":
            with open(sortie, "wb") as f:
                f.write(octets)
            print(f"CIQUAL téléchargée depuis {url} ({len(octets)} octets)", file=sys.stderr)
            return
        print(f"{url} n'est pas une archive ZIP", file=sys.stderr)
    raise SystemExit("Aucune archive CIQUAL téléchargée")


if __name__ == "__main__":
    main()
