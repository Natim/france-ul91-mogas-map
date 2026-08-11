import json
from datetime import date

import pytest

from fuelmap import cli, model
from fuelmap.render import csv_export, web

AIRAC = "2026-05-14"
EXTRACTED_ON = date(2026, 5, 18)


@pytest.fixture
def project(tmp_path):
    """A repository-shaped directory holding one previous extraction."""
    aerodromes = [
        model.Aerodrome(
            icao="LFDA",
            name="AIRE SUR L'ADOUR",
            fuels=frozenset({model.UL91}),
            latitude=43.708611,
            longitude=-0.247222,
            fuel_section="10 - AVT : Carburant / Fuel : UL91.",
        ),
        model.Aerodrome(
            icao="LFAT",
            name="LE TOUQUET",
            fuels=frozenset({model.AVGAS_100LL}),
            latitude=50.514722,
            longitude=1.6275,
            fuel_section="10 - AVT : Carburants / Fuel : 100LL.",
        ),
    ]
    csv_export.write_csv(tmp_path / "data" / "aerodromes-all.csv", aerodromes)
    web.write_map_data(
        tmp_path / "docs" / "aerodromes.json", aerodromes[:1], AIRAC, EXTRACTED_ON
    )
    return tmp_path


def rebuild(project, *extra):
    return cli.main(
        [
            "rebuild",
            "--all-csv", str(project / "data" / "aerodromes-all.csv"),
            "--unleaded-csv", str(project / "data" / "aerodromes-unleaded.csv"),
            "--markdown", str(project / "AERODROMES.md"),
            "--map-data", str(project / "docs" / "aerodromes.json"),
            *extra,
        ]
    )


class TestRebuild:
    def test_keeps_the_original_extraction_date(self, project):
        """Otherwise the committed files would churn on every rebuild."""
        assert rebuild(project) == 0
        payload = json.loads((project / "docs" / "aerodromes.json").read_text())
        assert payload["generated"] == EXTRACTED_ON.isoformat()
        assert payload["airac"] == AIRAC
        assert EXTRACTED_ON.isoformat() in (project / "AERODROMES.md").read_text()

    def test_is_a_no_op_when_nothing_changed(self, project):
        rebuild(project)
        before = {
            path.name: path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        rebuild(project)
        after = {
            path.name: path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        assert before == after

    def test_filters_out_aerodromes_without_unleaded_fuel(self, project):
        rebuild(project)
        unleaded = csv_export.read_csv(project / "data" / "aerodromes-unleaded.csv")
        assert [a.icao for a in unleaded] == ["LFDA"]

    def test_explicit_airac_overrides_the_recorded_one(self, project):
        rebuild(project, "--airac", "2026-06-11")
        payload = json.loads((project / "docs" / "aerodromes.json").read_text())
        assert payload["airac"] == "2026-06-11"

    def test_reports_a_missing_dataset(self, tmp_path, capsys):
        exit_code = rebuild(tmp_path)
        assert exit_code == 1
        assert "introuvable" in capsys.readouterr().err


class TestPreviousMetadata:
    def test_reads_a_generated_file(self, project):
        airac, extracted = cli._previous_metadata(project / "docs" / "aerodromes.json")
        assert (airac, extracted) == (AIRAC, EXTRACTED_ON)

    @pytest.mark.parametrize("content", ["", "{}", "not json", '{"airac": "x"}'])
    def test_falls_back_when_unreadable(self, tmp_path, content):
        path = tmp_path / "aerodromes.json"
        path.write_text(content, encoding="utf-8")
        assert cli._previous_metadata(path) == ("unknown", None)

    def test_falls_back_when_absent(self, tmp_path):
        assert cli._previous_metadata(tmp_path / "nope.json") == ("unknown", None)


class TestParser:
    def test_requires_a_subcommand(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args([])

    def test_extract_requires_a_vac_directory(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["extract"])
