"""Command line: python -m manager <command>."""

import argparse
import sys

from manager.build import BuildError, build
from manager.build.layers import corridor_layers, corridor_tile_set, read_tracks
from manager.build.read import read_source_data
from manager.cli import build_parser
from manager.publish import PublishError, publish
from manager.publish.preview import serve
from manager.schema import generate
from manager.settings import ROOT, env, load_env, tile_cache_dir
from manager.sources import lipas, osm, visitfinland
from manager.state import mark_built, mark_published
from manager.tiles.fetch import cached_tiles, download_missing, estimate_bytes


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
        mark_built()
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
            if bundle.published:
                mark_published()
            print("Published:" if bundle.published else "Nothing published.")
            for line in bundle.published:
                print(f"  {line}")
        return 0
    if args.command == "preview":
        try:
            bundle = publish(args.data, args.dist, args.frontend, args.work_dir, [])
        except PublishError as e:
            print(f"Preview aborted:\n{e}", file=sys.stderr)
            return 1
        print(bundle.text())
        serve(bundle.directory, args.port)
        return 0
    if args.command == "import-lipas":
        return import_lipas(args)
    if args.command == "fetch":
        return fetch_tiles(args) if args.source == "tiles" else fetch_services(args)
    return 2


def fetch_services(args: argparse.Namespace) -> int:
    try:
        data = read_source_data(args.data)
    except BuildError as e:
        print(f"Fix the source data first:\n{e}", file=sys.stderr)
        return 2
    try:
        if args.source == "osm":
            previous, write = data.osm_services, osm.write_snapshot
            services = osm.parse(osm.fetch(data.project.area))
        else:
            city = args.city or data.project.municipality
            if not city:
                print("Pass --city or set project.municipality in project.json", file=sys.stderr)
                return 2
            url, key = visitfinland.api_settings()
            previous, write = data.visitfinland_services, visitfinland.write_snapshot
            services = visitfinland.parse(visitfinland.fetch(city, url=url, key=key))
    except (ValueError, KeyError, OSError, visitfinland.SourceError) as e:
        print(f"{args.source} fetch aborted:\n{e}", file=sys.stderr)
        return 1
    changes = osm.diff(previous, services)
    print(f"{args.source}: {len(services)} services; {changes.summary()}")
    for label, group in (("+", changes.added), ("-", changes.removed), ("~", changes.changed)):
        for s in group:
            print(f"  {label} {s.id}  {s.category}  {(s.name or {}).get('fi', '')}")
    print(f"Snapshot: {write(args.data, services)}")
    return 0


def fetch_tiles(args: argparse.Namespace) -> int:
    """Download the corridor tiles the cache lacks, one mml_corridor layer at a time (7.3)."""
    key = env("MML_API_KEY")
    if not key:
        print("Set MML_API_KEY in .env", file=sys.stderr)
        return 2
    try:
        data = read_source_data(args.data)
    except BuildError as e:
        print(f"Fix the source data first:\n{e}", file=sys.stderr)
        return 2
    layers = corridor_layers(data, args.layer)
    if not layers:
        print("No mml_corridor layer" + (f" {args.layer}" if args.layer else ""), file=sys.stderr)
        return 2
    cache = tile_cache_dir()
    tracks = read_tracks(data)
    for layer in layers:
        tiles = corridor_tile_set(layer, tracks, data.project.area)
        cached = len(cached_tiles(tiles, cache, layer.source.layer))
        estimate = estimate_bytes(len(tiles), cache, layer.source.layer)
        print(
            f"layer {layer.id}: {len(tiles)} tiles needed, {cached} cached,"
            f" estimated size {estimate / 1e6:.1f} MB"
        )
        report = download_missing(
            tiles,
            cache,
            layer.source.layer,
            key=key,
            progress=lambda done, total: print(f"  {done} / {total} tiles"),
        )
        print(f"layer {layer.id}: {report.text()}")
        for line in report.errors[:10]:
            print(f"  ! {line}")
    print(f"Cache: {cache}")
    return 0


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
