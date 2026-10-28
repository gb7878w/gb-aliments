#!/usr/bin/env python3
"""Extrait les produits vendus en France de l'export CSV d'Open Food Facts (licence ODbL).

Entrée : en.openfoodfacts.org.products.csv.gz (lu en flux, sans le décompresser sur le disque).
Sortie : TSV trié par code-barres, valeurs pour 100 g, utilisable hors ligne par GB Santé.
"""
import csv
import gzip
import sys

csv.field_size_limit(sys.maxsize)

CHAMPS = {
    "kcal": "energy-kcal_100g",
    "prot": "proteins_100g",
    "gluc": "carbohydrates_100g",
    "lip": "fat_100g",
    "sucres": "sugars_100g",
    "fibres": "fiber_100g",
    "satures": "saturated-fat_100g",
    "sel": "salt_100g",
}
# Ajoutées après « scans » : les versions précédentes de GB Santé lisent les 13 premières colonnes.
COLONNES = ["code", "nom", "marque", *CHAMPS.keys(), "portion", "scans", "nutriscore", "nova", "alcool", "categorie"]


def nombre(v: str, maxi: float):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if 0 <= x <= maxi else None


def texte(v: str) -> str:
    return " ".join((v or "").replace("\t", " ").split())[:120]


def format_nombre(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return f"{v:.2f}".rstrip("0").rstrip(".")


def produits(lignes):
    lecteur = csv.DictReader(lignes, delimiter="\t", quoting=csv.QUOTE_NONE)
    for p in lecteur:
        if "en:france" not in (p.get("countries_tags") or ""):
            continue
        code = (p.get("code") or "").strip()
        nom = texte(p.get("product_name_fr") or p.get("product_name"))
        kcal = nombre(p.get(CHAMPS["kcal"]), 950)
        if not code.isdigit() or len(code) < 8 or not nom or kcal is None:
            continue
        valeurs = {k: nombre(p.get(c), 100) for k, c in CHAMPS.items() if k != "kcal"}
        yield {
            "code": code,
            "nom": nom,
            "marque": texte((p.get("brands") or "").split(",")[0]),
            "kcal": kcal,
            **valeurs,
            "portion": nombre(p.get("serving_quantity"), 5000),
            "scans": int(nombre(p.get("unique_scans_n"), 1e9) or 0),
            "nutriscore": nutriscore(p.get("nutriscore_grade")),
            "nova": nova(p.get("nova_group")),
            "alcool": nombre(p.get("alcohol_100g"), 100),
            "categorie": categorie(p.get("pnns_groups_2")),
        }


def categorie(v: str) -> str:
    """Groupe PNNS 2 d'Open Food Facts (une quarantaine de valeurs, ex. « Biscuits and cakes »), vide si inconnu."""
    v = texte(v)
    return "" if v.lower() in ("", "unknown", "en:unknown") else v


def nutriscore(v: str) -> str:
    v = (v or "").strip().lower()
    return v.upper() if v in ("a", "b", "c", "d", "e") else ""


def nova(v: str):
    n = nombre(v, 4)
    return int(n) if n is not None and n >= 1 and n == int(n) else None


def main() -> None:
    entree, sortie = sys.argv[1], sys.argv[2]
    ouvrir = gzip.open if entree.endswith(".gz") else open
    with ouvrir(entree, "rt", encoding="utf-8", errors="replace", newline="") as f:
        liste = {p["code"]: p for p in produits(f)}
    if len(liste) < 10000:
        raise SystemExit(f"Seulement {len(liste)} produits français : format Open Food Facts changé ?")
    with gzip.open(sortie, "wt", encoding="utf-8", newline="\n") as s:
        s.write("\t".join(COLONNES) + "\n")
        for code in sorted(liste):
            p = liste[code]
            s.write("\t".join([p["code"], p["nom"], p["marque"]] + [format_nombre(p.get(k)) for k in COLONNES[3:]]) + "\n")
    print(f"Open Food Facts : {len(liste)} produits français", file=sys.stderr)


if __name__ == "__main__":
    main()
