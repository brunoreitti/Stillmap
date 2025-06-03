import pygame
import pygame_gui
import sys
import os
import json
import platform
import asyncio
from PIL import Image, ExifTags, ImageOps
from tkinter import Tk, filedialog, simpledialog, messagebox
import cv2
import numpy as np
import cairosvg
from datetime import datetime
import ctypes

pygame.init()

os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Image Path")

if sys.platform == "win32":
    hwnd = pygame.display.get_wm_info()['window']
    SW_MAXIMIZE = 3
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

icon = pygame.image.load('mappiclogo.ico')
pygame.display.set_icon(icon)

ROWS, COLS = 9, 9
NUM_BOARDS = 3
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (200, 200, 200)
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
CARD_BG_COLOR = (255, 255, 255)

player_pos = [ROWS // 2, COLS // 2]
player_direction = 0
current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]
edit_mode = False
root = Tk()
root.withdraw()
current_image_index = 0
save_directory = "saved_game_states"
os.makedirs(save_directory, exist_ok=True)

DEFAULT_IMAGE_PATH = 'image_path_logo8.svg'
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

def display_image(current_image, display_area, is_pygame_surface=False):
    if current_image is not None:
        if is_pygame_surface:
            img_width, img_height = current_image.get_size()
        else:
            img_height, img_width = current_image.shape[:2]
        
        scale_factor = min(display_area.width / img_width, display_area.height / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)

        if is_pygame_surface:
            scaled_image = pygame.transform.smoothscale(current_image, (new_width, new_height))
        else:
            scaled_image_cv2 = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            scaled_image = cv2_to_pygame(scaled_image_cv2)

        image_rect = scaled_image.get_rect(center=display_area.center)
        screen.blit(scaled_image, image_rect.topleft)
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

def get_image_date(image_path):
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    if decoded == "DateTimeOriginal":
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
    return None

def resize_image(input_path, output_path, max_dimension=2400):
    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        original_width, original_height = img.size
        if original_width > original_height:
            new_width = max_dimension
            new_height = int(original_height * (max_dimension / original_width))
        else:
            new_height = max_dimension
            new_width = int(original_width * (max_dimension / original_height))
        resized_image = img.resize((new_width, new_height), Image.LANCZOS)
        resized_image.save(output_path, quality=95, exif=img.info.get('exif'))

def organize_photos(input_directory, max_dimension=2400):
    files = []
    for f in os.listdir(input_directory):
        file_path = os.path.join(input_directory, f)
        if os.path.isfile(file_path):
            exif_date = get_image_date(file_path)
            if exif_date:
                files.append((f, exif_date.timestamp()))
            else:
                creation_date = os.path.getctime(file_path)
                modification_date = os.path.getmtime(file_path)
                files.append((f, min(creation_date, modification_date)))
    
    files.sort(key=lambda x: x[1])
    sorted_files = [f[0] for f in files]
    total_files = len(sorted_files)
    
    output_directory = os.path.join(input_directory, "organized_photos")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    batch_size = 8
    processed_files = 0
    bar_width = 400
    bar_height = 20
    bar_x = (screen_width - bar_width) // 2
    bar_y = (effective_screen_height - bar_height) // 2
    progress_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    font = pygame.font.Font(None, 36)
    console_font = pygame.font.Font(None, 18)

    card_padding = 20
    card_width = bar_width + 2 * card_padding
    card_height = bar_height + 180
    card_x = (screen_width - card_width) // 2
    card_y = (effective_screen_height - card_height) // 2
    card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
    shadow_offset = 5
    shadow_rect = pygame.Rect(card_x + shadow_offset, card_y + shadow_offset, card_width, card_height)
    console_height = 100
    console_y = card_y + 90
    console_rect = pygame.Rect(card_x + 5, console_y + 5, card_width - 10, console_height - 10)

    console_lines = []
    animation_offset = 0

    for i in range(0, len(sorted_files), batch_size):
        folder_name = str((i // batch_size) + 1)
        new_folder_path = os.path.join(output_directory, folder_name)
        os.makedirs(new_folder_path, exist_ok=True)
        
        for j in range(batch_size):
            if i + j < len(sorted_files):
                src_file = os.path.join(input_directory, sorted_files[i + j])
                dst_file = os.path.join(new_folder_path, f"{j + 1}.jpg")
                resize_image(src_file, dst_file, max_dimension)
                processed_files += 1
                console_lines.append(f"Processed: {sorted_files[i + j]} -> {dst_file}")
                
                for frame in range(3):
                    animation_offset = (3 - frame) * 3
                    progress = processed_files / total_files
                    progress_width = int(bar_width * progress)
                    progress_surface.fill((0, 0, 0, 0))

                    pygame.draw.rect(progress_surface, (0, 0, 0, 50), shadow_rect, border_radius=10)
                    pygame.draw.rect(progress_surface, CARD_BG_COLOR, card_rect, border_radius=10)
                    bar_rect = pygame.Rect(bar_x, card_y + 60, bar_width, bar_height)
                    pygame.draw.rect(progress_surface, (100, 100, 100), bar_rect, border_radius=10)
                    pygame.draw.rect(progress_surface, (0, 255, 0), (bar_x, card_y + 60, progress_width, bar_height), border_radius=10)

                    text_clear_rect = pygame.Rect(card_x, card_y, card_width, 40)
                    progress_surface.fill(CARD_BG_COLOR, text_clear_rect)
                    main_text = font.render(f"Organizing Photos: {int(progress * 100)}%", True, (0, 0, 0))
                    main_text_rect = main_text.get_rect(center=(screen_width // 2, card_y + 40))
                    progress_surface.blit(main_text, main_text_rect)

                    pygame.draw.rect(progress_surface, (100, 100, 100), console_rect, 2)
                    progress_surface.fill((0, 0, 0), console_rect)

                    line_height = console_font.get_height()
                    max_lines = (console_height - 10) // line_height
                    visible_lines = console_lines[-max_lines:]
                    for idx, line in enumerate(reversed(visible_lines)):
                        console_text = console_font.render(line, True, (255, 255, 255))
                        text_rect = console_text.get_rect(topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height + animation_offset))
                        if text_rect.top >= console_rect.top:
                            if text_rect.right > console_rect.right:
                                clipped_text = line[:int((console_rect.right - text_rect.left) / (console_font.size('a')[0]))]
                                console_text = console_font.render(clipped_text, True, (255, 255, 255))
                                text_rect = console_text.get_rect(topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height + animation_offset))
                            progress_surface.blit(console_text, text_rect)

                    screen.blit(progress_surface, (0, 0))
                    pygame.display.flip()
                    pygame.time.wait(10)

                animation_offset = 0

        progress = processed_files / total_files
        progress_width = int(bar_width * progress)
        progress_surface.fill((0, 0, 0, 0))

        pygame.draw.rect(progress_surface, (0, 0, 0, 50), shadow_rect, border_radius=10)
        pygame.draw.rect(progress_surface, CARD_BG_COLOR, card_rect, border_radius=10)
        bar_rect = pygame.Rect(bar_x, card_y + 60, bar_width, bar_height)
        pygame.draw.rect(progress_surface, (100, 100, 100), bar_rect, border_radius=10)
        pygame.draw.rect(progress_surface, (0, 255, 0), (bar_x, card_y + 60, progress_width, bar_height), border_radius=10)

        text_clear_rect = pygame.Rect(card_x, card_y, card_width, 40)
        progress_surface.fill(CARD_BG_COLOR, text_clear_rect)
        main_text = font.render(f"Organizing Photos: {int(progress * 100)}%", True, (0, 0, 0))
        main_text_rect = main_text.get_rect(center=(screen_width // 2, card_y + 40))
        progress_surface.blit(main_text, main_text_rect)

        pygame.draw.rect(progress_surface, (100, 100, 100), console_rect, 2)
        progress_surface.fill((0, 0, 0), console_rect)

        line_height = console_font.get_height()
        max_lines = (console_height - 10) // line_height
        visible_lines = console_lines[-max_lines:]
        for idx, line in enumerate(reversed(visible_lines)):
            console_text = console_font.render(line, True, (255, 255, 255))
            text_rect = console_text.get_rect(topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height))
            if text_rect.top >= console_rect.top:
                if text_rect.right > console_rect.right:
                    clipped_text = line[:int((console_rect.right - text_rect.left) / (console_font.size('a')[0]))]
                    console_text = console_font.render(clipped_text, True, (255, 255, 255))
                    text_rect = console_text.get_rect(topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height))
                progress_surface.blit(console_text, text_rect)

        screen.blit(progress_surface, (0, 0))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            manager.process_events(event)
    
    root = Tk()
    root.withdraw()
    root.iconbitmap('mappiclogo.ico')
    root.after(4000, root.destroy)
    messagebox.showinfo(
        "Success",
        f"Photos successfully organized into:\n{output_directory}",
        icon='info',
        parent=root
    )

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

boards = [[[[Tile(row, col, 0) for col in range(COLS)] for row in range(ROWS)] for _ in range(NUM_BOARDS)] for _ in range(NUM_BOARDS)]

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

def draw_all_boards(mouse_pos, screen_width, screen_height, effective_screen_height):
    full_map_size = BOARD_SIZE * NUM_BOARDS
    scale_factor = min(screen_width / full_map_size, effective_screen_height / full_map_size)
    scaled_size = int(BOARD_SIZE * scale_factor)
    scaled_square_size = scaled_size // COLS
    offset_x = (screen_width - (scaled_size * NUM_BOARDS)) // 2
    offset_y = (effective_screen_height - (scaled_size * NUM_BOARDS)) // 2

    for board_row in range(NUM_BOARDS):
        for board_col in range(NUM_BOARDS):
            board = boards[board_row][board_col]
            board_offset_x = offset_x + (board_col * scaled_size)
            board_offset_y = offset_y + (board_row * scaled_size)
            for row in board:
                for tile in row:
                    adjusted_rect = pygame.Rect(
                        board_offset_x + (tile.col * scaled_square_size),
                        board_offset_y + (tile.row * scaled_square_size),
                        scaled_square_size,
                        scaled_square_size
                    )
                    if adjusted_rect.collidepoint(mouse_pos) and edit_mode:
                        tile.color = LIGHT_GRAY
                    else:
                        tile.color = LIGHTER_BLUE if tile.active else BLACK
                    pygame.draw.rect(screen, tile.color, adjusted_rect)
                    pygame.draw.rect(screen, GRID_COLOR, adjusted_rect, 1)
            if board_row == current_board[0] and board_col == current_board[1]:
                player_rect = pygame.Rect(
                    board_offset_x + (player_pos[1] * scaled_square_size),
                    board_offset_y + (player_pos[0] * scaled_square_size),
                    scaled_square_size,
                    scaled_square_size
                )
                pygame.draw.rect(screen, SIDEBAR_BG_COLOR, player_rect)
                center_x = player_rect.centerx
                center_y = player_rect.centery
                arrow_length = scaled_square_size // 2
                if player_direction == 0:
                    pygame.draw.polygon(screen, WHITE, [(center_x, center_y - arrow_length), (center_x - 5, center_y), (center_x + 5, center_y)])
                elif player_direction == 1:
                    pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 5), (center_x + 5, center_y)])
                elif player_direction == 2:
                    pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y), (center_x, center_y - 5), (center_x, center_y + 5)])
                elif player_direction == 3:
                    pygame.draw.polygon(screen, WHITE, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 5), (center_x + 5, center_y)])
                elif player_direction == 4:
                    pygame.draw.polygon(screen, WHITE, [(center_x, center_y + arrow_length), (center_x - 5, center_y), (center_x + 5, center_y)])
                elif player_direction == 5:
                    pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y + arrow_length), (center_x - 5, center_y), (center_x, center_y + 5)])
                elif player_direction == 6:
                    pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y), (center_x, center_y - 5), (center_x, center_y + 5)])
                elif player_direction == 7:
                    pygame.draw.polygon(screen, WHITE, [(center_x - arrow_length, center_y - arrow_length), (center_x - 5, center_y), (center_x, center_y - 5)])

def draw_player(offset_x, offset_y, square_size):
    player_rect = pygame.Rect(player_pos[1] * square_size, player_pos[0] * square_size, square_size, square_size).move(offset_x, offset_y)
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, player_rect)
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = square_size // 2
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

manager = pygame_gui.UIManager((800, 600))

top_container_buttons = [
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Edit Mode: OFF", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 100, 40), text="Hide Sidebar", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 80, 40), text="Big Map", manager=manager),
]

bottom_container_buttons = [
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Select Folder", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Save Game", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Load Game", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Remove Folder", manager=manager),
    pygame_gui.elements.UIButton(relative_rect=pygame.Rect(0, 0, 120, 40), text="Orga/derez", manager=manager),
]

sidebar_visible = True
maximized = False

def toggle_sidebar():
    global sidebar_visible, maximized
    sidebar_visible = not sidebar_visible
    top_container_buttons[1].set_text("Show Sidebar" if not sidebar_visible else "Hide Sidebar")
    if not maximized:
        update_button_positions()

def toggle_maximize():
    global maximized, sidebar_visible
    maximized = not maximized
    if maximized:
        sidebar_visible = False
        top_container_buttons[1].set_position(pygame.math.Vector2(-1000, -1000))
        top_container_buttons[0].set_position(pygame.math.Vector2(-1000, -1000))
        for button in bottom_container_buttons:
            button.set_position(pygame.math.Vector2(-1000, -1000))
        top_container_buttons[2].set_position(pygame.math.Vector2(screen_width - 90, 10))
        top_container_buttons[2].set_text("Normal View")
    else:
        sidebar_visible = True
        top_container_buttons[2].set_text("Big Map")
        update_button_positions()

def update_button_positions():
    button_width = SIDEBAR_WIDTH - (2 * sidebar_padding)
    button_x_center = sidebar_rect.left + (SIDEBAR_WIDTH - button_width) // 2
    edit_mode_button_y = map_offset_y + BOARD_SIZE + sidebar_padding
    top_container_buttons[0].set_position(pygame.math.Vector2(button_x_center, edit_mode_button_y) if sidebar_visible and not maximized else pygame.math.Vector2(-1000, -1000))
    top_container_buttons[0].set_dimensions((button_width, button_height) if sidebar_visible and not maximized else (120, 40))
    if sidebar_visible and not maximized:
        top_container_buttons[1].set_position(pygame.math.Vector2(sidebar_rect.left + sidebar_padding, sidebar_rect.top + sidebar_padding))
    else:
        button_x = image_display_area.right - 100 - 1 - 5
        button_y = sidebar_padding
        top_container_buttons[1].set_position(pygame.math.Vector2(button_x, button_y))
    top_container_buttons[2].set_position(pygame.math.Vector2(sidebar_rect.left + SIDEBAR_WIDTH - sidebar_padding - 90, sidebar_rect.top + sidebar_padding) if sidebar_visible and not maximized else pygame.math.Vector2(-1000, -1000))
    for i, button in enumerate(bottom_container_buttons):
        button_y = bottom_container_y_start + (i * (button_height + sidebar_spacing))
        button.set_position(pygame.math.Vector2(button_x_center, button_y) if sidebar_visible and not maximized else pygame.math.Vector2(-1000, -1000))
        button.set_dimensions((button_width, button_height) if sidebar_visible and not maximized else (120, 40))

async def setup():
    global screen_width, screen_height, effective_screen_height, manager
    screen_width, screen_height = screen.get_size()
    effective_screen_height = screen_height
    manager.set_window_resolution((screen_width, screen_height))

async def update_loop():
    global screen_width, screen_height, effective_screen_height

    screen_width, screen_height = screen.get_size()
    effective_screen_height = screen_height

    manager.set_window_resolution((screen_width, screen_height))

    global SIDEBAR_WIDTH, sidebar_padding, sidebar_spacing, button_height, separator_height, sidebar_gap
    SIDEBAR_WIDTH = int(screen_width * 0.153)
    sidebar_padding = 10
    sidebar_spacing = 10
    button_height = 40
    separator_height = 2
    sidebar_gap = 20

    global sidebar_rect
    sidebar_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH - sidebar_padding, sidebar_padding,
                               SIDEBAR_WIDTH, effective_screen_height - (sidebar_padding * 2))

    global map_offset_x, map_offset_y
    map_offset_x = sidebar_rect.left + sidebar_padding
    map_offset_y = sidebar_rect.top + sidebar_padding + button_height + sidebar_spacing

    global BOARD_SIZE, SQUARE_SIZE
    map_width = SIDEBAR_WIDTH - (2 * sidebar_padding)
    map_height = map_width
    BOARD_SIZE = map_height
    SQUARE_SIZE = BOARD_SIZE // COLS

    for board_row in boards:
        for board in board_row:
            for row in board:
                for tile in row:
                    tile.size = SQUARE_SIZE
                    tile.rect = pygame.Rect(tile.col * SQUARE_SIZE, tile.row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)

    global separator_y
    separator_y = map_offset_y + map_height + sidebar_spacing + button_height + sidebar_spacing

    global bottom_container_y_start
    bottom_container_y_start = separator_y + separator_height + sidebar_spacing

    screen.fill(MAIN_BG_COLOR)

    mouse_pos = pygame.mouse.get_pos()

    if maximized:
        draw_all_boards(mouse_pos, screen_width, screen_height, effective_screen_height)
    else:
        if sidebar_visible:
            pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)

            draw_board(mouse_pos, map_offset_x, map_offset_y)
            draw_player(map_offset_x, map_offset_y, SQUARE_SIZE)

            pygame.draw.line(screen, SEPARATOR_COLOR,
                            (sidebar_rect.left + sidebar_padding, separator_y),
                            (sidebar_rect.right - sidebar_padding, separator_y),
                            separator_height)

        global image_display_area
        image_display_area = pygame.Rect(
            sidebar_padding, 
            sidebar_padding,
            screen_width - (SIDEBAR_WIDTH + sidebar_padding + sidebar_gap if sidebar_visible else sidebar_padding * 2),
            effective_screen_height - (sidebar_padding * 2)
        )
        pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)
        pygame.draw.rect(screen, SIDEBAR_BORDER_COLOR, image_display_area, 1)

        current_tile = get_current_tile()
        display_image(default_image_cv2, image_display_area, is_pygame_surface=False)
        if current_tile.images:
            current_image = current_tile.images[current_image_index]
            display_image(current_image, image_display_area, is_pygame_surface=True)

    update_button_positions()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            effective_screen_height = screen_height
            manager.set_window_resolution((screen_width, screen_height))
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
            if edit_mode and (sidebar_visible or maximized):
                if maximized:
                    full_map_size = BOARD_SIZE * NUM_BOARDS
                    scale_factor = min(screen_width / full_map_size, effective_screen_height / full_map_size)
                    scaled_size = int(BOARD_SIZE * scale_factor)
                    scaled_square_size = scaled_size // COLS
                    offset_x = (screen_width - (scaled_size * NUM_BOARDS)) // 2
                    offset_y = (effective_screen_height - (scaled_size * NUM_BOARDS)) // 2
                    for board_row in range(NUM_BOARDS):
                        for board_col in range(NUM_BOARDS):
                            board = boards[board_row][board_col]
                            board_offset_x = offset_x + (board_col * scaled_size)
                            board_offset_y = offset_y + (board_row * scaled_size)
                            for row in board:
                                for tile in row:
                                    adjusted_rect = pygame.Rect(
                                        board_offset_x + (tile.col * scaled_square_size),
                                        board_offset_y + (tile.row * scaled_square_size),
                                        scaled_square_size,
                                        scaled_square_size
                                    )
                                    if adjusted_rect.collidepoint(event.pos):
                                        tile.toggle_active()
                                        break
                elif sidebar_visible:
                    for row in get_current_board():
                        for tile in row:
                            adjusted_rect = tile.rect.move(map_offset_x, map_offset_y)
                            if adjusted_rect.collidepoint(event.pos):
                                tile.toggle_active()
                                break
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == top_container_buttons[0] and sidebar_visible and not maximized:
                toggle_edit_mode()
            elif event.ui_element == top_container_buttons[1] and not maximized:
                toggle_sidebar()
            elif event.ui_element == top_container_buttons[2]:
                toggle_maximize()
            elif event.ui_element == bottom_container_buttons[0] and sidebar_visible and not maximized:
                directory = open_file_explorer()
                if directory:
                    get_current_tile().set_directory(directory)
                    current_image_index = 0
            elif event.ui_element == bottom_container_buttons[1] and sidebar_visible and not maximized:
                save_game_state()
            elif event.ui_element == bottom_container_buttons[2] and sidebar_visible and not maximized:
                load_game_state()
            elif event.ui_element == bottom_container_buttons[3] and sidebar_visible and not maximized:
                remove_current_tile_folder()
            elif event.ui_element == bottom_container_buttons[4] and sidebar_visible and not maximized:
                directory = open_file_explorer()
                if directory:
                    organize_photos(directory)
                    screen.fill(MAIN_BG_COLOR)
                    if not maximized and sidebar_visible:
                        pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)
                        draw_board(mouse_pos, map_offset_x, map_offset_y)
                        draw_player(map_offset_x, map_offset_y, SQUARE_SIZE)
                        pygame.draw.line(screen, SEPARATOR_COLOR,
                                        (sidebar_rect.left + sidebar_padding, separator_y),
                                        (sidebar_rect.right - sidebar_padding, separator_y),
                                        separator_height)
                    image_display_area = pygame.Rect(
                        sidebar_padding, 
                        sidebar_padding,
                        screen_width - (SIDEBAR_WIDTH + sidebar_padding + sidebar_gap if sidebar_visible else sidebar_padding * 2),
                        effective_screen_height - (sidebar_padding * 2)
                    )
                    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)
                    pygame.draw.rect(screen, SIDEBAR_BORDER_COLOR, image_display_area, 1)
                    display_image(default_image_cv2, image_display_area, is_pygame_surface=False)
                    if current_tile.images:
                        current_image = current_tile.images[current_image_index]
                        display_image(current_image, image_display_area, is_pygame_surface=True)
                    manager.update(1.0 / FPS)
                    manager.draw_ui(screen)
                    pygame.display.flip()
        manager.process_events(event)

    manager.update(1.0 / FPS)
    manager.draw_ui(screen)
    pygame.display.flip()

async def main():
    await setup()
    while True:
        await update_loop()
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
