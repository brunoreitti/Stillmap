# tile_system.py

import pygame
import os
import json
from tkinter import filedialog, simpledialog, messagebox

# Constants
SQUARE_SIZE = None  # Will be set from main.py

# Colors
COLOR1 = (40, 42, 54)
COLOR2 = (68, 71, 90)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Player's starting position and direction
player_pos = [0, 0]  # Starting at (0, 0)
player_direction = 0

# Modes and toggles
edit_mode = False
json_link_mode = False
clear_json_link_mode = False
link_area_mode = False  # New mode for adding link areas
grid_visible = True  # Grid lines are visible by default

# Image management
current_image_index = 0

# Directories and file management
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)
current_loaded_file = None

# Functions to be assigned from main.py
bring_window_to_front = None
load_image = None
cv2_to_pygame = None

# History management
history = []
history_index = -1  # Start at -1 to indicate that no history is recorded yet
max_history_length = 50  # Limit the history size to prevent excessive memory use

# Tiles storage
tiles = {}  # Key: (row, col), Value: Tile object

# Background image for the map
background_image = None  # Pygame Surface for the background image
background_image_path = None  # Path to the background image file

# Map view offset for panning
map_offset = [0, 0]  # [offset_x, offset_y]

# Tile class definition
class Tile:
    def __init__(self, row, col):
        # Initialize tile properties
        self.row = row
        self.col = col
        self.size = SQUARE_SIZE
        self.rect = pygame.Rect(col * self.size, row * self.size, self.size, self.size)
        self.color = COLOR2
        self.active = True  # Tile is active (can be moved to)
        self.directory = None
        self.image_filenames = []
        self.json_file = None  # Associated JSON file
        self.text_content = ""  # Text content
        self.folder_link = None  # Folder link
        self.link_areas = {}  # Dictionary with image_index as key

    # Methods for the Tile class
    def draw(self, surface, offset_x, offset_y, zoom_factor):
        scaled_size = self.size * zoom_factor
        tile_pos_x = self.col * scaled_size + offset_x
        tile_pos_y = self.row * scaled_size + offset_y
        adjusted_rect = pygame.Rect(tile_pos_x, tile_pos_y, scaled_size, scaled_size)

        if self.directory:
            # Draw grid lines in green if tile has an image folder assigned
            pygame.draw.rect(surface, GREEN, adjusted_rect, 1)
        elif self.json_file:
            # Draw grid lines in blue if tile has a JSON file assigned
            pygame.draw.rect(surface, BLUE, adjusted_rect, 1)
        else:
            # Draw grid lines in black
            pygame.draw.rect(surface, BLACK, adjusted_rect, 1)

    def toggle_active(self):
        self.active = not self.active

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [f for f in os.listdir(directory)
                                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            self.image_filenames.sort()  # Ensure consistent order

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []

    def set_json_file(self, json_file):
        self.json_file = json_file

    def clear_json_file(self):
        self.json_file = None

    def set_folder_link(self, link):
        self.folder_link = link

    def get_current_image(self, index):
        if not self.directory or index >= len(self.image_filenames):
            return None
        filepath = os.path.join(self.directory, self.image_filenames[index])
        image = load_image(filepath)
        if image is not None:
            return image
        return None

    def get_json_text(self):
        if self.json_file:
            try:
                with open(self.json_file, 'r') as file:
                    data = json.load(file)
                    return json.dumps(data, indent=2)
            except Exception as e:
                return f"Error loading JSON: {e}"
        return "No JSON linked."

    # Methods for link areas
    def add_link_area(self, image_index, area):
        if image_index not in self.link_areas:
            self.link_areas[image_index] = []
        self.link_areas[image_index].append(area)
        print(f"Added link area to tile ({self.row}, {self.col}), image {image_index}: {area}")

    def clear_link_areas(self, image_index=None):
        if image_index is not None:
            if image_index in self.link_areas:
                del self.link_areas[image_index]
                print(f"Cleared link areas for tile ({self.row}, {self.col}), image {image_index}")
        else:
            self.link_areas = {}
            print(f"Cleared all link areas for tile ({self.row}, {self.col})")

# Initialize the tile system
def initialize():
    global tiles
    tiles = {}  # Clear existing tiles if any

def get_tile(row, col):
    return tiles.get((row, col))

def create_tile(row, col):
    key = (row, col)
    if key not in tiles:
        tiles[key] = Tile(row, col)
        print(f"Created tile at position ({row}, {col})")
    else:
        print(f"Tile at position ({row}, {col}) already exists.")

def get_current_tile():
    return get_tile(player_pos[0], player_pos[1])

def draw_board(mouse_pos, offset_x, offset_y, surface, visible_area, zoom_factor):
    # Draw the background image if it exists
    if background_image is not None:
        # Calculate the scale factor for the background image
        bg_width = background_image.get_width()
        bg_height = background_image.get_height()
        scaled_bg_width = bg_width * zoom_factor
        scaled_bg_height = bg_height * zoom_factor

        # Scale the background image
        bg_image_scaled = pygame.transform.scale(background_image, (int(scaled_bg_width), int(scaled_bg_height)))

        # Since the background image represents the entire map, align it at (0, 0)
        bg_pos_x = 0
        bg_pos_y = 0

        # Draw the background image
        surface.blit(bg_image_scaled, (bg_pos_x + offset_x + map_offset[0], bg_pos_y + offset_y + map_offset[1]))

    # Determine the range of tiles to draw based on visible area
    scaled_square_size = SQUARE_SIZE * zoom_factor
    start_col = int((-offset_x - map_offset[0]) // scaled_square_size) - 1
    end_col = int((visible_area.width - offset_x - map_offset[0]) // scaled_square_size) + 1
    start_row = int((-offset_y - map_offset[1]) // scaled_square_size) - 1
    end_row = int((visible_area.height - offset_y - map_offset[1]) // scaled_square_size) + 1

    # Draw existing tiles
    for row in range(start_row, end_row):
        for col in range(start_col, end_col):
            tile = get_tile(row, col)
            if tile:
                tile.draw(surface, offset_x + map_offset[0], offset_y + map_offset[1], zoom_factor)

def draw_player(offset_x, offset_y, surface, zoom_factor):
    scaled_size = SQUARE_SIZE * zoom_factor
    player_rect = pygame.Rect(
        player_pos[1] * scaled_size + offset_x + map_offset[0],
        player_pos[0] * scaled_size + offset_y + map_offset[1],
        scaled_size,
        scaled_size
    )
    # No need to draw a transparent rectangle here

    # Draw direction arrow
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = scaled_size // 2
    arrow_width = max(1, int(10 * zoom_factor))

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
    tile_pos_x = col * scaled_size + offset_x + map_offset[0]
    tile_pos_y = row * scaled_size + offset_y + map_offset[1]
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
        current_tile = get_current_tile()
        if current_tile and current_tile.image_filenames:
            current_image_index = (current_image_index - 1) % len(current_tile.image_filenames)
        else:
            current_image_index = 0
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
        reset_map_view()  # Reset the map view to center on the player
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

def edit_text():
    current_tile = get_current_tile()
    if current_tile:
        new_text = simpledialog.askstring("Edit Description", "Enter new text:", initialvalue=current_tile.text_content)
        if new_text is not None:
            current_tile.text_content = new_text
    else:
        messagebox.showwarning("No Tile", "No tile exists at the player's current position.")

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

# Function to set the background image
def set_background_image(image_surface, image_path):
    global background_image, background_image_path
    background_image = image_surface
    background_image_path = image_path

def reset_map_view():
    global map_offset
    map_offset = [0, 0]
    print("Map view reset to follow the player.")

# Functions to save and load the game state
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
        "grid_visible": grid_visible,  # Save the grid visibility state
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
            "text_content": tile.text_content,  # Include text content in the save
            "folder_link": tile.folder_link,  # Include folder link in the save
            "link_areas": link_areas_serializable  # Save link areas
        }
        game_state["tiles"].append(tile_data)
    return game_state

def load_game_state_from_dict(game_state):
    global player_pos, player_direction, tiles, current_image_index, background_image, background_image_path, grid_visible, map_offset

    try:
        player_pos[:] = game_state["player_position"]
        player_direction = game_state["player_direction"]
        grid_visible = game_state.get("grid_visible", True)  # Load grid visibility state
        map_offset = game_state.get("map_offset", [0, 0])  # Load map view offset

        # Clear the current game state
        tiles.clear()

        for tile_data in game_state["tiles"]:
            row = tile_data["row"]
            col = tile_data["col"]
            tile = Tile(row, col)
            tile.active = tile_data.get("active", True)
            tile.set_directory(tile_data.get("directory"))
            tile.json_file = tile_data.get("json_file")
            tile.text_content = tile_data.get("text_content", "")
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
    'toggle_clear_json_link_mode', 'edit_text', 'remove_current_tile_folder',
    'player_pos', 'player_direction', 'edit_mode', 'json_link_mode',
    'clear_json_link_mode', 'current_image_index', 'current_loaded_file',
    'save_directory', 'clear_current_tile_json_link',
    'save_game_state', 'load_game_state', 'load_game_state_from_file', 'link_area_mode',
    'save_current_state_to_history', 'go_back', 'go_forward',
    'bring_window_to_front', 'load_image', 'SQUARE_SIZE', 'set_background_image',
    'cv2_to_pygame', 'grid_visible', 'draw_ghost_tile', 'create_tile',
    'map_offset', 'reset_map_view', 'move_player_to_tile'  # Added move_player_to_tile to exports
]
