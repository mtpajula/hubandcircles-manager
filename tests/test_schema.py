"""Schema generation is complete and deterministic."""

from manager.schema import generate


def test_generation_produces_six_files_deterministically(tmp_path):
    paths = generate(tmp_path)
    assert sorted(p.name for p in paths) == [
        "catalog.schema.json",
        "project.schema.json",
        "publishedroute.schema.json",
        "publishsettings.schema.json",
        "route.schema.json",
        "theme.schema.json",
    ]
    first = {p.name: p.read_bytes() for p in paths}
    second = {p.name: p.read_bytes() for p in generate(tmp_path)}
    assert first == second
