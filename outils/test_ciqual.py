"""Essai de outils/ciqual.py sur une mini-archive au format de l'ANSES."""
import io
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
import ciqual  # noqa: E402

ALIM = """<?xml version="1.0" encoding="windows-1252"?>
<TABLE>
<ALIM>
<alim_code> 13050 </alim_code>
<alim_nom_fr> Pomme, crue, pulpe et peau </alim_nom_fr>
<alim_grp_code> 02 </alim_grp_code>
<alim_ssgrp_code> 0204 </alim_ssgrp_code>
<alim_ssssgrp_code/>
</ALIM>
<ALIM>
<alim_code> 2000 </alim_code>
<alim_nom_fr> Riz blanc, cuit </alim_nom_fr>
<alim_grp_code> 02 </alim_grp_code>
</ALIM>
<ALIM>
<alim_code> 9999 </alim_code>
<alim_nom_fr> Aliment sans énergie </alim_nom_fr>
<alim_grp_code> 02 </alim_grp_code>
</ALIM>
</TABLE>
""".encode("windows-1252")

GRP = """<?xml version="1.0" encoding="windows-1252"?>
<TABLE><ALIM_GRP><alim_grp_code> 02 </alim_grp_code><alim_grp_nom_fr> fruits, légumes, légumineuses et oléagineux </alim_grp_nom_fr></ALIM_GRP></TABLE>
""".encode("windows-1252")

COMPO = """<?xml version="1.0" encoding="windows-1252"?>
<TABLE>
<COMPO><alim_code> 13050 </alim_code><const_code> 328 </const_code><teneur> 52,9 </teneur><min/><max/><code_confiance> A </code_confiance></COMPO>
<COMPO><alim_code> 13050 </alim_code><const_code> 25000 </const_code><teneur> < 0,5 </teneur></COMPO>
<COMPO><alim_code> 13050 </alim_code><const_code> 31000 </const_code><teneur> 11,6 </teneur></COMPO>
<COMPO><alim_code> 13050 </alim_code><const_code> 40000 </const_code><teneur> traces </teneur></COMPO>
<COMPO><alim_code> 13050 </alim_code><const_code> 10004 </const_code><teneur> - </teneur></COMPO>
<COMPO><alim_code> 2000 </alim_code><const_code> 328 </const_code><teneur> - </teneur></COMPO>
<COMPO><alim_code> 2000 </alim_code><const_code> 327 </const_code><teneur> 418,4 </teneur></COMPO>
</TABLE>
""".encode("windows-1252")


class TestCiqual(unittest.TestCase):
    def archive(self) -> bytes:
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("alim_2020_07_07.xml", ALIM)
            z.writestr("alim_grp_2020_07_07.xml", GRP)
            z.writestr("compo_2020_07_07.xml", COMPO)
        return b.getvalue()

    def test_preparer(self):
        lignes, version = ciqual.preparer(self.archive())
        self.assertEqual(version, "2020_07_07")
        self.assertEqual(len(lignes), 2)  # l'aliment sans énergie est écarté
        self.assertAlmostEqual(lignes[1]["kcal"], 100.0)  # kJ convertis
        a = lignes[0]
        self.assertEqual(a["nom"], "Pomme, crue, pulpe et peau")
        self.assertEqual(a["groupe"], "fruits, légumes, légumineuses et oléagineux")
        self.assertAlmostEqual(a["kcal"], 52.9)
        self.assertEqual(a["prot"], 0.0)
        self.assertEqual(a["lip"], 0.0)
        self.assertIsNone(a["sel"])

    def test_ecrire(self):
        lignes, version = ciqual.preparer(self.archive())
        s = io.StringIO()
        ciqual.ecrire(lignes, version, s)
        l = s.getvalue().splitlines()
        self.assertEqual(l[0], "#ciqual\t2020_07_07")
        self.assertEqual(l[2], "13050\tPomme, crue, pulpe et peau\tfruits, légumes, légumineuses et oléagineux\t52.9\t0\t11.6\t0\t\t\t\t")


if __name__ == "__main__":
    unittest.main()
