from import_oni import convertir_saison_en_date

def test_saison_valide():
    """Vérifie qu'une saison valide est bien convertie en date."""
    date = convertir_saison_en_date("DJF", 1950)
    assert date.year == 1950
    assert date.month == 1
    assert date.day == 1

def test_saison_invalide():
    """Vérifie qu'une saison invalide renvoie None (pas d'insertion)."""
    assert convertir_saison_en_date("XYZ", 1950) is None