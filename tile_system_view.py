# tile_system_view.py
#
# This is the "map module" that mirrors tile_system.py's approach,
# so the background won't drift and re-initializing the tile window
# won't break anything.
#
import os
import pygame
import json
from tkinter import filedialog, simpledialog, messagebox

# Data structures
tiles = {}
player_pos = [0, 0]
player_direction = 0

edit_mode = False
json_link_mode = False
clear_json_link_mode = False
link_area_mode = False

current_image_index = 0
current_loaded_file = None
save_directory = "saves"

map_offset = [0, 0]
selected_tile = None
# Set default to False to hide subgrid drawing
sub_grid_visible = False

background_image = None
background_image_path = None

history = []
history_index = -1
max_history_length = 100

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

# Will be set by view_page.py
bring_window_to_front = None
load_image = None
cv2_to_pygame = None

SQUARE_SIZE = 36

vector_lines = []

class VectorLine:
    def __init__(self, start_tile, start_subgrid_pos, end_tile=None, end_subgrid_pos=None):
        self.start_tile = start_tile
        self.start_subgrid_pos = start_subgrid_pos
        self.end_tile = end_tile
        self.end_subgrid_pos = end_subgrid_pos
        self.is_complete = (end_tile is not None)

def find_vector_with_end_point(tile, subgrid_pos):
    for v in vector_lines:
        if v.end_tile == tile and v.end_subgrid_pos == subgrid_pos:
            return v
    return None

class Tile:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.active = True
        self.directory = None
        self.image_filenames = []
        self.json_file = None
        self.folder_link = None
        self.selected = False
        self.link_areas = {}

        # 3x3 subgrid: center (1,1) is always occupied
        self.subgrid_occupied = [[False]*3 for _ in range(3)]
        self.subgrid_occupied[1][1] = True

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [
                f for f in os.listdir(directory)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf', '.svg'))
            ]
            self.image_filenames.sort()
        else:
            self.image_filenames = []

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []

    def set_json_file(self, json_file):
        self.json_file = json_file

    def clear_json_file(self):
        self.json_file = None

    def toggle_active(self):
        self.active = not self.active

    def add_link_area(self, image_index, area):
        if image_index not in self.link_areas:
            self.link_areas[image_index] = []
        self.link_areas[image_index].append(area)

    def get_current_image(self, image_index):
        if self.directory and self.image_filenames:
            idx_mod = image_index % len(self.image_filenames)
            path = os.path.join(self.directory, self.image_filenames[idx_mod])
            if load_image:
                return load_image(path)
        return None

    def is_subgrid_square_free(self, sub_row, sub_col):
        return not self.subgrid_occupied[sub_row][sub_col]

    def set_subgrid_square_occupied(self, sub_row, sub_col, occupied=True):
        self.subgrid_occupied[sub_row][sub_col] = occupied

    def get_subgrid_square_center(self, sub_row, sub_col, offset_x, offset_y, zoom_factor):
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_pos_x = self.col * scaled_size + offset_x
        tile_pos_y = self.row * scaled_size + offset_y
        sub_sq = scaled_size / 3
        cx = tile_pos_x + sub_col * sub_sq + sub_sq / 2
        cy = tile_pos_y + sub_row * sub_sq + sub_sq / 2
        return (cx, cy)

    def draw(self, surface, offset_x, offset_y, zoom_factor, mouse_pos):
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_x = self.col * scaled_size + offset_x
        tile_y = self.row * scaled_size + offset_y
        rect = pygame.Rect(tile_x, tile_y, scaled_size, scaled_size)

        # Default color
        color = (128, 128, 128) if not self.active else BLACK
        
        # Check if mouse is over this tile and it's active
        highlight = False
        if mouse_pos is not None and self.active:
            mx, my = mouse_pos
            if (tile_x <= mx < tile_x + scaled_size) and (tile_y <= my < tile_y + scaled_size):
                color = (0, 255, 0)  # Green for clickable tiles
                highlight = True

        pygame.draw.rect(surface, color, rect, 3 if highlight else 1)

        if sub_grid_visible:
            sub_s = scaled_size / 3
            for i in range(1, 3):
                pygame.draw.line(surface, color,
                                 (rect.left, rect.top + i * sub_s),
                                 (rect.right, rect.top + i * sub_s), 1)
            for j in range(1, 3):
                pygame.draw.line(surface, color,
                                 (rect.left + j * sub_s, rect.top),
                                 (rect.left + j * sub_s, rect.bottom), 1)

            if self.selected:
                pygame.draw.rect(surface, (255, 0, 0), rect, 3)

def initialize():
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

def get_tile(row, col):
    return tiles.get((row, col))

def create_tile(row, col):
    if (row, col) not in tiles:
        tiles[(row, col)] = Tile(row, col)
    else:
        print(f"[tile_system_view] create_tile => tile already exists => ({row},{col})")

def delete_tile(row, col):
    if (row, col) in tiles:
        t = tiles[(row, col)]
        global vector_lines
        vector_lines = [v for v in vector_lines if v.start_tile != t and v.end_tile != t]
        del tiles[(row, col)]
    else:
        print(f"[tile_system_view] delete_tile => no tile => ({row},{col})")

def get_current_tile():
    return tiles.get((player_pos[0], player_pos[1]))

def draw_board(mouse_pos, offset_x, offset_y, surface, visible_area, zoom_factor):
    """
    Draw the background image first at (offset_x, offset_y), then the tiles.
    This matches tile_system.py approach, ensuring no drifting.
    """
    if background_image is not None:
        bg_w = background_image.get_width() * zoom_factor
        bg_h = background_image.get_height() * zoom_factor
        scaled_bg = pygame.transform.smoothscale(background_image, (int(bg_w), int(bg_h)))
        surface.blit(scaled_bg, (offset_x, offset_y))

    for key, tile_obj in tiles.items():
        tile_obj.draw(surface, offset_x, offset_y, zoom_factor, mouse_pos)

def draw_player(offset_x, offset_y, surface, zoom_factor):
    px = player_pos[1] * SQUARE_SIZE * zoom_factor + offset_x + (SQUARE_SIZE*zoom_factor/2)
    py = player_pos[0] * SQUARE_SIZE * zoom_factor + offset_y + (SQUARE_SIZE*zoom_factor/2)
    arrow_len = (SQUARE_SIZE*zoom_factor)/2
    arrow_w   = (SQUARE_SIZE*zoom_factor)/4
    color = WHITE

    d = player_direction % 8
    if d == 0:  # up
        pygame.draw.polygon(surface, color, [
            (px, py - arrow_len),
            (px - arrow_w, py),
            (px + arrow_w, py)
        ])
    elif d == 1:  # up-right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py - arrow_len),
            (px + arrow_w, py),
            (px, py - arrow_w)
        ])
    elif d == 2:  # right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py),
            (px, py - arrow_w),
            (px, py + arrow_w)
        ])
    elif d == 3:  # down-right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py + arrow_len),
            (px + arrow_w, py),
            (px, py + arrow_w)
        ])
    elif d == 4:  # down
        pygame.draw.polygon(surface, color, [
            (px, py + arrow_len),
            (px - arrow_w, py),
            (px + arrow_w, py)
        ])
    elif d == 5:  # down-left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py + arrow_len),
            (px - arrow_w, py),
            (px, py + arrow_w)
        ])
    elif d == 6:  # left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py),
            (px, py - arrow_w),
            (px, py + arrow_w)
        ])
    elif d == 7:  # up-left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py - arrow_len),
            (px - arrow_w, py),
            (px, py - arrow_w)
        ])

def draw_ghost_tile(row, col, offset_x, offset_y, surface, zoom_factor):
    scaled_size = SQUARE_SIZE * zoom_factor
    tile_x = col * scaled_size + offset_x
    tile_y = row * scaled_size + offset_y
    rect = pygame.Rect(tile_x, tile_y, scaled_size, scaled_size)

    ghost_color = (255, 255, 255, 100)
    ghost_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    ghost_surf.fill(ghost_color)
    surface.blit(ghost_surf, rect)

def move_player(forward=True):
    global player_pos, player_direction, current_image_index
    d = player_direction if forward else (player_direction + 4) % 8

    new_pos = [player_pos[0], player_pos[1]]
    if d == 0:
        new_pos[0] -= 1
    elif d == 1:
        new_pos[0] -= 1
        new_pos[1] += 1
    elif d == 2:
        new_pos[1] += 1
    elif d == 3:
        new_pos[0] += 1
        new_pos[1] += 1
    elif d == 4:
        new_pos[0] += 1
    elif d == 5:
        new_pos[0] += 1
        new_pos[1] -= 1
    elif d == 6:
        new_pos[1] -= 1
    elif d == 7:
        new_pos[0] -= 1
        new_pos[1] -= 1

    t = tiles.get(tuple(new_pos))
    if t and t.active:
        player_pos[:] = new_pos
        if t.image_filenames:
            current_image_index = player_direction % len(t.image_filenames)
        else:
            current_image_index = 0
    else:
        print("[tile_system_view] move_player => cannot move => missing or inactive tile")

def rotate_player(key):
    global player_direction, current_image_index
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8

    t = get_current_tile()
    if t and t.image_filenames:
        current_image_index = player_direction % len(t.image_filenames)
    else:
        current_image_index = 0

def move_player_to_tile(row, col):
    global player_pos, current_image_index
    t = tiles.get((row, col))
    if t and t.active:
        player_pos[:] = [row, col]
        if t.image_filenames:
            current_image_index = player_direction % len(t.image_filenames)
        else:
            current_image_index = 0

def toggle_edit_mode():
    global edit_mode
    edit_mode = not edit_mode

def toggle_json_link_mode():
    global json_link_mode, clear_json_link_mode
    json_link_mode = not json_link_mode
    clear_json_link_mode = False

def toggle_clear_json_link_mode():
    global clear_json_link_mode, json_link_mode
    clear_json_link_mode = not clear_json_link_mode
    json_link_mode = False

def remove_current_tile_folder():
    t = get_current_tile()
    if t:
        t.clear_directory()

def clear_current_tile_json_link():
    t = get_current_tile()
    if t:
        t.clear_json_file()

def set_background_image(image_surface, image_path):
    global background_image, background_image_path
    background_image = image_surface
    background_image_path = image_path

def reset_map_view():
    global map_offset
    map_offset = [0, 0]

def select_tile(row, col):
    global selected_tile
    tile_obj = tiles.get((row, col))
    if tile_obj:
        if selected_tile and selected_tile in tiles:
            tiles[selected_tile].selected = False
        tile_obj.selected = True
        selected_tile = (row, col)

def deselect_tile():
    global selected_tile
    if selected_tile and selected_tile in tiles:
        tiles[selected_tile].selected = False
    selected_tile = None

def move_selected_tile_to(row, col):
    pass  # For view-only mode, we skip actually moving a tile.

###############################################################################
# Undo/Redo (same approach)
###############################################################################
def save_current_state_to_history():
    global history, history_index
    game_state = serialize_game_state()
    if history_index < len(history) - 1:
        history = history[:history_index+1]
    history.append(game_state)
    if len(history) > max_history_length:
        history = history[-max_history_length:]
    history_index = len(history) - 1

def go_back():
    global history_index
    if history_index > 0:
        history_index -= 1
        load_game_state_from_dict(history[history_index])

def go_forward():
    global history_index
    if history_index < len(history) - 1:
        history_index += 1
        load_game_state_from_dict(history[history_index])

###############################################################################
# Load/Save
###############################################################################
def load_game_state():
    global current_loaded_file
    files = [f for f in os.listdir(save_directory) if f.endswith(".json")]
    if not files:
        messagebox.showwarning("Load Game", "No saved games found.")
        return

    selected_file = filedialog.askopenfilename(
        title="Select a saved game",
        initialdir=save_directory,
        filetypes=[("JSON files", "*.json")]
    )
    if not selected_file:
        return

    current_loaded_file = selected_file
    load_game_state_from_file(selected_file)
    if bring_window_to_front:
        bring_window_to_front()

def load_game_state_from_file(filepath):
    global current_loaded_file
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            game_state = json.load(f)
        load_game_state_from_dict(game_state)
    except Exception as e:
        messagebox.showerror("Load Game", f"Error => {e}")

def save_game_state():
    global current_loaded_file
    if current_loaded_file is None:
        filename = simpledialog.askstring("Save Game", "Enter the save file name:")
        if not filename:
            messagebox.showwarning("Save Game", "Save file name cannot be empty.")
            return
        current_loaded_file = os.path.join(save_directory, f"{filename}.json")

    gs = serialize_game_state()
    with open(current_loaded_file, "w", encoding="utf-8") as f:
        json.dump(gs, f, indent=4)

def serialize_game_state():
    out = {
        "player_position": list(player_pos),
        "player_direction": player_direction,
        "tiles": [],
        "background_image_path": background_image_path,
        "grid_visible": sub_grid_visible,
        "map_offset": list(map_offset),
        "vector_lines": []
    }

    for (r, c), tile_obj in tiles.items():
        link_areas_serializable = {}
        for img_idx, areas in tile_obj.link_areas.items():
            link_areas_serializable[str(img_idx)] = []
            for area in areas:
                a_copy = dict(area)
                a_copy['coords'] = list(a_copy['coords'])
                link_areas_serializable[str(img_idx)].append(a_copy)

        tile_data = {
            "row": r,
            "col": c,
            "active": tile_obj.active,
            "directory": tile_obj.directory,
            "image_filenames": tile_obj.image_filenames,
            "json_file": tile_obj.json_file,
            "folder_link": tile_obj.folder_link,
            "link_areas": link_areas_serializable,
            "subgrid_occupied": tile_obj.subgrid_occupied
        }
        out["tiles"].append(tile_data)

    for v in vector_lines:
        vdata = {
            "start_tile": (v.start_tile.row, v.start_tile.col),
            "start_subgrid_pos": v.start_subgrid_pos,
            "end_tile": (v.end_tile.row, v.end_tile.col) if v.end_tile else None,
            "end_subgrid_pos": v.end_subgrid_pos,
            "is_complete": v.is_complete
        }
        out["vector_lines"].append(vdata)

    return out

def load_game_state_from_dict(game_state):
    global player_pos, player_direction, sub_grid_visible, map_offset
    global background_image, background_image_path, vector_lines, tiles, selected_tile
    global current_image_index

    try:
        player_pos[:] = game_state["player_position"]
        player_direction = game_state["player_direction"]
        sub_grid_visible = game_state.get("grid_visible", False)
        map_offset[:] = game_state.get("map_offset", [0, 0])
        background_image_path = game_state.get("background_image_path", None)

        tiles.clear()
        vector_lines.clear()
        selected_tile = None

        for t_data in game_state["tiles"]:
            r = t_data["row"]
            c = t_data["col"]
            tile_obj = Tile(r, c)
            tile_obj.active = t_data.get("active", True)
            tile_obj.directory = t_data.get("directory", None)
            tile_obj.image_filenames = t_data.get("image_filenames", [])
            tile_obj.json_file = t_data.get("json_file", None)
            tile_obj.folder_link = t_data.get("folder_link", None)
            tile_obj.subgrid_occupied = t_data.get("subgrid_occupied", [[False]*3 for _ in range(3)])

            link_areas_data = t_data.get("link_areas", {})
            new_link_areas = {}
            for img_idx_str, areas in link_areas_data.items():
                idx_num = int(img_idx_str)
                area_list = []
                for a in areas:
                    a['coords'] = list(a['coords'])
                    area_list.append(a)
                new_link_areas[idx_num] = area_list
            tile_obj.link_areas = new_link_areas

            tiles[(r, c)] = tile_obj

        # Load background if present
        if background_image_path and os.path.exists(background_image_path):
            if load_image and cv2_to_pygame:
                cv2_img = load_image(background_image_path)
                if cv2_img is not None:
                    background_image = cv2_to_pygame(cv2_img)
                else:
                    background_image = None
            else:
                background_image = None
        else:
            background_image = None

        # Vectors
        for vdata in game_state.get("vector_lines", []):
            st_tile = tiles.get(tuple(vdata["start_tile"]))
            endt_tile = tiles.get(tuple(vdata["end_tile"])) if vdata["end_tile"] else None
            vec = VectorLine(st_tile, vdata["start_subgrid_pos"], endt_tile, vdata["end_subgrid_pos"])
            vec.is_complete = vdata["is_complete"]
            vector_lines.append(vec)

        current_image_index = 0
    except Exception as e:
        messagebox.showerror("Load Game", f"Error => {e}")

def get_subgrid_square_at_pixel(x, y, offset_x, offset_y, zoom_factor):
    scaled = SQUARE_SIZE * zoom_factor
    tile_col = int((x - offset_x) // scaled)
    tile_row = int((y - offset_y) // scaled)
    tile_obj = tiles.get((tile_row, tile_col))
    if tile_obj:
        rel_x = (x - offset_x) - tile_col * scaled
        rel_y = (y - offset_y) - tile_row * scaled
        sub_s = scaled / 3
        sub_c = int(rel_x // sub_s)
        sub_r = int(rel_y // sub_s)
        if 0 <= sub_r < 3 and 0 <= sub_c < 3:
            if sub_r == 1 and sub_c == 1:
                return None, None
            return tile_obj, (sub_r, sub_c)
    return None, None

__all__ = [
    "tiles", "player_pos", "player_direction", "edit_mode", "json_link_mode", "clear_json_link_mode",
    "link_area_mode", "current_image_index", "current_loaded_file", "save_directory", "map_offset",
    "selected_tile", "sub_grid_visible", "background_image", "background_image_path", "history",
    "history_index", "max_history_length", "WHITE", "BLUE", "BLACK", "bring_window_to_front",
    "load_image", "cv2_to_pygame", "SQUARE_SIZE", "vector_lines", "VectorLine", "find_vector_with_end_point",
    "Tile", "initialize", "get_tile", "create_tile", "delete_tile", "get_current_tile",
    "draw_board", "draw_player", "draw_ghost_tile", "move_player", "rotate_player", "move_player_to_tile",
    "toggle_edit_mode", "toggle_json_link_mode", "toggle_clear_json_link_mode",
    "remove_current_tile_folder", "clear_current_tile_json_link", "set_background_image", "reset_map_view",
    "select_tile", "deselect_tile", "move_selected_tile_to", "save_current_state_to_history",
    "go_back", "go_forward", "load_game_state", "load_game_state_from_file", "save_game_state",
    "serialize_game_state", "load_game_state_from_dict", "get_subgrid_square_at_pixel"
]
