import pytest

from fuelmap import model


def _aerodrome(**overrides):
    defaults = dict(
        icao="LFDA",
        name="AIRE SUR L'ADOUR",
        fuels=frozenset({model.UL91}),
        latitude=43.708611,
        longitude=-0.247222,
        fuel_section="10 - AVT : Carburant / Fuel : UL91.",
    )
    return model.Aerodrome(**{**defaults, **overrides})


class TestFuelFamilies:
    @pytest.mark.parametrize(
        ("fuels", "expected"),
        [
            ({model.UL91}, [model.FAMILY_UL91]),
            ({model.UL_AERO}, [model.FAMILY_UL91]),
            ({model.UL91, model.AVGAS_100LL}, [model.FAMILY_UL91]),
            ({model.SUPER_PLUS}, [model.FAMILY_MOGAS]),
            ({model.MOGAS}, [model.FAMILY_MOGAS]),
            ({model.SUPER_PLUS, model.JET_A1}, [model.FAMILY_MOGAS]),
            (
                {model.UL91, model.SUPER_PLUS},
                [model.FAMILY_UL91, model.FAMILY_MOGAS],
            ),
            ({model.AVGAS_100LL}, []),
            (set(), []),
        ],
    )
    def test_splits_fuels_into_families(self, fuels, expected):
        aerodrome = _aerodrome(fuels=frozenset(fuels))
        assert aerodrome.families() == expected

    def test_families_are_returned_in_legend_order(self):
        aerodrome = _aerodrome(fuels=frozenset({model.SUPER_PLUS, model.UL91}))
        assert aerodrome.families() == list(model.FUEL_FAMILIES)

    def test_every_family_has_a_label(self):
        assert set(model.FAMILY_LABELS) == set(model.FUEL_FAMILIES)

    def test_families_partition_the_unleaded_fuels(self):
        covered = set().union(*model.FUEL_FAMILIES.values())
        assert covered == set(model.UNLEADED_FUELS)


class TestFamilyAvailability:
    def test_uses_the_best_level_within_a_family(self):
        """UL91 and UL AERO SUPER+ are one product, so either being open counts."""
        aerodrome = _aerodrome(
            fuels=frozenset({model.UL91, model.UL_AERO}),
            availability=(
                (model.UL91, model.AVAILABILITY_RESTRICTED),
                (model.UL_AERO, model.AVAILABILITY_SELF_SERVICE),
            ),
        )
        assert (
            aerodrome.family_availability(model.FAMILY_UL91)
            == model.AVAILABILITY_SELF_SERVICE
        )

    def test_families_are_scored_independently(self):
        aerodrome = _aerodrome(
            fuels=frozenset({model.UL91, model.SUPER_PLUS}),
            availability=(
                (model.SUPER_PLUS, model.AVAILABILITY_RESTRICTED),
                (model.UL91, model.AVAILABILITY_SELF_SERVICE),
            ),
        )
        assert (
            aerodrome.family_availability(model.FAMILY_UL91)
            == model.AVAILABILITY_SELF_SERVICE
        )
        assert (
            aerodrome.family_availability(model.FAMILY_MOGAS)
            == model.AVAILABILITY_RESTRICTED
        )

    def test_unrecorded_fuel_is_unknown(self):
        aerodrome = _aerodrome(fuels=frozenset({model.UL91}), availability=())
        assert aerodrome.availability_of(model.UL91) == model.AVAILABILITY_UNKNOWN

    def test_every_level_has_a_label_and_a_hint(self):
        assert set(model.AVAILABILITY_LABELS) == set(model.AVAILABILITY_ORDER)
        assert set(model.AVAILABILITY_HINTS) == set(model.AVAILABILITY_ORDER)


class TestFuelTaxonomy:
    def test_unleaded_is_the_union_of_avgas_and_mogas(self):
        assert model.UNLEADED_FUELS == model.UNLEADED_AVGAS | model.MOGAS_FUELS

    def test_leaded_and_turbine_fuels_are_not_unleaded(self):
        assert model.AVGAS_100LL not in model.UNLEADED_FUELS
        assert model.JET_A1 not in model.UNLEADED_FUELS

    def test_every_fuel_has_a_label_and_a_rank(self):
        assert set(model.FUEL_LABELS) == set(model.FUEL_DISPLAY_ORDER)


class TestFormatFuels:
    def test_uses_display_order_not_alphabetical(self):
        fuels = {model.JET_A1, model.AVGAS_100LL, model.UL91}
        assert model.format_fuels(fuels) == "UL91, 100LL, Jet A1"

    def test_empty_set_renders_empty(self):
        assert model.format_fuels(set()) == ""

    def test_unknown_keys_are_kept_verbatim(self):
        assert model.format_fuels({model.UL91, "F34"}) == "UL91, F34"


class TestAerodrome:
    def test_reports_unleaded_availability(self):
        assert _aerodrome().has_unleaded
        assert not _aerodrome(fuels=frozenset({model.AVGAS_100LL})).has_unleaded

    def test_position_requires_both_coordinates(self):
        assert _aerodrome().has_position
        assert not _aerodrome(latitude=None).has_position
        assert not _aerodrome(longitude=None).has_position

    def test_is_hashable_so_it_survives_the_process_pool(self):
        availability = ((model.UL91, model.AVAILABILITY_SELF_SERVICE),)
        assert hash(_aerodrome(availability=availability)) == hash(
            _aerodrome(availability=availability)
        )
