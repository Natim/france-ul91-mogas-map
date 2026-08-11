import json
from datetime import date

import pytest

from fuelmap import model
from fuelmap.render import csv_export, markdown, web

AIRAC = "2026-05-14"
TODAY = date(2026, 8, 11)


SELF = model.AVAILABILITY_SELF_SERVICE
RESTRICTED = model.AVAILABILITY_RESTRICTED


def aerodrome(
    icao,
    fuels,
    name="TERRAIN",
    latitude=45.0,
    longitude=2.0,
    availability=None,
    **kwargs,
):
    fuels = frozenset(fuels)
    if availability is None:
        availability = dict.fromkeys(fuels, RESTRICTED)
    return model.Aerodrome(
        icao=icao,
        name=name,
        fuels=fuels,
        latitude=latitude,
        longitude=longitude,
        fuel_section=f"10 - AVT : {', '.join(sorted(fuels))}",
        availability=tuple(sorted(availability.items())),
        **kwargs,
    )


@pytest.fixture
def aerodromes():
    return [
        aerodrome("LFDA", {model.UL91}, availability={model.UL91: SELF}),
        aerodrome("LFCU", {model.AVGAS_100LL, model.SUPER_PLUS}),
        aerodrome(
            "LFMW",
            {model.SUPER_PLUS, model.UL91},
            availability={model.UL91: SELF, model.SUPER_PLUS: RESTRICTED},
        ),
        aerodrome("LFXX", {model.UL91}, latitude=None, longitude=None),
    ]


class TestCsvRoundTrip:
    def test_survives_a_write_then_read(self, tmp_path, aerodromes):
        path = tmp_path / "all.csv"
        csv_export.write_csv(path, aerodromes)
        assert csv_export.read_csv(path) == aerodromes

    def test_subset_columns_drop_the_error_field(self, tmp_path, aerodromes):
        path = tmp_path / "subset.csv"
        csv_export.write_csv(path, aerodromes, columns=csv_export.SUBSET_COLUMNS)
        header = path.read_text(encoding="utf-8").splitlines()[0]
        assert "error" not in header
        assert csv_export.read_csv(path) == aerodromes

    def test_availability_round_trips_per_fuel(self, tmp_path):
        path = tmp_path / "all.csv"
        original = aerodrome(
            "LFGM",
            {model.UL91, model.AVGAS_100LL},
            availability={model.AVGAS_100LL: SELF, model.UL91: RESTRICTED},
        )
        csv_export.write_csv(path, [original])
        restored = csv_export.read_csv(path)[0]
        assert restored == original
        assert restored.availability_of(model.UL91) == RESTRICTED
        assert restored.availability_of(model.AVGAS_100LL) == SELF

    def test_creates_missing_directories(self, tmp_path, aerodromes):
        path = tmp_path / "nested" / "dir" / "all.csv"
        csv_export.write_csv(path, aerodromes)
        assert path.exists()

    def test_missing_coordinates_stay_empty_rather_than_zero(self, tmp_path):
        path = tmp_path / "all.csv"
        csv_export.write_csv(path, [aerodrome("LFXX", {model.UL91}, latitude=None,
                                              longitude=None)])
        assert ",," in path.read_text(encoding="utf-8").splitlines()[1]
        assert csv_export.read_csv(path)[0].latitude is None


class TestMarkdown:
    def test_reports_counts_and_metadata(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        assert "**4 aérodromes**" in rendered
        assert f"**Cycle AIRAC** : {AIRAC}" in rendered
        assert "2026-08-11" in rendered

    def test_lists_every_aerodrome_sorted_by_icao(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        rows = [line for line in rendered.splitlines() if line.startswith("| LF")]
        assert [row.split(" | ")[0].removeprefix("| ") for row in rows] == [
            "LFCU",
            "LFDA",
            "LFMW",
            "LFXX",
        ]

    def test_omits_fuels_nobody_sells(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        assert "| Jet A1 |" not in rendered
        assert "| UL91 | 3 |" in rendered

    def test_breaks_down_access_conditions(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        assert "## Conditions d'accès" in rendered
        assert f"| {model.AVAILABILITY_LABELS[SELF]} | 2 |" in rendered
        assert f"| {model.AVAILABILITY_LABELS[RESTRICTED]} | 2 |" in rendered

    def test_lists_access_per_aerodrome(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        row = next(line for line in rendered.splitlines() if line.startswith("| LFCU"))
        assert model.AVAILABILITY_LABELS[RESTRICTED] in row

    def test_footnotes_curated_access_conditions(self, aerodromes):
        curated = aerodrome(
            "LFRS",
            {model.UL91},
            name="NANTES ATLANTIQUE",
            availability={model.UL91: SELF},
            availability_note="Automate accessible H24.",
        )
        rendered = markdown.render_markdown([*aerodromes, curated], AIRAC, today=TODAY)
        row = next(line for line in rendered.splitlines() if line.startswith("| LFRS"))
        assert markdown.OVERRIDE_MARK in row
        assert "- **LFRS** NANTES ATLANTIQUE — Automate accessible H24." in rendered

    def test_omits_the_footnote_when_nothing_is_curated(self, aerodromes):
        rendered = markdown.render_markdown(aerodromes, AIRAC, today=TODAY)
        assert "renseignée manuellement" not in rendered


class TestMapData:
    def test_drops_aerodromes_without_coordinates(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert payload["aerodromeCount"] == 3
        assert {m["icao"] for m in payload["markers"]} == {"LFCU", "LFDA", "LFMW"}

    def test_emits_one_marker_per_fuel_family(self, aerodromes):
        """A field selling both must be filterable under either family."""
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        pairs = [(m["icao"], m["family"]) for m in payload["markers"]]
        assert pairs == [
            ("LFCU", model.FAMILY_MOGAS),
            ("LFDA", model.FAMILY_UL91),
            ("LFMW", model.FAMILY_UL91),
            ("LFMW", model.FAMILY_MOGAS),
        ]

    def test_each_marker_carries_only_its_family_fuels(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        by_key = {(m["icao"], m["family"]): m for m in payload["markers"]}
        assert by_key[("LFMW", model.FAMILY_UL91)]["fuels"] == [model.UL91]
        assert by_key[("LFMW", model.FAMILY_MOGAS)]["fuels"] == [model.SUPER_PLUS]

    def test_ul_aero_super_plus_lands_on_the_sp98_filter(self):
        """A ROTAX pilot filtering for SP98 must see Lyon-Bron and its kin."""
        lyon = model.Aerodrome(
            icao="LFLY",
            name="LYON BRON",
            fuels=frozenset({model.UL_AERO, model.AVGAS_100LL}),
            latitude=45.72,
            longitude=4.94,
            fuel_section="10 - AVT : UL AERO SUPER+ - 100 LL.",
            availability=((model.UL_AERO, RESTRICTED),),
        )
        payload = web.build_payload([lyon], AIRAC, today=TODAY)
        assert [m["family"] for m in payload["markers"]] == [model.FAMILY_MOGAS]
        assert payload["markers"][0]["fuelsLabel"] == "UL AERO SUPER+"

    def test_availability_is_resolved_per_family(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        by_key = {(m["icao"], m["family"]): m for m in payload["markers"]}
        assert by_key[("LFMW", model.FAMILY_UL91)]["availability"] == SELF
        assert by_key[("LFMW", model.FAMILY_MOGAS)]["availability"] == RESTRICTED

    def test_curated_levels_are_flagged_for_the_reader(self):
        """The chart text in the popup will not back this up, so say so."""
        curated = aerodrome(
            "LFRS",
            {model.UL91},
            availability={model.UL91: SELF},
            availability_note="Automate accessible H24.",
        )
        payload = web.build_payload([curated], AIRAC, today=TODAY)
        assert payload["markers"][0]["note"] == "Automate accessible H24."

    def test_uncurated_markers_carry_no_note(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert all(m["note"] == "" for m in payload["markers"])

    def test_markers_show_the_whole_field_for_context(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        mogas = next(m for m in payload["markers"] if m["icao"] == "LFCU")
        assert mogas["fuelsLabel"] == "Super Plus"
        assert mogas["allFuelsLabel"] == "Super Plus, 100LL"
        assert mogas["section"].startswith("10 - AVT")

    def test_every_marker_uses_known_legend_keys(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert {m["family"] for m in payload["markers"]} <= set(model.FAMILY_LABELS)
        assert {m["availability"] for m in payload["markers"]} <= set(
            model.AVAILABILITY_LABELS
        )

    def test_records_schema_and_cycle(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert payload["schema"] == web.SCHEMA_VERSION
        assert payload["airac"] == AIRAC
        assert payload["generated"] == "2026-08-11"

    def test_writes_valid_utf8_json(self, tmp_path, aerodromes):
        path = tmp_path / "docs" / "aerodromes.json"
        plotted = web.write_map_data(path, aerodromes, AIRAC, today=TODAY)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert plotted == payload["aerodromeCount"] == 3
        assert len(payload["markers"]) == 4

    def test_refuses_aerodromes_the_legend_cannot_explain(self):
        """A 100LL-only field has no family and must not vanish silently."""
        with pytest.raises(ValueError):
            web.build_payload([aerodrome("LFAT", {model.AVGAS_100LL})], AIRAC)
