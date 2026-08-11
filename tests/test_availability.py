import pytest

from fuelmap import model
from fuelmap.availability import detect_availability

SELF = model.AVAILABILITY_SELF_SERVICE
RESTRICTED = model.AVAILABILITY_RESTRICTED
UNKNOWN = model.AVAILABILITY_UNKNOWN


def availability(section, *fuels):
    return detect_availability(section, frozenset(fuels))


class TestSingleSignal:
    @pytest.mark.parametrize(
        ("section", "expected"),
        [
            ("10 - AVT : UL 91 H24 par carte TOTAL.", SELF),
            ("10 - AVT : UL 91. Station automatique : CB uniquement.", SELF),
            ("10 - AVT : UL 91. Libre service : H24 avec carte Air BP.", SELF),
            ("10 - AVT : UL 91. Pompe automatique.", SELF),
            ("10 - AVT : UL 91 HX.", RESTRICTED),
            ("10 - AVT : UL 91 PPR 06 77 63 68 41.", RESTRICTED),
            ("10 - AVT : UL 91 - O/R ACB.", RESTRICTED),
            ("10 - AVT : UL 91 sur demande.", RESTRICTED),
            ("10 - AVT : UL 91 réservé aux ACFT basés.", RESTRICTED),
            ("10 - AVT : UL 91 : 0800-1100, 1300-1700.", RESTRICTED),
            ("10 - AVT : UL 91. HJ sur PPR ACB.", RESTRICTED),
            ("10 - AVT : UL 91 : se renseigner auprès de l'ACB.", RESTRICTED),
            ("10 - AVT : UL 91. Contacter l'ACB auparavant.", RESTRICTED),
            # A number and no hours means somebody has to be called.
            ("10 - AVT : UL 91. TEL : 07 82 77 32 56.", RESTRICTED),
            ("10 - AVT : UL 91. AVIA TÉL : 06.49.75.14.88.", RESTRICTED),
            ("10 - AVT : UL 91. Renseignements 06 49 75 14 88.", RESTRICTED),
            ("10 - AVT : Carburant / Fuel : UL 91.", UNKNOWN),
            ("10 - AVT : Carburant / Fuel : UL91 Lubrifiant : NIL.", UNKNOWN),
        ],
    )
    def test_classifies_a_lone_signal(self, section, expected):
        assert availability(section, model.UL91) == {model.UL91: expected}

    @pytest.mark.parametrize(
        "section",
        [
            "10 - AVT : UL 91 : automate CB H24. TEL : 07 82 77 32 56.",
            "10 - AVT : UL 91 libre service. En cas de panne TEL : 06 49 75 14 88.",
        ],
    )
    def test_a_phone_number_never_demotes_a_dispenser(self, section):
        """Support numbers sit next to automats; the pump is still self-service."""
        assert availability(section, model.UL91)[model.UL91] == SELF

    @pytest.mark.parametrize(
        "section",
        [
            "10 - AVT : UL 91 H24. FREQ 120.500.",
            "10 - AVT : UL 91 automate, poste 61.",
        ],
    )
    def test_frequencies_and_stand_numbers_are_not_phone_numbers(self, section):
        assert availability(section, model.UL91)[model.UL91] == SELF


class TestConflictingSignals:
    def test_self_service_beats_a_restriction_in_the_same_breath(self):
        """"H24 by card, or during club hours" still means you can help yourself."""
        section = (
            "10 - AVT : AVGAS 100 LL et UL 91 H24 par carte TOTAL, ou bureau de "
            "piste. HOR / SKED : 0900-1600."
        )
        assert availability(section, model.UL91)[model.UL91] == SELF

    def test_sked_only_cancels_the_dispenser(self):
        """A dispenser that only runs during published hours is not self-service."""
        section = (
            "10 - AVT : Automate / Dispenser AVGAS 100LL - UL AERO SUPER+ : "
            "HOR AVT uniquement, paiement carte TOTAL."
        )
        assert availability(section, model.UL_AERO)[model.UL_AERO] == RESTRICTED

    def test_english_sked_only_is_recognised(self):
        section = "10 - AVT : Dispenser UL 91 : AVT SKED only, payment by card."
        assert availability(section, model.UL91)[model.UL91] == RESTRICTED

    def test_uniquement_without_hours_is_not_a_restriction(self):
        section = "10 - AVT : H24 avec CB VISA pour UL91 uniquement."
        assert availability(section, model.UL91)[model.UL91] == SELF


class TestPerFuelAttribution:
    def test_each_fuel_keeps_its_own_terms(self):
        """Montceau-les-Mines: 100LL on an H24 dispenser, UL91 only 0800-1500."""
        section = (
            "10 - AVT : Carburant / Fuel: 100 LL Automate avec carte de crédit "
            "TOTAL H 24. UL 91, Lubrifiant : 80 - 100 W : 0800-1500 tous les "
            "jours, sauf mardi."
        )
        assert availability(section, model.UL91, model.AVGAS_100LL) == {
            model.AVGAS_100LL: SELF,
            model.UL91: RESTRICTED,
        }

    def test_unnamed_clauses_apply_to_every_fuel(self):
        section = "10 - AVT : Carburant : UL 91, 100 LL. HX."
        assert availability(section, model.UL91, model.AVGAS_100LL) == {
            model.UL91: RESTRICTED,
            model.AVGAS_100LL: RESTRICTED,
        }

    def test_a_named_fuel_overrides_the_section_default(self):
        """Lyon-Bron: the H24 card applies to 100LL only, not to UL AERO."""
        section = (
            "10 - AVT : Carburants : UL AERO SUPER+ - 100 LL. 0630-2230, carte "
            "crédit. Carte TOTAL à la station 100LL : H24."
        )
        result = availability(section, model.UL_AERO, model.AVGAS_100LL)
        assert result[model.UL_AERO] == RESTRICTED
        assert result[model.AVGAS_100LL] == SELF

    def test_tous_carburants_binds_to_everything(self):
        section = (
            "10 - AVT : Carburants : 100 LL, UL91 HOR AFIS. "
            "Tous carburants / All fuels : CB H24."
        )
        assert availability(section, model.UL91)[model.UL91] == SELF

    def test_a_fuel_the_clause_never_names_stays_unknown(self):
        """The HX applies to UL91 by name, so it says nothing about Jet A1."""
        result = availability("10 - AVT : UL 91 HX.", model.UL91, model.JET_A1)
        assert result == {model.UL91: RESTRICTED, model.JET_A1: UNKNOWN}


class TestBestAvailability:
    @pytest.mark.parametrize(
        ("levels", "expected"),
        [
            ({SELF, RESTRICTED}, SELF),
            ({RESTRICTED, UNKNOWN}, RESTRICTED),
            ({UNKNOWN}, UNKNOWN),
            (set(), UNKNOWN),
        ],
    )
    def test_picks_the_most_permissive(self, levels, expected):
        assert model.best_availability(levels) == expected
