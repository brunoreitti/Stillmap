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
from tkinter import TclError
import shutil
import tempfile
import zipfile

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Stillmap")

if sys.platform == "win32":
    hwnd = pygame.display.get_wm_info()['window']
    SW_MAXIMIZE = 3
    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)

icon = pygame.image.load('ico1.ico')
pygame.display.set_icon(icon)

VIEW_ROWS, VIEW_COLS = 9, 9
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
SEPARATOR_COLOR = (0, 0, 0)
SIDEBAR_BORDER_COLOR = (120, 120, 120)
GRID_COLOR = (100, 100, 200)
CARD_BG_COLOR = (255, 255, 255)
LINK_HOVER_COLOR = (180, 180, 180)
GREEN = (0, 255, 0)
TOP_BAR_COLOR = (40, 42, 54)
TAB_TEXT_COLOR = WHITE
TAB_HOVER_COLOR = (50, 50, 50)

player_pos = [0, 0]
player_direction = 0
edit_mode = False
audio_mode = False
audio_muted = False
map_making_mode = False
free_move_mode = False
root = Tk()
root.withdraw()
current_image_index = 0
save_directory = os.path.join(os.getenv("LOCALAPPDATA"), "Stillmap", "saved_game_states")
shared_maps_dir = os.path.join(os.getenv("LOCALAPPDATA"), "Stillmap", "shared_maps")
try:
    os.makedirs(save_directory, exist_ok=True)
    os.makedirs(shared_maps_dir, exist_ok=True)
    test_file = os.path.join(save_directory, ".test_write_access")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
except PermissionError:
    messagebox.showerror("Permission Error", f"Cannot write to {save_directory}. Please run as administrator.")
    sys.exit(1)
except Exception as e:
    messagebox.showerror("Error", f"Failed to set up save directory: {str(e)}")
    sys.exit(1)

screen_width = 800
screen_height = 600
effective_screen_height = 600
SIDEBAR_WIDTH = 0
sidebar_padding = 10
sidebar_spacing = 10
separator_height = 2
sidebar_gap = 20
map_offset_x = 0
map_offset_y = 0
BOARD_SIZE = 0
SQUARE_SIZE = 0
separator_y = 0
bottom_container_y_start = 0
sidebar_rect = pygame.Rect(0, 0, 0, 0)
image_display_area = pygame.Rect(0, 0, 0, 0)

group1_box_rect = pygame.Rect(0, 0, 0, 0)
group2_box_rect = pygame.Rect(0, 0, 0, 0)

DEFAULT_IMAGE_PATH = 'image_path_logo9.svg'
default_image_cv2 = None


def load_svg_image(svg_path, output_width=None, output_height=None):
    try:
        png_data = cairosvg.svg2png(url=svg_path, output_width=output_width, output_height=output_height)
        nparr = np.frombuffer(png_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        return image
    except Exception as e:
        print(f"Failed to load SVG {svg_path}: {e}")
        return None


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
    except Exception:
        return None


def cv2_to_pygame(image):
    if image.shape[2] == 4:
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        return pygame.image.frombuffer(image_rgba.tobytes(), image_rgba.shape[1::-1], 'RGBA')
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')


# Load sound icons
sound_on_svg = load_image('sound_on.svg')
sound_off_svg = load_image('sound_off.svg')
sound_on_surface = cv2_to_pygame(sound_on_svg) if sound_on_svg is not None else None
sound_off_surface = cv2_to_pygame(sound_off_svg) if sound_off_svg is not None else None

# Resize base icons
if sound_on_surface:
    sound_on_surface = pygame.transform.smoothscale(sound_on_surface, (36, 36))
if sound_off_surface:
    sound_off_surface = pygame.transform.smoothscale(sound_off_surface, (36, 36))

default_image_cv2 = load_image(DEFAULT_IMAGE_PATH)

top_bar_height = 30
dropdown_open = None
dropdown_items = {
    0: ['Save Game', 'Load Game'],
    1: ['Toggle Edit Mode', 'Select Folder', 'Remove Folder'],
    2: ['Map Maker', 'Export Map', 'Import Map']
}
tab_width = 60

hide_text = "Hide"
map_text = "Map"
info_text = "Info"
exit_map_making_text = "Exit Map Making"
lift_text = "Lift Off"
exit_map_making_hovered = False
lift_hovered = False
hide_rect = pygame.Rect(0, 0, 0, 0)
map_rect = pygame.Rect(0, 0, 0, 0)
info_rect = pygame.Rect(0, 0, 0, 0)
exit_map_making_rect = pygame.Rect(0, 0, 0, 0)
lift_rect = pygame.Rect(0, 0, 0, 0)
hide_hovered = False
map_hovered = False
info_hovered = False

# Sound button - pure SVG, no background
sound_icon_rect = pygame.Rect(0, 0, 42, 42)
sound_button_hitbox = pygame.Rect(0, 0, 90, 90)  # Large invisible click area
sound_icon_hovered = False
sound_icon_scale = 1.0

font = pygame.font.SysFont('Arial', 16)
progress_font = pygame.font.SysFont('Arial', 20)

info_dialog = None
close_info_button = None

map_making_folders = []
map_making_index = 0
map_making_total = 0
map_making_direction = None
map_making_arrow_rect = pygame.Rect(0, 0, 20, 20)
pressed_keys = set()
preview_next_image = False

tiles = {}

turn_flag = False
move_flag = False

turn_sound = None
move_sound = None
try:
    turn_sound = pygame.mixer.Sound('sound1.wav')
    move_sound = pygame.mixer.Sound('sound2.wav')
except:
    pass

sidebar_links = [
    lambda: f"Edit Mode: {'On' if edit_mode else 'Off'}",
    lambda: f"Audio Mode: {'On' if audio_mode else 'Off'}",
    "Select Folder",
    "Save Game",
    "Load Game",
    "Remove Folder",
    "Map Maker",
    "Map Share",
    "Install Map"
]

GROUP1_INFICES = [0, 1, 2, 5]
GROUP2_INDICES = [3, 4, 6, 7, 8]

sidebar_link_rects = []
sidebar_link_hovered = [False] * len(sidebar_links)

manager = pygame_gui.UIManager((800, 600), theme_path=None)
manager.get_theme().load_theme({
    'button': {
        'normal_bg': f'#{SIDEBAR_BG_COLOR[0]:02x}{SIDEBAR_BG_COLOR[1]:02x}{SIDEBAR_BG_COLOR[2]:02x}',
        'hovered_bg': '#787878',
        'selected_bg': '#323232',
        'normal_border': '#787878',
        'hovered_border': '#a0a0a0',
        'font': {'size': 16, 'name': 'Arial'},
        'text_colour': '#FFFFFF'
    },
    '#info_dialog': {
        'background_colour': f'#{SIDEBAR_BG_COLOR[0]:02x}{SIDEBAR_BG_COLOR[1]:02x}{SIDEBAR_BG_COLOR[2]:02x}',
        'border_colour': '#787878',
        'title_bar': {
            'background_colour': '#323232',
            'text_colour': '#FFFFFF'}
    },
    '#close_info_button': {
        'normal_bg': '#323232',
        'hovered_bg': '#787878',
        'normal_border': '#787878',
        'hovered_border': '#a0a0a0',
        'font': {'size': 16, 'name': 'Arial'},
        'text_colour': '#FFFFFF'
    }
})


class Tile:
    def __init__(self, size):
        self.size = size
        self.color = LIGHTER_BLUE
        self.active = False
        self.directory = None
        self.images = []
        self.image_filenames = []
        self.audio_path = None

    def draw(self, target, mouse_pos, draw_rect):
        hover = draw_rect.collidepoint(mouse_pos) and edit_mode
        if hover:
            self.color = LIGHT_GRAY
        else:
            self.color = LIGHTER_BLUE if self.active else MAIN_BG_COLOR
        border_color = LIGHT_GRAY if hover and edit_mode else GRID_COLOR
        draw_fill = self.active
        draw_border = self.active or edit_mode
        if draw_fill:
            pygame.draw.rect(target, self.color, draw_rect)
        if draw_border:
            pygame.draw.rect(target, border_color, draw_rect, 1)
        if self.active and self.directory and self.images:
            inner_size = draw_rect.width // 3
            inner_rect = draw_rect.inflate(-inner_size, -inner_size)
            pygame.draw.rect(target, GREEN, inner_rect, 1)
        if self.active and self.audio_path:
            pygame.draw.circle(target, BLUE, draw_rect.center, 2)

    def toggle_active(self):
        self.active = not self.active
        self.color = LIGHTER_BLUE if self.active else MAIN_BG_COLOR

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.images, self.image_filenames = load_images_from_directory(directory)
            if not self.images:
                messagebox.showwarning("No Images", f"No supported images found in {directory}")

    def clear_directory(self):
        self.directory = None
        self.images = []
        self.image_filenames = []


center_pos = (0, 0)
tiles[center_pos] = Tile(0)
tiles[center_pos].active = True


def get_current_tile():
    pos = tuple(player_pos)
    return tiles.get(pos)


def display_image(current_image, display_area, is_pygame_surface=False, scale_multiplier=1.0):
    if current_image is not None:
        if is_pygame_surface:
            img_width, img_height = current_image.get_size()
        else:
            img_height, img_width = current_image.shape[:2]

        scale_factor = min(display_area.width / img_width, display_area.height / img_height)
        new_width = int(img_width * scale_factor * scale_multiplier)
        new_height = int(img_height * scale_factor * scale_multiplier)

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
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
    files.sort(key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x)
    for filename in files:
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
    except Exception:
        return None
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
    global screen_width, effective_screen_height
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
    font_local = pygame.font.Font(None, 36)
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
                    pygame.draw.rect(progress_surface, (0, 255, 0),
                                     (bar_x, card_y + 60, progress_width, bar_height), border_radius=10)

                    text_clear_rect = pygame.Rect(card_x, card_y, card_width, 40)
                    progress_surface.fill(CARD_BG_COLOR, text_clear_rect)
                    main_text = font_local.render(f"Organizing Photos: {int(progress * 100)}%", True, (0, 0, 0))
                    main_text_rect = main_text.get_rect(center=(screen_width // 2, card_y + 40))
                    progress_surface.blit(main_text, main_text_rect)

                    pygame.draw.rect(progress_surface, (100, 100, 100), console_rect, 2)
                    progress_surface.fill((0, 0, 0), console_rect)

                    line_height = console_font.get_height()
                    max_lines = (console_height - 10) // line_height
                    visible_lines = console_lines[-max_lines:]
                    for idx, line in enumerate(reversed(visible_lines)):
                        console_text = console_font.render(line, True, (255, 255, 255))
                        text_rect = console_text.get_rect(
                            topleft=(console_rect.left + 5,
                                     console_rect.bottom - (idx + 1) * line_height + animation_offset))
                        if text_rect.top >= console_rect.top:
                            if text_rect.right > console_rect.right:
                                max_chars = int(
                                    (console_rect.right - text_rect.left) / (console_font.size('a')[0]))
                                clipped_text = line[:max_chars]
                                console_text = console_font.render(clipped_text, True, (255, 255, 255))
                                text_rect = console_text.get_rect(
                                    topleft=(console_rect.left + 5,
                                             console_rect.bottom - (idx + 1) * line_height + animation_offset))
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
        pygame.draw.rect(progress_surface, (0, 255, 0),
                         (bar_x, card_y + 60, progress_width, bar_height), border_radius=10)

        text_clear_rect = pygame.Rect(card_x, card_y, card_width, 40)
        progress_surface.fill(CARD_BG_COLOR, text_clear_rect)
        main_text = font_local.render(f"Organizing Photos: {int(progress * 100)}%", True, (0, 0, 0))
        main_text_rect = main_text.get_rect(center=(screen_width // 2, card_y + 40))
        progress_surface.blit(main_text, main_text_rect)

        pygame.draw.rect(progress_surface, (100, 100, 100), console_rect, 2)
        progress_surface.fill((0, 0, 0), console_rect)

        line_height = console_font.get_height()
        max_lines = (console_height - 10) // line_height
        visible_lines = console_lines[-max_lines:]
        for idx, line in enumerate(reversed(visible_lines)):
            console_text = console_font.render(line, True, (255, 255, 255))
            text_rect = console_text.get_rect(
                topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height))
            if text_rect.top >= console_rect.top:
                if text_rect.right > console_rect.right:
                    max_chars = int((console_rect.right - text_rect.left) / (console_font.size('a')[0]))
                    clipped_text = line[:max_chars]
                    console_text = console_font.render(clipped_text, True, (255, 255, 255))
                    text_rect = console_text.get_rect(
                        topleft=(console_rect.left + 5, console_rect.bottom - (idx + 1) * line_height))
                progress_surface.blit(console_text, text_rect)

        screen.blit(progress_surface, (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            manager.process_events(event)


def restore_pygame_focus():
    if sys.platform == "win32":
        hwnd_local = pygame.display.get_wm_info()['window']
        ctypes.windll.user32.SetForegroundWindow(hwnd_local)
        ctypes.windll.user32.SetFocus(hwnd_local)


DIRECTIONS = [
    (-1, 0), (-1, 1), (0, 1), (1, 1),
    (1, 0), (1, -1), (0, -1), (-1, -1)
]


def draw_view(mouse_pos, map_offset_x, map_offset_y, SQUARE_SIZE, BOARD_SIZE, target, maximized=False):
    center_x = map_offset_x + (BOARD_SIZE / 2)
    center_y = map_offset_y + (BOARD_SIZE / 2)
    half_rows = (VIEW_ROWS - 1) // 2
    half_cols = (VIEW_COLS - 1) // 2

    if not maximized:
        for dr in range(-half_rows, half_rows + 1):
            r = player_pos[0] + dr
            for dc in range(-half_cols, half_cols + 1):
                c = player_pos[1] + dc
                pos = (r, c)
                if pos in tiles:
                    tile = tiles[pos]
                    tile_x = center_x + dc * SQUARE_SIZE - SQUARE_SIZE / 2
                    tile_y = center_y + dr * SQUARE_SIZE - SQUARE_SIZE / 2
                    draw_rect = pygame.Rect(tile_x, tile_y, SQUARE_SIZE, SQUARE_SIZE)
                    tile.draw(target, mouse_pos, draw_rect)
                    if audio_mode and pos in selected_tiles:
                        pygame.draw.rect(target, BLUE, draw_rect, 3)

        player_rect = pygame.Rect(
            center_x - (SQUARE_SIZE / 2),
            center_y - (SQUARE_SIZE / 2),
            SQUARE_SIZE,
            SQUARE_SIZE
        )
        pygame.draw.rect(target, LIGHTER_BLUE, player_rect)
        arrow_length = SQUARE_SIZE // 2
        arrow_color = GREEN if get_current_tile() and get_current_tile().images else WHITE
        if player_direction == 0:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x, center_y - arrow_length), (center_x - 10, center_y),
                                 (center_x + 10, center_y)])
        elif player_direction == 1:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10),
                                 (center_x + 10, center_y)])
        elif player_direction == 2:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x + arrow_length, center_y),
                                 (center_x, center_y - 10), (center_x, center_y + 10)])
        elif player_direction == 3:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x + arrow_length, center_y + arrow_length),
                                 (center_x, center_y + 10), (center_x + 10, center_y)])
        elif player_direction == 4:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x, center_y + arrow_length),
                                 (center_x - 10, center_y), (center_x + 10, center_y)])
        elif player_direction == 5:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x - arrow_length, center_y + arrow_length),
                                 (center_x - 10, center_y), (center_x, center_y + 10)])
        elif player_direction == 6:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x - arrow_length, center_y),
                                 (center_x, center_y - 10), (center_x, center_y + 10)])
        elif player_direction == 7:
            pygame.draw.polygon(target, arrow_color,
                                [(center_x - arrow_length, center_y - arrow_length),
                                 (center_x - 10, center_y), (center_x, center_y - 10)])
        return SQUARE_SIZE, 0, 0, 0, 0
    else:
        if not tiles:
            player_rect = pygame.Rect(
                screen_width / 2 - 20,
                top_bar_height + effective_screen_height / 2 - 20,
                40, 40
            )
            pygame.draw.rect(target, LIGHTER_BLUE, player_rect)
            return 40, 0, 0, 0, 0, 40

        all_pos = list(tiles.keys())
        min_r = min(p[0] for p in all_pos)
        max_r = max(p[0] for p in all_pos)
        min_c = min(p[1] for p in all_pos)
        max_c = max(p[1] for p in all_pos)
        bb_height = max_r - min_r + 1
        bb_width = max_c - min_c + 1

        fit_width = screen_width * 0.9
        fit_height = (effective_screen_height - top_bar_height) * 0.9
        scale = min(fit_width / bb_width, fit_height / bb_height)
        scaled_tile_size = scale

        player_rel_r = player_pos[0] - min_r
        player_rel_c = player_pos[1] - min_c
        player_draw_x = (player_rel_c + 0.5) * scale
        player_draw_y = (player_rel_r + 0.5) * scale
        offset_x = (screen_width / 2) - player_draw_x
        offset_y = top_bar_height + ((effective_screen_height - top_bar_height) / 2) - player_draw_y

        for pos in all_pos:
            r, c = pos
            rel_r = r - min_r
            rel_c = c - min_c
            draw_x = offset_x + (rel_c + 0.5) * scale - scaled_tile_size / 2
            draw_y = offset_y + (rel_r + 0.5) * scale - scaled_tile_size / 2
            draw_rect = pygame.Rect(draw_x, draw_y, scaled_tile_size, scaled_tile_size)
            tiles[pos].draw(target, mouse_pos, draw_rect)
            if audio_mode and pos in selected_tiles:
                pygame.draw.rect(target, BLUE, draw_rect, 3)

        player_screen_x = screen_width / 2
        player_screen_y = top_bar_height + (effective_screen_height - top_bar_height) / 2
        player_rect = pygame.Rect(
            player_screen_x - scaled_tile_size / 2,
            player_screen_y - scaled_tile_size / 2,
            scaled_tile_size,
            scaled_tile_size
        )
        pygame.draw.rect(target, LIGHTER_BLUE, player_rect)
        arrow_length = scaled_tile_size // 2
        arrow_color = GREEN if get_current_tile() and get_current_tile().images else WHITE
        if player_direction == 0:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x, player_screen_y - arrow_length),
                                 (player_screen_x - 10, player_screen_y),
                                 (player_screen_x + 10, player_screen_y)])
        elif player_direction == 1:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x + arrow_length, player_screen_y - arrow_length),
                                 (player_screen_x, player_screen_y - 10),
                                 (player_screen_x + 10, player_screen_y)])
        elif player_direction == 2:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x + arrow_length, player_screen_y),
                                 (player_screen_x, player_screen_y - 10),
                                 (player_screen_x, player_screen_y + 10)])
        elif player_direction == 3:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x + arrow_length, player_screen_y + arrow_length),
                                 (player_screen_x, player_screen_y + 10),
                                 (player_screen_x + 10, player_screen_y)])
        elif player_direction == 4:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x, player_screen_y + arrow_length),
                                 (player_screen_x - 10, player_screen_y),
                                 (player_screen_x + 10, player_screen_y)])
        elif player_direction == 5:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x - arrow_length, player_screen_y + arrow_length),
                                 (player_screen_x - 10, player_screen_y),
                                 (player_screen_x, player_screen_y + 10)])
        elif player_direction == 6:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x - arrow_length, player_screen_y),
                                 (player_screen_x, player_screen_y - 10),
                                 (player_screen_x, player_screen_y + 10)])
        elif player_direction == 7:
            pygame.draw.polygon(target, arrow_color,
                                [(player_screen_x - arrow_length, player_screen_y - arrow_length),
                                 (player_screen_x - 10, player_screen_y),
                                 (player_screen_x, player_screen_y - 10)])
        return scaled_tile_size, offset_x, offset_y, 0, 0, scale


def move_player(forward=True):
    global player_pos, move_flag
    direction = player_direction if forward else (player_direction + 4) % 8
    dr, dc = DIRECTIONS[direction]
    new_r = player_pos[0] + dr
    new_c = player_pos[1] + dc
    new_pos = (new_r, new_c)
    if new_pos in tiles and tiles[new_pos].active:
        player_pos = [new_r, new_c]
        move_flag = True
        play_tile_audio()
        return True
    return False


def rotate_player(key):
    global player_direction, current_image_index, turn_flag
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
        current_tile = get_current_tile()
        if current_tile and current_tile.images:
            current_image_index = (current_image_index - 1) % len(current_tile.images)
            turn_flag = True
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8
        current_tile = get_current_tile()
        if current_tile and current_tile.images:
            current_image_index = (current_image_index + 1) % len(current_tile.images)
            turn_flag = True


def toggle_edit_mode():
    global edit_mode
    edit_mode = not edit_mode


def toggle_audio_mode():
    global audio_mode, selected_audio_path
    audio_mode = not audio_mode
    if audio_mode:
        filepath = filedialog.askopenfilename(title="Select Audio File",
                                              filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if filepath:
            selected_audio_path = filepath
        else:
            audio_mode = False
    else:
        for pos in selected_tiles:
            if pos in tiles:
                tiles[pos].audio_path = selected_audio_path
        selected_tiles.clear()
        selected_audio_path = None
        play_tile_audio()


def toggle_audio_mute():
    global audio_muted, current_audio_path
    audio_muted = not audio_muted
    if audio_muted:
        pygame.mixer.music.stop()
        current_audio_path = None
    else:
        play_tile_audio()


def remove_current_tile_folder():
    current_tile = get_current_tile()
    if current_tile:
        current_tile.clear_directory()


def save_game_state():
    filename = simpledialog.askstring("Save Game", "Enter the save file name:")
    if not filename:
        messagebox.showwarning("Save Game", "Save file name cannot be empty.")
        return
    filepath = os.path.join(save_directory, f"{filename}.json")
    game_state = {
        "player_pos": player_pos,
        "player_direction": player_direction,
        "tiles": {}
    }
    for pos, tile in tiles.items():
        game_state["tiles"][str(pos)] = {
            "active": tile.active,
            "directory": tile.directory,
            "audio_path": tile.audio_path
        }
    with open(filepath, 'w') as f:
        json.dump(game_state, f)
    messagebox.showinfo("Save Game", f"Game saved to {filepath}")


def load_game_state():
    filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], initialdir=save_directory)
    if not filepath:
        return
    with open(filepath, 'r') as f:
        game_state = json.load(f)
    player_pos[:] = game_state["player_pos"]
    global player_direction, current_image_index
    player_direction = game_state["player_direction"]
    tiles.clear()
    for pos_str, tile_data in game_state["tiles"].items():
        pos = eval(pos_str)
        tile = Tile(0)
        tile.active = tile_data["active"]
        if tile_data["directory"]:
            tile.set_directory(tile_data["directory"])
        tile.audio_path = tile_data.get("audio_path", None)
        tiles[pos] = tile
    current_image_index = 0
    play_tile_audio()


def export_map():
    filename = simpledialog.askstring("Export Map", "Enter the map file name:")
    if not filename:
        messagebox.showwarning("Export Map", "Map file name cannot be empty.")
        return
    filepath = os.path.join(shared_maps_dir, f"{filename}.zip")
    with tempfile.TemporaryDirectory() as temp_dir:
        map_data = {
            "tiles": {}
        }
        for pos, tile in tiles.items():
            tile_info = {
                "active": tile.active
            }
            if tile.directory:
                folder_name = f"tile_{pos[0]}_{pos[1]}"
                temp_folder_path = os.path.join(temp_dir, folder_name)
                shutil.copytree(tile.directory, temp_folder_path)
                tile_info["directory"] = folder_name
            if tile.audio_path:
                audio_ext = os.path.splitext(tile.audio_path)[1]
                audio_name = f"audio_{pos[0]}_{pos[1]}{audio_ext}"
                shutil.copy(tile.audio_path, os.path.join(temp_dir, audio_name))
                tile_info["audio_path"] = audio_name
            map_data["tiles"][str(pos)] = tile_info
        map_json_path = os.path.join(temp_dir, "map.json")
        with open(map_json_path, 'w') as f:
            json.dump(map_data, f)
        with zipfile.ZipFile(filepath, 'w') as zipf:
            for root_dir, _, files in os.walk(temp_dir):
                for file in files:
                    zipf.write(os.path.join(root_dir, file),
                               os.path.relpath(os.path.join(root_dir, file), temp_dir))
    messagebox.showinfo("Export Map", f"Map exported to {filepath}")


def import_map():
    filepath = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")], initialdir=shared_maps_dir)
    if not filepath:
        return
    map_name = os.path.splitext(os.path.basename(filepath))[0]
    extract_dir = os.path.join(shared_maps_dir, map_name)
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    with zipfile.ZipFile(filepath, 'r') as zipf:
        zipf.extractall(extract_dir)
    map_json_path = os.path.join(extract_dir, "map.json")
    with open(map_json_path, 'r') as f:
        map_data = json.load(f)
    tiles.clear()
    for pos_str, tile_data in map_data["tiles"].items():
        pos = eval(pos_str)
        tile = Tile(0)
        tile.active = tile_data["active"]
        if "directory" in tile_data:
            folder_path = os.path.join(extract_dir, tile_data["directory"])
            tile.set_directory(folder_path)
        tile.audio_path = os.path.join(extract_dir, tile_data["audio_path"]) if "audio_path" in tile_data else None
        tiles[pos] = tile
    player_pos[:] = [0, 0]
    global player_direction, current_image_index
    player_direction = 0
    current_image_index = 0
    play_tile_audio()
    messagebox.showinfo("Import Map", "Map imported successfully.")


def show_info_dialog():
    global info_dialog, close_info_button, screen_width, screen_height
    dialog_width, dialog_height = 600, 400
    dialog_x = (screen_width - dialog_width) // 2
    dialog_y = (screen_height - dialog_height) // 2
    info_dialog = pygame_gui.windows.UIMessageWindow(
        rect=pygame.Rect((dialog_x, dialog_y), (dialog_width, dialog_height)),
        html_message="<font color=#FFFFFF>Stillmap is a program for viewing images in a map-like format.</font>",
        manager=manager,
        window_title="Info"
    )
    close_info_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((dialog_width - 100, dialog_height - 50), (80, 30)),
        text="Close",
        manager=manager,
        container=info_dialog
    )


def start_map_making():
    global map_making_mode, map_making_folders, map_making_index, map_making_total
    global map_making_direction, preview_next_image, free_move_mode

    directory = open_file_explorer()
    if not directory:
        return

    organized_dir = os.path.join(directory, "organized_photos")
    if os.path.isdir(organized_dir):
        root_dir = organized_dir
    else:
        root_dir = directory

    map_making_folders = [
        os.path.join(root_dir, d)
        for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d))
    ]

    map_making_folders = [
        d for d in map_making_folders
        if any(
            f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
            for f in os.listdir(d)
        )
    ]

    def folder_sort_key(path):
        name = os.path.basename(path)
        return int(name) if name.isdigit() else name

    map_making_folders.sort(key=folder_sort_key)

    map_making_total = len(map_making_folders)
    if map_making_total == 0:
        messagebox.showwarning("Map Maker", "No image folders found.")
        return

    map_making_mode = True
    map_making_index = 0
    map_making_direction = None
    preview_next_image = False
    free_move_mode = False

    current_tile = get_current_tile()
    if current_tile:
        current_tile.set_directory(map_making_folders[0])

    restore_pygame_focus()


def exit_map_making():
    global map_making_mode, map_making_folders, map_making_index, map_making_total
    global map_making_direction, preview_next_image, free_move_mode, current_image_index
    map_making_mode = False
    map_making_folders = []
    map_making_index = 0
    map_making_total = 0
    map_making_direction = None
    preview_next_image = False
    free_move_mode = False
    pressed_keys.clear()
    current_tile = get_current_tile()
    if current_tile and current_tile.images:
        current_image_index = 0


def toggle_free_move_mode():
    global free_move_mode, lift_text, map_making_direction, pressed_keys
    free_move_mode = not free_move_mode
    lift_text = "Resume" if free_move_mode else "Lift Off"
    if not free_move_mode:
        map_making_direction = None
        pressed_keys.clear()


def set_map_making_direction():
    global map_making_direction
    if pressed_keys:
        if pygame.K_UP in pressed_keys and pygame.K_RIGHT in pressed_keys:
            map_making_direction = 1
        elif pygame.K_RIGHT in pressed_keys and pygame.K_DOWN in pressed_keys:
            map_making_direction = 3
        elif pygame.K_DOWN in pressed_keys and pygame.K_LEFT in pressed_keys:
            map_making_direction = 5
        elif pygame.K_LEFT in pressed_keys and pygame.K_UP in pressed_keys:
            map_making_direction = 7
        elif pygame.K_UP in pressed_keys:
            map_making_direction = 0
        elif pygame.K_RIGHT in pressed_keys:
            map_making_direction = 2
        elif pygame.K_DOWN in pressed_keys:
            map_making_direction = 4
        elif pygame.K_LEFT in pressed_keys:
            map_making_direction = 6


def assign_next_tile():
    global map_making_index, player_pos, map_making_direction, move_flag
    if map_making_direction is not None and map_making_index + 1 < map_making_total:
        dr, dc = DIRECTIONS[map_making_direction]
        new_r = player_pos[0] + dr
        new_c = player_pos[1] + dc
        new_pos = (new_r, new_c)
        if new_pos not in tiles:
            tiles[new_pos] = Tile(0)
            tiles[new_pos].active = True
        current_tile = tiles[new_pos]
        current_tile.set_directory(map_making_folders[map_making_index + 1])
        player_pos = [new_r, new_c]
        map_making_index += 1
        map_making_direction = None
        pressed_keys.clear()
        move_flag = True


sidebar_visible = True
maximized = False


def toggle_sidebar():
    global sidebar_visible, maximized, hide_text
    sidebar_visible = not sidebar_visible
    hide_text = "Show" if not sidebar_visible else "Hide"
    if not maximized:
        update_button_positions()


def toggle_maximize():
    global maximized, sidebar_visible, map_text
    maximized = not maximized
    if maximized:
        sidebar_visible = False
        map_text = "Normal"
    else:
        sidebar_visible = True
        map_text = "Map"
        update_button_positions()


def update_button_positions():
    global screen_width, SIDEBAR_WIDTH, sidebar_padding, sidebar_spacing, map_offset_x, map_offset_y, BOARD_SIZE
    global sidebar_rect, image_display_area, hide_rect, map_rect, info_rect, sidebar_link_rects
    global bottom_container_y_start, group1_box_rect, group2_box_rect

    if sidebar_visible and not maximized:
        hide_rect = font.render(hide_text, True, WHITE).get_rect(
            topleft=(sidebar_rect.left + sidebar_padding, sidebar_rect.top + sidebar_padding)
        )
        map_rect = font.render(map_text, True, WHITE).get_rect(
            topleft=(sidebar_rect.left + SIDEBAR_WIDTH - sidebar_padding - font.size(map_text)[0],
                     sidebar_rect.top + sidebar_padding)
        )
        info_rect = font.render(info_text, True, WHITE).get_rect(
            bottomright=(sidebar_rect.right - sidebar_padding, sidebar_rect.bottom - sidebar_padding)
        )
    elif not maximized:
        button_x = image_display_area.right - font.size(hide_text)[0] - 5
        button_y = top_bar_height + sidebar_padding
        hide_rect = font.render(hide_text, True, WHITE).get_rect(topleft=(button_x, button_y))
        map_rect = pygame.Rect(-1000, -1000, 0, 0)
        info_rect = pygame.Rect(-1000, -1000, 0, 0)
    else:
        hide_rect = pygame.Rect(-1000, -1000, 0, 0)
        map_rect = font.render(map_text, True, WHITE).get_rect(
            topleft=(screen_width - font.size(map_text)[0] - 10, top_bar_height + 10)
        )
        info_rect = pygame.Rect(-1000, -1000, 0, 0)

    sidebar_link_rects = [pygame.Rect(0, 0, 0, 0) for _ in sidebar_links]
    group1_box_rect = pygame.Rect(0, 0, 0, 0)
    group2_box_rect = pygame.Rect(0, 0, 0, 0)

    if not (sidebar_visible and not maximized):
        return

    box_width = sidebar_rect.width - 2 * sidebar_padding
    line_h = font.get_height()
    box_inner_pad = 8
    box_gap = 15

    current_y = bottom_container_y_start

    def place_group(indices, start_y):
        group_count = len(indices)
        height = box_inner_pad * 2 + group_count * line_h + (group_count - 1) * sidebar_spacing
        rect = pygame.Rect(sidebar_rect.left + sidebar_padding, start_y, box_width, height)
        link_y = rect.top + box_inner_pad
        for idx in indices:
            link_text = sidebar_links[idx]() if callable(sidebar_links[idx]) else sidebar_links[idx]
            link_surface = font.render(link_text, True, WHITE)
            link_rect = link_surface.get_rect(left=rect.left + box_inner_pad, top=link_y)
            sidebar_link_rects[idx] = link_rect
            link_y += line_h + sidebar_spacing
        return rect, rect.bottom + box_gap

    group1_box_rect, current_y = place_group(GROUP1_INFICES, current_y)
    group2_box_rect, current_y = place_group(GROUP2_INDICES, current_y)


current_audio_path = None
selected_tiles = set()
selected_audio_path = None


def play_tile_audio():
    global current_audio_path
    current_tile = get_current_tile()
    if audio_muted:
        return
    if current_tile and current_tile.audio_path:
        if current_audio_path != current_tile.audio_path:
            pygame.mixer.music.stop()
            current_audio_path = None
            if current_tile.audio_path:
                try:
                    pygame.mixer.music.load(current_tile.audio_path)
                    pygame.mixer.music.play(-1)
                    current_audio_path = current_tile.audio_path
                except:
                    messagebox.showerror("Error", "Failed to load audio")
    else:
        if current_audio_path:
            pygame.mixer.music.stop()
            current_audio_path = None


async def setup():
    global screen_width, screen_height, effective_screen_height, manager
    screen_width, screen_height = screen.get_size()
    effective_screen_height = screen_height
    manager.set_window_resolution((screen_width, screen_height))
    center_pos_local = (0, 0)
    if center_pos_local not in tiles:
        tiles[center_pos_local] = Tile(0)
        tiles[center_pos_local].active = True
    player_pos[:] = [0, 0]
    play_tile_audio()


async def update_loop():
    global screen_width, screen_height, effective_screen_height
    global current_image_index, SIDEBAR_WIDTH, sidebar_padding, sidebar_spacing, separator_height, sidebar_gap
    global sidebar_rect, map_offset_x, map_offset_y, BOARD_SIZE, SQUARE_SIZE, separator_y, bottom_container_y_start
    global image_display_area, hide_hovered, map_hovered, info_hovered
    global exit_map_making_hovered, lift_hovered, lift_text
    global info_dialog, close_info_button, map_making_arrow_rect, preview_next_image
    global turn_flag, move_flag, dropdown_open, tab_rects, sidebar_link_hovered, map_area_rect
    global sound_icon_hovered, sound_icon_scale

    if 'current_image_index' not in globals():
        current_image_index = 0

    screen_width, screen_height = screen.get_size()
    effective_screen_height = screen_height

    manager.set_window_resolution((screen_width, screen_height))

    SIDEBAR_WIDTH = int(screen_width * 0.153)
    sidebar_padding = 10
    sidebar_spacing = 10
    separator_height = 2
    sidebar_gap = 20

    sidebar_rect = pygame.Rect(
        screen_width - SIDEBAR_WIDTH - sidebar_padding,
        top_bar_height + sidebar_padding,
        SIDEBAR_WIDTH,
        effective_screen_height - top_bar_height - (sidebar_padding * 2)
    )

    map_offset_x = sidebar_rect.left + sidebar_padding
    map_offset_y = sidebar_rect.top + sidebar_padding

    map_width = SIDEBAR_WIDTH - (2 * sidebar_padding)
    map_height = map_width
    BOARD_SIZE = map_height
    SQUARE_SIZE = BOARD_SIZE / VIEW_COLS

    for tile in tiles.values():
        tile.size = SQUARE_SIZE

    separator_y = map_offset_y + map_height + sidebar_spacing
    bottom_container_y_start = separator_y + separator_height + sidebar_spacing

    screen.fill(MAIN_BG_COLOR)

    mouse_pos = pygame.mouse.get_pos()

    if maximized:
        draw_view(mouse_pos, 0, 0, SQUARE_SIZE, BOARD_SIZE, screen, maximized=True)
    else:
        if sidebar_visible:
            pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)
            map_area_rect = pygame.Rect(map_offset_x, map_offset_y, BOARD_SIZE, BOARD_SIZE)
            map_surface = pygame.Surface((int(BOARD_SIZE), int(BOARD_SIZE)))
            map_surface.fill(SIDEBAR_BG_COLOR)
            rel_mouse_pos = (mouse_pos[0] - map_offset_x, mouse_pos[1] - map_offset_y)
            draw_view(rel_mouse_pos, 0, 0, SQUARE_SIZE, BOARD_SIZE, map_surface, maximized=False)
            screen.blit(map_surface, map_area_rect.topleft)
            pygame.draw.rect(screen, GRID_COLOR, map_area_rect, 1)

        image_display_area = pygame.Rect(
            sidebar_padding,
            top_bar_height + sidebar_padding,
            screen_width - (SIDEBAR_WIDTH + sidebar_padding + sidebar_gap if sidebar_visible else sidebar_padding * 2),
            effective_screen_height - top_bar_height - (sidebar_padding * 2)
        )
        pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)
        pygame.draw.rect(screen, SIDEBAR_BORDER_COLOR, image_display_area, 1)
        inner_display_area = image_display_area.inflate(-2, -2)

        current_tile = get_current_tile()
        display_image(default_image_cv2, inner_display_area, is_pygame_surface=False, scale_multiplier=1.25)
        if map_making_mode and not free_move_mode:
            if preview_next_image and map_making_index + 1 < map_making_total:
                next_folder = map_making_folders[map_making_index + 1]
                next_images, _ = load_images_from_directory(next_folder)
                if next_images:
                    display_image(next_images[0], inner_display_area, is_pygame_surface=True)
            elif current_tile and current_tile.images:
                current_image = current_tile.images[0]
                display_image(current_image, inner_display_area, is_pygame_surface=True)
        elif current_tile and current_tile.images and 0 <= current_image_index < len(current_tile.images):
            current_image = current_tile.images[current_image_index]
            display_image(current_image, inner_display_area, is_pygame_surface=True)

    update_button_positions()

    if sidebar_visible and not maximized:
        pygame.draw.rect(screen, SEPARATOR_COLOR, (map_offset_x, separator_y, map_width, separator_height))

        shadow_offset = 3
        shadow_color = (30, 30, 60)
        box_color = LIGHTER_BLUE

        for box_rect in (group1_box_rect, group2_box_rect):
            if box_rect.width > 0 and box_rect.height > 0:
                shadow_rect = box_rect.move(shadow_offset, shadow_offset)
                pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=8)
                pygame.draw.rect(screen, box_color, box_rect, border_radius=8)

        for i in range(len(sidebar_links)):
            link_rect = sidebar_link_rects[i]
            link = sidebar_links[i]
            link_text = link() if callable(link) else link
            sidebar_link_hovered[i] = link_rect.collidepoint(mouse_pos)
            link_surface = font.render(link_text, True,
                                       LINK_HOVER_COLOR if sidebar_link_hovered[i] else WHITE)
            screen.blit(link_surface, link_rect.topleft)
            if sidebar_link_hovered[i]:
                pygame.draw.line(
                    screen,
                    LINK_HOVER_COLOR,
                    (link_rect.left, link_rect.bottom - 2),
                    (link_rect.right, link_rect.bottom - 2),
                    1
                )

    if map_making_mode:
        exit_map_making_rect_local = progress_font.render(exit_map_making_text, True, WHITE).get_rect(
            topleft=(image_display_area.left + sidebar_padding, image_display_area.top + sidebar_padding)
        )
        exit_map_making_rect = exit_map_making_rect_local
        exit_map_making_hovered = exit_map_making_rect.collidepoint(mouse_pos)
        exit_map_making_surface = progress_font.render(
            exit_map_making_text,
            True,
            LINK_HOVER_COLOR if exit_map_making_hovered else WHITE
        )
        screen.blit(exit_map_making_surface, exit_map_making_rect.topleft)
        if exit_map_making_hovered:
            pygame.draw.line(
                screen,
                LINK_HOVER_COLOR,
                (exit_map_making_rect.left, exit_map_making_rect.bottom - 2),
                (exit_map_making_rect.right, exit_map_making_rect.bottom - 2),
                1
            )

        progress_text = f"{map_making_index + 1}/{map_making_total} images done"
        progress_rect = progress_font.render(progress_text, True, WHITE).get_rect(
            topleft=(image_display_area.left + sidebar_padding, image_display_area.top + sidebar_padding + 30)
        )
        screen.blit(progress_font.render(progress_text, True, WHITE), progress_rect.topleft)

        lift_rect_local = progress_font.render(lift_text, True, WHITE).get_rect(
            bottomleft=(image_display_area.left + sidebar_padding, image_display_area.bottom - sidebar_padding)
        )
        lift_rect = lift_rect_local
        lift_hovered = lift_rect.collidepoint(mouse_pos)
        lift_surface = progress_font.render(lift_text, True, LINK_HOVER_COLOR if lift_hovered else WHITE)
        screen.blit(lift_surface, lift_rect.topleft)
        if lift_hovered:
            pygame.draw.line(
                screen,
                LINK_HOVER_COLOR,
                (lift_rect.left, lift_rect.bottom - 2),
                (lift_rect.right, lift_rect.bottom - 2),
                1
            )

        if not free_move_mode:
            map_making_arrow_rect = pygame.Rect(image_display_area.right - 30,
                                                image_display_area.bottom - 30, 20, 20)
            if map_making_direction is None:
                pygame.draw.circle(screen, GREEN, map_making_arrow_rect.center, 10)
            else:
                center_x_arrow, center_y_arrow = map_making_arrow_rect.center
                arrow_length = 10
                if map_making_direction == 0:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow, center_y_arrow - arrow_length),
                        (center_x_arrow - 5, center_y_arrow),
                        (center_x_arrow + 5, center_y_arrow)
                    ])
                elif map_making_direction == 1:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow + arrow_length, center_y_arrow - arrow_length),
                        (center_x_arrow, center_y_arrow - 5),
                        (center_x_arrow + 5, center_y_arrow)
                    ])
                elif map_making_direction == 2:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow + arrow_length, center_y_arrow),
                        (center_x_arrow, center_y_arrow - 5),
                        (center_x_arrow, center_y_arrow + 5)
                    ])
                elif map_making_direction == 3:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow + arrow_length, center_y_arrow + arrow_length),
                        (center_x_arrow, center_y_arrow + 5),
                        (center_x_arrow + 5, center_y_arrow)
                    ])
                elif map_making_direction == 4:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow, center_y_arrow + arrow_length),
                        (center_x_arrow - 5, center_y_arrow),
                        (center_x_arrow + 5, center_y_arrow)
                    ])
                elif map_making_direction == 5:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow - arrow_length, center_y_arrow + arrow_length),
                        (center_x_arrow - 5, center_y_arrow),
                        (center_x_arrow, center_y_arrow + 5)
                    ])
                elif map_making_direction == 6:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow - arrow_length, center_y_arrow),
                        (center_x_arrow, center_y_arrow - 5),
                        (center_x_arrow, center_y_arrow + 5)
                    ])
                elif map_making_direction == 7:
                    pygame.draw.polygon(screen, GREEN, [
                        (center_x_arrow - arrow_length, center_y_arrow - arrow_length),
                        (center_x_arrow - 5, center_y_arrow),
                        (center_x_arrow, center_y_arrow - 5)
                    ])

    else:
        hide_hovered = hide_rect.collidepoint(mouse_pos)
        map_hovered = map_rect.collidepoint(mouse_pos)
        info_hovered = info_rect.collidepoint(mouse_pos)

        # --- NEW: Beautiful Transparent SVG Sound Button (no background) ---
        sound_icon_rect.topright = (image_display_area.right - 18, image_display_area.top + 18)
        sound_icon_rect.size = (42, 42)

        # Large invisible hitbox for easy clicking
        sound_button_hitbox.center = sound_icon_rect.center
        sound_button_hitbox.size = (90, 90)
        sound_icon_hovered = sound_button_hitbox.collidepoint(mouse_pos)

        # Smooth hover scale
        target_scale = 1.28 if sound_icon_hovered else 1.0
        sound_icon_scale += (target_scale - sound_icon_scale) * 0.18

        # Subtle glow on hover
        if sound_icon_hovered and sound_icon_scale > 1.1:
            glow_intensity = int(30 + (sound_icon_scale - 1.0) * 120)
            glow_size = int(70 * sound_icon_scale)
            glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 170, 255, glow_intensity),
                              (glow_size//2, glow_size//2), glow_size//2)
            screen.blit(glow_surf, glow_surf.get_rect(center=sound_icon_rect.center))

        current_icon = sound_off_surface if audio_muted else sound_on_surface
        if current_icon:
            w, h = current_icon.get_size()
            new_w, new_h = int(w * sound_icon_scale), int(h * sound_icon_scale)
            scaled = pygame.transform.smoothscale(current_icon, (new_w, new_h))
            rect = scaled.get_rect(center=sound_icon_rect.center)
            screen.blit(scaled, rect)

            # Breathing pulse when audio is playing
            if not audio_muted and current_audio_path:
                pulse = int(80 + 50 * abs((pygame.time.get_ticks() % 800 - 400) / 400))
                pulse_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(pulse_surf, (0, 255, 150, pulse), (12, 12), 10)
                screen.blit(pulse_surf, pulse_surf.get_rect(center=sound_icon_rect.center))
        else:
            color = (200, 200, 200) if not audio_muted else (100, 100, 100)
            pygame.draw.circle(screen, color, sound_icon_rect.center, 16)
            if audio_muted:
                pygame.draw.line(screen, (255, 80, 80),
                                 sound_icon_rect.topleft, sound_icon_rect.bottomright, 4)

        # Text buttons (Hide / Map / Info)
        hide_surface = font.render(hide_text, True, LINK_HOVER_COLOR if hide_hovered else WHITE)
        screen.blit(hide_surface, hide_rect.topleft)
        if hide_hovered:
            pygame.draw.line(screen, LINK_HOVER_COLOR,
                             (hide_rect.left, hide_rect.bottom - 2),
                             (hide_rect.right, hide_rect.bottom - 2), 1)

        map_surface_text = font.render(map_text, True, LINK_HOVER_COLOR if map_hovered else WHITE)
        screen.blit(map_surface_text, map_rect.topleft)
        if map_hovered:
            pygame.draw.line(screen, LINK_HOVER_COLOR,
                             (map_rect.left, map_rect.bottom - 2),
                             (map_rect.right, map_rect.bottom - 2), 1)

        info_surface = font.render(info_text, True, LINK_HOVER_COLOR if info_hovered else WHITE)
        screen.blit(info_surface, info_rect.topleft)
        if info_hovered:
            pygame.draw.line(screen, LINK_HOVER_COLOR,
                             (info_rect.left, info_rect.bottom - 2),
                             (info_rect.right, info_rect.bottom - 2), 1)

    # Top bar + menus
    top_bar_rect = pygame.Rect(0, 0, screen_width, top_bar_height)
    pygame.draw.rect(screen, TOP_BAR_COLOR, top_bar_rect)
    pygame.draw.rect(screen, SEPARATOR_COLOR, top_bar_rect, 1)
    current_x = 10 + 2
    tab_rects = []
    for i, tab_name in enumerate(['File', 'Edit', 'Other']):
        tab_rect = pygame.Rect(current_x, 2, tab_width, top_bar_height - 4)
        color = TAB_HOVER_COLOR if tab_rect.collidepoint(pygame.mouse.get_pos()) else TOP_BAR_COLOR
        pygame.draw.rect(screen, color, tab_rect)
        text_surf = font.render(tab_name, True, TAB_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=(current_x + tab_width // 2, top_bar_height // 2))
        screen.blit(text_surf, text_rect)
        tab_rects.append(tab_rect)
        current_x += tab_width + 10

    if dropdown_open is not None and 0 <= dropdown_open < len(tab_rects):
        i = dropdown_open
        tab_rect = tab_rects[i]
        drop_x, drop_y = tab_rect.x, tab_rect.bottom
        items = dropdown_items[i]
        item_height = 22
        drop_width = max(tab_width, max([font.size(it)[0] for it in items]) + 20)
        drop_height = len(items) * item_height + 4
        drop_rect = pygame.Rect(drop_x, drop_y, drop_width, drop_height)
        pygame.draw.rect(screen, TOP_BAR_COLOR, drop_rect)
        pygame.draw.rect(screen, SEPARATOR_COLOR, drop_rect, 1)
        for j, item in enumerate(items):
            i_y = drop_y + 2 + j * item_height
            i_rect = pygame.Rect(drop_x, i_y, drop_width, item_height)
            hover = i_rect.collidepoint(pygame.mouse.get_pos())
            if hover:
                pygame.draw.rect(screen, TAB_HOVER_COLOR, i_rect)
            text_surf = font.render(item, True, WHITE)
            t_rect = text_surf.get_rect(left=drop_x + 5, centery=i_y + item_height // 2)
            screen.blit(text_surf, t_rect)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            effective_screen_height = screen_height
            manager.set_window_resolution((screen_width, screen_height))
            if info_dialog:
                dialog_width, dialog_height = 600, 400
                dialog_x = (screen_width - dialog_width) // 2
                dialog_y = (screen_height - dialog_height) // 2
                info_dialog.set_position((dialog_x, dialog_y))
        elif event.type == pygame.KEYDOWN:
            if map_making_mode and not free_move_mode:
                if event.key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT):
                    pressed_keys.add(event.key)
                    set_map_making_direction()
                elif event.key == pygame.K_RETURN and map_making_direction is not None:
                    assign_next_tile()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    preview_next_image = True
            elif map_making_mode and free_move_mode or not map_making_mode:
                if event.key == pygame.K_e:
                    toggle_edit_mode()
                elif event.key == pygame.K_UP:
                    move_player(forward=True)
                elif event.key == pygame.K_DOWN:
                    move_player(forward=False)
                elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    rotate_player(event.key)
        elif event.type == pygame.KEYUP:
            if map_making_mode and not free_move_mode:
                if event.key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT):
                    pressed_keys.discard(event.key)
                    set_map_making_direction()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    preview_next_image = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                processed = False
                current_x_temp = 10 + 2
                tab_rects_temp = []
                for i in range(len(['File', 'Edit', 'Other'])):
                    tab_rect_temp = pygame.Rect(current_x_temp, 2, tab_width, top_bar_height - 4)
                    tab_rects_temp.append(tab_rect_temp)
                    current_x_temp += tab_width + 10
                clicked_tab = None
                for i, rect in enumerate(tab_rects_temp):
                    if rect.collidepoint(event.pos):
                        clicked_tab = i
                        break
                if clicked_tab is not None:
                    if dropdown_open == clicked_tab:
                        dropdown_open = None
                    else:
                        dropdown_open = clicked_tab
                    processed = True
                elif dropdown_open is not None:
                    i = dropdown_open
                    tab_rect_temp = tab_rects_temp[i]
                    items = dropdown_items[i]
                    item_height = 22
                    drop_width = max(tab_width, max([font.size(it)[0] for it in items]) + 20)
                    drop_height = len(items) * item_height + 4
                    drop_rect_temp = pygame.Rect(tab_rect_temp.x, tab_rect_temp.bottom, drop_width, drop_height)
                    if drop_rect_temp.collidepoint(event.pos):
                        for j, item in enumerate(items):
                            i_y = tab_rect_temp.bottom + 2 + j * item_height
                            i_rect = pygame.Rect(tab_rect_temp.x, i_y, drop_width, item_height)
                            if i_rect.collidepoint(event.pos):
                                if item == "Save Game":
                                    save_game_state()
                                elif item == "Load Game":
                                    load_game_state()
                                elif item == "Toggle Edit Mode":
                                    toggle_edit_mode()
                                elif item == "Select Folder":
                                    if not map_making_mode:
                                        directory = open_file_explorer()
                                        if directory:
                                            current_tile3 = get_current_tile()
                                            if current_tile3:
                                                current_tile3.set_directory(directory)
                                                current_image_index = 0
                                            restore_pygame_focus()
                                elif item == "Remove Folder":
                                    remove_current_tile_folder()
                                elif item == "Map Maker":
                                    start_map_making()
                                elif item == "Export Map":
                                    export_map()
                                elif item == "Import Map":
                                    import_map()
                        dropdown_open = None
                        processed = True
                    else:
                        dropdown_open = None

                if not processed:
                    if map_making_mode:
                        if exit_map_making_rect.collidepoint(event.pos):
                            exit_map_making()
                        elif lift_rect.collidepoint(event.pos):
                            toggle_free_move_mode()
                    elif not map_making_mode:
                        if hide_rect.collidepoint(event.pos) and not maximized:
                            toggle_sidebar()
                        elif map_rect.collidepoint(event.pos):
                            toggle_maximize()
                        elif info_rect.collidepoint(event.pos) and sidebar_visible and not maximized:
                            show_info_dialog()
                        elif sound_button_hitbox.collidepoint(event.pos):
                            toggle_audio_mute()
                        elif sidebar_visible and not maximized:
                            for i, link_rect in enumerate(sidebar_link_rects):
                                if link_rect.collidepoint(event.pos):
                                    link_text = sidebar_links[i]() if callable(sidebar_links[i]) else sidebar_links[i]
                                    if link_text.startswith("Edit Mode"):
                                        toggle_edit_mode()
                                    elif link_text.startswith("Audio Mode"):
                                        toggle_audio_mode()
                                    elif link_text == "Select Folder":
                                        directory = open_file_explorer()
                                        if directory:
                                            current_tile4 = get_current_tile()
                                            if current_tile4:
                                                current_tile4.set_directory(directory)
                                                current_image_index = 0
                                            restore_pygame_focus()
                                    elif link_text == "Save Game":
                                        save_game_state()
                                    elif link_text == "Load Game":
                                        load_game_state()
                                    elif link_text == "Remove Folder":
                                        remove_current_tile_folder()
                                    elif link_text == "Map Maker":
                                        start_map_making()
                                    elif link_text == "Map Share":
                                        export_map()
                                    elif link_text == "Install Map":
                                        import_map()
                                    processed = True
                                    break
                        if audio_mode or edit_mode:
                            if not maximized:
                                if 'map_area_rect' in globals() and map_area_rect.collidepoint(event.pos):
                                    rel_x = event.pos[0] - map_offset_x
                                    rel_y = event.pos[1] - map_offset_y
                                    dc = round((rel_x - BOARD_SIZE / 2) / SQUARE_SIZE)
                                    dr = round((rel_y - BOARD_SIZE / 2) / SQUARE_SIZE)
                                    new_r = player_pos[0] + dr
                                    new_c = player_pos[1] + dc
                                    new_pos = (new_r, new_c)
                                    if audio_mode:
                                        if new_pos in tiles and tiles[new_pos].active:
                                            if new_pos in selected_tiles:
                                                selected_tiles.remove(new_pos)
                                            else:
                                                selected_tiles.add(new_pos)
                                    elif edit_mode:
                                        if new_pos in tiles:
                                            tiles[new_pos].toggle_active()
                                            if not tiles[new_pos].active:
                                                del tiles[new_pos]
                                        else:
                                            tiles[new_pos] = Tile(SQUARE_SIZE)
                                            tiles[new_pos].active = True
                            else:
                                if tiles:
                                    all_pos = list(tiles.keys())
                                    min_r = min(p[0] for p in all_pos)
                                    max_r = max(p[0] for p in all_pos)
                                    min_c = min(p[1] for p in all_pos)
                                    max_c = max(p[1] for p in all_pos)
                                    bb_height = max_r - min_r + 1
                                    bb_width = max_c - min_c + 1
                                    fit_width = screen_width * 0.9
                                    fit_height = (effective_screen_height - top_bar_height) * 0.9
                                    scale = min(fit_width / bb_width, fit_height / bb_height)
                                    scaled_tile_size = scale
                                    player_rel_r = player_pos[0] - min_r
                                    player_rel_c = player_pos[1] - min_c
                                    player_draw_x = (player_rel_c + 0.5) * scale
                                    player_draw_y = (player_rel_r + 0.5) * scale
                                    offset_x = (screen_width / 2) - player_draw_x
                                    offset_y = top_bar_height + (
                                            (effective_screen_height - top_bar_height) / 2) - player_draw_y
                                    mouse_rel_x = event.pos[0] - offset_x
                                    mouse_rel_y = event.pos[1] - offset_y
                                    rel_c_float = mouse_rel_x / scale - 0.5 + min_c
                                    rel_r_float = mouse_rel_y / scale - 0.5 + min_r
                                    new_c = round(rel_c_float)
                                    new_r = round(rel_r_float)
                                    new_pos = (new_r, new_c)
                                    if audio_mode:
                                        if new_pos in tiles and tiles[new_pos].active:
                                            if new_pos in selected_tiles:
                                                selected_tiles.remove(new_pos)
                                            else:
                                                selected_tiles.add(new_pos)
                                    elif edit_mode:
                                        if new_pos in tiles:
                                            tiles[new_pos].toggle_active()
                                            if not tiles[new_pos].active:
                                                del tiles[new_pos]
                                        else:
                                            tiles[new_pos] = Tile(scaled_tile_size)
                                            tiles[new_pos].active = True
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == close_info_button:
                if info_dialog:
                    info_dialog.kill()
                    info_dialog = None
                    close_info_button = None
        manager.process_events(event)

    manager.update(1.0 / FPS)
    manager.draw_ui(screen)
    pygame.display.flip()

    if turn_flag and turn_sound:
        turn_sound.play()
        turn_flag = False
    if move_flag and move_sound:
        move_sound.play()
        move_flag = False


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
