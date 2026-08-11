import pytest

from fuelmap import model, parsing


class TestIcaoFromFilename:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("AD-2.LFOU.pdf", "LFOU"),
            ("AD-2.lfou.pdf", "LFOU"),
            ("AD-2.LFPG.pdf", "LFPG"),
            ("AD-2.LF1234.pdf", None),
            ("AD-2.EGLL.pdf", None),
            ("AD-3.LFOU.pdf", None),
            ("LFOU.pdf", None),
        ],
    )
    def test_recognises_vac_filenames(self, filename, expected):
        assert parsing.icao_from_filename(filename) == expected


class TestFuelSection:
    def test_stops_at_section_11(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFOU"))
        assert section.lstrip().startswith("10 - AVT")
        assert "JET A1" in section
        assert "RFFS" not in section

    def test_stops_at_section_12_when_11_is_absent(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFDA"))
        assert "UL91" in section
        assert "PERIL ANIMALIER" not in section

    def test_handles_amended_paragraph_marker(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFLY"))
        assert "UL AERO SUPER+" in section

    def test_returns_empty_when_absent(self, vac_text):
        assert parsing.extract_fuel_section(vac_text("LFOJ")) == ""


class TestDetectFuels:
    def test_reads_plain_listing(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFOU"))
        assert parsing.detect_fuels(section) == {model.AVGAS_100LL, model.JET_A1}

    def test_ul_aero_super_plus_is_not_mogas(self, vac_text):
        """"UL AERO SUPER+" is TotalEnergies' UL91, not SP95/SP98."""
        section = parsing.extract_fuel_section(vac_text("LFLY"))
        fuels = parsing.detect_fuels(section)
        assert model.UL_AERO in fuels
        assert model.SUPER_PLUS not in fuels

    def test_genuine_mogas_is_still_detected(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFCU"))
        assert parsing.detect_fuels(section) == {model.AVGAS_100LL, model.SUPER_PLUS}

    def test_nil_section_yields_no_fuel(self, vac_text):
        section = parsing.extract_fuel_section(vac_text("LFJB"))
        assert parsing.detect_fuels(section) == frozenset()

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Carburant : UL 91", {model.UL91}),
            ("Carburant : UL91", {model.UL91}),
            ("Carburant : SUPER PLUS", {model.SUPER_PLUS}),
            ("Carburant : SP95", {model.SUPER_PLUS}),
            ("Carburant : SP 98", {model.SUPER_PLUS}),
            ("Carburant : MOGAS", {model.MOGAS}),
            ("Carburant : AVGAS 100LL", {model.AVGAS_100LL}),
            ("Carburant : 100 LL", {model.AVGAS_100LL}),
            ("Carburant : JET A-1", {model.JET_A1}),
            ("Carburant : JET A1", {model.JET_A1}),
            ("AERO SUPER+ uniquement", {model.UL_AERO}),
            ("UL AERO SUPER + par automate", {model.UL_AERO}),
            ("SP98 UL 91", {model.SUPER_PLUS, model.UL91}),
        ],
    )
    def test_spelling_variants(self, text, expected):
        assert parsing.detect_fuels(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["ULM interdit", "Piste 91 fermée", "SP 100 non disponible", "Parking JET"],
    )
    def test_does_not_match_unrelated_text(self, text):
        assert parsing.detect_fuels(text) == frozenset()


class TestCoordinates:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (("47", "04", "55", "N"), 47.081944),
            (("000", "52", "38", "W"), -0.877222),
            (("45", "43", "46", "N"), 45.729444),
            (("004", "56", "20", "E"), 4.938889),
        ],
    )
    def test_dms_conversion(self, args, expected):
        assert parsing.dms_to_decimal(*args) == expected

    def test_both_hemispheres_are_rounded_identically(self):
        north = parsing.dms_to_decimal("12", "30", "30", "N")
        south = parsing.dms_to_decimal("12", "30", "30", "S")
        assert south == -north
        assert len(str(south).split(".")[1]) <= 6

    def test_reads_header_position(self, vac_text):
        assert parsing.extract_position(vac_text("LFOU")) == (47.081944, -0.877222)

    def test_reads_southern_position(self, vac_text):
        latitude, _ = parsing.extract_position(vac_text("LFDA"))
        assert latitude == -43.708611

    def test_missing_position_returns_none(self):
        assert parsing.extract_position("pas de coordonnées ici") == (None, None)


class TestAerodromeName:
    @pytest.mark.parametrize(
        ("icao", "expected"),
        [
            ("LFOU", "CHOLET LE PONTREAU"),
            ("LFLY", "LYON BRON"),
            ("LFCU", "USSEL THALAMY"),
            ("LFJB", "MAULEON"),
            ("LFDA", "AIRE SUR L'ADOUR"),
        ],
    )
    def test_reads_name_from_header(self, vac_text, icao, expected):
        assert parsing.extract_aerodrome_name(vac_text(icao)) == expected

    def test_skips_boilerplate_in_multi_column_header(self, vac_text):
        assert parsing.extract_aerodrome_name(vac_text("LFOJ")) == "ORLEANS BRICY"


class TestMojibake:
    def test_repairs_windows_1252_leftovers(self):
        repaired = parsing.fix_mojibake("l\x92ACB \x93AVT\x94 \x96 NIL")
        assert repaired == "l'ACB \"AVT\" - NIL"

    def test_leaves_clean_text_untouched(self):
        assert parsing.fix_mojibake("Carburant : UL91") == "Carburant : UL91"


class TestParseVacText:
    def test_builds_a_complete_record(self, vac_text):
        aerodrome = parsing.parse_vac_text("LFCU", vac_text("LFCU"))
        assert aerodrome.icao == "LFCU"
        assert aerodrome.name == "USSEL THALAMY"
        assert aerodrome.fuels == {model.AVGAS_100LL, model.SUPER_PLUS}
        assert aerodrome.has_position
        assert aerodrome.has_unleaded
        assert aerodrome.error == ""

    def test_empty_text_is_flagged(self):
        aerodrome = parsing.parse_vac_text("LFXX", "   \n  ")
        assert aerodrome.error == "no_text"
        assert aerodrome.fuels == frozenset()
        assert not aerodrome.has_position

    def test_missing_section_still_yields_position(self, vac_text):
        aerodrome = parsing.parse_vac_text("LFOJ", vac_text("LFOJ"))
        assert aerodrome.fuel_section == ""
        assert not aerodrome.has_unleaded
        assert aerodrome.has_position

    def test_excerpt_is_collapsed_and_truncated(self, vac_text):
        aerodrome = parsing.parse_vac_text("LFOU", vac_text("LFOU"))
        assert "\n" not in aerodrome.fuel_section
        assert "  " not in aerodrome.fuel_section
        assert len(aerodrome.fuel_section) <= parsing.FUEL_SECTION_EXCERPT_LENGTH
