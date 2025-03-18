import pygame
import pygame_gui
import ctypes
import sys
import os
import json
from tkinter import Tk, filedialog, simpledialog, messagebox
import cv2
import numpy as np
import cairosvg

pygame.init()

screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Image Path")

# Set the window icon
icon = pygame.image.load('mappiclogo.ico')
pygame.display.set_icon(icon)

window_handle = pygame.display.get_wm_info()["window"]
SW_MAXIMIZE = 3
user32 = ctypes.windll.user32
user32.ShowWindow(window_handle, SW_MAXIMIZE)
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# Reserve space for the Windows taskbar (adjustable)
TASKBAR_HEIGHT = 60
effective_screen_height = screen_height - TASKBAR_HEIGHT

BOARD_SIZE = 300
ROWS, COLS = 9, 9
SQUARE_SIZE = BOARD_SIZE // COLS
SIDEBAR_WIDTH = BOARD_SIZE + 20
NUM_BOARDS = 3

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 0, 255)
BUTTON_GRAY = (77, 77, 77)
LIGHTER_BLUE = (68, 71, 90)
MAIN_BG_COLOR = (68, 71, 90)
SIDEBAR_BG_COLOR = (50, 50, 50)
IMAGE_BG_COLOR = (40, 42, 54)
SEPARATOR_COLOR = (120, 120, 120)
SIDEBAR_BORDER_COLOR = (120, 120, 120)
GRID_COLOR = (100, 100, 200)

player_pos = [ROWS // 2, COLS // 2]
player_direction = 0
current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]
edit_mode = False
root = Tk()
root.withdraw()
current_image_index = 0
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)

DEFAULT_IMAGE_PATH = 'earthscanlogo3.svg'
default_image_cv2 = None

def load_image(filepath):
    try:
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        if ext == '.svg':
            return load_svg_image(filepath)
        else:
            image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
            if image is None:
                raise ValueError("Image not found or unable to load")
            return image
    except Exception as e:
        print(f"Failed to load image {filepath}: {e}")
        return None

def cv2_to_pygame(image):
    if image.shape[2] == 4:
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        return pygame.image.frombuffer(image_rgba.tobytes(), image_rgba.shape[1::-1], 'RGBA')
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')

def load_svg_image(svg_path, output_width=None, output_height=None):
    try:
        png_data = cairosvg.svg2png(url=svg_path, output_width=output_width, output_height=output_height)
        nparr = np.frombuffer(png_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        return image
    except Exception as e:
        print(f"Failed to load SVG {svg_path}: {e}")
        return None

default_image_cv2 = load_image(DEFAULT_IMAGE_PATH)
if default_image_cv2 is None:
    print(f"Failed to load default image from {DEFAULT_IMAGE_PATH}")

def display_image(current_image, display_area):
    if current_image is not None:
        img_height, img_width = current_image.shape[:2]
        scale_factor = min(display_area.width / img_width, display_area.height / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        scaled_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        scaled_image_pygame = cv2_to_pygame(scaled_image)
        image_rect = scaled_image_pygame.get_rect(center=display_area.center)
        screen.blit(scaled_image_pygame, image_rect.topleft)
        return image_rect
    return None

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
        self.color = LIGHTER_BLUE
        self.active = True
        self.image = None
        self.directory = None
        self.images = []
        self.image_filenames = []

    def draw(self, screen, mouse_pos, offset_x, offset_y):
        adjusted_rect = self.rect.move(offset_x, offset_y)
        if adjusted_rect.collidepoint(mouse_pos) and edit_mode:
            self.color = LIGHT_GRAY
        else:
            self.color = LIGHTER_BLUE if self.active else BLACK
        pygame.draw.rect(screen, self.color, adjusted_rect)
        pygame.draw.rect(screen, GRID_COLOR, adjusted_rect, 1)

    def toggle_active(self):
        self.active = not self.active
        self.color = LIGHTER_BLUE if self.active else BLACK

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.images, self.image_filenames = load_images_from_directory(directory)

    def clear_directory(self):
        self.directory = None
        self.images = []
        self.image_filenames = []

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
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, player_rect)
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = SQUARE_SIZE // 2
    if player_direction == 0:
        pygame.draw.polygon(screen, WHITE, [(center_x, center_y - arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 1:
        pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10), (center_x + 10, center_y)])
    elif player_direction == 2:
        pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 3:
        pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 10), (center_x + 10, center_y)])
    elif player_direction == 4:
        pygame.draw.polygon(screen, WHITE, [(center_x, center_y + arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 5:
        pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y + arrow_length), (center_x - 10, center_y), (center_x, center_y + 10)])
    elif player_direction == 6:
        pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 7:
        pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y - arrow_length), (center_x - 10, center_y), (center_x, center_y - 10)])

def move_player(forward=True):
    global current_board
    new_pos = player_pos[:]
    direction = player_direction if forward else (player_direction + 4) % 8
    if direction == 0: new_pos[0] -= 1
    elif direction == 1: new_pos[0] -= 1; new_pos[1] += 1
    elif direction == 2: new_pos[1] += 1
    elif direction == 3: new_pos[0] += 1; new_pos[1] += 1
    elif direction == 4: new_pos[0] += 1
    elif direction == 5: new_pos[0] += 1; new_pos[1] -= 1
    elif direction == 6: new_pos[1] -= 1
    elif direction == 7: new_pos[0] -= 1; new_pos[1] -= 1
    new_board = current_board[:]
    if new_pos[0] < 0:
        if current_board[0] > 0: new_pos[0] = ROWS - 1; new_board[0] -= 1
        else: new_pos[0] = 0
    elif new_pos[0] >= ROWS:
        if current_board[0] < NUM_BOARDS - 1: new_pos[0] = 0; new_board[0] += 1
        else: new_pos[0] = ROWS - 1
    if new_pos[1] < 0:
        if current_board[1] > 0: new_pos[1] = COLS - 1; new_board[1] -= 1
        else: new_pos[1] = 0
    elif new_pos[1] >= COLS:
        if current_board[1] < NUM_BOARDS - 1: new_pos[1] = 0; new_board[1] += 1
        else: new_pos[1] = COLS - 1
    if new_board != current_board:
        if get_board(new_board[0] * NUM_BOARDS + new_board[1])[new_pos[0]][new_pos[1]].active:
            current_board[:] = new_board
            player_pos[:] = new_pos
    else:
        if get_current_board()[new_pos[0]][new_pos[1]].active:
            player_pos[:] = new_pos

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
    top_container_buttons[0].set_text(f"Edit Mode: {'ON' if edit_mode else 'OFF'}")

def remove_current_tile_folder():
    current_tile = get_current_tile()
    current_tile.clear_directory()

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
                        "image_filenames": tile.image_filenames
                    }
                    game_state["tiles"].append(tile_data)
    with open(filepath, "w") as file:
        json.dump(game_state, file, indent=4)

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
            board_index = tile_data["board_row"] * NUM_BOARDS + tile_data["board_col"]
            tile = boards[tile_data["board_row"]][tile_data["board_col"]][tile_data["row"]][tile_data["col"]]
            tile.active = tile_data["active"]
            tile.directory = tile_data["directory"]
            tile.image_filenames = tile_data["image_filenames"]
            if tile_data["directory"]:
                tile.images, _ = load_images_from_directory(tile_data["directory"])
        current_image_index = 0
    except FileNotFoundError:
        print("No saved game state found.")

# Sidebar button definitions
manager = pygame_gui.UIManager((screen_width, screen_height))

# Top container (map + Edit Mode button)
top_container_buttons = [
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, SIDEBAR_WIDTH - 30, 40), text="Edit Mode: OFF", manager=manager),
]

# Bottom container (other buttons)
bottom_container_buttons = [
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, SIDEBAR_WIDTH - 30, 40), text="Select Folder", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, SIDEBAR_WIDTH - 30, 40), text="Save Game", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, SIDEBAR_WIDTH - 30, 40), text="Load Game", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, SIDEBAR_WIDTH - 30, 40), text="Remove Folder", manager=manager),
]

clock = pygame.time.Clock()

running = True
while running:
    time_delta = clock.tick(60) / 1000.0
    screen.fill(MAIN_BG_COLOR)

    # Define sidebar rectangle
    sidebar_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH - 10, 10, SIDEBAR_WIDTH, effective_screen_height - 20)
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)
    pygame.draw.rect(screen, SIDEBAR_BORDER_COLOR, sidebar_rect, 1)

    # Sidebar layout constants
    sidebar_padding = 10
    map_offset_x = sidebar_rect.left + sidebar_padding
    map_offset_y = sidebar_rect.top + sidebar_padding
    map_height = BOARD_SIZE
    button_height = 40
    separator_height = 2
    separator_padding = 10 + button_height
    button_width = SIDEBAR_WIDTH - 30
    button_x_center = sidebar_rect.left + (SIDEBAR_WIDTH - button_width) // 2

    # Top container: Map + Edit Mode button
    top_container_height = map_height + sidebar_padding + button_height
    edit_mode_button_y = map_offset_y + map_height + sidebar_padding
    top_container_buttons[0].set_position(pygame.math.Vector2(button_x_center, edit_mode_button_y))

    # Separator line
    separator_y = map_offset_y + top_container_height + separator_padding
    pygame.draw.line(screen, SEPARATOR_COLOR, (sidebar_rect.left + sidebar_padding, separator_y),
                     (sidebar_rect.right - sidebar_padding, separator_y), separator_height)

    # Bottom container: Remaining buttons
    bottom_container_y_start = separator_y + separator_height + sidebar_padding
    bottom_container_height = sidebar_rect.height - top_container_height - (2 * sidebar_padding) - separator_padding - separator_height - sidebar_padding
    num_bottom_buttons = len(bottom_container_buttons)
    if num_bottom_buttons > 0:
        total_button_space = bottom_container_height - ((num_bottom_buttons - 1) * sidebar_padding)
        button_spacing = total_button_space // num_bottom_buttons if total_button_space > 0 else sidebar_padding
        for i, button in enumerate(bottom_container_buttons):
            button_y = bottom_container_y_start + (i * (button_height + sidebar_padding))
            button.set_position(pygame.math.Vector2(button_x_center, button_y))

    # Define and draw main display area with border
    image_display_area = pygame.Rect(10, 10, screen_width - SIDEBAR_WIDTH - 20, effective_screen_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)
    pygame.draw.rect(screen, SIDEBAR_BORDER_COLOR, image_display_area, 1)  # Add 1-pixel border

    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                toggle_edit_mode()
            elif event.key == pygame.K_UP:
                move_player(forward=True)
            elif event.key == pygame.K_DOWN:
                move_player(forward=False)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if edit_mode:
                for row in get_current_board():
                    for tile in row:
                        adjusted_rect = tile.rect.move(map_offset_x, map_offset_y)
                        if adjusted_rect.collidepoint(event.pos):
                            tile.toggle_active()
                            break
        elif event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == top_container_buttons[0]:  # Edit Mode
                    toggle_edit_mode()
                elif event.ui_element == bottom_container_buttons[0]:  # Select Folder
                    directory = open_file_explorer()
                    if directory:
                        get_current_tile().set_directory(directory)
                        current_image_index = 0
                elif event.ui_element == bottom_container_buttons[1]:  # Save Game
                    save_game_state()
                elif event.ui_element == bottom_container_buttons[2]:  # Load Game
                    load_game_state()
                elif event.ui_element == bottom_container_buttons[3]:  # Remove Folder
                    remove_current_tile_folder()
        manager.process_events(event)

    manager.update(time_delta)

    draw_board(mouse_pos, map_offset_x, map_offset_y)
    draw_player(map_offset_x, map_offset_y)
    current_tile = get_current_tile()

    display_image(default_image_cv2, image_display_area)

    if current_tile.images:
        current_image = current_tile.images[current_image_index]
        scaled_image = pygame.transform.scale(current_image, (image_display_area.width, image_display_area.height))
        screen.blit(scaled_image, (image_display_area.x, image_display_area.y))

    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
