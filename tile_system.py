# tile_system.py

import os
import pygame
import json
from tkinter import filedialog, simpledialog, messagebox

# Initialize necessary variables
tiles = {}  # Dictionary to store tiles with their positions as keys
player_pos = [0, 0]  # Starting position of the player
player_direction = 0  # Starting direction of the player (0-7)
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

# Variables for background image
background_image = None
background_image_path = None

# Variables for history (undo/redo)
history = []
history_index = -1
max_history_length = 100  # Maximum number of states to keep in history

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)  # Ensure grid lines are black

# Placeholder functions to be assigned from main.py
bring_window_to_front = None
load_image = None
cv2_to_pygame = None
SQUARE_SIZE = 36  # Default value; should be set from main.py

def initialize():
    global save_directory
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

class Tile:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.active = True
        self.directory = None  # Directory containing images
        self.image_filenames = []  # List of image filenames
        self.json_file = None
        self.folder_link = None  # Link to another folder
        self.selected = False  # For moving tiles
        self.link_areas = {}  # Key: image index, Value: list of link areas

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [f for f in os.listdir(directory)
                                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf', '.svg'))]
            self.image_filenames.sort()
            print(f"Set directory for tile at ({self.row}, {self.col}): {directory}")
        else:
            self.image_filenames = []
            print(f"Cleared directory for tile at ({self.row}, {self.col})")

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []
        print(f"Cleared directory for tile at ({self.row}, {self.col})")

    def set_json_file(self, json_file):
        self.json_file = json_file
        print(f"Set JSON file for tile at ({self.row}, {self.col}): {json_file}")

    def clear_json_file(self):
        self.json_file = None
        print(f"Cleared JSON file for tile at ({self.row}, {self.col})")

    def toggle_active(self):
        self.active = not self.active
        print(f"Tile at ({self.row}, {self.col}) is now {'active' if self.active else 'inactive'}")

    def draw(self, surface, offset_x, offset_y, zoom_factor, mouse_pos):
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_pos_x = self.col * scaled_size + offset_x
        tile_pos_y = self.row * scaled_size + offset_y
        adjusted_rect = pygame.Rect(tile_pos_x, tile_pos_y, scaled_size, scaled_size)

        if not self.active:
            color = (128, 128, 128)
        else:
            color = BLACK  # Grid lines are black

        pygame.draw.rect(surface, color, adjusted_rect, 1)  # Draw the tile border

        if sub_grid_visible:
            sub_square_size = scaled_size / 3
            for i in range(1, 3):
                # Draw horizontal sub-grid lines
                start_pos = (adjusted_rect.left, adjusted_rect.top + i * sub_square_size)
                end_pos = (adjusted_rect.right, adjusted_rect.top + i * sub_square_size)
                pygame.draw.line(surface, color, start_pos, end_pos, 1)
            for j in range(1, 3):
                # Draw vertical sub-grid lines
                start_pos = (adjusted_rect.left + j * sub_square_size, adjusted_rect.top)
                end_pos = (adjusted_rect.left + j * sub_square_size, adjusted_rect.bottom)
                pygame.draw.line(surface, color, start_pos, end_pos, 1)

            # Highlight sub-square if mouse is over it
            if adjusted_rect.collidepoint(mouse_pos):
                mouse_x, mouse_y = mouse_pos
                rel_x = mouse_x - adjusted_rect.left
                rel_y = mouse_y - adjusted_rect.top
                sub_col = int(rel_x // sub_square_size)
                sub_row = int(rel_y // sub_square_size)
                sub_rect = pygame.Rect(
                    adjusted_rect.left + sub_col * sub_square_size,
                    adjusted_rect.top + sub_row * sub_square_size,
                    sub_square_size,
                    sub_square_size
                )
                pygame.draw.rect(surface, BLUE, sub_rect)

        if self.selected:
            # Draw selection highlight
            pygame.draw.rect(surface, (255, 0, 0), adjusted_rect, 3)

    def get_current_image(self, image_index):
        if self.directory and self.image_filenames:
            image_filename = self.image_filenames[image_index]
            image_path = os.path.join(self.directory, image_filename)
            image_cv2 = load_image(image_path)
            if image_cv2 is not None:
                return image_cv2
            else:
                print(f"Failed to load image: {image_path}")
                return None
        else:
            return None

    def add_link_area(self, image_index, area):
        if image_index not in self.link_areas:
            self.link_areas[image_index] = []
        self.link_areas[image_index].append(area)
        print(f"Added link area to tile at ({self.row}, {self.col}), image index {image_index}")

def get_tile(row, col):
    return tiles.get((row, col))

def create_tile(row, col):
    if (row, col) not in tiles:
        tiles[(row, col)] = Tile(row, col)
        print(f"Created tile at ({row}, {col})")
    else:
        print(f"Tile at ({row}, {col}) already exists.")

def delete_tile(row, col):
    if (row, col) in tiles:
        del tiles[(row, col)]
        print(f"Deleted tile at ({row}, {col})")
    else:
        print(f"No tile at ({row}, {col}) to delete.")

def get_current_tile():
    return get_tile(player_pos[0], player_pos[1])

def draw_board(mouse_pos, offset_x, offset_y, surface, visible_area, zoom_factor):
    # Draw background image if it exists
    if background_image is not None:
        bg_width = background_image.get_width() * zoom_factor
        bg_height = background_image.get_height() * zoom_factor
        bg_image_scaled = pygame.transform.smoothscale(background_image, (int(bg_width), int(bg_height)))
        surface.blit(bg_image_scaled, (offset_x, offset_y))

    for tile_key in tiles:
        tile = tiles[tile_key]
        tile.draw(surface, offset_x, offset_y, zoom_factor, mouse_pos)

def draw_player(offset_x, offset_y, surface, zoom_factor):
    center_x = player_pos[1] * SQUARE_SIZE * zoom_factor + offset_x + SQUARE_SIZE * zoom_factor / 2
    center_y = player_pos[0] * SQUARE_SIZE * zoom_factor + offset_y + SQUARE_SIZE * zoom_factor / 2
    arrow_length = SQUARE_SIZE * zoom_factor / 2
    arrow_width = SQUARE_SIZE * zoom_factor / 4

    # Draw a simple arrow indicating player direction
    if player_direction == 0:  # Up
        pygame.draw.polygon(surface, WHITE, [
            (center_x, center_y - arrow_length),
            (center_x - arrow_width, center_y),
            (center_x + arrow_width, center_y)
        ])
    elif player_direction == 1:  # Up-right
        pygame.draw.polygon(surface, WHITE, [
            (center_x + arrow_length, center_y - arrow_length),
            (center_x + arrow_width, center_y),
            (center_x, center_y - arrow_width)
        ])
    elif player_direction == 2:  # Right
        pygame.draw.polygon(surface, WHITE, [
            (center_x + arrow_length, center_y),
            (center_x, center_y - arrow_width),
            (center_x, center_y + arrow_width)
        ])
    elif player_direction == 3:  # Down-right
        pygame.draw.polygon(surface, WHITE, [
            (center_x + arrow_length, center_y + arrow_length),
            (center_x + arrow_width, center_y),
            (center_x, center_y + arrow_width)
        ])
    elif player_direction == 4:  # Down
        pygame.draw.polygon(surface, WHITE, [
            (center_x, center_y + arrow_length),
            (center_x - arrow_width, center_y),
            (center_x + arrow_width, center_y)
        ])
    elif player_direction == 5:  # Down-left
        pygame.draw.polygon(surface, WHITE, [
            (center_x - arrow_length, center_y + arrow_length),
            (center_x - arrow_width, center_y),
            (center_x, center_y + arrow_width)
        ])
    elif player_direction == 6:  # Left
        pygame.draw.polygon(surface, WHITE, [
            (center_x - arrow_length, center_y),
            (center_x, center_y - arrow_width),
            (center_x, center_y + arrow_width)
        ])
    elif player_direction == 7:  # Up-left
        pygame.draw.polygon(surface, WHITE, [
            (center_x - arrow_length, center_y - arrow_length),
            (center_x - arrow_width, center_y),
            (center_x, center_y - arrow_width)
        ])

def draw_ghost_tile(row, col, offset_x, offset_y, surface, zoom_factor):
    scaled_size = SQUARE_SIZE * zoom_factor
    tile_pos_x = col * scaled_size + offset_x
    tile_pos_y = row * scaled_size + offset_y
    adjusted_rect = pygame.Rect(tile_pos_x, tile_pos_y, scaled_size, scaled_size)
    # Draw a semi-transparent rectangle
    ghost_color = (255, 255, 255, 100)  # White with alpha
    ghost_surface = pygame.Surface((int(adjusted_rect.width), int(adjusted_rect.height)), pygame.SRCALPHA)
    ghost_surface.fill(ghost_color)
    surface.blit(ghost_surface, adjusted_rect.topleft)
    # Draw arrow indicating player direction
    center_x = adjusted_rect.centerx
    center_y = adjusted_rect.centery
    arrow_length = scaled_size // 2
    arrow_width = max(1, int(2 * zoom_factor))
    arrow_color = (0, 0, 0, 150)
    arrow_surface = pygame.Surface((int(adjusted_rect.width), int(adjusted_rect.height)), pygame.SRCALPHA)
    pygame.draw.polygon(arrow_surface, arrow_color, [
        (adjusted_rect.width / 2, adjusted_rect.height / 2 - arrow_length),
        (adjusted_rect.width / 2 - arrow_width, adjusted_rect.height / 2),
        (adjusted_rect.width / 2 + arrow_width, adjusted_rect.height / 2)
    ])
    surface.blit(arrow_surface, adjusted_rect.topleft)

def move_player(forward=True):
    global player_pos, current_image_index

    new_pos = player_pos[:]
    direction = player_direction if forward else (player_direction + 4) % 8  # Adjust direction for backward movement

    if direction == 0:  # Up
        new_pos[0] -= 1
    elif direction == 1:  # Up-right
        new_pos[0] -= 1
        new_pos[1] += 1
    elif direction == 2:  # Right
        new_pos[1] += 1
    elif direction == 3:  # Down-right
        new_pos[0] += 1
        new_pos[1] += 1
    elif direction == 4:  # Down
        new_pos[0] += 1
    elif direction == 5:  # Down-left
        new_pos[0] += 1
        new_pos[1] -= 1
    elif direction == 6:  # Left
        new_pos[1] -= 1
    elif direction == 7:  # Up-left
        new_pos[0] -= 1
        new_pos[1] -= 1

    new_tile = get_tile(new_pos[0], new_pos[1])
    if new_tile and new_tile.active:
        player_pos[:] = new_pos
        current_image_index = 0  # Reset image index when moving to a new tile
        print(f"Moved to position: {new_pos}")
    else:
        print("Cannot move to inactive or non-existent tile.")

def rotate_player(key):
    global player_direction, current_image_index
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8

    current_tile = get_current_tile()
    if current_tile and current_tile.image_filenames:
        current_image_index = (current_image_index + 1) % len(current_tile.image_filenames)
    else:
        current_image_index = 0

def move_player_to_tile(row, col):
    """Move the player arrow to the specified tile if it exists and is active."""
    global player_pos, current_image_index
    target_tile = get_tile(row, col)
    if target_tile and target_tile.active:
        player_pos[:] = [row, col]
        current_image_index = 0  # Reset image index when moving to a new tile
        # No need to reset map view here; handled in main.py if needed
        print(f"Player moved to tile ({row}, {col})")
    else:
        print(f"Cannot move to tile ({row}, {col}). Tile does not exist or is inactive.")

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
    current_tile = get_current_tile()
    if current_tile:
        current_tile.clear_directory()
        print(f"Removed folder association from the current tile.")
    else:
        print("No current tile to remove directory.")

def clear_current_tile_json_link():
    current_tile = get_current_tile()
    if current_tile:
        current_tile.clear_json_file()
        print(f"Cleared JSON link from the current tile.")
    else:
        print("No current tile to clear JSON link.")

def set_background_image(image_surface, image_path):
    global background_image, background_image_path
    background_image = image_surface
    background_image_path = image_path

def reset_map_view():
    global map_offset
    map_offset = [0, 0]
    print("Map view reset to follow the player.")

def select_tile(row, col):
    global selected_tile
    tile = get_tile(row, col)
    if tile is not None:
        # Deselect previous selected tile
        if selected_tile is not None:
            prev_row, prev_col = selected_tile
            prev_tile = get_tile(prev_row, prev_col)
            if prev_tile is not None:
                prev_tile.selected = False
        # Select new tile
        tile.selected = True
        selected_tile = (row, col)
        print(f"Selected tile at ({row}, {col})")
    else:
        print(f"No tile at ({row}, {col}) to select")

def deselect_tile():
    global selected_tile
    if selected_tile is not None:
        row, col = selected_tile
        tile = get_tile(row, col)
        if tile is not None:
            tile.selected = False
        selected_tile = None

def move_selected_tile_to(row, col):
    global selected_tile, tiles
    if selected_tile is not None:
        src_row, src_col = selected_tile
        src_tile = get_tile(src_row, src_col)
        if src_tile is not None:
            dest_tile = get_tile(row, col)
            if dest_tile is None:
                # Move the tile
                tiles[(row, col)] = src_tile
                del tiles[(src_row, src_col)]
                src_tile.row = row
                src_tile.col = col
                src_tile.selected = False
                selected_tile = None
                print(f"Moved tile from ({src_row}, {src_col}) to ({row}, {col})")
            else:
                print(f"Cannot move tile to ({row}, {col}): Tile already exists")
        else:
            print("Selected tile does not exist")
    else:
        print("No tile selected to move")

def save_game_state():
    global current_loaded_file

    if current_loaded_file is None:
        filename = simpledialog.askstring("Save Game", "Enter the save file name:")
        if not filename:
            messagebox.showwarning("Save Game", "Save file name cannot be empty.")
            return
        current_loaded_file = os.path.join(save_directory, f"{filename}.json")

    game_state = serialize_game_state()

    with open(current_loaded_file, "w") as file:
        json.dump(game_state, file, indent=4)
    print("Game state saved.")

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
        bring_window_to_front()  # Ensure window is brought to the front after loading

def load_game_state_from_file(filepath):
    global player_pos, player_direction, current_image_index

    try:
        with open(filepath, "r") as file:
            game_state = json.load(file)

        load_game_state_from_dict(game_state)
        print("Game state loaded from file.")
    except Exception as e:
        print(f"Error loading game state: {e}")
        messagebox.showerror("Load Game", f"Error loading game state: {e}")

def serialize_game_state():
    # Return the current game state as a dictionary
    game_state = {
        "player_position": player_pos.copy(),
        "player_direction": player_direction,
        "tiles": [],
        "background_image_path": background_image_path,  # Save the background image path
        "grid_visible": sub_grid_visible,  # Save the sub-grid visibility state
        "map_offset": map_offset  # Save the map view offset
    }
    for key, tile in tiles.items():
        # Prepare link areas for JSON serialization
        link_areas_serializable = {}
        for img_index, areas in tile.link_areas.items():
            link_areas_serializable[str(img_index)] = []
            for area in areas:
                # Ensure 'coords' are lists
                area_copy = area.copy()
                area_copy['coords'] = list(area_copy['coords'])
                link_areas_serializable[str(img_index)].append(area_copy)
        tile_data = {
            "row": tile.row,
            "col": tile.col,
            "active": tile.active,
            "directory": tile.directory,
            "image_filenames": tile.image_filenames,
            "json_file": tile.json_file,
            "folder_link": tile.folder_link,  # Include folder link in the save
            "link_areas": link_areas_serializable  # Save link areas
        }
        game_state["tiles"].append(tile_data)
    return game_state

def load_game_state_from_dict(game_state):
    global player_pos, player_direction, tiles, current_image_index, background_image, background_image_path, sub_grid_visible, map_offset, selected_tile

    try:
        player_pos[:] = game_state["player_position"]
        player_direction = game_state["player_direction"]
        sub_grid_visible = game_state.get("grid_visible", True)  # Load sub-grid visibility state
        map_offset = game_state.get("map_offset", [0, 0])  # Load map view offset

        # Clear the current game state
        tiles.clear()
        selected_tile = None  # Clear selected tile

        for tile_data in game_state["tiles"]:
            row = tile_data["row"]
            col = tile_data["col"]
            tile = Tile(row, col)
            tile.active = tile_data.get("active", True)
            tile.set_directory(tile_data.get("directory"))
            tile.json_file = tile_data.get("json_file")
            tile.folder_link = tile_data.get("folder_link", None)
            link_areas = tile_data.get("link_areas", {})
            # Convert image_index keys back to integers
            new_link_areas = {}
            for img_index_str, areas in link_areas.items():
                img_index = int(img_index_str)
                new_areas = []
                for area in areas:
                    # Ensure 'coords' are lists
                    area['coords'] = list(area['coords'])
                    new_areas.append(area)
                new_link_areas[img_index] = new_areas
            tile.link_areas = new_link_areas
            tiles[(row, col)] = tile

        # Load background image if path is saved
        background_image_path = game_state.get("background_image_path")
        if background_image_path and os.path.exists(background_image_path):
            bg_image_cv2 = load_image(background_image_path)
            if bg_image_cv2 is not None and cv2_to_pygame is not None:
                background_image = cv2_to_pygame(bg_image_cv2)
            else:
                background_image = None
        else:
            background_image = None

        current_image_index = 0
        print("Game state loaded from dict.")
    except Exception as e:
        print(f"Error loading game state: {e}")
        messagebox.showerror("Load Game", f"Error loading game state: {e}")

def save_current_state_to_history():
    global history, history_index
    # Serialize the current game state
    game_state = serialize_game_state()
    # If we are not at the end of history, discard future history
    if history_index < len(history) - 1:
        history = history[:history_index+1]
    history.append(game_state)
    # Keep history within limits
    if len(history) > max_history_length:
        history = history[-max_history_length:]
    history_index = len(history) - 1

def go_back():
    global history_index
    if history_index > 0:
        history_index -= 1
        game_state = history[history_index]
        load_game_state_from_dict(game_state)
        print("Went back in history.")
    else:
        print("No previous state in history.")

def go_forward():
    global history_index
    if history_index < len(history) - 1:
        history_index += 1
        game_state = history[history_index]
        load_game_state_from_dict(game_state)
        print("Went forward in history.")
    else:
        print("No next state in history.")

# Expose necessary variables and functions for import
__all__ = [
    'Tile', 'initialize', 'get_tile', 'get_current_tile', 'draw_board', 'draw_player',
    'move_player', 'rotate_player', 'toggle_edit_mode', 'toggle_json_link_mode',
    'toggle_clear_json_link_mode', 'remove_current_tile_folder',
    'player_pos', 'player_direction', 'edit_mode', 'json_link_mode',
    'clear_json_link_mode', 'current_image_index', 'current_loaded_file',
    'save_directory', 'clear_current_tile_json_link',
    'save_game_state', 'load_game_state', 'load_game_state_from_file', 'link_area_mode',
    'save_current_state_to_history', 'go_back', 'go_forward',
    'bring_window_to_front', 'load_image', 'SQUARE_SIZE', 'set_background_image',
    'cv2_to_pygame', 'draw_ghost_tile', 'create_tile',
    'map_offset', 'reset_map_view', 'move_player_to_tile',
    'select_tile', 'deselect_tile', 'move_selected_tile_to',
    'delete_tile',  # Include delete_tile in the list
    'sub_grid_visible',  # Include sub_grid_visible in the list
]
