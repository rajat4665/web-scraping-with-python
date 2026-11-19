import json
import subprocess
import sys
from pathlib import Path

from webscraper.cli import interactive, main
from webscraper.storage import load_db


def test_cli_full_flow(tmp_path, offline, capsys):
    db = str(tmp_path / "db.json")

    assert main(["--db", db, "scrape", "https://example.com", "--alias", "ex"]) == 0
    assert "Saved to" in capsys.readouterr().out

    assert main(["--db", db, "list"]) == 0
    assert "Sample Page" in capsys.readouterr().out

    assert main(["--db", db, "show", "ex", "--field", "all_h2_data"]) == 0
    assert capsys.readouterr().out.splitlines() == ["Section one", "Section two"]

    out_file = tmp_path / "ex.json"
    assert main(["--db", db, "export", "ex", "-o", str(out_file)]) == 0
    assert json.loads(out_file.read_text())["title"] == "Sample Page"

    assert main(["--db", db, "delete", "ex"]) == 0
    assert load_db(db)["scraped_data"] == {}


def test_cli_reports_errors(tmp_path, capsys):
    db = str(tmp_path / "db.json")
    assert main(["--db", db, "show", "missing"]) == 1
    assert "No data saved as 'missing'" in capsys.readouterr().err


def test_interactive_menu_handles_bad_input(tmp_path, offline, monkeypatch, capsys):
    db = str(tmp_path / "db.json")
    answers = iter(["abc", "1", "2", "https://example.com", "", "3", "example.com", "4"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert interactive(db) == 0
    out = capsys.readouterr().out
    assert "Please enter 1, 2, 3 or 4." in out
    assert "No scraped websites yet" in out
    assert "Saved to" in out
    assert "Thank you for using!" in out


def test_python_dash_m_entry_point(tmp_path):
    """`python -m webscraper` works without installing the package."""
    result = subprocess.run(
        [sys.executable, "-m", "webscraper", "--db", str(tmp_path / "db.json"), "list"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],  # the repo root
    )
    assert result.returncode == 0
    assert "No scraped websites yet" in result.stdout
