"""Merge of the service sources (5.5): priority, duplicates, manual markers, expired issues."""

from datetime import date

from manager.build.services import merge, normalised_name, same_place, services_collection
from manager.models import ManualMarker, Service

TODAY = date(2026, 9, 13)


def service(id: str, name: str | None = None, source: str = "osm", **fields) -> Service:
    return Service(
        id=id,
        name={"fi": name} if name else None,
        category=fields.pop("category", "cafe"),
        source=source,
        location=fields.pop("location", (25.72, 66.5)),
        **fields,
    )


def test_normalised_name_strips_case_punctuation_and_spacing():
    assert normalised_name(service("a", "Kahvila  Napa & Piirit!")) == "kahvila napa piirit"
    assert normalised_name(service("a")) == ""


def test_same_place_needs_50_m_and_similar_names():
    a = service("a", "Kahvila Napa", location=(25.72, 66.5))
    within = service("b", "Kahvila NAPA", location=(25.72, 66.5003))  # 33 m north
    beyond = service("c", "Kahvila Napa", location=(25.72, 66.5006))  # 67 m north
    other = service("d", "Pizzeria Roma", location=(25.72, 66.5003))
    nameless = service("e", None, location=(25.72, 66.5003))
    assert same_place(a, within) and same_place(a, nameless)
    assert not same_place(a, beyond) and not same_place(a, other)


def test_merge_priority_manual_over_visitfinland_over_osm():
    osm = [service("osm:node/1", "Kahvila Napa", url="https://osm.test")]
    vf = [service("vf:1", "Kahvila Napa", source="visitfinland", url="https://vf.test")]
    manual = [
        ManualMarker(
            id="manual:napa", name={"fi": "Kahvila Napa"}, category="cafe", location=(25.72, 66.5)
        )
    ]
    result = merge(osm, vf, manual, today=TODAY)
    assert [s.id for s in result.services] == ["manual:napa"] and result.warnings == []
    assert [s.id for s in merge(osm, vf, [], today=TODAY).services] == ["vf:1"]
    assert [s.id for s in merge(osm, [], [], today=TODAY).services] == ["osm:node/1"]


def test_merge_keeps_distinct_points():
    osm = [
        service("osm:node/1", "Kahvila Napa"),
        service("osm:node/2", "Kahvila Napa", location=(25.73, 66.5)),
    ]
    assert len(merge(osm, [], [], today=TODAY).services) == 2


def test_replaces_overrides_fields_and_keeps_id_and_source():
    osm = [service("osm:node/1", "Kahvila Nappa", url="https://old.test")]
    marker = ManualMarker(replaces="osm:node/1", name={"fi": "Kahvila Napa", "en": "Cafe Hub"})
    result = merge(osm, [], [marker], today=TODAY)
    (merged,) = result.services
    assert merged.id == "osm:node/1" and merged.source == "osm"
    assert merged.name == {"fi": "Kahvila Napa", "en": "Cafe Hub"}
    assert merged.url == "https://old.test" and result.warnings == []


def test_hidden_marker_drops_the_target():
    osm = [
        service("osm:node/1", "Kahvila Napa"),
        service("osm:node/2", "Toinen", location=(25.8, 66.5)),
    ]
    result = merge(osm, [], [ManualMarker(replaces="osm:node/1", hidden=True)], today=TODAY)
    assert [s.id for s in result.services] == ["osm:node/2"] and result.warnings == []


def test_expired_issue_is_dropped():
    issues = [
        service(
            "manual:tree", "Kaatunut puu", "manual", category="issue", valid_until="2026-09-12"
        ),
        service(
            "manual:ice",
            "Jäätä",
            "manual",
            category="issue",
            valid_until="2026-09-13",
            location=(25.8, 66.5),
        ),
        service("manual:open", "Avoin", "manual", category="issue", location=(25.9, 66.5)),
    ]
    result = merge(issues, [], [], today=TODAY)
    assert [s.id for s in result.services] == ["manual:ice", "manual:open"]


def test_missing_target_is_a_warning():
    markers = [
        ManualMarker(id="manual:fix", replaces="osm:node/404", name={"fi": "x"}),
        ManualMarker(replaces="osm:node/405", hidden=True),
    ]
    result = merge([service("osm:node/1", "a")], [], markers, today=TODAY)
    assert [s.id for s in result.services] == ["osm:node/1"]
    assert result.warnings == [
        "manual marker manual:fix: replaces 'osm:node/404', which no longer exists",
        "manual marker (no id): replaces 'osm:node/405', which no longer exists",
    ]


def test_new_marker_without_required_fields_is_a_warning_not_a_crash():
    result = merge([], [], [ManualMarker(id="manual:half", name={"fi": "x"})], today=TODAY)
    assert result.services == []
    assert result.warnings == [
        "manual marker manual:half: category: Field required; location: Field required"
    ]


def test_new_marker_becomes_a_manual_service():
    marker = ManualMarker(
        id="manual:cafe-x", name={"fi": "X"}, category="cafe", location=(25.72, 66.5)
    )
    (merged,) = merge([], [], [marker], today=TODAY).services
    assert merged.source == "manual" and merged.id == "manual:cafe-x"
    collection = services_collection([merged])
    assert collection["features"][0]["properties"] == {
        "id": "manual:cafe-x",
        "name": {"fi": "X"},
        "category": "cafe",
        "source": "manual",
    }
    assert collection["features"][0]["geometry"] == {"type": "Point", "coordinates": [25.72, 66.5]}
