import pytest

from fuelmap import model


class TestMapCategory:
    @pytest.mark.parametrize(
        ("fuels", "expected"),
        [
            ({model.UL91}, model.CATEGORY_UL91),
            ({model.UL_AERO}, model.CATEGORY_UL91),
            ({model.UL91, model.AVGAS_100LL}, model.CATEGORY_UL91),
            ({model.SUPER_PLUS}, model.CATEGORY_MOGAS),
            ({model.MOGAS}, model.CATEGORY_MOGAS),
            ({model.SUPER_PLUS, model.JET_A1}, model.CATEGORY_MOGAS),
            ({model.UL91, model.SUPER_PLUS}, model.CATEGORY_BOTH),
            ({model.UL_AERO, model.MOGAS}, model.CATEGORY_BOTH),
        ],
    )
    def test_classifies_unleaded_aerodromes(self, fuels, expected):
        assert model.map_category(fuels) == expected

    @pytest.mark.parametrize(
        "fuels", [set(), {model.AVGAS_100LL}, {model.AVGAS_100LL, model.JET_A1}]
    )
    def test_rejects_aerodromes_without_unleaded_fuel(self, fuels):
        """The legend has no colour for these, so they must not reach the map."""
        with pytest.raises(ValueError):
            model.map_category(fuels)

    def test_every_category_has_a_label(self):
        categories = {model.CATEGORY_UL91, model.CATEGORY_MOGAS, model.CATEGORY_BOTH}
        assert set(model.CATEGORY_LABELS) == categories


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
    def _aerodrome(self, **overrides):
        defaults = dict(
            icao="LFDA",
            name="AIRE SUR L'ADOUR",
            fuels=frozenset({model.UL91}),
            latitude=43.708611,
            longitude=-0.247222,
            fuel_section="10 - AVT : Carburant / Fuel : UL91.",
        )
        return model.Aerodrome(**{**defaults, **overrides})

    def test_reports_unleaded_availability(self):
        assert self._aerodrome().has_unleaded
        assert not self._aerodrome(fuels=frozenset({model.AVGAS_100LL})).has_unleaded

    def test_position_requires_both_coordinates(self):
        assert self._aerodrome().has_position
        assert not self._aerodrome(latitude=None).has_position
        assert not self._aerodrome(longitude=None).has_position

    def test_is_hashable_so_it_survives_the_process_pool(self):
        assert hash(self._aerodrome()) == hash(self._aerodrome())
