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
    def test_entry_names_at_least_one_fuel(self, icao):
        """An empty entry changes nothing but still claims to be a correction.

        A level of "unknown" is allowed: it adds a fuel the chart omits without
        asserting hours nobody has verified.
        """
        assert overrides.OVERRIDES[icao].availability


class TestAdditions:
    @pytest.mark.parametrize("addition", overrides.ADDITIONS, ids=lambda a: a.code)
    def test_entry_is_plottable_and_sells_something_unleaded(self, addition):
        record = addition.to_aerodrome()
        assert record.has_position
        assert record.has_unleaded, "an entry with no unleaded fuel would vanish"
        assert record.families()

    @pytest.mark.parametrize("addition", overrides.ADDITIONS, ids=lambda a: a.code)
    def test_entry_declares_its_provenance_and_conditions(self, addition):
        """Nothing here was checked against a chart, so both are mandatory."""
        record = addition.to_aerodrome()
        assert record.is_off_aip
        assert record.curated_source.strip()
        assert record.availability_note.strip()

    @pytest.mark.parametrize("addition", overrides.ADDITIONS, ids=lambda a: a.code)
    def test_entry_sits_inside_france(self, addition):
        assert 41.0 < addition.latitude < 51.5
        assert -5.5 < addition.longitude < 9.6

    def test_additions_do_not_collide_with_aip_codes(self):
        aip = {"LFRS", "LFOF", "LFGI"}
        assert not {a.code for a in overrides.ADDITIONS} & aip

    def test_apply_all_merges_and_sorts(self):
        aip = [_aerodrome("LFZZ", {model.UL91}), _aerodrome("LFAA", {model.UL91})]
        merged = overrides.apply_all(aip)
        assert [a.icao for a in merged] == sorted(a.icao for a in merged)
        assert len(merged) == len(aip) + len(overrides.ADDITIONS)

    def test_extracted_aerodromes_are_not_marked_off_aip(self):
        assert not _aerodrome("LFZZ", {model.UL91}).is_off_aip


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

    def test_adding_a_fuel_can_qualify_a_field_that_had_none(self):
        """Figeac sells only 100LL; the SP98 next door is why it appears at all.

        This only works if overrides run before the unleaded filter, so the
        filter is applied here in the same order as the CLI does it.
        """
        from fuelmap.pipeline import unleaded_only

        figeac = _aerodrome(
            "LFCF",
            {model.AVGAS_100LL},
            {model.AVGAS_100LL: RESTRICTED},
        )
        assert not figeac.has_unleaded
        qualified = unleaded_only(overrides.apply_all([figeac]))
        assert "LFCF" in {a.icao for a in qualified}

    def test_is_idempotent(self):
        for icao in overrides.OVERRIDES:
            original = _aerodrome(icao, {model.UL91}, {model.UL91: UNKNOWN})
            once = overrides.apply(original)
            assert overrides.apply(once) == once
