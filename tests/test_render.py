import json
from datetime import date

import pytest

from fuelmap import model
from fuelmap.render import csv_export, markdown, web

AIRAC = "2026-05-14"
TODAY = date(2026, 8, 11)


def aerodrome(icao, fuels, name="TERRAIN", latitude=45.0, longitude=2.0, **kwargs):
    return model.Aerodrome(
        icao=icao,
        name=name,
        fuels=frozenset(fuels),
        latitude=latitude,
        longitude=longitude,
        fuel_section=f"10 - AVT : {', '.join(sorted(fuels))}",
        **kwargs,
    )


@pytest.fixture
def aerodromes():
    return [
        aerodrome("LFDA", {model.UL91}),
        aerodrome("LFCU", {model.AVGAS_100LL, model.SUPER_PLUS}),
        aerodrome("LFMW", {model.SUPER_PLUS, model.UL91}),
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


class TestMapData:
    def test_drops_aerodromes_without_coordinates(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert [a["icao"] for a in payload["aerodromes"]] == ["LFCU", "LFDA", "LFMW"]

    def test_assigns_a_legend_category_to_every_point(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        categories = {a["icao"]: a["category"] for a in payload["aerodromes"]}
        assert categories == {
            "LFCU": model.CATEGORY_MOGAS,
            "LFDA": model.CATEGORY_UL91,
            "LFMW": model.CATEGORY_BOTH,
        }
        assert set(categories.values()) <= set(model.CATEGORY_LABELS)

    def test_records_schema_and_cycle(self, aerodromes):
        payload = web.build_payload(aerodromes, AIRAC, today=TODAY)
        assert payload["schema"] == web.SCHEMA_VERSION
        assert payload["airac"] == AIRAC
        assert payload["generated"] == "2026-08-11"

    def test_writes_valid_utf8_json(self, tmp_path, aerodromes):
        path = tmp_path / "docs" / "aerodromes.json"
        plotted = web.write_map_data(path, aerodromes, AIRAC, today=TODAY)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert plotted == len(payload["aerodromes"]) == 3

    def test_refuses_aerodromes_the_legend_cannot_explain(self):
        """A 100LL-only field must never silently reach the map."""
        with pytest.raises(ValueError):
            web.build_payload([aerodrome("LFAT", {model.AVGAS_100LL})], AIRAC)
