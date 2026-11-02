import tkinter
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .map_widget import TkinterMapView

from .utility_functions import decimal_to_osm, osm_to_decimal, unwrapped_tile_positions


class CanvasPolygon:
    def __init__(self,
                 map_widget: "TkinterMapView",
                 position_list: list,
                 outline_color: str = "#3e97cb",
                 fill_color: str = "gray95",
                 border_width: int = 5,
                 command: Callable = None,
                 name: str = None,
                 data: any = None):

        self.map_widget = map_widget
        self.position_list = position_list  # list with decimal positions
        self.canvas_polygon_positions = []  # list with canvas coordinates positions
        self.canvas_polygon = None
        self.deleted = False

        self.name = name
        self.data = data
        self.outline_color = outline_color
        self.fill_color = fill_color  # can also be None for transparent fill
        self.border_width = border_width
        self.command = command

        self.last_upper_left_tile_pos = None
        self.last_position_list_length = len(self.position_list)
        self.last_world_offset = None
        self.tile_position_cache = None  # unwrapped tile positions, recomputed only when zoom or points change
        self.tile_position_cache_key = None

    def delete(self):
        self.map_widget.canvas.delete(self.canvas_polygon)

        if self in self.map_widget.canvas_polygon_list:
            self.map_widget.canvas_polygon_list.remove(self)

        self.canvas_polygon = None
        self.deleted = True

    def add_position(self, deg_x, deg_y, index=-1):
        if index == -1:
            self.position_list.append((deg_x, deg_y))
        else:
            self.position_list.insert(index, (deg_x, deg_y))
        self.draw()

    def remove_position(self, deg_x, deg_y):
        self.position_list.remove((deg_x, deg_y))
        self.draw()

    def mouse_enter(self, event=None):
        if sys.platform == "darwin":
            self.map_widget.canvas.config(cursor="pointinghand")
        elif sys.platform.startswith("win"):
            self.map_widget.canvas.config(cursor="hand2")
        else:
            self.map_widget.canvas.config(cursor="hand2")  # not tested what it looks like on Linux!

    def mouse_leave(self, event=None):
        self.map_widget.canvas.config(cursor="arrow")

    def click(self, event=None):
        if self.command is not None:
            self.command(self)

    def get_canvas_pos(self, tile_position, widget_tile_width, widget_tile_height):
        # tile_position is an already unwrapped OSM tile position, see draw()

        canvas_pos_x = ((tile_position[0] - self.map_widget.upper_left_tile_pos[0]) / widget_tile_width) * self.map_widget.width
        canvas_pos_y = ((tile_position[1] - self.map_widget.upper_left_tile_pos[1]) / widget_tile_height) * self.map_widget.height

        return canvas_pos_x, canvas_pos_y

    def draw(self, move=False):
        # check if number of positions in position_list has changed
        new_line_length = self.last_position_list_length != len(self.position_list)
        self.last_position_list_length = len(self.position_list)

        # get current tile size of map widget
        widget_tile_width = self.map_widget.lower_right_tile_pos[0] - self.map_widget.upper_left_tile_pos[0]
        widget_tile_height = self.map_widget.lower_right_tile_pos[1] - self.map_widget.upper_left_tile_pos[1]

        # if only moving happened and len(self.position_list) did not change, shift current positions, else calculate new position_list
        # pick the world copy to draw in; if it changed, recompute all canvas positions
        zoom = round(self.map_widget.zoom)
        cache_key = (zoom, id(self.position_list), len(self.position_list))
        if cache_key != self.tile_position_cache_key:
            # expensive trig conversion: only when zoom or the point list changes, not on every mouse move
            self.tile_position_cache = unwrapped_tile_positions(self.position_list, None, zoom)
            self.tile_position_cache_key = cache_key
        n = 2 ** zoom
        if self.tile_position_cache:
            world_offset = round((self.map_widget.get_view_center_tile_x() - self.tile_position_cache[0][0]) / n) * n
        else:
            world_offset = 0
        world_changed = world_offset != self.last_world_offset
        self.last_world_offset = world_offset

        if move is True and self.last_upper_left_tile_pos is not None and new_line_length is False and not world_changed:
            x_move = ((self.last_upper_left_tile_pos[0] - self.map_widget.upper_left_tile_pos[0]) / widget_tile_width) * self.map_widget.width
            y_move = ((self.last_upper_left_tile_pos[1] - self.map_widget.upper_left_tile_pos[1]) / widget_tile_height) * self.map_widget.height

            for i in range(0, len(self.position_list) * 2, 2):
                self.canvas_polygon_positions[i] += x_move
                self.canvas_polygon_positions[i + 1] += y_move
        else:
            self.canvas_polygon_positions = []
            for tile_x, tile_y in self.tile_position_cache:
                canvas_position = self.get_canvas_pos((tile_x + world_offset, tile_y), widget_tile_width, widget_tile_height)
                self.canvas_polygon_positions.append(canvas_position[0])
                self.canvas_polygon_positions.append(canvas_position[1])

        if not self.deleted:
            if self.canvas_polygon is None:
                self.map_widget.canvas.delete(self.canvas_polygon)
                self.canvas_polygon = self.map_widget.canvas.create_polygon(self.canvas_polygon_positions,
                                                                            width=self.border_width,
                                                                            outline=self.outline_color,
                                                                            joinstyle=tkinter.ROUND,
                                                                            stipple="gray25",
                                                                            tag="polygon")
                if self.fill_color is None:
                    self.map_widget.canvas.itemconfig(self.canvas_polygon, fill="")
                else:
                    self.map_widget.canvas.itemconfig(self.canvas_polygon, fill=self.fill_color)

                if self.command is not None:
                    self.map_widget.canvas.tag_bind(self.canvas_polygon, "<Enter>", self.mouse_enter)
                    self.map_widget.canvas.tag_bind(self.canvas_polygon, "<Leave>", self.mouse_leave)
                    self.map_widget.canvas.tag_bind(self.canvas_polygon, "<Button-1>", self.click)
            else:
                self.map_widget.canvas.coords(self.canvas_polygon, self.canvas_polygon_positions)
        else:
            self.map_widget.canvas.delete(self.canvas_polygon)
            self.canvas_polygon = None

        self.map_widget.manage_z_order()
        self.last_upper_left_tile_pos = self.map_widget.upper_left_tile_pos