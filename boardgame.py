import pygame
import ctypes
import sys
import os
import json
from tkinter import Tk, filedialog, simpledialog, messagebox

# Initialize Pygame
pygame.init()

# Create a resizable Pygame window
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Checkerboard Game")

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

# Player's starting position in the center of the middle board
player_pos = [ROWS // 2, COLS // 2]
player_direction = 0

# Track which 9x9 board the player is currently in (starting in the center of the larger grid)
current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]

# Edit mode toggle
edit_mode = False

# Initialize Tkinter root and hide the main window
root = Tk()
root.withdraw()

# Image management
current_image_index = 0

# Define the directory to save and load the game state JSON files
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)

def load_images_from_directory(directory):
    images = []
    filenames = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            filepath = os.path.join(directory, filename)
            image = pygame.image.load(filepath)
            images.append(image)
            filenames.append(filename)
    return images, filenames

def open_file_explorer():
    directory = filedialog.askdirectory()
    return directory

class Tile:
    def __init__(self, row, col, size):
        self.row = row
        self.col = col
        self.size = size
        self.rect = pygame.Rect(col * size, row * size, size, size)
        self.color = WHITE
        self.active = True  # Tile is active (can be moved to)
        self.image = None
        self.directory = None
        self.images = []
        self.image_filenames = []

    def draw(self, screen, mouse_pos, offset_x, offset_y):
        adjusted_rect = self.rect.move(offset_x, offset_y)
        if adjusted_rect.collidepoint(mouse_pos) and edit_mode:
            self.color = LIGHT_GRAY
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
            self.images, self.image_filenames = load_images_from_directory(directory)

    def clear_directory(self):
        self.directory = None
        self.images = []
        self.image_filenames = []

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
    pygame.draw.rect(screen, GREEN, player_rect)
    
    # Draw direction arrow
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = SQUARE_SIZE // 2
    
    if player_direction == 0:  # Up
        pygame.draw.polygon(screen, RED, [(center_x, center_y - arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 1:  # Up-right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10), (center_x + 10, center_y)])
    elif player_direction == 2:  # Right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 3:  # Down-right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 10), (center_x + 10, center_y)])
    elif player_direction == 4:  # Down
        pygame.draw.polygon(screen, RED, [(center_x, center_y + arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 5:  # Down-left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y + arrow_length), (center_x - 10, center_y), (center_x, center_y + 10)])
    elif player_direction == 6:  # Left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 7:  # Up-left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y - arrow_length), (center_x - 10, center_y), (center_x, center_y - 10)])


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
            player_pos[:] = new_pos
            print(f"Moved to position: {new_pos}")
        else:
            print("Cannot move to inactive tile.")

def rotate_player(key):
    global player_direction, current_image_index
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
        current_image_index = (current_image_index - 1) % len(get_current_tile().images) if get_current_tile().images else 0
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8
        current_image_index = (current_image_index + 1) % len(get_current_tile().images) if get_current_tile().images else 0

def toggle_edit_mode():
    global edit_mode
    edit_mode = not edit_mode

def draw_edit_button():
    button_color = GREEN if edit_mode else RED
    button_text = "Edit Mode: ON" if edit_mode else "Edit Mode: OFF"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, 10, SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_image_button():
    button_color = BLUE
    button_text = "Select Folder"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, (screen_height // 2) - 60, SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_save_button():
    button_color = BLUE
    button_text = "Save Game"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, (screen_height // 2), SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_load_button():
    button_color = BLUE
    button_text = "Load Game"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, (screen_height // 2) + 60, SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_delete_button():
    button_color = BLUE
    button_text = "Remove Folder"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, (screen_height // 2) + 120, SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

def draw_file_list(tile):
    font = pygame.font.Font(None, 24)
    start_y = screen_height - 200  # Start displaying from 200 pixels above the bottom
    for i, filename in enumerate(tile.image_filenames):
        text_surface = font.render(filename, True, BLACK)
        text_rect = text_surface.get_rect(topleft=(screen_width - SIDEBAR_WIDTH + 10, start_y + i * 30))
        screen.blit(text_surface, text_rect)

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
                        "active": tile.active,
                        "directory": tile.directory,
                        "image_filenames": tile.image_filenames
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

    global player_pos, player_direction, current_board, current_image_index

    # Clear the current game state
    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
                    tile.active = True
                    tile.clear_directory()

    try:
        with open(selected_file, "r") as file:
            game_state = json.load(file)
        
        player_pos = game_state["player_position"]
        player_direction = game_state["player_direction"]
        current_board = game_state["current_board"]

        for tile_data in game_state["tiles"]:
            board_index = tile_data["row"] // ROWS * NUM_BOARDS + tile_data["col"] // COLS
            tile = boards[board_index // NUM_BOARDS][board_index % NUM_BOARDS][tile_data["row"] % ROWS][tile_data["col"] % COLS]
            tile.active = tile_data["active"]
            tile.directory = tile_data["directory"]
            tile.image_filenames = tile_data["image_filenames"]
            if tile_data["directory"]:
                tile.images, _ = load_images_from_directory(tile_data["directory"])
                
        current_image_index = 0
        print("Game state loaded.")
    except FileNotFoundError:
        print("No saved game state found.")

# Main game loop
running = True
selected_tile = None
while running:
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
            elif event.key == pygame.K_UP:
                move_player(forward=True)
            elif event.key == pygame.K_DOWN:
                move_player(forward=False)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if edit_button_rect.collidepoint(event.pos):
                    toggle_edit_mode()
                elif image_button_rect.collidepoint(event.pos):
                    directory = open_file_explorer()
                    if directory:
                        current_tile = get_current_tile()
                        current_tile.set_directory(directory)
                        current_image_index = 0  # Reset image index when a new folder is assigned
                elif save_button_rect.collidepoint(event.pos):
                    save_game_state()
                elif load_button_rect.collidepoint(event.pos):
                    load_game_state()
                elif delete_button_rect.collidepoint(event.pos):
                    remove_current_tile_folder()
            elif event.button == 3 and edit_mode:  # Right-click to toggle tile active/inactive in edit mode
                board = get_current_board()
                for row in board:
                    for tile in row:
                        adjusted_rect = tile.rect.move(offset_x, offset_y)
                        if adjusted_rect.collidepoint(event.pos):
                            tile.toggle_active()

    offset_x = screen_width - SIDEBAR_WIDTH + 10
    offset_y = 60

    draw_board(mouse_pos, offset_x, offset_y)
    draw_player(offset_x, offset_y)
    edit_button_rect = draw_edit_button()
    image_button_rect = draw_image_button()
    save_button_rect = draw_save_button()
    load_button_rect = draw_load_button()
    delete_button_rect = draw_delete_button()
    current_tile = get_current_tile()
    if current_tile.directory:
        draw_file_list(current_tile)

    # Draw the image display area
    image_display_area = pygame.Rect(10, 10, screen_width - SIDEBAR_WIDTH - 20, screen_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    # Display the selected image if the current tile has images
    if current_tile.images:
        current_image = current_tile.images[current_image_index]
        scaled_image = pygame.transform.scale(current_image, (image_display_area.width, image_display_area.height))
        screen.blit(scaled_image, (image_display_area.x, image_display_area.y))

    pygame.display.flip()

pygame.quit()
sys.exit()
