"""Command line: python -m manager <command>."""

import argparse
import sys

from manager.build import BuildError, build
from manager.build.read import read_source_data
from manager.cli import build_parser
from manager.publish import PublishError, publish
from manager.publish.preview import serve
from manager.schema import generate
from manager.settings import ROOT, load_env
from manager.sources import lipas


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = build_parser().parse_args(argv)

    if args.command == "schema":
        for path in generate(ROOT / "schema"):
            print(path.relative_to(ROOT))
        return 0
    if args.data is None:
        print("Source data missing: pass --data or set DATA_DIR in .env", file=sys.stderr)
        return 2
    if args.command == "build":
        try:
            report = build(args.data, args.dist)
        except BuildError as e:
            print(f"Build aborted, dist/ unchanged:\n{e}", file=sys.stderr)
            return 1
        print(report.text())
        return 0
    if args.command == "publish":
        try:
            bundle = publish(args.data, args.dist, args.frontend, ROOT, args.targets, args.dry_run)
        except PublishError as e:
            print(f"Publish aborted:\n{e}", file=sys.stderr)
            return 1
        print(bundle.text())
        if args.dry_run:
            print("Dry run, nothing published.")
        else:
            print("Published:" if bundle.published else "Nothing published.")
            for line in bundle.published:
                print(f"  {line}")
        return 0
    if args.command == "preview":
        try:
            bundle = publish(args.data, args.dist, args.frontend, ROOT, [])
        except PublishError as e:
            print(f"Preview aborted:\n{e}", file=sys.stderr)
            return 1
        print(bundle.text())
        serve(bundle.directory, args.port)
        return 0
    if args.command == "import-lipas":
        return import_lipas(args)
    return 2


def import_lipas(args: argparse.Namespace) -> int:
    bbox = args.bbox
    if bbox is None:
        try:
            bbox = lipas.bbox_to_3067(read_source_data(args.data).project.area)
        except BuildError as e:
            print(f"Pass --bbox or fix project.json:\n{e}", file=sys.stderr)
            return 2
    try:
        routes = lipas.group(lipas.fetch(bbox, args.types))
    except (ValueError, OSError) as e:
        print(f"Lipas import aborted:\n{e}", file=sys.stderr)
        return 1
    print(f"Snapshot: {lipas.write_snapshot(args.data, routes)}")
    for r in routes:
        print(f"{r.lipas_id}  {r.type_code}  {r.name_fi}  {r.length_km}")
    if args.create_routes:
        print("\n".join(lipas.import_routes(args.data, routes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
