"""Small geometry helpers built on shapely."""
import math
from shapely.geometry import shape, Point, LineString
from shapely.prepared import prep


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Area:
    """A GeoJSON geometry with fast point / line tests."""

    def __init__(self, geojson):
        self.geom = shape(geojson)
        if not self.geom.is_valid:
            self.geom = self.geom.buffer(0)
        self._prepared = prep(self.geom)

    def contains(self, lat, lon):
        return self._prepared.contains(Point(lon, lat))

    def crosses_line(self, lat1, lon1, lat2, lon2):
        return self._prepared.intersects(LineString([(lon1, lat1), (lon2, lat2)]))
