import pygame
import pygame_gui
import ctypes
import sys
import os
import json
from tkinter import Tk, filedialog, simpledialog, messagebox
import cv2
import numpy as np
import subprocess
from pdf2image import convert_from_path  # For PDF support
import cairosvg  # For SVG support

import tile_system
from tile_system import vector_lines, VectorLine, find_vector_with_end_point

pygame.init()

# --- IMAGE LOADING HELPERS ---
def load_image_with_orientation(filepath):
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext == '.pdf':
        return load_pdf_page(filepath)
    elif ext == '.svg':
        return load_svg_image(filepath)
    else:
        image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError("Image not found or unable to load")
        try:
            from PIL import Image, ExifTags
            pil_image = Image.open(filepath)
            exif = pil_image._getexif()
            if exif is not None:
                orientation_key = next((key for key, val in ExifTags.TAGS.items() if val == 'Orientation'), None)
                if orientation_key is not None and orientation_key in exif:
                    orientation = exif[orientation_key]
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
    if image.shape[2] == 4:
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        return pygame.image.frombuffer(image_rgba.tobytes(), image_rgba.shape[1::-1], 'RGBA')
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')

def load_pdf_page(pdf_path, page_number=0, dpi=300):
    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
        if pages:
            pil_image = pages[page_number]
            open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGRA)
            return open_cv_image
        else:
            print(f"No pages found in PDF: {pdf_path}")
            return None
    except Exception as e:
        print(f"Failed to load PDF {pdf_path}: {e}")
        return None

def load_svg_image(svg_path, output_width=None, output_height=None):
    try:
        png_data = cairosvg.svg2png(url=svg_path, output_width=output_width, output_height=output_height)
        nparr = np.frombuffer(png_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        return image
    except Exception as e:
        print(f"Failed to load SVG {svg_path}: {e}")
        return None

# --- DEFAULT IMAGE ---
DEFAULT_IMAGE_PATH = 'craybg2.svg'
default_image_cv2 = load_image(DEFAULT_IMAGE_PATH)
if default_image_cv2 is None:
    print(f"Failed to load default image from {DEFAULT_IMAGE_PATH}")

# --- PYGAME SETUP ---
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("MAPPIC software")

icon = pygame.image.load('mappiclogo.ico')
pygame.display.set_icon(icon)

window_handle = pygame.display.get_wm_info()["window"]
SW_MAXIMIZE = 3
user32 = ctypes.windll.user32
user32.ShowWindow(window_handle, SW_MAXIMIZE)
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def bring_window_to_front():
    user32.SetForegroundWindow(window_handle)

MAIN_BG_COLOR = (68, 71, 90)
IMAGE_BG_COLOR = (40, 42, 54)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

root = Tk()
root.withdraw()

# --- FILE/IMAGE DIALOG HELPERS ---
def open_file_explorer():
    return filedialog.askdirectory()

def open_image_file_explorer():
    filetypes = (('Supported files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.pdf;*.svg'), ('All files', '*.*'))
    return filedialog.askopenfilename(title='Open an image', initialdir=os.getcwd(), filetypes=filetypes)

def load_image_viewing_link_areas():
    global image_viewing_link_areas
    image_viewing_link_areas = {}
    link_areas_file = os.path.join(image_viewing_directory, 'link_areas.json')
    if os.path.exists(link_areas_file):
        try:
            with open(link_areas_file, 'r') as f:
                data = json.load(f)
                for image_name, areas in data.items():
                    image_path = os.path.join(image_viewing_directory, image_name)
                    image_viewing_link_areas[image_path] = areas
            print(f"Loaded link areas from {link_areas_file}")
        except Exception as e:
            print(f"Failed to load link areas: {e}")
    else:
        print(f"No link_areas.json found in {image_viewing_directory}")

def save_image_viewing_link_areas():
    link_areas_file = os.path.join(image_viewing_directory, 'link_areas.json')
    data = {os.path.basename(image_path): areas for image_path, areas in image_viewing_link_areas.items()}
    try:
        with open(link_areas_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved link areas to {link_areas_file}")
    except Exception as e:
        print(f"Failed to save link areas: {e}")

# --- SETUP TILE SYSTEM ---
tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame

SQUARE_SIZE = 36
tile_system.SQUARE_SIZE = SQUARE_SIZE
tile_system.initialize()

# --- UI MANAGER & MAIN BOTTOM BAR (Compact Style) ---
manager = pygame_gui.UIManager((screen_width, screen_height))
bottom_bar_height = 40  # compact main bar height
bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

button_padding = 5
button_height = 30
button_texts = ["Load Game", "Save Game", "Edit Mode", "Select Image Folder", "Remove Image Folder",
                "Manage JSON Links", "Clear JSON Links", "Add Link Area", "Assign Link Folder", "Assign JSON Area", "Show Links"]
num_buttons = len(button_texts)
button_width = (screen_width - (num_buttons + 1) * button_padding) // num_buttons

buttons = []
for i, text in enumerate(button_texts):
    btn = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            (button_padding + i * (button_width + button_padding),
             (bottom_bar_height - button_height) // 2),
            (button_width, button_height)
        ),
        text=text,
        manager=manager,
        container=bottom_bar_panel
    )
    buttons.append(btn)
(load_button, save_button, edit_button, image_button, delete_button,
 json_link_button, clear_json_link_button, add_link_area_button, assign_link_folder_button,
 assign_json_area_button, show_links_button) = buttons

# --- CREATE TILE SYSTEM WINDOW WITH TWO Bottom Bar Rows ---
EXTRA_TITLEBAR_HEIGHT = 30
tile_window_width = SQUARE_SIZE * 9
tile_window_height = SQUARE_SIZE * 9
# Total bottom bar height is now two rows (e.g., 2 x 40 = 80)
tile_window_bottom_bar_total = 80

tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect((screen_width - tile_window_width - 10, 10),
                     (tile_window_width, tile_window_height + tile_window_bottom_bar_total + EXTRA_TITLEBAR_HEIGHT)),
    manager=manager,
    window_display_title="Tile System",
    object_id="#tile_window"
)

# Use the window's content container for proper positioning.
window_container = tile_window.get_container()
container_size = window_container.get_size()
tile_image_height = container_size[1] - tile_window_bottom_bar_total

tile_image_surface = pygame.Surface((tile_window_width, tile_image_height), pygame.SRCALPHA)
tile_image = pygame_gui.elements.UIImage(
    relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_image_height)),
    image_surface=tile_image_surface,
    manager=manager,
    container=window_container
)

# Create two bottom bar panels (top row and bottom row)
top_bar_height = 40
bottom_bar_height_tile = 40
tile_window_top_bottom_bar = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, tile_image_height), (tile_window_width, top_bar_height)),
    manager=manager,
    container=window_container,
    object_id="#tile_window_top_bottom_bar"
)
tile_window_bottom_bottom_bar = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, tile_image_height + top_bar_height), (tile_window_width, bottom_bar_height_tile)),
    manager=manager,
    container=window_container,
    object_id="#tile_window_bottom_bottom_bar"
)

# Top row buttons (original controls: Add, Reset View, Maximize, Set BG)
top_padding = 5
top_button_width = (tile_window_width - (5 * top_padding)) // 4
top_button_height = top_bar_height - (2 * top_padding)

add_tile_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((top_padding, top_padding), (top_button_width, top_button_height)),
    text="Add: OFF",
    manager=manager,
    container=tile_window_top_bottom_bar
)
reset_zoom_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((2 * top_padding + top_button_width, top_padding), (top_button_width, top_button_height)),
    text="Reset View",
    manager=manager,
    container=tile_window_top_bottom_bar
)
maximize_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((3 * top_padding + 2 * top_button_width, top_padding), (top_button_width, top_button_height)),
    text="Maximize",
    manager=manager,
    container=tile_window_top_bottom_bar
)
set_bg_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((4 * top_padding + 3 * top_button_width, top_padding), (top_button_width, top_button_height)),
    text="Set BG",
    manager=manager,
    container=tile_window_top_bottom_bar
)

# Bottom row buttons (new row: Sub and Size)
bottom_padding = 5
bottom_button_width = (tile_window_width - (3 * bottom_padding)) // 2
bottom_button_height = bottom_bar_height_tile - (2 * bottom_padding)

sub_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((bottom_padding, bottom_padding), (bottom_button_width, bottom_button_height)),
    text=f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}",
    manager=manager,
    container=tile_window_bottom_bottom_bar
)
size_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((2 * bottom_padding + bottom_button_width, bottom_padding), (bottom_button_width, bottom_button_height)),
    text=f"Size: {'ON' if tile_system.bg_resize_mode else 'OFF'}",
    manager=manager,
    container=tile_window_bottom_bottom_bar
)

tile_window_visible = True
tile_window_maximized = False
zoom_factor = 1.0
MIN_ZOOM = 0.5
MAX_ZOOM = 3.0

restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",
    manager=manager,
    object_id="#restore_button"
)

home_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 10), (50, 50)),
    text="Home",
    manager=manager,
    object_id="#home_button"
)

# --- VARIABLES FOR DRAGGING, ETC. ---
panning = False
pan_start_local = None  # This will hold the tile-image local coordinates when panning starts
right_dragging = False
right_pan_start_local = None

drawing_link_area = False
link_area_start_pos = None
link_area_rect = None
image_viewing_mode = False
image_viewing_images = []
image_viewing_index = 0
image_viewing_directory = ''
get_back_button = None
assign_link_folder_mode = False
assign_json_area_mode = False
show_link_areas = False
link_area_mode = False
image_viewing_link_areas = {}
add_tile_mode = False
pan_start_pos = None
last_click_time = 0
DOUBLE_CLICK_TIME = 500
last_click_pos = None
move_tile_button = None
move_tile_mode = False
follow_player = True
vector_drawing = False
current_vector_line = None
running = True
confirmation_button = None
confirmation_end_time = 0
original_button_texts = {}
original_tile_window_rect = tile_window.get_relative_rect().copy()

def update_move_button_position():
    if move_tile_button is not None and tile_window is not None:
        move_button_width = 100
        move_button_height = 40
        tile_abs = tile_window.get_abs_rect()
        move_tile_button.set_relative_position((tile_abs.left + tile_abs.width - move_button_width - 10, tile_abs.top + 10))

def display_image(current_image):
    if current_image is not None:
        img_height, img_width = current_image.shape[:2]
        image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
        scale_factor = min(image_display_area.width / img_width, image_display_area.height / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        scaled_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        scaled_image_pygame = cv2_to_pygame(scaled_image)
        image_rect = scaled_image_pygame.get_rect(center=image_display_area.center)
        temp_surface = pygame.Surface((image_rect.width, image_rect.height), pygame.SRCALPHA)
        temp_surface.blit(scaled_image_pygame, (0, 0))
        screen.blit(temp_surface, image_rect.topleft)
        return image_rect
    else:
        return None

def reset_map_view():
    global follow_player
    scaled_square_size = SQUARE_SIZE * zoom_factor
    tile_image_rect = tile_image.get_abs_rect()
    tile_system.map_offset[0] = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
    tile_system.map_offset[1] = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
    print("Map view reset to follow the player.")

def adjust_zoom(old_zoom, new_zoom):
    if follow_player:
        pass
    else:
        tile_image_rect = tile_image.get_abs_rect()
        center_x = tile_image_rect.width / 2
        center_y = tile_image_rect.height / 2
        map_x_before = (center_x - tile_system.map_offset[0]) / (SQUARE_SIZE * old_zoom)
        map_y_before = (center_y - tile_system.map_offset[1]) / (SQUARE_SIZE * old_zoom)
        tile_system.map_offset[0] = center_x - map_x_before * SQUARE_SIZE * new_zoom
        tile_system.map_offset[1] = center_y - map_y_before * SQUARE_SIZE * new_zoom

clock = pygame.time.Clock()

while running:
    time_delta = clock.tick(60) / 1000.0
    screen.fill(MAIN_BG_COLOR)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if image_viewing_mode:
                save_image_viewing_link_areas()
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            manager.set_window_resolution((screen_width, screen_height))
            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))
            home_button.set_relative_position((10, 10))
            if tile_window is not None:
                if tile_window_maximized:
                    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    tile_window.set_relative_position((image_display_area.left, image_display_area.top))
                    tile_window.set_dimensions((image_display_area.width, image_display_area.height))
                    container_size = tile_window.get_container().get_size()
                    new_tile_image_height = container_size[1] - tile_window_bottom_bar_total
                    tile_image.set_dimensions((container_size[0], new_tile_image_height))
                    tile_window_top_bottom_bar.set_relative_position((0, new_tile_image_height))
                    tile_window_top_bottom_bar.set_dimensions((container_size[0], top_bar_height))
                    tile_window_bottom_bottom_bar.set_relative_position((0, new_tile_image_height + top_bar_height))
                    tile_window_bottom_bottom_bar.set_dimensions((container_size[0], bottom_bar_height_tile))
                    # Update top row buttons using maximized container dimensions:
                    top_button_width = (container_size[0] - (5 * top_padding)) // 4
                    top_button_height = top_bar_height - (2 * top_padding)
                    add_tile_button.set_relative_position((top_padding, top_padding))
                    add_tile_button.set_dimensions((top_button_width, top_button_height))
                    reset_zoom_button.set_relative_position((2 * top_padding + top_button_width, top_padding))
                    reset_zoom_button.set_dimensions((top_button_width, top_button_height))
                    maximize_button.set_relative_position((3 * top_padding + 2 * top_button_width, top_padding))
                    maximize_button.set_dimensions((top_button_width, top_button_height))
                    set_bg_button.set_relative_position((4 * top_padding + 3 * top_button_width, top_padding))
                    set_bg_button.set_dimensions((top_button_width, top_button_height))
                    bottom_button_width = (container_size[0] - (3 * bottom_padding)) // 2
                    bottom_button_height = bottom_bar_height_tile - (2 * bottom_padding)
                    sub_button.set_relative_position((bottom_padding, bottom_padding))
                    sub_button.set_dimensions((bottom_button_width, bottom_button_height))
                    size_button.set_relative_position((2 * bottom_padding + bottom_button_width, bottom_padding))
                    size_button.set_dimensions((bottom_button_width, bottom_button_height))
                    tile_image_surface = pygame.Surface((container_size[0], new_tile_image_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                else:
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
            update_move_button_position()

        elif event.type == pygame.KEYDOWN:
            if image_viewing_mode:
                if event.key == pygame.K_ESCAPE:
                    save_image_viewing_link_areas()
                    image_viewing_mode = False
                    if get_back_button is not None:
                        get_back_button.kill()
                        get_back_button = None
                elif event.key == pygame.K_LEFT:
                    image_viewing_index = (image_viewing_index - 1) % len(image_viewing_images)
                elif event.key == pygame.K_RIGHT:
                    image_viewing_index = (image_viewing_index + 1) % len(image_viewing_images)
            else:
                if tile_system.bg_resize_mode:
                    if event.key == pygame.K_UP:
                        tile_system.bg_offset[1] -= 10
                    elif event.key == pygame.K_DOWN:
                        tile_system.bg_offset[1] += 10
                else:
                    if event.key == pygame.K_e:
                        tile_system.toggle_edit_mode()
                        edit_button.set_text(f"Edit Mode: {'ON' if tile_system.edit_mode else 'OFF'}")
                    elif event.key == pygame.K_j:
                        tile_system.toggle_json_link_mode()
                        json_link_button.set_text(f"Manage JSON Links: {'ON' if tile_system.json_link_mode else 'OFF'}")
                    elif event.key == pygame.K_c:
                        tile_system.toggle_clear_json_link_mode()
                        clear_json_link_button.set_text(f"Clear JSON Links: {'ON' if tile_system.clear_json_link_mode else 'OFF'}")
                    elif event.key == pygame.K_UP:
                        tile_system.save_current_state_to_history()
                        tile_system.move_player(forward=True)
                    elif event.key == pygame.K_DOWN:
                        tile_system.save_current_state_to_history()
                        tile_system.move_player(forward=False)
                    elif event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                if tile_system.bg_resize_mode:
                    old_scale = tile_system.bg_scale
                    new_scale = min(old_scale + 0.1, 5.0)
                    rect = tile_image.get_relative_rect()
                    P_x = rect.width / 2
                    P_y = rect.height / 2
                    old_offset = tile_system.bg_offset
                    new_offset_x = P_x - (P_x - old_offset[0]) * (new_scale / old_scale)
                    new_offset_y = P_y - (P_y - old_offset[1]) * (new_scale / old_scale)
                    tile_system.bg_scale = new_scale
                    tile_system.bg_offset = [new_offset_x, new_offset_y]
                else:
                    old_zoom = zoom_factor
                    zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
                    adjust_zoom(old_zoom, zoom_factor)
            elif event.button == 5:
                if tile_system.bg_resize_mode:
                    old_scale = tile_system.bg_scale
                    new_scale = max(old_scale - 0.1, 0.1)
                    rect = tile_image.get_relative_rect()
                    P_x = rect.width / 2
                    P_y = rect.height / 2
                    old_offset = tile_system.bg_offset
                    new_offset_x = P_x - (P_x - old_offset[0]) * (new_scale / old_scale)
                    new_offset_y = P_y - (P_y - old_offset[1]) * (new_scale / old_scale)
                    tile_system.bg_scale = new_scale
                    tile_system.bg_offset = [new_offset_x, new_offset_y]
                else:
                    old_zoom = zoom_factor
                    zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
                    adjust_zoom(old_zoom, zoom_factor)
            elif event.button == 1:
                # When starting a drag, record the local coordinates (relative to tile_image)
                if tile_window and tile_window.visible and tile_image is not None:
                    tile_image_rect = tile_image.get_abs_rect()
                    local_pos = (event.pos[0] - tile_image_rect.left, event.pos[1] - tile_image_rect.top)
                if add_tile_mode:
                    if tile_window and tile_window.visible and tile_image is not None:
                        scaled_square_size = SQUARE_SIZE * zoom_factor
                        if follow_player:
                            offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
                            offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
                        else:
                            offset_x = tile_system.map_offset[0]
                            offset_y = tile_system.map_offset[1]
                        tile_col = int((local_pos[0] - offset_x) // scaled_square_size)
                        tile_row = int((local_pos[1] - offset_y) // scaled_square_size)
                        tile = tile_system.get_tile(tile_row, tile_col)
                        if tile:
                            if not tile.directory:
                                tile_system.delete_tile(tile_row, tile_col)
                                print(f"Deleted empty tile at ({tile_row}, {tile_col})")
                            else:
                                confirm = messagebox.askyesno("Delete Tile", "This tile has images, are you sure you want to delete it?")
                                bring_window_to_front()
                                if confirm:
                                    tile_system.delete_tile(tile_row, tile_col)
                                    print(f"Deleted tile with images at ({tile_row}, {tile_col})")
                                else:
                                    print("Tile deletion canceled")
                        else:
                            tile_system.create_tile(tile_row, tile_col)
                            print(f"Created tile at ({tile_row}, {tile_col})")
                else:
                    if tile_window and tile_window.visible and tile_image is not None:
                        scaled_square_size = SQUARE_SIZE * zoom_factor
                        if follow_player:
                            offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
                            offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
                        else:
                            offset_x = tile_system.map_offset[0]
                            offset_y = tile_system.map_offset[1]
                        tile_col = int((local_pos[0] - offset_x) // scaled_square_size)
                        tile_row = int((local_pos[1] - offset_y) // scaled_square_size)
                        current_time = pygame.time.get_ticks()
                        if last_click_time and (current_time - last_click_time) < DOUBLE_CLICK_TIME:
                            if last_click_pos and (abs(event.pos[0] - last_click_pos[0]) < 10) and (abs(event.pos[1] - last_click_pos[1]) < 10):
                                tile_system.move_player_to_tile(tile_row, tile_col)
                                last_click_time = 0
                                if follow_player:
                                    reset_map_view()
                            else:
                                last_click_time = current_time
                                last_click_pos = event.pos
                        else:
                            last_click_time = current_time
                            last_click_pos = event.pos
                            panning = True
                            pan_start_pos = event.pos
                            # Set the local starting point for panning
                            pan_start_local = local_pos
                            follow_player = False
                    elif event.button == 1 and tile_window is not None and not tile_window.get_abs_rect().collidepoint(event.pos):
                        if not add_tile_mode:
                            panning = True
                            pan_start_pos = event.pos
                            follow_player = False
            elif event.button == 3:
                if tile_window and tile_window.visible and tile_image is not None:
                    tile_image_rect = tile_image.get_abs_rect()
                    local_pos = (event.pos[0] - tile_image_rect.left, event.pos[1] - tile_image_rect.top)
                    scaled_square_size = SQUARE_SIZE * zoom_factor
                    if follow_player:
                        offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
                        offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
                    else:
                        offset_x = tile_system.map_offset[0]
                        offset_y = tile_system.map_offset[1]
                    tile_col = int((local_pos[0] - offset_x) // scaled_square_size)
                    tile_row = int((local_pos[1] - offset_y) // scaled_square_size)
                    if not add_tile_mode:
                        tile = tile_system.get_tile(tile_row, tile_col)
                        if tile:
                            if tile_system.edit_mode:
                                tile.toggle_active()
                            elif tile_system.json_link_mode:
                                selected_file = filedialog.askopenfilename(
                                    title="Select a JSON file",
                                    initialdir=tile_system.save_directory,
                                    filetypes=[("JSON files", "*.json")]
                                )
                                if selected_file:
                                    tile.set_json_file(selected_file)
                            elif tile_system.clear_json_link_mode:
                                tile.clear_json_file()
                            else:
                                directory = open_file_explorer()
                                if directory:
                                    tile.set_directory(directory)
                                    bring_window_to_front()
                        else:
                            print(f"No tile exists at position ({tile_row}, {tile_col}).")
                    else:
                        tile = tile_system.get_tile(tile_row, tile_col)
                        if tile:
                            if not tile.directory:
                                tile_system.delete_tile(tile_row, tile_col)
                                print(f"Deleted empty tile at ({tile_row}, {tile_col})")
                            else:
                                confirm = messagebox.askyesno("Delete Tile", "This tile has images, are you sure you want to delete it?")
                                bring_window_to_front()
                                if confirm:
                                    tile_system.delete_tile(tile_row, tile_col)
                                    print(f"Deleted tile with images at ({tile_row}, {tile_col})")
                                else:
                                    print("Tile deletion canceled")
                        else:
                            tile_system.create_tile(tile_row, tile_col)
                            print(f"Created tile at ({tile_row}, {tile_col})")
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                panning = False
                pan_start_local = None
            elif event.button == 3:
                right_dragging = False
                right_pan_start_local = None
        elif event.type == pygame.MOUSEMOTION:
            if right_dragging and tile_window and tile_window.visible and tile_image is not None:
                tile_image_rect = tile_image.get_abs_rect()
                current_local_x = event.pos[0] - tile_image_rect.left
                current_local_y = event.pos[1] - tile_image_rect.top
                if right_pan_start_local is not None:
                    dx = current_local_x - right_pan_start_local[0]
                    dy = current_local_y - right_pan_start_local[1]
                    tile_system.map_offset[0] += dx
                    tile_system.map_offset[1] += dy
                    tile_system.bg_offset[0] += dx
                    tile_system.bg_offset[1] += dy
                    right_pan_start_local = (current_local_x, current_local_y)
            elif panning and tile_window and tile_window.visible and tile_image is not None:
                tile_image_rect = tile_image.get_abs_rect()
                current_local_x = event.pos[0] - tile_image_rect.left
                current_local_y = event.pos[1] - tile_image_rect.top
                if pan_start_local is not None:
                    dx = current_local_x - pan_start_local[0]
                    dy = current_local_y - pan_start_local[1]
                    if tile_system.bg_resize_mode:
                        tile_system.bg_offset[0] += dx
                        tile_system.bg_offset[1] += dy
                    else:
                        tile_system.map_offset[0] += dx
                        tile_system.map_offset[1] += dy
                    pan_start_local = (current_local_x, current_local_y)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == load_button:
                tile_system.save_current_state_to_history()
                tile_system.load_game_state()
            elif event.ui_element == save_button:
                tile_system.save_game_state()
                if image_viewing_mode:
                    save_image_viewing_link_areas()
            elif event.ui_element == edit_button:
                tile_system.toggle_edit_mode()
                edit_button.set_text(f"Edit Mode: {'ON' if tile_system.edit_mode else 'OFF'}")
            elif event.ui_element == image_button:
                directory = open_file_explorer()
                if directory:
                    current_tile = tile_system.get_current_tile()
                    if current_tile:
                        current_tile.set_directory(directory)
                        bring_window_to_front()
                    else:
                        print("No current tile to set directory.")
            elif event.ui_element == delete_button:
                current_tile = tile_system.get_current_tile()
                if current_tile:
                    current_tile.clear_directory()
                    print("Removed folder association from the current tile.")
                else:
                    print("No current tile to remove directory.")
            elif event.ui_element == json_link_button:
                tile_system.toggle_json_link_mode()
                json_link_button.set_text(f"Manage JSON Links: {'ON' if tile_system.json_link_mode else 'OFF'}")
            elif event.ui_element == clear_json_link_button:
                tile_system.toggle_clear_json_link_mode()
                clear_json_link_button.set_text(f"Clear JSON Links: {'ON' if tile_system.clear_json_link_mode else 'OFF'}")
            elif event.ui_element == add_link_area_button:
                tile_system.link_area_mode = not tile_system.link_area_mode
                add_link_area_button.set_text(f"Add Link Area: {'ON' if tile_system.link_area_mode else 'OFF'}")
                link_area_mode = tile_system.link_area_mode
            elif event.ui_element == assign_link_folder_button:
                assign_link_folder_mode = not assign_link_folder_mode
                assign_link_folder_button.set_text(f"Assign Link Folder: {'ON' if assign_link_folder_mode else 'OFF'}")
            elif event.ui_element == assign_json_area_button:
                assign_json_area_mode = not assign_json_area_mode
                assign_json_area_button.set_text(f"Assign JSON Area: {'ON' if assign_json_area_mode else 'OFF'}")
            elif event.ui_element == show_links_button:
                show_link_areas = not show_link_areas
                show_links_button.set_text(f"Show Links: {'ON' if show_link_areas else 'OFF'}")
            elif event.ui_element == add_tile_button:
                add_tile_mode = not add_tile_mode
                add_tile_button.set_text(f"Add: {'ON' if add_tile_mode else 'OFF'}")
                if add_tile_mode:
                    if move_tile_button is None:
                        move_button_width = 100
                        move_button_height = 40
                        move_tile_button = pygame_gui.elements.UIButton(
                            relative_rect=pygame.Rect((0, 0), (move_button_width, move_button_height)),
                            text="Move",
                            manager=manager
                        )
                        update_move_button_position()
                else:
                    if move_tile_button is not None:
                        move_tile_button.kill()
                        move_tile_button = None
            elif event.ui_element == move_tile_button:
                move_tile_mode = not move_tile_mode
                move_tile_button.set_text("Move (ON)" if move_tile_mode else "Move")
                if move_tile_mode:
                    move_tile_button.select()
                else:
                    move_tile_button.unselect()
                    tile_system.deselect_tile()
            elif event.ui_element == reset_zoom_button:
                zoom_factor = 1.0
                reset_map_view()
                follow_player = True
            elif event.ui_element == maximize_button:
                tile_window_maximized = not tile_window_maximized
                if tile_window_maximized:
                    maximize_button.set_text("Restore")
                    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    tile_window.set_relative_position((image_display_area.left, image_display_area.top))
                    tile_window.set_dimensions((image_display_area.width, image_display_area.height))
                    container_size = tile_window.get_container().get_size()
                    new_tile_image_height = container_size[1] - tile_window_bottom_bar_total
                    tile_image.set_dimensions((container_size[0], new_tile_image_height))
                    tile_window_top_bottom_bar.set_relative_position((0, new_tile_image_height))
                    tile_window_top_bottom_bar.set_dimensions((container_size[0], top_bar_height))
                    tile_window_bottom_bottom_bar.set_relative_position((0, new_tile_image_height + top_bar_height))
                    tile_window_bottom_bottom_bar.set_dimensions((container_size[0], bottom_bar_height_tile))
                    # Recalculate top row buttons based on maximized container:
                    top_button_width = (container_size[0] - (5 * top_padding)) // 4
                    top_button_height = top_bar_height - (2 * top_padding)
                    add_tile_button.set_relative_position((top_padding, top_padding))
                    add_tile_button.set_dimensions((top_button_width, top_button_height))
                    reset_zoom_button.set_relative_position((2 * top_padding + top_button_width, top_padding))
                    reset_zoom_button.set_dimensions((top_button_width, top_button_height))
                    maximize_button.set_relative_position((3 * top_padding + 2 * top_button_width, top_padding))
                    maximize_button.set_dimensions((top_button_width, top_button_height))
                    set_bg_button.set_relative_position((4 * top_padding + 3 * top_button_width, top_padding))
                    set_bg_button.set_dimensions((top_button_width, top_button_height))
                    bottom_button_width = (container_size[0] - (3 * bottom_padding)) // 2
                    bottom_button_height = bottom_bar_height_tile - (2 * bottom_padding)
                    sub_button.set_relative_position((bottom_padding, bottom_padding))
                    sub_button.set_dimensions((bottom_button_width, bottom_button_height))
                    size_button.set_relative_position((2 * bottom_padding + bottom_button_width, bottom_padding))
                    size_button.set_dimensions((bottom_button_width, bottom_button_height))
                    tile_image_surface = pygame.Surface((container_size[0], new_tile_image_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                else:
                    maximize_button.set_text("Maximize")
                    # Restore to fixed (normal) layout
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                    tile_window.set_dimensions((tile_window_width, tile_window_height + tile_window_bottom_bar_total + EXTRA_TITLEBAR_HEIGHT))
                    tile_image.set_dimensions((tile_window_width, tile_window_height))
                    tile_window_top_bottom_bar.set_relative_position((0, tile_window_height))
                    tile_window_top_bottom_bar.set_dimensions((tile_window_width, 40))
                    tile_window_bottom_bottom_bar.set_relative_position((0, tile_window_height + 40))
                    tile_window_bottom_bottom_bar.set_dimensions((tile_window_width, 40))
                    tile_image_surface = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                    # Use fixed (normal) values for buttons:
                    top_padding = 5
                    top_button_width = (tile_window_width - (5 * top_padding)) // 4
                    top_button_height = 40 - (2 * top_padding)
                    add_tile_button.set_relative_position((top_padding, top_padding))
                    add_tile_button.set_dimensions((top_button_width, top_button_height))
                    reset_zoom_button.set_relative_position((2 * top_padding + top_button_width, top_padding))
                    reset_zoom_button.set_dimensions((top_button_width, top_button_height))
                    maximize_button.set_relative_position((3 * top_padding + 2 * top_button_width, top_padding))
                    maximize_button.set_dimensions((top_button_width, top_button_height))
                    set_bg_button.set_relative_position((4 * top_padding + 3 * top_button_width, top_padding))
                    set_bg_button.set_dimensions((top_button_width, top_button_height))
                    bottom_padding = 5
                    bottom_button_width = (tile_window_width - (3 * bottom_padding)) // 2
                    bottom_button_height = 40 - (2 * bottom_padding)
                    sub_button.set_relative_position((bottom_padding, bottom_padding))
                    sub_button.set_dimensions((bottom_button_width, bottom_button_height))
                    size_button.set_relative_position((2 * bottom_padding + bottom_button_width, bottom_padding))
                    size_button.set_dimensions((bottom_button_width, bottom_button_height))
            elif event.ui_element == set_bg_button:
                bg_image_path = open_image_file_explorer()
                if bg_image_path:
                    background_image_cv2 = load_image(bg_image_path)
                    if background_image_cv2 is not None:
                        background_image_surface = cv2_to_pygame(background_image_cv2)
                        tile_system.set_background_image(background_image_surface, bg_image_path)
                bring_window_to_front()
            elif event.ui_element == restore_tile_window_button:
                if tile_window is None:
                    tile_window = pygame_gui.elements.UIWindow(
                        rect=pygame.Rect((screen_width - tile_window_width - 10, 10),
                                         (tile_window_width, tile_window_height + tile_window_bottom_bar_total + EXTRA_TITLEBAR_HEIGHT)),
                        manager=manager,
                        window_display_title="Tile System",
                        object_id="#tile_window"
                    )
                    window_container = tile_window.get_container()
                    container_size = window_container.get_size()
                    tile_image_height = container_size[1] - tile_window_bottom_bar_total
                    tile_image_surface = pygame.Surface((tile_window_width, tile_image_height), pygame.SRCALPHA)
                    tile_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_image_height)),
                        image_surface=tile_image_surface,
                        manager=manager,
                        container=window_container
                    )
                    tile_window_top_bottom_bar = pygame_gui.elements.UIPanel(
                        relative_rect=pygame.Rect((0, tile_image_height), (tile_window_width, 40)),
                        manager=manager,
                        container=window_container,
                        object_id="#tile_window_top_bottom_bar"
                    )
                    tile_window_bottom_bottom_bar = pygame_gui.elements.UIPanel(
                        relative_rect=pygame.Rect((0, tile_image_height + 40), (tile_window_width, 40)),
                        manager=manager,
                        container=window_container,
                        object_id="#tile_window_bottom_bottom_bar"
                    )
                    top_padding = 5
                    top_button_width = (tile_window_width - (5 * top_padding)) // 4
                    top_button_height = 40 - (2 * top_padding)
                    add_tile_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((top_padding, top_padding), (top_button_width, top_button_height)),
                        text="Add: OFF",
                        manager=manager,
                        container=tile_window_top_bottom_bar
                    )
                    reset_zoom_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((2 * top_padding + top_button_width, top_padding), (top_button_width, top_button_height)),
                        text="Reset View",
                        manager=manager,
                        container=tile_window_top_bottom_bar
                    )
                    maximize_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((3 * top_padding + 2 * top_button_width, top_padding), (top_button_width, top_button_height)),
                        text="Maximize",
                        manager=manager,
                        container=tile_window_top_bottom_bar
                    )
                    set_bg_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((4 * top_padding + 3 * top_button_width, top_padding), (top_button_width, top_button_height)),
                        text="Set BG",
                        manager=manager,
                        container=tile_window_top_bottom_bar
                    )
                    bottom_padding = 5
                    bottom_button_width = (tile_window_width - (3 * bottom_padding)) // 2
                    bottom_button_height = 40 - (2 * bottom_padding)
                    sub_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((bottom_padding, bottom_padding), (bottom_button_width, bottom_button_height)),
                        text=f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}",
                        manager=manager,
                        container=tile_window_bottom_bottom_bar
                    )
                    size_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((2 * bottom_padding + bottom_button_width, bottom_padding), (bottom_button_width, bottom_button_height)),
                        text=f"Size: {'ON' if tile_system.bg_resize_mode else 'OFF'}",
                        manager=manager,
                        container=tile_window_bottom_bottom_bar
                    )
                    tile_window_visible = True
            elif event.ui_element == home_button:
                subprocess.Popen(["python", "home_page.py"])
                pygame.quit()
                sys.exit()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if tile_window and event.ui_element == tile_window:
                tile_window.kill()
                tile_window = None
                tile_window_visible = False
                tile_window_maximized = False

        manager.process_events(event)

    manager.update(time_delta)

    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    if image_viewing_mode:
        if image_viewing_images:
            image_path = image_viewing_images[image_viewing_index]
            current_image = load_image(image_path)
            image_rect = display_image(current_image)
            if image_rect is None:
                current_image = default_image_cv2
                image_rect = display_image(current_image)
        else:
            current_image = default_image_cv2
            image_rect = display_image(current_image)
        if show_link_areas:
            link_areas = image_viewing_link_areas.get(image_path, [])
            for area in link_areas:
                rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                x0 = image_rect.left + rel_x0 * image_rect.width
                y0 = image_rect.top + rel_y0 * image_rect.height
                x1 = image_rect.left + rel_x1 * image_rect.width
                y1 = image_rect.top + rel_y1 * image_rect.height
                rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
                pygame.draw.rect(screen, (255, 0, 0), rect, 2)
        if drawing_link_area and link_area_rect is not None:
            pygame.draw.rect(screen, (0, 255, 0), link_area_rect, 1)
    else:
        current_tile = tile_system.get_current_tile()
        if current_tile and current_tile.image_filenames:
            current_image = current_tile.get_current_image(tile_system.current_image_index)
            image_rect = display_image(current_image)
            if image_rect is None:
                current_image = default_image_cv2
                image_rect = display_image(current_image)
        else:
            current_image = default_image_cv2
            image_rect = display_image(current_image)
        image_index = tile_system.current_image_index if current_tile else 0
        link_areas = current_tile.link_areas.get(image_index, []) if current_tile else []
        if show_link_areas:
            for area in link_areas:
                rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                x0 = image_rect.left + rel_x0 * image_rect.width
                y0 = image_rect.top + rel_y0 * image_rect.height
                x1 = image_rect.left + rel_x1 * image_rect.width
                y1 = image_rect.top + rel_y1 * image_rect.height
                rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
                pygame.draw.rect(screen, (255, 0, 0), rect, 2)
        if drawing_link_area and link_area_rect is not None:
            pygame.draw.rect(screen, (0, 255, 0), link_area_rect, 1)

    if tile_window is not None and not image_viewing_mode:
        tile_image.image.fill((0, 0, 0, 0))
        local_mouse_pos = pygame.mouse.get_pos()
        tile_image_rect = tile_image.get_abs_rect()
        local_mouse_pos = (local_mouse_pos[0] - tile_image_rect.left, local_mouse_pos[1] - tile_image_rect.top)
        visible_area = pygame.Rect(0, 0, tile_image_rect.width, tile_image_rect.height)
        scaled_square_size = SQUARE_SIZE * zoom_factor
        if follow_player:
            offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
            offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
        else:
            offset_x = tile_system.map_offset[0]
            offset_y = tile_system.map_offset[1]
        tile_system.draw_board(local_mouse_pos, offset_x, offset_y, tile_image.image, visible_area, zoom_factor)
        tile_system.draw_player(offset_x, offset_y, tile_image.image, zoom_factor)
        if add_tile_mode:
            tile_col = int((local_mouse_pos[0] - offset_x) // scaled_square_size)
            tile_row = int((local_mouse_pos[1] - offset_y) // scaled_square_size)
            tile_system.draw_ghost_tile(tile_row, tile_col, offset_x, offset_y, tile_image.image, zoom_factor)
        tile_image_surface.blit(tile_image.image, (0, 0))

    manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
