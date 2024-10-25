# tile_system.py

import pygame
import os
import json
import cv2
from tkinter import filedialog, simpledialog, messagebox

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
update_message_box = None
bring_window_to_front = None
load_image = None

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

# Functions related to the tile system
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
            if update_message_box:
                update_message_box()
            print(f"Moved to new board: {new_board}, new position: {new_pos}")
        else:
            print("Cannot move to inactive tile.")
    else:
        if get_current_board()[new_pos[0]][new_pos[1]].active:
            # Check if the tile has a JSON link
            if get_current_board()[new_pos[0]][new_pos[1]].json_file:
                response = messagebox.askyesno("Trigger JSON Link", "Do you want to trigger the linked JSON file?")
                if response:
                    # Save temporary position and direction
                    temporary_player_pos = player_pos[:]
                    temporary_player_direction = player_direction
                    temporary_player_orientation = get_direction_name(player_direction)
                    
                    load_game_state_from_file(get_current_board()[new_pos[0]][new_pos[1]].json_file, link_triggered=True)
                    if bring_window_to_front:
                        bring_window_to_front()  # Ensure window is brought to the front after loading
                    return  # Prevent movement to the tile after loading the new game state
                else:
                    return  # Prevent movement to the tile
            else:
                player_pos[:] = new_pos
            if update_message_box:
                update_message_box()
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
        if update_message_box:
            update_message_box()

def remove_current_tile_folder():
    current_tile = get_current_tile()
    current_tile.clear_directory()
    if update_message_box:
        update_message_box()
    print(f"Removed folder association from the current tile.")

def clear_current_tile_json_link():
    current_tile = get_current_tile()
    current_tile.clear_json_file()
    current_tile.color = WHITE  # Reset color to white to indicate no link
    if update_message_box:
        update_message_box()
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
    
    game_state = {
        "player_position": player_pos,
        "player_direction": player_direction,
        "current_board": current_board,
        "tiles": []
    }

    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
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
                        "folder_link": tile.folder_link  # Include folder link in the save
                    }
                    game_state["tiles"].append(tile_data)

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

def fetch_game_state(filepath):
    try:
        with open(filepath, "r") as file:
            game_state = json.load(file)
        return game_state
    except Exception as e:
        print(f"Error fetching game state: {e}")
        return None

def find_link_tile(game_state, previous_game_file):
    for tile_data in game_state["tiles"]:
        if tile_data.get("json_file") == previous_game_file:
            return tile_data
    return None

def calculate_opposite_tile(tile, direction):
    row, col = tile["row"], tile["col"]
    if direction == "North":
        return row + 1, col
    elif direction == "North-East":
        return row + 1, col - 1
    elif direction == "East":
        return row, col - 1
    elif direction == "South-East":
        return row - 1, col - 1
    elif direction == "South":
        return row - 1, col
    elif direction == "South-West":
        return row - 1, col + 1
    elif direction == "West":
        return row, col + 1
    elif direction == "North-West":
        return row + 1, col + 1
    return None

def get_opposite_direction(direction):
    opposites = {
        "North": "South",
        "North-East": "South-West",
        "East": "West",
        "South-East": "North-West",
        "South": "North",
        "South-West": "North-East",
        "West": "East",
        "North-West": "South-East"
    }
    return opposites[direction]

def get_direction_name(direction):
    directions = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
    return directions[direction]

def load_game_state_from_file(filepath, link_triggered=False):
    global player_pos, player_direction, current_board, current_image_index, temporary_player_pos, temporary_player_direction, temporary_player_orientation, current_loaded_file

    game_state = fetch_game_state(filepath)
    if not game_state:
        return

    previous_game_file = current_loaded_file
    current_loaded_file = filepath

    if link_triggered:
        link_tile = find_link_tile(game_state, previous_game_file)
        if link_tile and temporary_player_orientation:
            opp_direction = get_opposite_direction(temporary_player_orientation)
            opp_row, opp_col = calculate_opposite_tile(link_tile, temporary_player_orientation)

            if 0 <= opp_row < ROWS and 0 <= opp_col < COLS:
                player_pos = [opp_row, opp_col]
            else:
                print("Opposite tile is out of bounds.")
                return

            player_direction = temporary_player_direction
            current_board = [link_tile["board_row"], link_tile["board_col"]]
    else:
        player_pos = game_state["player_position"]
        player_direction = game_state["player_direction"]
        current_board = game_state["current_board"]

    # Clear the current game state
    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
                    tile.active = True
                    tile.clear_directory()

    try:
        for tile_data in game_state["tiles"]:
            tile = boards[tile_data.get("board_row", 0)][tile_data.get("board_col", 0)][tile_data["row"]][tile_data["col"]]
            tile.active = tile_data["active"]
            tile.directory = tile_data["directory"]
            tile.image_filenames = tile_data["image_filenames"]
            tile.json_file = tile_data.get("json_file")
            tile.text_content = tile_data.get("text_content", "")
            tile.folder_link = tile_data.get("folder_link", None)

        current_image_index = 0
        if update_message_box:
            update_message_box()
        print("Game state loaded.")
    except FileNotFoundError:
        print("No saved game state found.")
    except Exception as e:
        print(f"Error loading game state: {e}")
        messagebox.showerror("Load Game", f"Error loading game state: {e}")

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
    # Include other necessary functions and variables
]
