"""Essai de outils/openfoodfacts.py sur quelques lignes au format de l'export CSV."""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import openfoodfacts  # noqa: E402

ENTETE = "code\tproduct_name\tproduct_name_fr\tbrands\tcountries_tags\tenergy-kcal_100g\tproteins_100g\tcarbohydrates_100g\tfat_100g\tsugars_100g\tfiber_100g\tsaturated-fat_100g\tsalt_100g\tserving_quantity\tunique_scans_n\tnutriscore_grade\tnova_group\talcohol_100g\tpnns_groups_2"
LIGNES = [
    "3017620422003\tNutella\tNutella\tFerrero,Nutella\ten:france,en:germany\t539\t6.3\t57.5\t30.9\t56.3\t\t10.6\t0.107\t15\t4000\te\t4\t\tChocolate products",
    "5000112637922\tCoca-Cola\t\tCoca-Cola\ten:united-kingdom\t42\t0\t10.6\t0\t10.6\t0\t0\t0\t330\t10",
    "123\tCode trop court\t\t\ten:france\t100\t1\t1\t1\t1\t1\t1\t1\t\t",
    "3270190207924\tSans énergie\t\t\ten:france\t\t1\t1\t1\t1\t1\t1\t1\t\t",
]


class TestOpenFoodFacts(unittest.TestCase):
    def test_produits(self):
        liste = list(openfoodfacts.produits(io.StringIO("\n".join([ENTETE, *LIGNES]) + "\n")))
        self.assertEqual(len(liste), 1)
        p = liste[0]
        self.assertEqual(p["code"], "3017620422003")
        self.assertEqual(p["marque"], "Ferrero")
        self.assertEqual(p["kcal"], 539)
        self.assertIsNone(p["fibres"])
        self.assertEqual(p["portion"], 15)
        self.assertEqual(p["scans"], 4000)
        self.assertEqual(p["nutriscore"], "E")
        self.assertEqual(p["nova"], 4)
        self.assertIsNone(p["alcool"])
        self.assertEqual(p["categorie"], "Chocolate products")
        self.assertEqual(openfoodfacts.categorie("unknown"), "")
        self.assertEqual(openfoodfacts.nutriscore("unknown"), "")
        self.assertIsNone(openfoodfacts.nova("5"))


if __name__ == "__main__":
    unittest.main()
