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

DEFAULT_IMAGE_PATH = 'craybg2.svg'
default_image_cv2 = load_image(DEFAULT_IMAGE_PATH)
if default_image_cv2 is None:
    print(f"Failed to load default image from {DEFAULT_IMAGE_PATH}")

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

def open_file_explorer():
    directory = filedialog.askdirectory()
    return directory

def open_image_file_explorer():
    filetypes = (
        ('Supported files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.pdf;*.svg'),
        ('All files', '*.*')
    )
    filename = filedialog.askopenfilename(
        title='Open an image',
        initialdir=os.getcwd(),
        filetypes=filetypes)
    return filename

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
    data = {}
    for image_path, areas in image_viewing_link_areas.items():
        image_name = os.path.basename(image_path)
        data[image_name] = areas
    try:
        with open(link_areas_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved link areas to {link_areas_file}")
    except Exception as e:
        print(f"Failed to save link areas: {e}")

tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame

SQUARE_SIZE = 36
tile_system.SQUARE_SIZE = SQUARE_SIZE
tile_system.initialize()

manager = pygame_gui.UIManager((screen_width, screen_height))
bottom_bar_height = 60
bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

button_padding = 10
button_height = 40
button_texts = ["Load Game", "Save Game", "Edit Mode", "Select Image Folder", "Remove Image Folder",
                "Manage JSON Links", "Clear JSON Links", "Add Link Area", "Assign Link Folder", "Assign JSON Area", "Show Links"]
num_buttons = len(button_texts)
button_width = (screen_width - (num_buttons + 1) * button_padding) // num_buttons

buttons = []
for i, text in enumerate(button_texts):
    button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((button_padding + i * (button_width + button_padding),
                                   (bottom_bar_height - button_height) // 2),
                                  (button_width, button_height)),
        text=text,
        manager=manager,
        container=bottom_bar_panel
    )
    buttons.append(button)

(load_button, save_button, edit_button, image_button, delete_button,
 json_link_button, clear_json_link_button, add_link_area_button, assign_link_folder_button,
 assign_json_area_button, show_links_button) = buttons

tile_window_width = SQUARE_SIZE * 9
tile_window_height = SQUARE_SIZE * 9
tile_window_bottom_bar_height = 60

tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect((screen_width - tile_window_width - 10, 10), (tile_window_width, tile_window_height + tile_window_bottom_bar_height)),
    manager=manager,
    window_display_title="Tile System",
    object_id="#tile_window"
)

tile_window_left_panel_width = 50
tile_window_left_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, 0), (tile_window_left_panel_width, tile_window_height)),
    manager=manager,
    container=tile_window,
    object_id="#tile_window_left_panel"
)

tile_image_width = tile_window_width - tile_window_left_panel_width
tile_image_surface = pygame.Surface((tile_image_width, tile_window_height), pygame.SRCALPHA)
tile_image = pygame_gui.elements.UIImage(
    relative_rect=pygame.Rect((tile_window_left_panel_width, 0), (tile_image_width, tile_window_height)),
    image_surface=tile_image_surface,
    manager=manager,
    container=tile_window
)

sub_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((0, 0), (tile_window_left_panel_width, 50)),
    text=f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}",
    manager=manager,
    container=tile_window_left_panel
)

tile_window_bottom_bar = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, tile_window_height), (tile_window_width, tile_window_bottom_bar_height)),
    manager=manager,
    container=tile_window,
    object_id="#tile_window_bottom_bar"
)

tile_window_button_width = (tile_window_width - 50) // 4
tile_window_button_height = tile_window_bottom_bar_height - 10
tile_window_button_padding = 10

add_tile_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding, 5), (tile_window_button_width, tile_window_button_height)),
    text="Add: OFF",
    manager=manager,
    container=tile_window_bottom_bar
)

reset_zoom_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding * 2 + tile_window_button_width, 5), (tile_window_button_width, tile_window_button_height)),
    text="Reset View",
    manager=manager,
    container=tile_window_bottom_bar
)

maximize_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding * 3 + tile_window_button_width * 2, 5), (tile_window_button_width, tile_window_button_height)),
    text="Maximize",
    manager=manager,
    container=tile_window_bottom_bar
)

set_bg_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding * 4 + tile_window_button_width * 3, 5), (tile_window_button_width, tile_window_button_height)),
    text="Set BG",
    manager=manager,
    container=tile_window_bottom_bar
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
panning = False
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
        move_button_x = tile_window.get_abs_rect().left + tile_window.get_abs_rect().width - move_button_width - 10
        move_button_y = tile_window.get_abs_rect().top + 10
        move_tile_button.set_relative_position((move_button_x, move_button_y))

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
            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))
            home_button.set_relative_position((10, 10))
            if tile_window is not None:
                if tile_window_maximized:
                    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    tile_window.set_relative_position((image_display_area.left, image_display_area.top))
                    tile_window.set_dimensions((image_display_area.width, image_display_area.height))
                    tile_image_width = image_display_area.width - tile_window_left_panel_width
                    tile_image_height = image_display_area.height - tile_window_bottom_bar_height
                    tile_image.set_dimensions((tile_image_width, tile_image_height))
                    tile_image.set_relative_position((tile_window_left_panel_width, 0))
                    tile_window_left_panel.set_dimensions((tile_window_left_panel_width, image_display_area.height - tile_window_bottom_bar_height))
                    tile_window_bottom_bar.set_relative_position((0, image_display_area.height - tile_window_bottom_bar_height))
                    tile_window_bottom_bar.set_dimensions((image_display_area.width, tile_window_bottom_bar_height))
                    tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)
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
                old_zoom = zoom_factor
                zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
                adjust_zoom(old_zoom, zoom_factor)
            elif event.button == 5:
                old_zoom = zoom_factor
                zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
                adjust_zoom(old_zoom, zoom_factor)
            elif image_viewing_mode:
                if 'image_rect' in locals() and image_rect.collidepoint(event.pos):
                    if (link_area_mode or assign_link_folder_mode or assign_json_area_mode) and event.button == 1:
                        link_area_start_pos = event.pos
                        drawing_link_area = True
            else:
                if tile_window is not None:
                    tile_window_rect = tile_window.get_abs_rect()
                    tile_image_rect = tile_image.get_abs_rect()
                    if tile_image_rect.collidepoint(event.pos):
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

                        if event.button == 1:
                            if tile_system.sub_grid_visible:
                                tile, subgrid_pos = tile_system.get_subgrid_square_at_pixel(local_pos[0], local_pos[1], offset_x, offset_y, zoom_factor)
                                if tile and subgrid_pos:
                                    sub_row, sub_col = subgrid_pos
                                    if tile.subgrid_occupied[sub_row][sub_col]:
                                        current_time = pygame.time.get_ticks()
                                        if last_click_time and (current_time - last_click_time) < DOUBLE_CLICK_TIME:
                                            vector = tile_system.find_vector_with_end_point(tile, (sub_row, sub_col))
                                            if vector:
                                                vector_drawing = True
                                                current_vector_line = vector
                                                tile.set_subgrid_square_occupied(sub_row, sub_col, False)
                                                vector.end_tile = None
                                                vector.end_subgrid_pos = None
                                                vector.is_complete = False
                                                last_click_time = 0
                                        else:
                                            last_click_time = current_time
                                            last_click_pos = event.pos
                                    else:
                                        if not vector_drawing:
                                            vector_drawing = True
                                            current_vector_line = tile_system.VectorLine(tile, (sub_row, sub_col))
                                            tile.set_subgrid_square_occupied(sub_row, sub_col, True)
                                        else:
                                            if current_vector_line.start_tile != tile:
                                                current_vector_line.end_tile = tile
                                                current_vector_line.end_subgrid_pos = (sub_row, sub_col)
                                                current_vector_line.is_complete = True
                                                vector_drawing = False
                                                tile.set_subgrid_square_occupied(sub_row, sub_col, True)
                                                tile_system.vector_lines.append(current_vector_line)
                                                current_vector_line = None
                                            else:
                                                messagebox.showwarning("Invalid Connection", "Cannot create a vector within the same tile.")
                                                bring_window_to_front()
                            elif add_tile_mode:
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
                            elif move_tile_mode:
                                if tile_system.selected_tile is None:
                                    tile_system.select_tile(tile_row, tile_col)
                                else:
                                    tile_system.move_selected_tile_to(tile_row, tile_col)
                                    tile_system.deselect_tile()
                            else:
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
                                    follow_player = False
                        elif event.button == 3:
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
                    if event.button == 1 and not tile_window.get_abs_rect().collidepoint(event.pos):
                        if not add_tile_mode:
                            panning = True
                            pan_start_pos = event.pos
                            follow_player = False
        elif event.type == pygame.MOUSEBUTTONUP:
            if drawing_link_area and event.button == 1:
                drawing_link_area = False
                if link_area_rect is not None:
                    link_area_rect = link_area_rect.clip(image_rect)
                    img_x0, img_y0 = image_rect.topleft
                    img_width, img_height = image_rect.size
                    rel_x0 = (link_area_rect.left - img_x0) / img_width
                    rel_y0 = (link_area_rect.top - img_y0) / img_height
                    rel_x1 = (link_area_rect.right - img_x0) / img_width
                    rel_y1 = (link_area_rect.bottom - img_y0) / img_height
                    if image_viewing_mode:
                        image_path = image_viewing_images[image_viewing_index]
                        if image_path not in image_viewing_link_areas:
                            image_viewing_link_areas[image_path] = []
                        area = {'coords': [rel_x0, rel_y0, rel_x1, rel_y1], 'link': None, 'json': None}
                        image_viewing_link_areas[image_path].append(area)
                        print(f"Added link area to image {image_path}: {area}")
                    else:
                        current_tile = tile_system.get_current_tile()
                        if current_tile:
                            image_index = tile_system.current_image_index
                            area = {'coords': [rel_x0, rel_y0, rel_x1, rel_y1], 'link': None, 'json': None}
                            current_tile.add_link_area(image_index, area)
                        else:
                            print("No current tile to add link area.")
                    link_area_rect = None
                    link_area_start_pos = None
            elif drawing_link_area:
                drawing_link_area = False
                link_area_rect = None
            elif event.button == 1 and panning:
                panning = False
        elif event.type == pygame.MOUSEMOTION:
            if drawing_link_area:
                x0, y0 = link_area_start_pos
                x1, y1 = event.pos
                link_area_rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            elif panning:
                dx = event.pos[0] - pan_start_pos[0]
                dy = event.pos[1] - pan_start_pos[1]
                tile_system.map_offset[0] += dx
                tile_system.map_offset[1] += dy
                pan_start_pos = event.pos
            elif vector_drawing and current_vector_line:
                pass
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
                if tile_system.link_area_mode:
                    tile_system.edit_mode = False
                    tile_system.json_link_mode = False
                    tile_system.clear_json_link_mode = False
                    assign_link_folder_mode = False
                    assign_json_area_mode = False
                    edit_button.set_text("Edit Mode: OFF")
                    json_link_button.set_text("Manage JSON Links: OFF")
                    clear_json_link_button.set_text("Clear JSON Links: OFF")
                    assign_link_folder_button.set_text("Assign Link Folder: OFF")
                    assign_json_area_button.set_text("Assign JSON Area: OFF")
            elif event.ui_element == assign_link_folder_button:
                assign_link_folder_mode = not assign_link_folder_mode
                assign_link_folder_button.set_text(f"Assign Link Folder: {'ON' if assign_link_folder_mode else 'OFF'}")
                if assign_link_folder_mode:
                    tile_system.edit_mode = False
                    tile_system.json_link_mode = False
                    tile_system.clear_json_link_mode = False
                    tile_system.link_area_mode = False
                    link_area_mode = False
                    assign_json_area_mode = False
                    drawing_link_area = False
                    edit_button.set_text("Edit Mode: OFF")
                    json_link_button.set_text("Manage JSON Links: OFF")
                    clear_json_link_button.set_text("Clear JSON Links: OFF")
                    add_link_area_button.set_text("Add Link Area: OFF")
                    assign_json_area_button.set_text("Assign JSON Area: OFF")
            elif event.ui_element == assign_json_area_button:
                assign_json_area_mode = not assign_json_area_mode
                assign_json_area_button.set_text(f"Assign JSON Area: {'ON' if assign_json_area_mode else 'OFF'}")
                if assign_json_area_mode:
                    tile_system.edit_mode = False
                    tile_system.json_link_mode = False
                    tile_system.clear_json_link_mode = False
                    tile_system.link_area_mode = False
                    link_area_mode = False
                    assign_link_folder_mode = False
                    drawing_link_area = False
                    edit_button.set_text("Edit Mode: OFF")
                    json_link_button.set_text("Manage JSON Links: OFF")
                    clear_json_link_button.set_text("Clear JSON Links: OFF")
                    add_link_area_button.set_text("Add Link Area: OFF")
                    assign_link_folder_button.set_text("Assign Link Folder: OFF")
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
                    tile_image_width = image_display_area.width - tile_window_left_panel_width
                    tile_image_height = image_display_area.height - tile_window_bottom_bar_height
                    tile_image.set_dimensions((tile_image_width, tile_image_height))
                    tile_image.set_relative_position((tile_window_left_panel_width, 0))
                    tile_window_left_panel.set_dimensions((tile_window_left_panel_width, image_display_area.height - tile_window_bottom_bar_height))
                    tile_window_bottom_bar.set_relative_position((0, image_display_area.height - tile_window_bottom_bar_height))
                    tile_window_bottom_bar.set_dimensions((image_display_area.width, tile_window_bottom_bar_height))
                    tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                else:
                    maximize_button.set_text("Maximize")
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                    tile_window.set_dimensions((tile_window_width, tile_window_height + tile_window_bottom_bar_height))
                    tile_image_width = tile_window_width - tile_window_left_panel_width
                    tile_image_height = tile_window_height
                    tile_image.set_dimensions((tile_image_width, tile_image_height))
                    tile_image.set_relative_position((tile_window_left_panel_width, 0))
                    tile_window_left_panel.set_dimensions((tile_window_left_panel_width, tile_window_height))
                    tile_window_bottom_bar.set_relative_position((0, tile_window_height))
                    tile_window_bottom_bar.set_dimensions((tile_window_width, tile_window_bottom_bar_height))
                    tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
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
                        rect=pygame.Rect((screen_width - tile_window_width - 10, 10), (tile_window_width, tile_window_height + tile_window_bottom_bar_height)),
                        manager=manager,
                        window_display_title="Tile System",
                        object_id="#tile_window"
                    )
                    tile_window_left_panel = pygame_gui.elements.UIPanel(
                        relative_rect=pygame.Rect((0, 0), (tile_window_left_panel_width, tile_window_height)),
                        manager=manager,
                        container=tile_window,
                        object_id="#tile_window_left_panel"
                    )
                    tile_image_width = tile_window_width - tile_window_left_panel_width
                    tile_image_height = tile_window_height
                    tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)
                    tile_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect((tile_window_left_panel_width, 0), (tile_image_width, tile_image_height)),
                        image_surface=tile_image_surface,
                        manager=manager,
                        container=tile_window
                    )
                    sub_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((0, 0), (tile_window_left_panel_width, 50)),
                        text=f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}",
                        manager=manager,
                        container=tile_window_left_panel
                    )
                    tile_window_bottom_bar = pygame_gui.elements.UIPanel(
                        relative_rect=pygame.Rect((0, tile_window_height), (tile_window_width, tile_window_bottom_bar_height)),
                        manager=manager,
                        container=tile_window,
                        object_id="#tile_window_bottom_bar"
                    )
                    add_tile_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((tile_window_button_padding, 5), (tile_window_button_width, tile_window_button_height)),
                        text="Add: OFF",
                        manager=manager,
                        container=tile_window_bottom_bar
                    )
                    reset_zoom_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((tile_window_button_padding * 2 + tile_window_button_width, 5), (tile_window_button_width, tile_window_button_height)),
                        text="Reset View",
                        manager=manager,
                        container=tile_window_bottom_bar
                    )
                    maximize_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((tile_window_button_padding * 3 + tile_window_button_width * 2, 5), (tile_window_button_width, tile_window_button_height)),
                        text="Maximize",
                        manager=manager,
                        container=tile_window_bottom_bar
                    )
                    set_bg_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((tile_window_button_padding * 4 + tile_window_button_width * 3, 5), (tile_window_button_width, tile_window_button_height)),
                        text="Set BG",
                        manager=manager,
                        container=tile_window_bottom_bar
                    )
                    tile_window_visible = True
            elif event.ui_element == sub_button:
                tile_system.sub_grid_visible = not tile_system.sub_grid_visible
                sub_button.set_text(f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}")
            elif event.ui_element == get_back_button:
                save_image_viewing_link_areas()
                image_viewing_mode = False
                if get_back_button is not None:
                    get_back_button.kill()
                    get_back_button = None
            elif event.ui_element == home_button:
                # Launch home_page.py and close main.py
                subprocess.Popen(["python", "home_page.py"])
                pygame.quit()
                sys.exit()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == tile_window:
                tile_window = None
                tile_window_visible = False
                tile_window_maximized = False

        manager.process_events(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if 'image_rect' in locals() and image_rect and image_rect.collidepoint(event.pos):
                x, y = event.pos
                rel_x = (x - image_rect.left) / image_rect.width
                rel_y = (y - image_rect.top) / image_rect.height
                found_area = None
                if image_viewing_mode:
                    image_path = image_viewing_images[image_viewing_index]
                    link_areas = image_viewing_link_areas.get(image_path, [])
                else:
                    current_tile = tile_system.get_current_tile()
                    if current_tile:
                        image_index = tile_system.current_image_index
                        link_areas = current_tile.link_areas.get(image_index, [])
                    else:
                        link_areas = []
                for area in link_areas:
                    rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                    if rel_x0 <= rel_x <= rel_x1 and rel_y0 <= rel_y <= rel_y1:
                        found_area = area
                        break
                if found_area:
                    if assign_link_folder_mode:
                        directory = open_file_explorer()
                        if directory:
                            found_area['link'] = directory
                            bring_window_to_front()
                            if image_viewing_mode:
                                save_image_viewing_link_areas()
                            else:
                                tile_system.save_game_state()
                        assign_link_folder_mode = False
                        assign_link_folder_button.set_text("Assign Link Folder: OFF")
                        drawing_link_area = False
                        link_area_start_pos = None
                        link_area_rect = None
                    elif assign_json_area_mode:
                        json_file = filedialog.askopenfilename(
                            title="Select a JSON file",
                            initialdir=tile_system.save_directory,
                            filetypes=[("JSON files", "*.json")]
                        )
                        if json_file:
                            found_area['json'] = json_file
                            bring_window_to_front()
                            if image_viewing_mode:
                                save_image_viewing_link_areas()
                            else:
                                tile_system.save_game_state()
                        assign_json_area_mode = False
                        assign_json_area_button.set_text("Assign JSON Area: OFF")
                        drawing_link_area = False
                        link_area_start_pos = None
                        link_area_rect = None
                    else:
                        if event.button == 1:
                            if 'json' in found_area and found_area['json']:
                                json_file = found_area['json']
                                tile_system.save_current_state_to_history()
                                tile_system.load_game_state_from_file(json_file)
                                bring_window_to_front()
                                image_viewing_mode = False
                                if get_back_button is not None:
                                    get_back_button.kill()
                                    get_back_button = None
                            elif 'link' in found_area and found_area['link']:
                                link = found_area['link']
                                if link and os.path.isdir(link):
                                    if image_viewing_mode:
                                        save_image_viewing_link_areas()
                                    image_viewing_mode = True
                                    image_viewing_directory = link
                                    image_viewing_images = [os.path.join(link, f) for f in os.listdir(link)
                                                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
                                    image_viewing_images.sort()
                                    image_viewing_index = 0
                                    load_image_viewing_link_areas()
                                    if get_back_button is None:
                                        get_back_button = pygame_gui.elements.UIButton(
                                            relative_rect=pygame.Rect((10, 70), (50, 50)),
                                            text="Back",
                                            manager=manager
                                        )
                                else:
                                    messagebox.showwarning("Folder Link", "No valid folder link found for this area.")
                                    bring_window_to_front()
                            else:
                                messagebox.showwarning("No Link Assigned", "No link or JSON assigned to this area.")
                                bring_window_to_front()

    if confirmation_button and pygame.time.get_ticks() > confirmation_end_time:
        confirmation_button.set_text(original_button_texts[confirmation_button])
        confirmation_button = None
        print("Button confirmation hidden")

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
        if tile_system.sub_grid_visible:
            for vector in tile_system.vector_lines:
                if vector.is_complete:
                    start_x, start_y = vector.start_tile.get_subgrid_square_center(
                        vector.start_subgrid_pos[0], vector.start_subgrid_pos[1], offset_x, offset_y, zoom_factor)
                    end_x, end_y = vector.end_tile.get_subgrid_square_center(
                        vector.end_subgrid_pos[0], vector.end_subgrid_pos[1], offset_x, offset_y, zoom_factor)
                    pygame.draw.line(tile_image.image, (0, 255, 0), (start_x, start_y), (end_x, end_y), 2)

            if vector_drawing and current_vector_line:
                start_x, start_y = current_vector_line.start_tile.get_subgrid_square_center(
                    current_vector_line.start_subgrid_pos[0], current_vector_line.start_subgrid_pos[1], offset_x, offset_y, zoom_factor)
                end_x, end_y = local_mouse_pos
                pygame.draw.line(tile_image.image, (0, 255, 0), (start_x, start_y), (end_x, end_y), 2)

        tile_image_surface.blit(tile_image.image, (0, 0))

    manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
