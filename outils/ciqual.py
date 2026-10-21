#!/usr/bin/env python3
"""Prépare la table CIQUAL de l'ANSES (composition nutritionnelle des aliments) pour GB Santé.

Entrée : l'archive ZIP « XML » publiée par l'ANSES (fichiers alim_*, alim_grp_*, compo_*).
Sortie : un fichier TSV compact, une ligne par aliment, valeurs pour 100 g.

Les fichiers XML de l'ANSES ne sont pas toujours du XML valide (teneurs du type « < 0,5 »),
on lit donc chaque enregistrement avec une expression régulière plutôt qu'avec un parseur XML.
"""
import argparse
import io
import re
import sys
import unicodedata
import zipfile

# Codes des constituants CIQUAL (identiques dans les tables 2016, 2017, 2020).
CONSTITUANTS = {
    "kcal": "328",       # Énergie, Règlement UE N° 1169/2011 (kcal/100 g)
    "prot": "25000",     # Protéines, N x facteur de Jones (g/100 g)
    "gluc": "31000",     # Glucides (g/100 g)
    "lip": "40000",      # Lipides (g/100 g)
    "sucres": "32000",   # Sucres (g/100 g)
    "fibres": "34100",   # Fibres alimentaires (g/100 g)
    "satures": "40302",  # AG saturés (g/100 g)
    "sel": "10004",      # Sel chlorure de sodium (g/100 g)
}
# Vitamines, minéraux et alcool (pour 100 g). Les codes sont ceux de la table 2020 ; on les
# retrouve aussi par le nom du constituant (fichier const_*), au cas où l'ANSES les renumérote.
MICROS = {
    "fer": ("10260", r"^fer\b"),                        # mg
    "calcium": ("10200", r"^calcium\b"),                # mg
    "magnesium": ("10120", r"^magnesium\b"),            # mg
    "potassium": ("10190", r"^potassium\b"),            # mg
    "zinc": ("10300", r"^zinc\b"),                      # mg
    "iode": ("10530", r"^iode\b"),                      # µg
    "vitd": ("52100", r"^vitamine d\s*\("),            # µg
    "vitc": ("55100", r"^vitamine c\b"),                # mg
    "b12": ("56600", r"^vitamine b12\b"),               # µg
    "b9": ("56700", r"^vitamine b9\b|folates totaux"),  # µg
    "alcool": ("60000", r"^alcool\b"),                  # g
}
COLONNES = ["code", "nom", "groupe", *CONSTITUANTS.keys(), *MICROS.keys()]
# Si l'énergie « règlement UE » manque : énergie selon les facteurs de Jones (kcal), puis kJ convertis.
SECOURS_ENERGIE = {"333": "kcal_jones", "327": "kj_ue", "332": "kj_jones", "60000": "alcool", "65000": "acides_org"}

ENREG = re.compile(r"<(ALIM|ALIM_GRP|COMPO|CONST)>(.*?)</\1>", re.S)
CHAMP = re.compile(r"<(\w+)>(.*?)</\1>", re.S)
VIDE = re.compile(r"<(\w+)\s*/>")


def decoder(octets: bytes) -> str:
    entete = octets[:200].decode("ascii", "ignore")
    m = re.search(r'encoding="([^"]+)"', entete)
    enc = m.group(1) if m else "windows-1252"
    try:
        return octets.decode(enc)
    except (LookupError, UnicodeDecodeError):
        return octets.decode("windows-1252", "replace")


def enregistrements(texte: str, balise: str):
    for m in ENREG.finditer(texte):
        if m.group(1) != balise:
            continue
        corps = VIDE.sub("", m.group(2))
        yield {k: nettoyer(v) for k, v in CHAMP.findall(corps)}


def nettoyer(v: str) -> str:
    v = v.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'").replace("&quot;", '"')
    return " ".join(v.split())


def teneur(v: str):
    """« 12,5 » -> 12.5 ; « traces » ou « < 0,5 » -> 0 ; « - » ou vide -> inconnu."""
    v = (v or "").strip().lower()
    if not v or v == "-":
        return None
    if v.startswith("trace") or v.startswith("<"):
        return 0.0
    try:
        return float(v.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def fichier(zf: zipfile.ZipFile, prefixe: str) -> str:
    noms = [n for n in zf.namelist() if re.match(rf"(.*/)?{prefixe}_\d", n.lower()) and n.lower().endswith(".xml")]
    if not noms:
        raise SystemExit(f"Fichier {prefixe}_*.xml introuvable dans l'archive : {zf.namelist()}")
    return decoder(zf.read(sorted(noms)[-1]))


def simplifier(v: str) -> str:
    v = unicodedata.normalize("NFD", v.lower())
    return "".join(c for c in v if not unicodedata.combining(c))


def codes_micros(zf: zipfile.ZipFile) -> dict[str, str]:
    """Code de chaque vitamine ou minéral : d'après le nom dans const_*.xml, sinon le code de 2020."""
    codes = {cle: code for cle, (code, _) in MICROS.items()}
    try:
        texte = fichier(zf, "const")
    except SystemExit:
        return codes
    trouves = {}
    for c in enregistrements(texte, "CONST"):
        nom = simplifier(c.get("const_nom_fr", ""))
        for cle, (_, motif) in MICROS.items():
            if cle not in trouves and re.search(motif, nom):
                trouves[cle] = c.get("const_code", "")
    for cle, code in trouves.items():
        if code and code != codes[cle]:
            print(f"{cle} : code {code} d'après son nom (au lieu de {codes[cle]})", file=sys.stderr)
            codes[cle] = code
    return codes


def preparer(archive: bytes) -> tuple[list[dict], str]:
    zf = zipfile.ZipFile(io.BytesIO(archive))
    version = next((m.group(1) for n in zf.namelist() if (m := re.search(r"compo_(\d{4}_\d{2}_\d{2})", n))), "inconnue")
    groupes = {}
    for g in enregistrements(fichier(zf, "alim_grp"), "ALIM_GRP"):
        groupes[g.get("alim_grp_code", "")] = g.get("alim_grp_nom_fr", "")
    aliments = {}
    for a in enregistrements(fichier(zf, "alim"), "ALIM"):
        code = a.get("alim_code", "")
        nom = a.get("alim_nom_fr", "")
        if code and nom:
            aliments[code] = {"code": code, "nom": nom, "groupe": groupes.get(a.get("alim_grp_code", ""), "")}
    micros = codes_micros(zf)
    codes = {v: k for k, v in CONSTITUANTS.items()} | SECOURS_ENERGIE
    # L'alcool sert aussi au calcul de l'énergie de secours : même clé.
    codes |= {code: cle for cle, code in micros.items()}
    for c in enregistrements(fichier(zf, "compo"), "COMPO"):
        a = aliments.get(c.get("alim_code", ""))
        cle = codes.get(c.get("const_code", ""))
        if a is not None and cle is not None:
            a[cle] = teneur(c.get("teneur", ""))
    for a in aliments.values():
        if a.get("kcal") is None:
            if a.get("kcal_jones") is not None:
                a["kcal"] = a["kcal_jones"]
            elif a.get("kj_ue") is not None:
                a["kcal"] = a["kj_ue"] / 4.184
            elif a.get("kj_jones") is not None:
                a["kcal"] = a["kj_jones"] / 4.184
            elif all(a.get(k) is not None for k in ("prot", "gluc", "lip")):
                # Énergie absente de la table (cas de la pomme crue en 2020) : on la calcule avec les
                # coefficients du règlement UE 1169/2011 (4, 4, 9, fibres 2, alcool 7, acides organiques 3).
                a["kcal"] = round(
                    4 * a["prot"] + 4 * a["gluc"] + 9 * a["lip"] + 2 * (a.get("fibres") or 0)
                    + 7 * (a.get("alcool") or 0) + 3 * (a.get("acides_org") or 0),
                    1,
                )
    sans = [a["nom"] for a in aliments.values() if a.get("kcal") is None]
    if sans:
        print(f"{len(sans)} aliments sans énergie écartés, par exemple : {sans[:5]}", file=sys.stderr)
    lignes = [a for a in aliments.values() if a.get("kcal") is not None]
    lignes.sort(key=lambda a: a["nom"].lower())
    return lignes, version


def format_nombre(v) -> str:
    if v is None:
        return ""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def ecrire(lignes: list[dict], version: str, sortie) -> None:
    sortie.write(f"#ciqual\t{version}\n")
    sortie.write("\t".join(COLONNES) + "\n")
    for a in lignes:
        valeurs = [a["code"], a["nom"].replace("\t", " "), a["groupe"].replace("\t", " ")]
        valeurs += [format_nombre(a.get(k)) for k in CONSTITUANTS]
        valeurs += [format_nombre(a.get(k)) for k in MICROS]
        sortie.write("\t".join(valeurs) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", help="ZIP XML de la table CIQUAL")
    p.add_argument("sortie", help="fichier TSV à écrire")
    args = p.parse_args()
    with open(args.archive, "rb") as f:
        lignes, version = preparer(f.read())
    if len(lignes) < 1000:
        raise SystemExit(f"Seulement {len(lignes)} aliments lus : format CIQUAL changé ?")
    with open(args.sortie, "w", encoding="utf-8", newline="\n") as s:
        ecrire(lignes, version, s)
    print(f"CIQUAL {version} : {len(lignes)} aliments", file=sys.stderr)
    for k in MICROS:
        print(f"  {k} : {sum(1 for a in lignes if a.get(k) is not None)} aliments renseignés", file=sys.stderr)


if __name__ == "__main__":
    main()
