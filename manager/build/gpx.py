"""Build stage: route.gpx written from the track points (7.11, GPX export).

Only latitude, longitude and elevation of the source points are kept: no timestamps, no
extensions, no creator, no waypoints, so private metadata of the original file never leaks.
"""

import gpxpy.gpx

CREATOR = "hubandcircles-manager"


def export_gpx(segments: list[list[gpxpy.gpx.GPXTrackPoint]], name: str) -> bytes:
    """One <trk> named `name`, one <trkseg> per segment; <ele> only where the source has it."""
    gpx = gpxpy.gpx.GPX()
    gpx.creator = CREATOR
    track = gpxpy.gpx.GPXTrack(name=name)
    gpx.tracks.append(track)
    for points in segments:
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points = [
            gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, elevation=p.elevation) for p in points
        ]
        track.segments.append(segment)
    return gpx.to_xml().encode("utf-8")
