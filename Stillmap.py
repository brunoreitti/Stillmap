import pygame
import pygame_gui
import ctypes
import sys
import os
import json
from tkinter import Tk, filedialog, simpledialog, messagebox
from tkinter import messagebox as tk_messagebox
import cv2
import numpy as np

# Initialize Pygame and Pygame GUI
pygame.init()

# Create a resizable Pygame window
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("viewalk software")

icon = pygame.image.load('viewalk.ico')
pygame.display.set_icon(icon)

# Get the handle of the Pygame window
window_handle = pygame.display.get_wm_info()["window"]

# Define constants for Windows messages
SW_MAXIMIZE = 3

# Define the user32 library for sending messages to the window
user32 = ctypes.windll.user32

# Maximize the window
user32.ShowWindow(window_handle, SW_MAXIMIZE)

# Get the screen dimensions after maximizing
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
# Constants
BOARD_SIZE = 300  # Size of the board
ROWS, COLS = 9, 9  # Size of the board
SQUARE_SIZE = BOARD_SIZE // COLS  # Size of each square
SIDEBAR_WIDTH = BOARD_SIZE + 20  # Width of the sidebar to house the board and button
NUM_BOARDS = 3  # Number of 9x9 boards in each direction (3x3 grid)

# Load the logo image
logo = pygame.image.load('väännös1.jpg')  # Replace with the actual path to your logo image

# Resize the logo to fit the sidebar
logo_width, logo_height = logo.get_size()
max_logo_width = SIDEBAR_WIDTH - 20  # Leave some padding on the sides
max_logo_height = 200  # Set a maximum height for the logo

# Calculate the scale factor to fit within the max dimensions
scale_factor = min(max_logo_width / logo_width, max_logo_height / logo_height)
new_logo_width = int(logo_width * scale_factor)
new_logo_height = int(logo_height * scale_factor)
resized_logo = pygame.transform.scale(logo, (new_logo_width, new_logo_height))

# Calculate the position to center the logo in the sidebar
logo_x = (SIDEBAR_WIDTH - new_logo_width) // 2
# Adjust the y-coordinate to position the logo slightly higher
logo_y = screen_height - new_logo_height - 110  # Adjust the 20 to move the logo up or down
resized_logo = pygame.transform.scale(logo, (new_logo_width, new_logo_height))

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 0, 255)
MAIN_BG_COLOR = (50, 50, 50)
SIDEBAR_BG_COLOR = (150, 150, 150)
IMAGE_BG_COLOR = (100, 100, 100)
ORANGE = (255, 189, 89)

# Player's starting position in the center of the middle board
player_pos = [ROWS // 2, COLS // 2]
player_direction = 0

# Track which 9x9 board the player is currently in (starting in the center of the larger grid)
current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]

# Edit mode toggle
edit_mode = False
json_link_mode = False

# Initialize Tkinter root and hide the main window
root = Tk()
root.withdraw()

# Image management
current_image_index = 0

# Define the directory to save and load the game state JSON files
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)

def open_file_explorer():
    directory = filedialog.askdirectory()
    return directory

def load_image_with_orientation(filepath):
    image = cv2.imread(filepath)
    if image is None:
        raise ValueError("Image not found or unable to load")
    try:
        image_exif = cv2.imread(filepath, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        if image_exif is None:
            raise ValueError("Image not found or unable to load with EXIF")
        exif_orientation_tag = 274
        if hasattr(image_exif, 'EXIF'):
            exif = dict(image_exif.EXIF.items())
            orientation = exif.get(exif_orientation_tag)
            if orientation == 3:
                image = cv2.rotate(image, cv2.ROTATE_180)
            elif orientation == 6:
                image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif orientation == 8:
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception as e:
        print(f"EXIF orientation handling failed: {e}")
    return image

def load_image(filepath):
    try:
        return load_image_with_orientation(filepath)
    except Exception as e:
        print(f"Failed to load image {filepath}: {e}")
        return None

def cv2_to_pygame(image):
    """Convert an OpenCV image to a Pygame surface."""
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(image_rgb.tostring(), image_rgb.shape[1::-1], 'RGB')

class Tile:
    def __init__(self, row, col, size):
        self.row = row
        self.col = col
        self.size = size
        self.rect = pygame.Rect(col * size, row * size, size, size)
        self.color = WHITE
        self.active = True  # Tile is active (can be moved to)
        self.directory = None
        self.image_filenames = []
        self.json_file = None  # New attribute to store the associated JSON file

    def draw(self, screen, mouse_pos, offset_x, offset_y):
        adjusted_rect = self.rect.move(offset_x, offset_y)
        if adjusted_rect.collidepoint(mouse_pos) and (edit_mode or json_link_mode):
            self.color = LIGHT_GRAY
        else:
            if self.json_file:
                self.color = BLUE
            else:
                self.color = WHITE if self.active else DARK_GRAY
        pygame.draw.rect(screen, self.color, adjusted_rect)
        pygame.draw.rect(screen, BLACK, adjusted_rect, 1)

    def toggle_active(self):
        self.active = not self.active
        self.color = WHITE if self.active else BLACK

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []

    def set_json_file(self, json_file):
        self.json_file = json_file

    def get_current_image(self, index):
        if not self.directory or index >= len(self.image_filenames):
            return None
        filepath = os.path.join(self.directory, self.image_filenames[index])
        image = load_image(filepath)
        if image is not None:
            return image
        return None

class SidebarContainer:
    def __init__(self, x, y, width, height, padding=10, offset=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.padding = padding
        self.offset = offset
        self.elements = []
        self.total_height = 0

    def add_element(self, element):
        self.elements.append(element)
        self.total_height += element.get_relative_rect().height + self.padding
        self.reposition_elements()

    def add_image(self, image, size):
        self.elements.append((image, size))
        self.total_height += size[1] + self.padding
        self.reposition_elements()

    def reposition_elements(self):
        current_y = self.y + self.height - self.padding - self.offset
        for element in reversed(self.elements):
            if isinstance(element, tuple):
                # It's an image
                image, size = element
                image_rect = image.get_rect()
                image_rect.topleft = (self.x + (self.width - size[0]) // 2, current_y - size[1])
                screen.blit(image, image_rect)
                current_y -= size[1] + self.padding
            else:
                rect = element.get_relative_rect()
                rect.topleft = (self.x + self.padding, current_y - rect.height)
                element.set_relative_position((self.x + self.padding, current_y - rect.height))
                current_y -= rect.height + self.padding

# Create the board with Tile objects for each 9x9 grid in the 3x3 grid
boards = [[[[Tile(row, col, SQUARE_SIZE) for col in range(COLS)] for row in range(ROWS)] for _ in range(NUM_BOARDS)] for _ in range(NUM_BOARDS)]

def get_board(board_index):
    return boards[board_index // NUM_BOARDS][board_index % NUM_BOARDS]

def get_current_board():
    board_index = current_board[0] * NUM_BOARDS + current_board[1]
    return get_board(board_index)

def get_current_tile():
    return get_current_board()[player_pos[0]][player_pos[1]]

def draw_board(mouse_pos, offset_x, offset_y):
    board = get_current_board()
    for row in board:
        for tile in row:
            tile.draw(screen, mouse_pos, offset_x, offset_y)

def draw_player(offset_x, offset_y):
    player_rect = pygame.Rect(player_pos[1] * SQUARE_SIZE, player_pos[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE).move(offset_x, offset_y)
    pygame.draw.rect(screen, ORANGE, player_rect)
    
    # Draw direction arrow
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = SQUARE_SIZE // 2
    
    if player_direction == 0:  # Up
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x, center_y - arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 1:  # Up-right
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10), (center_x + 10, center_y)])
    elif player_direction == 2:  # Right
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x + arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 3:  # Down-right
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 10), (center_x + 10, center_y)])
    elif player_direction == 4:  # Down
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x, center_y + arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 5:  # Down-left
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x - arrow_length, center_y + arrow_length), (center_x - 10, center_y), (center_x, center_y + 10)])
    elif player_direction == 6:  # Left
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x - arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 7:  # Up-left
        pygame.draw.polygon(screen, DARK_GRAY, [(center_x - arrow_length, center_y - arrow_length), (center_x - 10, center_y), (center_x, center_y - 10)])

def move_player(forward=True):
    global current_board

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
        if get_board(new_board[0] * NUM_BOARDS + new_board[1])[new_pos[0]][new_pos[1]].active:
            current_board[:] = new_board
            player_pos[:] = new_pos
            print(f"Moved to new board: {new_board}, new position: {new_pos}")
        else:
            print("Cannot move to inactive tile.")
    else:
        if get_current_board()[new_pos[0]][new_pos[1]].active:
            # Check if the tile has a JSON link
            if get_current_board()[new_pos[0]][new_pos[1]].json_file:
                response = tk_messagebox.askyesno("Trigger JSON Link", "Do you want to trigger the linked JSON file?")
                if response:
                    load_game_state_from_file(get_current_board()[new_pos[0]][new_pos[1]].json_file)
                    return  # Prevent movement to the tile after loading the new game state
                else:
                    return  # Prevent movement to the tile
            else:
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
    edit_button.set_text(f"Edit Mode: {'ON' if edit_mode else 'OFF'}")

def toggle_json_link_mode():
    global json_link_mode
    json_link_mode = not json_link_mode
    json_link_button.set_text(f"JSON Link Mode: {'ON' if json_link_mode else 'OFF'}")

def remove_current_tile_folder():
    current_tile = get_current_tile()
    current_tile.clear_directory()
    print(f"Removed folder association from the current tile.")

# Functions to save and load the game state
def save_game_state():
    filename = simpledialog.askstring("Save Game", "Enter the save file name:")
    if not filename:
        messagebox.showwarning("Save Game", "Save file name cannot be empty.")
        return

    filepath = os.path.join(save_directory, f"{filename}.json")
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
                        "json_file": tile.json_file
                    }
                    game_state["tiles"].append(tile_data)

    with open(filepath, "w") as file:
        json.dump(game_state, file, indent=4)
    print("Game state saved.")

def load_game_state():
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

    load_game_state_from_file(selected_file)

def load_game_state_from_file(filepath):
    global player_pos, player_direction, current_board, current_image_index

    # Clear the current game state
    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
                    tile.active = True
                    tile.clear_directory()

    try:
        with open(filepath, "r") as file:
            game_state = json.load(file)
        
        player_pos = game_state["player_position"]
        player_direction = game_state["player_direction"]
        current_board = game_state["current_board"]

        for tile_data in game_state["tiles"]:
            board_index = tile_data.get("board_row", 0) * NUM_BOARDS + tile_data.get("board_col", 0)
            tile = boards[tile_data.get("board_row", 0)][tile_data.get("board_col", 0)][tile_data["row"]][tile_data["col"]]
            tile.active = tile_data["active"]
            tile.directory = tile_data["directory"]
            tile.image_filenames = tile_data["image_filenames"]
            tile.json_file = tile_data.get("json_file")  # Handle potential missing key
                
        current_image_index = 0
        print("Game state loaded.")
    except FileNotFoundError:
        print("No saved game state found.")

def draw_current_tile_info():
    font = pygame.font.Font(None, 24)
    board_label = f"Board: ({current_board[0]}, {current_board[1]})"
    tile_label = f"Tile: ({player_pos[0]}, {player_pos[1]})"

    board_text = font.render(board_label, True, BLACK)
    tile_text = font.render(tile_label, True, BLACK)

    screen.blit(board_text, (screen_width - SIDEBAR_WIDTH + 10, screen_height - 700))
    screen.blit(tile_text, (screen_width - SIDEBAR_WIDTH + 10, screen_height - 670))

def draw_file_list(current_tile):
    font = pygame.font.Font(None, 24)
    start_y = 730
    for i, filename in enumerate(current_tile.image_filenames):
        text_surface = font.render(filename, True, BLACK)
        screen.blit(text_surface, (screen_width - SIDEBAR_WIDTH + 10, start_y + i * 30))

# Setup pygame_gui manager
manager = pygame_gui.UIManager((screen_width, screen_height))

# Create SidebarContainer with offset to raise elements higher
sidebar_container = SidebarContainer(
    x=screen_width - SIDEBAR_WIDTH,
    y=0,
    width=SIDEBAR_WIDTH,
    height=screen_height,
    offset=125  # Raise the elements by 125 pixels
)

# Create GUI buttons
edit_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="Edit Mode: OFF",
    manager=manager
)
sidebar_container.add_element(edit_button)

json_link_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="JSON Link Mode: OFF",
    manager=manager
)
sidebar_container.add_element(json_link_button)

image_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="Select Folder",
    manager=manager
)
sidebar_container.add_element(image_button)

save_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="Save Game",
    manager=manager
)
sidebar_container.add_element(save_button)

load_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="Load Game",
    manager=manager
)
sidebar_container.add_element(load_button)

delete_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (SIDEBAR_WIDTH - 20, 40)),
    text="Remove Folder",
    manager=manager
)
sidebar_container.add_element(delete_button)

# Add logo to the sidebar
sidebar_container.add_image(resized_logo, (new_logo_width, new_logo_height))

clock = pygame.time.Clock()

# Main game loop
running = True
selected_tile = None
while running:
    time_delta = clock.tick(60) / 1000.0  # Limits the frame rate to 60 FPS
    screen.fill(MAIN_BG_COLOR)  # Fill the main area with the main background color

    # Draw the sidebar background
    sidebar_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, screen_height)
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)

    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:  # Toggle edit mode with 'E' key
                toggle_edit_mode()
            elif event.key == pygame.K_j:  # Toggle JSON link mode with 'J' key
                toggle_json_link_mode()
            elif event.key == pygame.K_UP:
                move_player(forward=True)
            elif event.key == pygame.K_DOWN:
                move_player(forward=False)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            offset_x = screen_width - SIDEBAR_WIDTH + 10
            offset_y = 60
            board = get_current_board()
            for row in board:
                for tile in row:
                    adjusted_rect = tile.rect.move(offset_x, offset_y)
                    if adjusted_rect.collidepoint(event.pos):
                        if edit_mode:
                            tile.toggle_active()
                        elif json_link_mode:
                            selected_file = filedialog.askopenfilename(
                                title="Select a JSON file",
                                initialdir=save_directory,
                                filetypes=[("JSON files", "*.json")]
                            )
                            if selected_file:
                                tile.set_json_file(selected_file)
                        break
        elif event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == edit_button:
                    toggle_edit_mode()
                elif event.ui_element == json_link_button:
                    toggle_json_link_mode()
                elif event.ui_element == image_button:
                    directory = open_file_explorer()
                    if directory:
                        current_tile = get_current_tile()
                        current_tile.set_directory(directory)
                        current_image_index = 0  # Reset image index when a new folder is assigned
                elif event.ui_element == save_button:
                    save_game_state()
                elif event.ui_element == load_button:
                    load_game_state()
                elif event.ui_element == delete_button:
                    remove_current_tile_folder()
        
        manager.process_events(event)

    manager.update(time_delta)

    offset_x = screen_width - SIDEBAR_WIDTH + 10
    offset_y = 60

    draw_board(mouse_pos, offset_x, offset_y)
    draw_player(offset_x, offset_y)
    current_tile = get_current_tile()
    if current_tile.directory:
        draw_file_list(current_tile)

    # Draw the image display area
    image_display_area = pygame.Rect(10, 10, screen_width - SIDEBAR_WIDTH - 20, screen_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    # Display the selected image if the current tile has images
    if current_tile.image_filenames:
        current_image = current_tile.get_current_image(current_image_index)
        if current_image is not None:
            img_height, img_width = current_image.shape[:2]
            
            display_width, display_height = image_display_area.width, image_display_area.height

            # Calculate scale factors and new dimensions
            scale_factor = min(display_width / img_width, display_height / img_height)
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)

            scaled_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            scaled_image_pygame = cv2_to_pygame(scaled_image)
            image_rect = scaled_image_pygame.get_rect(center=image_display_area.center)
            
            screen.blit(scaled_image_pygame, image_rect.topleft)

    draw_current_tile_info()

    sidebar_container.reposition_elements()

    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
