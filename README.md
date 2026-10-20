# gb-aliments

Base d'aliments hors ligne de **GB Santé**, préparée chaque mois par GitHub Actions à partir de sources ouvertes :

- **Table CIQUAL** de l'ANSES (composition nutritionnelle de plus de 3 000 aliments courants), Licence Ouverte Etalab.
- **Open Food Facts** : les produits vendus en France (code-barres, marque, valeurs pour 100 g), licence ODbL.

Rien n'est collecté sur l'utilisateur : ce dépôt est public pour que GB Santé télécharge la base sans compte ni jeton, puis la garde sur le téléphone.

## Fichiers publiés (release « derniere-base »)

| Fichier | Contenu |
|---|---|
| `ciqual.tsv` | une ligne par aliment : code, nom, groupe, kcal, protéines, glucides, lipides, sucres, fibres, AG saturés, sel (pour 100 g) |
| `off-fr.tsv.gz` | une ligne par produit, triée par code-barres : code, nom, marque, mêmes valeurs, portion (g), nombre de scans |
| `manifeste.json` | date, version CIQUAL, taille et empreinte SHA-256 de chaque fichier |

## Mise à jour

Automatique le 3 de chaque mois, ou à la main : onglet **Actions** > « Préparer la base d'aliments » > **Run workflow**.
Les scripts sont dans `outils/` avec leurs tests (`python3 -m unittest discover -s outils`).
