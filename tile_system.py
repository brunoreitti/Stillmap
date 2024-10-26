# tile_system.py

import pygame
import os
import json
import cv2
from tkinter import filedialog, simpledialog, messagebox
import subprocess

# Constants
ROWS, COLS = 9, 9  # Size of the board

# These will be set from main.py
BOARD_SIZE = None
SQUARE_SIZE = None

# Colors
COLOR1 = (40, 42, 54)
COLOR2 = (68, 71, 90)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)

# Player's starting position and direction
player_pos = [ROWS // 2, COLS // 2]
player_direction = 0

# Current board indices
current_board = [1, 1]  # Center board in 3x3 grid

# Modes and toggles
edit_mode = False
json_link_mode = False
clear_json_link_mode = False
link_area_mode = False  # New mode for adding link areas

# Image management
current_image_index = 0

# Directories and file management
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)
current_loaded_file = None

# Temporary variables for JSON linking
temporary_player_pos = None
temporary_player_direction = None
temporary_player_orientation = None

# Functions to be assigned from main.py
bring_window_to_front = None
load_image = None

# History management
history = []
history_index = -1  # Start at -1 to indicate that no history is recorded yet
max_history_length = 50  # Limit the history size to prevent excessive memory use

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
    def draw(self, surface, mouse_pos, offset_x, offset_y):
        adjusted_rect = self.rect.move(offset_x, offset_y)
        if adjusted_rect.collidepoint(mouse_pos) and (edit_mode or json_link_mode or clear_json_link_mode):
            color = BLACK
        else:
            if self.json_file:
                color = BLUE
            else:
                color = COLOR1 if self.active else BLACK
        pygame.draw.rect(surface, color, adjusted_rect)
        pygame.draw.rect(surface, COLOR2, adjusted_rect, 1)

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

# Initialize the boards
NUM_BOARDS = 3  # Number of 9x9 boards in each direction (3x3 grid)
boards = None  # Will be initialized later

def initialize():
    global boards
    boards = [
        [
            [
                [Tile(row, col) for col in range(COLS)] for row in range(ROWS)
            ] for _ in range(NUM_BOARDS)
        ] for _ in range(NUM_BOARDS)
    ]

# Rest of tile_system.py remains the same, with link area handling added

def get_board(board_index):
    return boards[board_index // NUM_BOARDS][board_index % NUM_BOARDS]

def get_current_board():
    return boards[current_board[0]][current_board[1]]

def get_current_tile():
    return get_current_board()[player_pos[0]][player_pos[1]]

def draw_board(mouse_pos, offset_x, offset_y, surface):
    board = get_current_board()
    for row in board:
        for tile in row:
            tile.draw(surface, mouse_pos, offset_x, offset_y)

def draw_player(offset_x, offset_y, surface):
    player_rect = pygame.Rect(player_pos[1] * SQUARE_SIZE, player_pos[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE).move(offset_x, offset_y)
    pygame.draw.rect(surface, COLOR2, player_rect)
    
    # Draw direction arrow
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = SQUARE_SIZE // 2

    if player_direction == 0:  # Up
        pygame.draw.polygon(surface, WHITE, [(center_x, center_y - arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 1:  # Up-right
        pygame.draw.polygon(surface, WHITE, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10), (center_x + 10, center_y)])
    elif player_direction == 2:  # Right
        pygame.draw.polygon(surface, WHITE, [(center_x + arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 3:  # Down-right
        pygame.draw.polygon(surface, WHITE, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 10), (center_x + 10, center_y)])
    elif player_direction == 4:  # Down
        pygame.draw.polygon(surface, WHITE, [(center_x, center_y + arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 5:  # Down-left
        pygame.draw.polygon(surface, WHITE, [(center_x - arrow_length, center_y + arrow_length), (center_x - 10, center_y), (center_x, center_y + 10)])
    elif player_direction == 6:  # Left
        pygame.draw.polygon(surface, WHITE, [(center_x - arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 7:  # Up-left
        pygame.draw.polygon(surface, WHITE, [(center_x - arrow_length, center_y - arrow_length), (center_x - 10, center_y), (center_x, center_y - 10)])

def move_player(forward=True):
    global current_board, temporary_player_pos, temporary_player_direction, temporary_player_orientation, current_loaded_file

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

    new_board = current_board[:]
    print(f"Attempting to move to position: {new_pos} on board: {new_board}")

    # Check for board transitions
    if new_pos[0] < 0:
        if current_board[0] > 0:
            new_pos[0] = ROWS - 1
            new_board[0] -= 1
        else:
            new_pos[0] = 0
    elif new_pos[0] >= ROWS:
        if current_board[0] < NUM_BOARDS - 1:
            new_pos[0] = 0
            new_board[0] += 1
        else:
            new_pos[0] = ROWS - 1
    if new_pos[1] < 0:
        if current_board[1] > 0:
            new_pos[1] = COLS - 1
            new_board[1] -= 1
        else:
            new_pos[1] = 0
    elif new_pos[1] >= COLS:
        if current_board[1] < NUM_BOARDS - 1:
            new_pos[1] = 0
            new_board[1] += 1
        else:
            new_pos[1] = COLS - 1

    # Check if the new position is in an active tile
    if new_board != current_board:
        if boards[new_board[0]][new_board[1]][new_pos[0]][new_pos[1]].active:
            current_board[:] = new_board
            player_pos[:] = new_pos
            print(f"Moved to new board: {new_board}, new position: {new_pos}")
        else:
            print("Cannot move to inactive tile.")
    else:
        if get_current_board()[new_pos[0]][new_pos[1]].active:
            player_pos[:] = new_pos
            print(f"Moved to position: {new_pos}")
        else:
            print("Cannot move to inactive tile.")

def rotate_player(key):
    global player_direction, current_image_index
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
        current_image_index = (current_image_index - 1) % len(get_current_tile().image_filenames) if get_current_tile().image_filenames else 0
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8
        current_image_index = (current_image_index + 1) % len(get_current_tile().image_filenames) if get_current_tile().image_filenames else 0

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
    new_text = simpledialog.askstring("Edit Description", "Enter new text:", initialvalue=current_tile.text_content)
    if new_text is not None:
        current_tile.text_content = new_text

def remove_current_tile_folder():
    current_tile = get_current_tile()
    current_tile.clear_directory()
    print(f"Removed folder association from the current tile.")

def clear_current_tile_json_link():
    current_tile = get_current_tile()
    current_tile.clear_json_file()
    current_tile.color = WHITE  # Reset color to white to indicate no link
    print(f"Cleared JSON link from the current tile.")

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
    global player_pos, player_direction, current_board, current_image_index

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
        "current_board": current_board.copy(),
        "tiles": []
    }
    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
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
                        "board_row": boards.index(board_row),
                        "board_col": board_row.index(board),
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
    global player_pos, player_direction, current_board, current_image_index

    try:
        player_pos[:] = game_state["player_position"]
        player_direction = game_state["player_direction"]
        current_board[:] = game_state["current_board"]

        # Clear the current game state
        for board_row in boards:
            for board in board_row:
                for row in board:
                    for tile in row:
                        tile.active = True
                        tile.clear_directory()
                        tile.clear_json_file()
                        tile.text_content = ""
                        tile.folder_link = None
                        tile.clear_link_areas()

        for tile_data in game_state["tiles"]:
            board_row = tile_data["board_row"]
            board_col = tile_data["board_col"]
            row = tile_data["row"]
            col = tile_data["col"]
            tile = boards[board_row][board_col][row][col]
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
    'Tile', 'boards', 'get_current_board', 'get_current_tile', 'draw_board', 'draw_player',
    'move_player', 'rotate_player', 'toggle_edit_mode', 'toggle_json_link_mode',
    'toggle_clear_json_link_mode', 'edit_text', 'remove_current_tile_folder',
    'player_pos', 'player_direction', 'current_board', 'edit_mode', 'json_link_mode',
    'clear_json_link_mode', 'current_image_index', 'current_loaded_file',
    'temporary_player_pos', 'temporary_player_direction', 'temporary_player_orientation',
    'save_directory', 'clear_current_tile_json_link', 'get_board',
    'save_game_state', 'load_game_state', 'load_game_state_from_file', 'initialize',
    'link_area_mode', 'open_link_area', 'save_current_state_to_history',
    'go_back', 'go_forward',
    # Include other necessary functions and variables
]
