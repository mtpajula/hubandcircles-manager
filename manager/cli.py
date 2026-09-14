"""Command-line arguments. Dispatch lives in __main__.py, logic in the package modules."""

import argparse
from pathlib import Path

from manager.settings import ROOT, env


def _data_and_dist(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data", type=Path, default=env("DATA_DIR"), help="source data root")
    p.add_argument("--dist", type=Path, default=ROOT / "dist", help="published data directory")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manager")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("schema", help="generate JSON Schema into schema/")

    b = subcommands.add_parser("build", help="source data → dist/")
    _data_and_dist(b)

    j = subcommands.add_parser("publish", help="assemble the bundle and publish it to targets")
    _data_and_dist(j)
    j.add_argument("--frontend", type=Path, help="frontend directory or zip")
    j.add_argument(
        "--target", action="append", dest="targets", metavar="ID", help="only these targets"
    )
    j.add_argument("--dry-run", action="store_true", help="assemble and check, do not publish")

    e = subcommands.add_parser("preview", help="assemble the bundle and serve it locally")
    _data_and_dist(e)
    e.add_argument("--frontend", type=Path, help="frontend directory or zip")
    e.add_argument("--port", type=int, default=8765)
    e.add_argument("--work-dir", type=Path, default=ROOT, help="where bundle/ is assembled")

    f = subcommands.add_parser(
        "fetch",
        help="fetch a service source and write its snapshot into services/ (7.6)",
        description="Writes the snapshot directly; the Streamlit page shows the diff first and "
        "lets you accept it separately.",
    )
    f.add_argument(
        "source",
        choices=["osm", "visitfinland"],
        help="osm: Overpass query of project.area; visitfinland: DataHub products of the city",
    )
    f.add_argument("--data", type=Path, default=env("DATA_DIR"), help="source data root")
    f.add_argument("--city", help="visitfinland: city filter (default: project.municipality)")

    li = subcommands.add_parser("import-lipas", help="Lipas register → sources/lipas.geojson")
    li.add_argument("--data", type=Path, default=env("DATA_DIR"), help="source data root")
    li.add_argument("--bbox", type=_bbox, help="MINX,MINY,MAXX,MAXY in EPSG:3067 (default: area)")
    li.add_argument("--types", type=_codes, default=(4411, 4412), help="Lipas type codes")
    li.add_argument("--create-routes", action="store_true", help="also create routes/<id>/")
    return parser


def _bbox(text: str) -> tuple[float, float, float, float]:
    values = tuple(float(v) for v in text.split(","))
    if len(values) != 4:
        raise argparse.ArgumentTypeError("expected MINX,MINY,MAXX,MAXY")
    return values


def _codes(text: str) -> tuple[int, ...]:
    return tuple(int(v) for v in text.split(","))
