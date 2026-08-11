"""The curated layer sitting on top of what the charts say."""

import pytest

from fuelmap import model, overrides

SELF = model.AVAILABILITY_SELF_SERVICE
RESTRICTED = model.AVAILABILITY_RESTRICTED
UNKNOWN = model.AVAILABILITY_UNKNOWN


def _aerodrome(icao, fuels, availability=None, **kwargs):
    fuels = frozenset(fuels)
    return model.Aerodrome(
        icao=icao,
        name="TERRAIN",
        fuels=fuels,
        latitude=45.0,
        longitude=2.0,
        fuel_section="10 - AVT : Carburants / Fuel : UL91, JET A1.",
        availability=tuple(sorted((availability or {}).items())),
        **kwargs,
    )


class TestOverrideTable:
    @pytest.mark.parametrize("icao", sorted(overrides.OVERRIDES))
    def test_entry_uses_known_fuels_and_levels(self, icao):
        entry = overrides.OVERRIDES[icao]
        for fuel, level in entry.availability.items():
            assert fuel in model.FUEL_LABELS
            assert level in model.AVAILABILITY_ORDER

    @pytest.mark.parametrize("icao", sorted(overrides.OVERRIDES))
    def test_entry_explains_itself(self, icao):
        """The reason is shown to pilots, so it may not be blank."""
        assert overrides.OVERRIDES[icao].reason.strip()

    @pytest.mark.parametrize("icao", sorted(overrides.OVERRIDES))
    def test_entry_states_a_definite_level(self, icao):
        """An entry resolving to "unknown" would change nothing."""
        assert UNKNOWN not in overrides.OVERRIDES[icao].availability.values()


class TestApply:
    def test_untouched_aerodrome_is_returned_as_is(self):
        original = _aerodrome("LFZZ", {model.UL91}, {model.UL91: UNKNOWN})
        assert overrides.apply(original) is original

    def test_overrides_the_level_and_records_why(self):
        nantes = _aerodrome(
            "LFRS", {model.UL91, model.JET_A1}, {model.UL91: UNKNOWN}
        )
        curated = overrides.apply(nantes)
        assert curated.availability_of(model.UL91) == SELF
        assert curated.availability_note

    def test_leaves_unnamed_fuels_alone(self):
        """Only the fuels an entry names are touched."""
        nantes = _aerodrome(
            "LFRS",
            {model.UL91, model.JET_A1},
            {model.UL91: UNKNOWN, model.JET_A1: RESTRICTED},
        )
        curated = overrides.apply(nantes)
        assert curated.availability_of(model.JET_A1) == RESTRICTED

    def test_can_set_different_levels_on_one_field(self):
        """Alençon: the UL91 pump is HX, the SP98 across the road is not."""
        alencon = _aerodrome("LFOF", {model.UL91}, {model.UL91: UNKNOWN})
        curated = overrides.apply(alencon)
        assert curated.availability_of(model.UL91) == RESTRICTED
        assert curated.availability_of(model.SUPER_PLUS) == SELF

    def test_adds_a_fuel_the_chart_omits(self):
        alencon = _aerodrome("LFOF", {model.UL91}, {model.UL91: UNKNOWN})
        curated = overrides.apply(alencon)
        assert model.SUPER_PLUS in curated.fuels
        assert curated.families() == [model.FAMILY_UL91, model.FAMILY_MOGAS]

    def test_does_not_mutate_the_original(self):
        nantes = _aerodrome("LFRS", {model.UL91}, {model.UL91: UNKNOWN})
        overrides.apply(nantes)
        assert nantes.availability_of(model.UL91) == UNKNOWN
        assert nantes.availability_note == ""

    def test_is_idempotent(self):
        for icao in overrides.OVERRIDES:
            original = _aerodrome(icao, {model.UL91}, {model.UL91: UNKNOWN})
            once = overrides.apply(original)
            assert overrides.apply(once) == once
