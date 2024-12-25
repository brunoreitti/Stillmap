# tile_system_view.py
#
# A near-identical clone of your tile_system.py, with:
# - 8-direction arrow logic
# - Debug prints in get_current_image(...)
# - os.path.normpath(...) usage
# - No EXIF orientation code
#
# Called by view_page.py for read-only map viewing.

import os
import pygame
import json
from tkinter import filedialog, simpledialog, messagebox

tiles = {}
player_pos = [0, 0]
player_direction = 0
edit_mode = False
json_link_mode = False
clear_json_link_mode = False
current_image_index = 0
current_loaded_file = None
save_directory = "saves"
link_area_mode = False
map_offset = [0, 0]
selected_tile = None
sub_grid_visible = True

background_image = None
background_image_path = None

history = []
history_index = -1
max_history_length = 100

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

# to be set from view_page.py
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
        self.subgrid_occupied = [[False]*3 for _ in range(3)]
        # center sub-square is always inactive
        self.subgrid_occupied[1][1] = True

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [
                f for f in os.listdir(directory)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf', '.svg'))
            ]
            self.image_filenames.sort()
            print(f"[tile_system_view] Set directory for tile ({self.row},{self.col}): {directory}")
        else:
            self.image_filenames = []
            print(f"[tile_system_view] Cleared directory for tile ({self.row},{self.col})")

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []
        print(f"[tile_system_view] Cleared directory for tile ({self.row},{self.col})")

    def set_json_file(self, json_file):
        self.json_file = json_file
        print(f"[tile_system_view] Set JSON file for tile ({self.row},{self.col}): {json_file}")

    def clear_json_file(self):
        self.json_file = None
        print(f"[tile_system_view] Cleared JSON file for tile ({self.row},{self.col})")

    def toggle_active(self):
        self.active = not self.active
        print(f"[tile_system_view] Tile ({self.row},{self.col}) now {'active' if self.active else 'inactive'}")

    def get_current_image(self, image_index):
        """
        Minimal approach: Just normpath + call `load_image` from view_page.py,
        which uses a plain cv2.imread(...) style. No EXIF orientation.
        """
        if self.directory and self.image_filenames:
            if 0 <= image_index < len(self.image_filenames):
                filename = self.image_filenames[image_index]
                path = os.path.normpath(os.path.join(self.directory, filename))
                print(f"[DEBUG] Tile({self.row},{self.col}) get_current_image: dir={self.directory}, file={filename}")
                print(f"[DEBUG]   Full path => {path}")

                if load_image is not None:
                    cv2_img = load_image(path)  # a function from view_page.py
                    if cv2_img is None:
                        print(f"[DEBUG]  -> load_image returned None for path: {path}")
                    return cv2_img
                else:
                    print("[DEBUG]  -> load_image function not set")
            else:
                print(f"[DEBUG] Tile({self.row},{self.col}) image_index out of range: {image_index}")
        else:
            print(f"[DEBUG] Tile({self.row},{self.col}) has no directory or image_filenames.")
        return None

    def add_link_area(self, image_index, area):
        if image_index not in self.link_areas:
            self.link_areas[image_index] = []
        self.link_areas[image_index].append(area)
        print(f"[tile_system_view] Added link area => tile ({self.row},{self.col}), index={image_index}")

    def draw(self, surface, offset_x, offset_y, zoom_factor, mouse_pos):
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_x = self.col * scaled_size + offset_x
        tile_y = self.row * scaled_size + offset_y
        rect = pygame.Rect(tile_x, tile_y, scaled_size, scaled_size)

        color = BLACK
        if not self.active:
            color = (128,128,128)

        pygame.draw.rect(surface, color, rect, 1)
        if sub_grid_visible:
            sub_square_size = scaled_size/3
            for i in range(1,3):
                pygame.draw.line(surface, color,
                                 (rect.left, rect.top + i*sub_square_size),
                                 (rect.right, rect.top + i*sub_square_size), 1)
            for j in range(1,3):
                pygame.draw.line(surface, color,
                                 (rect.left + j*sub_square_size, rect.top),
                                 (rect.left + j*sub_square_size, rect.bottom), 1)

            if self.selected:
                pygame.draw.rect(surface, (255,0,0), rect, 3)


def initialize():
    global save_directory
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

def get_tile(row, col):
    return tiles.get((row, col))

def get_current_tile():
    return get_tile(player_pos[0], player_pos[1])

def create_tile(row, col):
    if (row, col) not in tiles:
        tiles[(row,col)] = Tile(row,col)
        print(f"[tile_system_view] Created tile => ({row},{col})")
    else:
        print(f"[tile_system_view] Tile => ({row},{col}) already exists.")

def delete_tile(row,col):
    if (row,col) in tiles:
        tile_obj = tiles[(row,col)]
        vector_lines[:] = [v for v in vector_lines if v.start_tile!= tile_obj and v.end_tile!= tile_obj]
        del tiles[(row,col)]
        print(f"[tile_system_view] Deleted tile => ({row},{col})")
    else:
        print("[tile_system_view] no tile to delete =>", (row,col))

def draw_board(mouse_pos, offset_x, offset_y, surface, visible_area, zoom_factor):
    if background_image is not None:
        bg_w = background_image.get_width() * zoom_factor
        bg_h = background_image.get_height() * zoom_factor
        scaled_bg = pygame.transform.smoothscale(background_image, (int(bg_w), int(bg_h)))
        surface.blit(scaled_bg, (offset_x, offset_y))

    for key, tile_obj in tiles.items():
        tile_obj.draw(surface, offset_x, offset_y, zoom_factor, mouse_pos)

def draw_player(offset_x, offset_y, surface, zoom_factor):
    global player_direction
    px = player_pos[1] * SQUARE_SIZE* zoom_factor + offset_x + (SQUARE_SIZE* zoom_factor/2)
    py = player_pos[0] * SQUARE_SIZE* zoom_factor + offset_y + (SQUARE_SIZE* zoom_factor/2)
    arrow_len = (SQUARE_SIZE* zoom_factor)/2
    arrow_w   = (SQUARE_SIZE* zoom_factor)/4
    color = (255,255,255)

    # 8 direction arrow
    if player_direction==0: # up
        pygame.draw.polygon(surface, color, [
            (px, py - arrow_len),
            (px - arrow_w, py),
            (px + arrow_w, py)
        ])
    elif player_direction==1: # up-right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py - arrow_len),
            (px + arrow_w, py),
            (px, py - arrow_w)
        ])
    elif player_direction==2: # right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py),
            (px, py - arrow_w),
            (px, py + arrow_w)
        ])
    elif player_direction==3: # down-right
        pygame.draw.polygon(surface, color, [
            (px + arrow_len, py + arrow_len),
            (px + arrow_w, py),
            (px, py + arrow_w)
        ])
    elif player_direction==4: # down
        pygame.draw.polygon(surface, color, [
            (px, py + arrow_len),
            (px - arrow_w, py),
            (px + arrow_w, py)
        ])
    elif player_direction==5: # down-left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py + arrow_len),
            (px - arrow_w, py),
            (px, py + arrow_w)
        ])
    elif player_direction==6: # left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py),
            (px, py - arrow_w),
            (px, py + arrow_w)
        ])
    elif player_direction==7: # up-left
        pygame.draw.polygon(surface, color, [
            (px - arrow_len, py - arrow_len),
            (px - arrow_w, py),
            (px, py - arrow_w)
        ])

def move_player(forward=True):
    global player_pos, player_direction, current_image_index
    d= player_direction
    if not forward:
        d= (d+4) % 8
    new_pos= player_pos[:]
    if d==0:
        new_pos[0]-=1
    elif d==1:
        new_pos[0]-=1
        new_pos[1]+=1
    elif d==2:
        new_pos[1]+=1
    elif d==3:
        new_pos[0]+=1
        new_pos[1]+=1
    elif d==4:
        new_pos[0]+=1
    elif d==5:
        new_pos[0]+=1
        new_pos[1]-=1
    elif d==6:
        new_pos[1]-=1
    elif d==7:
        new_pos[0]-=1
        new_pos[1]-=1

    tile= tiles.get((new_pos[0], new_pos[1]))
    if tile and tile.active:
        player_pos[:]= new_pos
        current_image_index=0
        print(f"[tile_system_view] move_player => new pos {player_pos}")
    else:
        print("[tile_system_view] can't move => tile missing or inactive")

def rotate_player(key):
    global player_direction, current_image_index
    if key== pygame.K_LEFT:
        player_direction= (player_direction-1) % 8
    elif key== pygame.K_RIGHT:
        player_direction= (player_direction+1) % 8

    cur_tile= get_current_tile()
    if cur_tile and cur_tile.image_filenames:
        current_image_index= (current_image_index+1) % len(cur_tile.image_filenames)

    print(f"[tile_system_view] rotate_player => direction={player_direction}, image_index={current_image_index}")

def move_player_to_tile(row, col):
    global player_pos, current_image_index
    tile= tiles.get((row,col))
    if tile and tile.active:
        player_pos[0]= row
        player_pos[1]= col
        current_image_index=0
        print(f"[tile_system_view] move_player_to_tile => new pos= {player_pos}")
    else:
        print("[tile_system_view] can't move => tile missing or inactive")

def toggle_edit_mode():
    global edit_mode
    edit_mode= not edit_mode

def toggle_json_link_mode():
    global json_link_mode, clear_json_link_mode
    json_link_mode= not json_link_mode
    clear_json_link_mode= False

def toggle_clear_json_link_mode():
    global clear_json_link_mode, json_link_mode
    clear_json_link_mode= not clear_json_link_mode
    json_link_mode= False

def remove_current_tile_folder():
    tile= get_current_tile()
    if tile:
        tile.clear_directory()

def clear_current_tile_json_link():
    tile= get_current_tile()
    if tile:
        tile.clear_json_file()

def set_background_image(image_surface, image_path):
    global background_image, background_image_path
    background_image= image_surface
    background_image_path= image_path

def reset_map_view():
    global map_offset
    map_offset= [0,0]
    print("[tile_system_view] reset_map_view => map_offset => [0,0]")

def select_tile(row,col):
    global selected_tile
    t= get_tile(row,col)
    if t:
        if selected_tile and selected_tile in tiles:
            tiles[selected_tile].selected= False
        t.selected= True
        selected_tile= (row,col)
        print(f"[tile_system_view] select_tile => tile ({row},{col})")
    else:
        print("[tile_system_view] no tile =>", (row,col))

def deselect_tile():
    global selected_tile
    if selected_tile and selected_tile in tiles:
        tiles[selected_tile].selected= False
    selected_tile= None

def move_selected_tile_to(row,col):
    pass

def load_game_state():
    global current_loaded_file
    files= [f for f in os.listdir(save_directory) if f.endswith(".json")]
    if not files:
        messagebox.showwarning("Load Game","No saved games found.")
        return

    selected_file= filedialog.askopenfilename(
        title="Select a saved game",
        initialdir=save_directory,
        filetypes=[("JSON files","*.json")]
    )
    if not selected_file:
        return

    current_loaded_file= selected_file
    load_game_state_from_file(selected_file)
    if bring_window_to_front:
        bring_window_to_front()

def load_game_state_from_file(filepath):
    global player_pos, player_direction, current_image_index, current_loaded_file
    try:
        with open(filepath,"r",encoding="utf-8") as f:
            game_state= json.load(f)
        load_game_state_from_dict(game_state)
        print("[tile_system_view] load_game_state_from_file => success =>", filepath)
    except Exception as e:
        print("[tile_system_view] error =>", e)
        messagebox.showerror("Load Game", f"Error => {e}")

def serialize_game_state():
    pass

def load_game_state_from_dict(game_state):
    global player_pos, player_direction, tiles, current_image_index, background_image, background_image_path
    global sub_grid_visible, map_offset, selected_tile, vector_lines

    try:
        player_pos[:] = game_state["player_position"]
        player_direction= game_state["player_direction"]
        sub_grid_visible= game_state.get("grid_visible", True)
        map_offset= game_state.get("map_offset",[0,0])
        background_image_path= game_state.get("background_image_path",None)

        tiles.clear()
        selected_tile= None
        vector_lines.clear()

        for t_data in game_state["tiles"]:
            row= t_data["row"]
            col= t_data["col"]
            tile= Tile(row,col)
            tile.active= t_data.get("active",True)
            tile.directory= t_data.get("directory",None)
            tile.image_filenames= t_data.get("image_filenames",[])
            tile.json_file= t_data.get("json_file",None)
            tile.folder_link= t_data.get("folder_link",None)
            tile.subgrid_occupied= t_data.get("subgrid_occupied", [[False]*3 for _ in range(3)])
            link_areas_data= t_data.get("link_areas",{})
            conv={}
            for img_i_str, areas in link_areas_data.items():
                conv[int(img_i_str)] = areas
            tile.link_areas= conv
            tiles[(row,col)] = tile

        if background_image_path and os.path.exists(background_image_path):
            if load_image:
                # read a plain image from background_image_path
                cv2_img= load_image(background_image_path)
                if cv2_img is not None and cv2_to_pygame is not None:
                    background_image= cv2_to_pygame(cv2_img)
                else:
                    background_image= None
            else:
                background_image= None
        else:
            background_image= None

        for vdata in game_state.get("vector_lines",[]):
            pass

        current_image_index=0
        print("[tile_system_view] load_game_state_from_dict => success")
    except Exception as e:
        print("[tile_system_view] error =>", e)
        messagebox.showerror("Load Game", f"Error => {e}")

def save_current_state_to_history():
    pass

def go_back():
    pass

def go_forward():
    pass

def get_subgrid_square_at_pixel(x, y, offset_x, offset_y, zoom_factor):
    pass
