import geocoder
import math
from typing import Union


def decimal_to_osm(lat_deg: float, lon_deg: float, zoom: int) -> tuple:
    """ converts decimal coordinates to internal OSM coordinates"""

    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return xtile, ytile


def osm_to_decimal(tile_x: Union[int, float], tile_y: Union[int, float], zoom: int) -> tuple:
    """ converts internal OSM coordinates to decimal coordinates """

    n = 2.0 ** zoom
    lon_deg = tile_x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def normalize_longitude(lon_deg: float) -> float:
    """ wraps any longitude into the range [-180, 180) """
    return ((lon_deg + 180.0) % 360.0) - 180.0


def wrap_tile_x(tile_x: int, zoom: int) -> int:
    """ maps an unbounded tile x index onto a real tile index 0 .. 2**zoom - 1 """
    return int(tile_x) % (2 ** zoom)


def nearest_world_copy_x(tile_x: float, reference_x: float, zoom: int) -> float:
    """ shifts tile_x by whole world widths so it lies as close as possible to reference_x """
    n = 2 ** zoom
    return tile_x + round((reference_x - tile_x) / n) * n


def unwrapped_tile_positions(position_list: list, reference_x, zoom: int) -> list:
    """ converts a list of (lat, lon) to tile positions where consecutive points never jump by more
        than half a world (so lines take the short way across the 180 meridian), then shifts the whole
        list by whole world widths so its first point is the copy closest to reference_x """
    n = 2 ** zoom
    result = []
    prev_x = None
    for position in position_list:
        x, y = decimal_to_osm(*position, zoom)
        if prev_x is not None:
            x = nearest_world_copy_x(x, prev_x, zoom)
        result.append((x, y))
        prev_x = x
    if result and reference_x is not None:
        offset = round((reference_x - result[0][0]) / n) * n
        result = [(x + offset, y) for x, y in result]
    return result


def convert_coordinates_to_address(deg_x: float, deg_y: float) -> geocoder.osm_reverse.OsmReverse:
    """ returns address object with the following attributes:
        street, housenumber, postal, city, state, country, latlng
        Geocoder docs: https://geocoder.readthedocs.io/api.html#reverse-geocoding """

    result = geocoder.osm([deg_x, deg_y], method="reverse")
    return result


def convert_coordinates_to_city(deg_x: float, deg_y: float) -> str:
    """ returns city name """
    return geocoder.osm([deg_x, deg_y], method="reverse").city


def convert_coordinates_to_country(deg_x: float, deg_y: float) -> str:
    """ returns country name """
    return geocoder.osm([deg_x, deg_y], method="reverse").country