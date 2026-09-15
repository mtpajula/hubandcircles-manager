"""The routes page map (ADMIN-UI-SPEC 2.2, 2.6): the track, markers and the last click.

streamlit-folium is imported inside route_map so the views import cleanly under AppTest,
where the tests replace route_map with a stub. Only the tool draws the track; the site never
loads folium.
"""

Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)
Marker = tuple[float, float, str, str]  # (lon, lat, label, colour)

PHOTO_COLOR = "#6B8E23"
HARDEST_COLOR = "#A8323E"
ISSUE_COLOR = "#E8A33D"
CURSOR_COLOR = "#2F6F7E"
TRACK_COLOR = "#333333"  # the cursor must stand out from the line


def route_map(
    lines: list[Coordinates], *, markers: list[Marker], height: int = 380, key: str = "route_map"
) -> tuple[float, float] | None:
    """Draw the track (OSM tiles, fitted) with circle markers; return the last clicked (lon, lat)
    or None. The click persists in the component: the caller decides whether it is new."""
    import folium
    from streamlit_folium import st_folium

    lons = [lon for line in lines for lon, _ in line]
    lats = [lat for line in lines for _, lat in line]
    figure = folium.Map(tiles="OpenStreetMap", control_scale=True)
    figure.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    for line in lines:
        folium.PolyLine([(lat, lon) for lon, lat in line], color=TRACK_COLOR, weight=4).add_to(
            figure
        )
    for lon, lat, label, color in markers:
        folium.CircleMarker(
            (lat, lon), radius=7, color=color, fill=True, fill_opacity=0.9, tooltip=label
        ).add_to(figure)
    state = (
        st_folium(
            figure,
            height=height,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key=key,
        )
        or {}
    )
    clicked = state.get("last_clicked")
    if not clicked:
        return None
    return (float(clicked["lng"]), float(clicked["lat"]))
