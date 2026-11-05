"""Player action menus must never be interpreted as bowling-figure names."""
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from live_match_scraper import (
    _without_player_action_menus,
    extract_bowlers,
    get_cricbuzz_match_details,
)


def player_cell(name, player_id=1):
    return f"""
        <div><span class="hover:underline">{name}</span></div>
        <div role="menu" class="invisible">
          <a href="/player-match-performance/match/1/player/{player_id}/bowling?inningsId=1">View match performance</a>
          <a href="/profiles/{player_id}/player">View profile</a>
        </div>
    """


def test_menu_cleanup_preserves_player_labels_and_original_dom():
    soup = BeautifulSoup(player_cell("Arshdeep Singh"), "html.parser")
    cleaned = _without_player_action_menus(soup)
    assert cleaned.get_text(" ", strip=True) == "Arshdeep Singh"
    assert soup.select_one('[role="menu"]') is not None


@pytest.mark.parametrize("quota", [4.0, 10.0])
@pytest.mark.parametrize("name", ["Arshdeep Singh", "Sophie Ecclestone", "Alana King"])
def test_table_bowler_names_exclude_hidden_actions(name, quota):
    html = f"""
      <table><tr><th>Bowling</th><th>Overs</th><th>M</th><th>R</th><th>W</th></tr>
      <tr><td>{player_cell(name)}</td><td>3.2</td><td>0</td><td>25</td><td>2</td></tr>
      </table>
    """
    bowlers = extract_bowlers(BeautifulSoup(html, "html.parser"), quota)
    assert [b["name"] for b in bowlers] == [name]
    assert bowlers[0]["runs_conceded"] == 25
    assert bowlers[0]["wickets"] == 2
    assert bowlers[0]["overs_remaining"] == (0.4 if quota == 4 else 6.4)


@pytest.mark.parametrize("title,quota", [
    ("NZ vs IND, 1st ODI", 10),
    ("NZ vs IND, 1st T20I", 4),
    ("NZ Women vs IND Women, 1st ODI", 10),
    ("NZ Women vs IND Women, 1st T20I", 4),
])
def test_modern_cricbuzz_grid_scorecard_names(title, quota):
    live = f"<html><title>{title}</title><body>IND 79/3 (15.0 ov)</body></html>"
    # Modern div-grid layout: the menu text used to replace every name.
    card = "<div>Bowler O M R W NB WD ECO</div><div>"
    for name, overs, runs, wickets in [
        ("Arshdeep Singh", 3.2, 25, 2),
        ("Auqib Nabi", 3, 27, 0),
        ("Anshul Kamboj", 4, 12, 0),
        ("Gurnoor Brar", 2, 20, 1),
    ]:
        card += f'<div class="scorecard-bowl-grid"><div>{player_cell(name)}</div>'
        card += "".join(f"<div>{v}</div>" for v in [overs, 0, runs, wickets, 0, 0, 6.0])
        card += "</div>"
    card += "</div>"

    def response(url, **kwargs):
        if "scorecard" in url:
            return Mock(status_code=200, text=card)
        if "squads" in url:
            return Mock(status_code=404, text="")
        return Mock(status_code=200, text=live)

    with patch("live_match_scraper.requests.get", side_effect=response):
        match = get_cricbuzz_match_details("1")
    assert [b["name"] for b in match["bowlers"]] == [
        "Arshdeep Singh", "Auqib Nabi", "Anshul Kamboj", "Gurnoor Brar",
    ]
    assert [b["runs_conceded"] for b in match["bowlers"]] == [25, 27, 12, 20]
    assert match["bowlers"][0]["overs_remaining"] == (6.4 if quota == 10 else 0.4)


def test_legacy_profile_link_still_provides_player_name():
    soup = BeautifulSoup('<a href="/profiles/1/bowler">Alana King</a>', "html.parser")
    assert _without_player_action_menus(soup).get_text(strip=True) == "Alana King"
