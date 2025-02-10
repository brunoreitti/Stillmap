import pygame
import pygame_gui
import ctypes
import sys
import os
import json
import cv2
import numpy as np
import subprocess
from tkinter import Tk, filedialog, messagebox
from pdf2image import convert_from_path
import cairosvg

# "map module" like tile_system_view.py
import tile_system_view as tile_system

pygame.init()
root = Tk()
root.withdraw()

###############################################################################
# CONSTANTS & GLOBALS
###############################################################################
EXTRA_TITLEBAR_HEIGHT = 30  # Extra height to account for the UIWindow title bar
tile_window_bottom_bar_height = 40

# Global variable to control whether panning (the “Pan Effect”) is enabled.
pan_effect_enabled = True

# Global references for our Settings popup and its toggle button.
settings_popup = None
pan_effect_toggle = None

# --- Transition effect globals ---
transition_active = False
transition_start_time = 0.0
transition_duration = 0.25  # in seconds, set 2x faster than before
transition_direction = 0   # 1 means new image comes from right; -1 means new image comes from left
transition_old_index = None
transition_new_index = None
transition_old_surface = None
transition_new_surface = None

###############################################################################
# --- BELT MODE GLOBALS ---
###############################################################################
belt_mode_active = False        # True when the main image area is in free (belt) mode.
belt_dragging = False           # True while the mouse is held down.
belt_drag_start_x = None        # The last mouse x-position (used for computing delta x).
belt_offset = None              # Horizontal offset into the belt (in pixels).
belt_surfaces = []              # List of tuples: (pygame.Surface, width) for each preloaded image.

###############################################################################
# If a JSON map path is passed as an argument, store it
###############################################################################
linked_json_to_load = None
if len(sys.argv) > 1:
    linked_json_to_load = sys.argv[1]
    print(f"[view_page] Received argument => {linked_json_to_load}")
else:
    print("[view_page] No argument passed => no immediate load")

###############################################################################
# HELPER FUNCTIONS (PDF/SVG or normal images)
###############################################################################
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

def load_image(filepath):
    path = os.path.normpath(filepath)
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    if ext == '.pdf':
        return load_pdf_page(path)
    elif ext == '.svg':
        return load_svg_image(path)
    else:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[DEBUG] cv2.imread returned None for: {path}")
        return img

def cv2_to_pygame(img_cv2):
    if img_cv2 is None:
        return None
    if len(img_cv2.shape) == 3:
        if img_cv2.shape[2] == 4:
            img_rgba = cv2.cvtColor(img_cv2, cv2.COLOR_BGRA2RGBA)
            return pygame.image.frombuffer(img_rgba.tobytes(), img_rgba.shape[1::-1], 'RGBA')
        else:
            img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
            return pygame.image.frombuffer(img_rgb.tobytes(), img_rgb.shape[1::-1], 'RGB')
    return None

###############################################################################
# PYGAME Setup
###############################################################################
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("MAPPIC Viewer")

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

###############################################################################
# Wire up tile_system_view
###############################################################################
tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame
tile_system.SQUARE_SIZE = 36
tile_system.initialize()
# Hide subgrid drawing and its UI functionality
tile_system.sub_grid_visible = False

###############################################################################
# UI Manager
###############################################################################
manager = pygame_gui.UIManager((screen_width, screen_height))

bottom_bar_height = 60
bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

home_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 10), (100, 40)),
    text="Home",
    manager=manager,
    container=bottom_bar_panel
)

load_game_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((120, 10), (120, 40)),
    text="Load Game",
    manager=manager,
    container=bottom_bar_panel
)

# Create the Settings button in the bottom bar.
settings_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((250, 10), (100, 40)),
    text="Settings",
    manager=manager,
    container=bottom_bar_panel
)

###############################################################################
# Function to create the Settings popup window
###############################################################################
def create_settings_popup():
    global settings_popup, pan_effect_toggle, screen_width, screen_height, pan_effect_enabled
    settings_popup = pygame_gui.elements.UIWindow(
        rect=pygame.Rect((screen_width // 2 - 150, screen_height // 2 - 75), (300, 150)),
        manager=manager,
        window_display_title="Settings",
        object_id="#settings_popup"
    )
    # Instead of a UICheckbox, we create a toggle button.
    pan_effect_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((20, 40), (260, 30)),
        text="Pan Effect: On" if pan_effect_enabled else "Pan Effect: Off",
        manager=manager,
        container=settings_popup
    )

###############################################################################
# Global references for tile window and its buttons
###############################################################################
tile_window = None
tile_image = None
tile_window_bottom_bar = None
reset_view_button = None
maximize_button = None

tile_window_width = tile_system.SQUARE_SIZE * 9
tile_window_height = tile_system.SQUARE_SIZE * 9
# tile_window_bottom_bar_height is defined above (set to 40 for a more compact layout)

###############################################################################
# Create Map Window Function (Modified for Space Saving Buttons)
###############################################################################
def create_map_window():
    """
    Create the map tile window (and its bottom bar) at the initial position/size.
    Store references globally so the event loop can check them.
    """
    global tile_window, tile_image
    global tile_window_bottom_bar, reset_view_button, maximize_button

    # Increase height to account for the title bar.
    tile_window_rect = pygame.Rect(
        (screen_width - tile_window_width - 10, 10),
        (tile_window_width, tile_window_height + tile_window_bottom_bar_height + EXTRA_TITLEBAR_HEIGHT)
    )

    tile_window = pygame_gui.elements.UIWindow(
        rect=tile_window_rect,
        manager=manager,
        window_display_title="Tile System",
        object_id="#tile_window"
    )

    # Use the window's content container for proper positioning.
    window_container = tile_window.get_container()
    container_size = window_container.get_size()

    # The tile image fills the area above the bottom bar.
    tile_image_height = container_size[1] - tile_window_bottom_bar_height
    tile_image_surf = pygame.Surface((tile_window_width, tile_image_height), pygame.SRCALPHA)
    tile_image = pygame_gui.elements.UIImage(
        relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_image_height)),
        image_surface=tile_image_surf,
        manager=manager,
        container=window_container
    )

    # The bottom bar panel is positioned at the bottom of the container.
    tile_window_bottom_bar = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect((0, tile_image_height), (tile_window_width, tile_window_bottom_bar_height)),
        manager=manager,
        container=window_container,
        object_id="#tile_window_bottom_bar"
    )

    # Use smaller padding for more compact buttons
    tile_window_button_padding = 5
    # Compute button width so that there are 3 gaps of padding (left, middle, right)
    tile_window_button_width = (tile_window_width - (3 * tile_window_button_padding)) // 2
    # Button height: subtract top and bottom padding from the bottom bar height
    tile_window_button_height = tile_window_bottom_bar_height - (2 * tile_window_button_padding)

    reset_view_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            (tile_window_button_padding, tile_window_button_padding),
            (tile_window_button_width, tile_window_button_height)
        ),
        text="Reset View",
        manager=manager,
        container=tile_window_bottom_bar
    )

    maximize_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(
            (2 * tile_window_button_padding + tile_window_button_width, tile_window_button_padding),
            (tile_window_button_width, tile_window_button_height)
        ),
        text="Maximize",
        manager=manager,
        container=tile_window_bottom_bar
    )

# Create the map window initially
create_map_window()
tile_window_maximized = False
tile_window_visible = True

###############################################################################
# MAP VIEW / ZOOM / PANNING
###############################################################################
zoom_factor = 1.0
MIN_ZOOM = 0.5
MAX_ZOOM = 3.0
follow_player = True

def reset_map_view():
    global zoom_factor
    if tile_image is None:
        return

    tile_image_rect = tile_image.get_relative_rect()
    scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
    tile_system.map_offset[0] = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_sq
    tile_system.map_offset[1] = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_sq
    print("[view_page] reset_map_view => map_offset updated for player pos")

def adjust_zoom(old_zoom, new_zoom):
    if follow_player or tile_image is None:
        return
    tile_image_rect = tile_image.get_relative_rect()
    center_x = tile_image_rect.width / 2
    center_y = tile_image_rect.height / 2
    map_x_before = (center_x - tile_system.map_offset[0]) / (tile_system.SQUARE_SIZE * old_zoom)
    map_y_before = (center_y - tile_system.map_offset[1]) / (tile_system.SQUARE_SIZE * old_zoom)
    tile_system.map_offset[0] = center_x - map_x_before * tile_system.SQUARE_SIZE * new_zoom
    tile_system.map_offset[1] = center_y - map_y_before * tile_system.SQUARE_SIZE * new_zoom

###############################################################################
# Function to start the slide transition effect when changing images
###############################################################################
def start_image_transition(key):
    global transition_active, transition_start_time, transition_direction
    global transition_old_index, transition_new_index, transition_old_surface, transition_new_surface

    current_tile = tile_system.get_current_tile()
    if current_tile is None or not current_tile.image_filenames:
        return

    # Store the current image index before rotation
    transition_old_index = tile_system.current_image_index

    # Rotate player (which updates current_image_index) and set the transition direction.
    if key == pygame.K_RIGHT:
        tile_system.save_current_state_to_history()
        tile_system.rotate_player(pygame.K_RIGHT)
        transition_direction = 1  # new image comes from right
    elif key == pygame.K_LEFT:
        tile_system.save_current_state_to_history()
        tile_system.rotate_player(pygame.K_LEFT)
        transition_direction = -1  # new image comes from left

    transition_new_index = tile_system.current_image_index

    # Get both old and new images (as cv2 images)
    old_cv2 = current_tile.get_current_image(transition_old_index)
    new_cv2 = current_tile.get_current_image(transition_new_index)
    if old_cv2 is None or new_cv2 is None:
        return

    # Define the main area rectangle (where the image is drawn)
    main_area_rect = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)

    # Scale the old image to fit the main area.
    ih_old, iw_old = old_cv2.shape[:2]
    scale_factor_old = min(main_area_rect.width / iw_old, main_area_rect.height / ih_old)
    new_w_old = int(iw_old * scale_factor_old)
    new_h_old = int(ih_old * scale_factor_old)
    scaled_old_cv2 = cv2.resize(old_cv2, (new_w_old, new_h_old), interpolation=cv2.INTER_AREA)
    transition_old_surface = cv2_to_pygame(scaled_old_cv2)

    # Scale the new image to fit the main area.
    ih_new, iw_new = new_cv2.shape[:2]
    scale_factor_new = min(main_area_rect.width / iw_new, main_area_rect.height / ih_new)
    new_w_new = int(iw_new * scale_factor_new)
    new_h_new = int(ih_new * scale_factor_new)
    scaled_new_cv2 = cv2.resize(new_cv2, (new_w_new, new_h_new), interpolation=cv2.INTER_AREA)
    transition_new_surface = cv2_to_pygame(scaled_new_cv2)

    transition_start_time = pygame.time.get_ticks() / 1000.0  # current time in seconds
    transition_active = True

###############################################################################
# RE-LAUNCH BUTTON
###############################################################################
restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",
    manager=manager,
    object_id="#restore_tile_window_button"
)

###############################################################################
# AUTO-LOAD ANY JSON
###############################################################################
if linked_json_to_load and os.path.isfile(linked_json_to_load):
    print(f"[view_page] Auto-loading map => {linked_json_to_load}")
    tile_system.save_current_state_to_history()
    tile_system.load_game_state_from_file(linked_json_to_load)
    zoom_factor = 1.0
    reset_map_view()

###############################################################################
# MAIN LOOP
###############################################################################
running = True
clock = pygame.time.Clock()

last_click_time = 0
DOUBLE_CLICK_TIME = 500
last_click_pos = None
panning = False
pan_start_local = None

while running:
    time_delta = clock.tick(60) / 1000.0
    screen.fill(MAIN_BG_COLOR)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            manager.set_window_resolution((screen_width, screen_height))

            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))

            if tile_window and tile_window_maximized:
                tile_window.set_relative_position((10, 10))
                tile_window.set_dimensions((screen_width - 20, screen_height - bottom_bar_height - 20))
                if tile_image is not None:
                    container = tile_window.get_container()
                    container_size = container.get_size()
                    new_w = container_size[0]
                    new_h = container_size[1] - tile_window_bottom_bar_height
                    tile_image.set_dimensions((new_w, new_h))
                    tile_image_surf = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surf)
                    tile_window_bottom_bar.set_relative_position((0, new_w))
                    tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))

        elif event.type == pygame.KEYDOWN:
            # If belt mode is active and the user presses left/right arrow, exit belt mode.
            if belt_mode_active and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                belt_mode_active = False
                belt_dragging = False
                belt_offset = None
                belt_surfaces = []
                if pan_effect_enabled:
                    start_image_transition(event.key)
                else:
                    if event.key == pygame.K_LEFT:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_LEFT)
                    elif event.key == pygame.K_RIGHT:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_RIGHT)
            else:
                # Process other key events.
                if event.key == pygame.K_LEFT:
                    if pan_effect_enabled:
                        start_image_transition(event.key)
                    else:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_LEFT)
                elif event.key == pygame.K_RIGHT:
                    if pan_effect_enabled:
                        start_image_transition(event.key)
                    else:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_RIGHT)
                elif event.key == pygame.K_UP:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=True)
                    if follow_player:
                        reset_map_view()
                elif event.key == pygame.K_DOWN:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=False)
                    if follow_player:
                        reset_map_view()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # zoom in
                old_z = zoom_factor
                zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
                adjust_zoom(old_z, zoom_factor)
            elif event.button == 5:  # zoom out
                old_z = zoom_factor
                zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
                adjust_zoom(old_z, zoom_factor)
            elif event.button == 1:  # left-click
                # Define the main image area.
                main_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                # First, check if tile_window is visible and if the click is within its bounds.
                if tile_window and tile_window.visible and tile_image is not None:
                    tw_abs_rect = tile_window.get_abs_rect()
                    if tw_abs_rect.collidepoint(event.pos):
                        ti_rel_rect = tile_image.get_relative_rect()
                        local_x = event.pos[0] - tw_abs_rect.left - ti_rel_rect.left
                        local_y = event.pos[1] - tw_abs_rect.top - ti_rel_rect.top
                        if 0 <= local_x < ti_rel_rect.width and 0 <= local_y < ti_rel_rect.height:
                            # Process tile window click (e.g. double-click and tile selection)
                            current_time = pygame.time.get_ticks()
                            if (last_click_pos and abs(event.pos[0] - last_click_pos[0]) < 10 and
                                abs(event.pos[1] - last_click_pos[1]) < 10 and
                                (current_time - last_click_time < DOUBLE_CLICK_TIME)):
                                
                                scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
                                row = int((local_y - tile_system.map_offset[1]) // scaled_sq)
                                col = int((local_x - tile_system.map_offset[0]) // scaled_sq)
                                tile_system.save_current_state_to_history()
                                tile_system.move_player_to_tile(row, col)
                                last_click_time = 0
                                last_click_pos = None
                                if follow_player:
                                    reset_map_view()
                            else:
                                # Single-click on tile window: select tile and start panning.
                                scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
                                row = int((local_y - tile_system.map_offset[1]) // scaled_sq)
                                col = int((local_x - tile_system.map_offset[0]) // scaled_sq)
                                tile_system.select_tile(row, col)
                                last_click_time = pygame.time.get_ticks()
                                last_click_pos = event.pos
                                panning = True
                                pan_start_local = (local_x, local_y)
                                follow_player = False
                        else:
                            # Click is inside tile window container but outside its image area.
                            if main_area.collidepoint(event.pos):
                                if not belt_mode_active:
                                    belt_mode_active = True
                                    belt_dragging = True
                                    belt_drag_start_x = event.pos[0]
                                    belt_offset = None
                                    belt_surfaces = []
                                else:
                                    belt_dragging = True
                                    belt_drag_start_x = event.pos[0]
                    else:
                        # Click is outside the tile window altogether.
                        if main_area.collidepoint(event.pos):
                            if not belt_mode_active:
                                belt_mode_active = True
                                belt_dragging = True
                                belt_drag_start_x = event.pos[0]
                                belt_offset = None
                                belt_surfaces = []
                            else:
                                belt_dragging = True
                                belt_drag_start_x = event.pos[0]
                else:
                    # No tile window visible; if click is in main area, trigger belt mode.
                    if main_area.collidepoint(event.pos):
                        if not belt_mode_active:
                            belt_mode_active = True
                            belt_dragging = True
                            belt_drag_start_x = event.pos[0]
                            belt_offset = None
                            belt_surfaces = []
                        else:
                            belt_dragging = True
                            belt_drag_start_x = event.pos[0]

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                panning = False
                pan_start_local = None
                if belt_mode_active:
                    belt_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            # Existing tile window panning.
            if panning and pan_effect_enabled and tile_window and tile_window.visible and tile_image is not None:
                tw_abs_rect = tile_window.get_abs_rect()
                ti_rel_rect = tile_image.get_relative_rect()
                current_local_x = event.pos[0] - tw_abs_rect.left - ti_rel_rect.left
                current_local_y = event.pos[1] - tw_abs_rect.top - ti_rel_rect.top
                if pan_start_local is not None:
                    dx = current_local_x - pan_start_local[0]
                    dy = current_local_y - pan_start_local[1]
                    tile_system.map_offset[0] += dx
                    tile_system.map_offset[1] += dy
                    pan_start_local = (current_local_x, current_local_y)
            # Belt mode dragging update.
            if belt_mode_active and belt_dragging:
                dx = event.pos[0] - belt_drag_start_x
                if belt_offset is None:
                    belt_offset = 0
                belt_offset -= dx  # Adjust offset so the belt moves with the drag.
                belt_drag_start_x = event.pos[0]

        # Process pygame_gui events.
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == pan_effect_toggle:
                pan_effect_enabled = not pan_effect_enabled
                pan_effect_toggle.set_text("Pan Effect: On" if pan_effect_enabled else "Pan Effect: Off")
            elif event.ui_element == home_button:
                subprocess.Popen(["python", "home_page.py"])
                pygame.quit()
                sys.exit()
            elif event.ui_element == load_game_button:
                tile_system.save_current_state_to_history()
                tile_system.load_game_state()
                zoom_factor = 1.0
                follow_player = True
                reset_map_view()
            elif event.ui_element == settings_button:
                if settings_popup is None:
                    create_settings_popup()
            elif event.ui_element == reset_view_button:
                zoom_factor = 1.0
                follow_player = True
                reset_map_view()
            elif event.ui_element == maximize_button:
                tile_window_maximized = not tile_window_maximized
                if tile_window is not None:
                    if tile_window_maximized:
                        maximize_button.set_text("Restore")
                        tile_window.set_relative_position((10, 10))
                        tile_window.set_dimensions((screen_width - 20, screen_height - bottom_bar_height - 20))
                        container = tile_window.get_container()
                        container_size = container.get_size()
                        new_w = container_size[0]
                        new_h = container_size[1] - tile_window_bottom_bar_height
                        tile_image.set_dimensions((new_w, new_h))
                        tile_image_surf = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                        tile_image.set_image(tile_image_surf)
                        tile_window_bottom_bar.set_relative_position((0, new_w))
                        tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))
                    else:
                        maximize_button.set_text("Maximize")
                        tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                        tile_window.set_dimensions((tile_window_width, tile_window_height + tile_window_bottom_bar_height + EXTRA_TITLEBAR_HEIGHT))
                        container = tile_window.get_container()
                        container_size = container.get_size()
                        tile_image_height = container_size[1] - tile_window_bottom_bar_height
                        tile_image.set_dimensions((tile_window_width, tile_image_height))
                        tile_image_surf = pygame.Surface((tile_window_width, tile_image_height), pygame.SRCALPHA)
                        tile_image.set_image(tile_image_surf)
                        tile_window_bottom_bar.set_relative_position((0, tile_image_height))
                        tile_window_bottom_bar.set_dimensions((tile_window_width, tile_window_bottom_bar_height))
            elif event.ui_element == restore_tile_window_button:
                if tile_window is None:
                    create_map_window()
                    tile_window_maximized = False
                else:
                    if tile_window.visible:
                        tile_window.hide()
                    else:
                        tile_window.show()

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if settings_popup and event.ui_element == settings_popup:
                settings_popup = None
                pan_effect_toggle = None
            elif tile_window and event.ui_element == tile_window:
                tile_window.kill()
                tile_window = None
                tile_image = None
                reset_view_button = None
                maximize_button = None
                tile_window_maximized = False

        manager.process_events(event)

    manager.update(time_delta)

    # Define the main area where the current tile’s image is drawn.
    main_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, main_area)

    # (A) DRAW MAP if tile_window is active.
    if tile_window and tile_window.visible and tile_image is not None:
        tile_image.image.fill((0, 0, 0, 0))
        tile_system.draw_board(
            (0, 0),
            tile_system.map_offset[0],
            tile_system.map_offset[1],
            tile_image.image,
            tile_image.get_relative_rect(),
            zoom_factor
        )
        tile_system.draw_player(
            tile_system.map_offset[0],
            tile_system.map_offset[1],
            tile_image.image,
            zoom_factor
        )
        tile_image_surface = tile_image.image
        tile_image_surface.blit(tile_image.image, (0, 0))

    # (B) DRAW CURRENT TILE’S IMAGE in the main area.
    current_tile = tile_system.get_current_tile()
    if current_tile and current_tile.image_filenames:
        if belt_mode_active:
            # --- BELT MODE DRAWING ---
            if not belt_surfaces:
                belt_surfaces = []
                for i in range(len(current_tile.image_filenames)):
                    cv2_img = current_tile.get_current_image(i)
                    if cv2_img is not None:
                        ih, iw = cv2_img.shape[:2]
                        # Scale each image so that its height matches main_area.height.
                        scale_factor = main_area.height / ih
                        new_w = int(iw * scale_factor)
                        new_h = main_area.height
                        scaled_cv2 = cv2.resize(cv2_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        surf = cv2_to_pygame(scaled_cv2)
                        belt_surfaces.append((surf, new_w))
            total_width = sum(width for (_, width) in belt_surfaces)
            if belt_offset is None:
                current_idx = tile_system.current_image_index % len(belt_surfaces)
                cum_width = sum(belt_surfaces[i][1] for i in range(current_idx))
                belt_offset = cum_width + belt_surfaces[current_idx][1] / 2 - main_area.width / 2

            # --- UPDATE PLAYER ORIENTATION BASED ON MOST VISIBLE IMAGE ---
            # We'll calculate for each image (in one cycle) what fraction is visible.
            if total_width > 0 and belt_surfaces:
                normalized_offset = belt_offset % total_width
                # Prepare cumulative positions for each image in one cycle.
                cumulative = []
                pos = 0
                for (surf, w) in belt_surfaces:
                    cumulative.append(pos)
                    pos += w
                best_index = 0
                best_fraction = -1.0
                # For each image, check its canonical placement and also the wrapped placement.
                for i, (surf, w) in enumerate(belt_surfaces):
                    start_i = cumulative[i] - normalized_offset
                    # Two candidate placements: one at start_i, and one wrapped by total_width.
                    candidates = [start_i, start_i + total_width]
                    max_visible = 0
                    for cand in candidates:
                        # The image occupies [cand, cand + w] in main_area coordinates (where main_area x: 0..main_area.width)
                        visible_start = max(cand, 0)
                        visible_end = min(cand + w, main_area.width)
                        visible = max(0, visible_end - visible_start)
                        if visible > max_visible:
                            max_visible = visible
                    fraction = max_visible / w
                    if fraction > best_fraction:
                        best_fraction = fraction
                        best_index = i
                tile_system.player_direction = best_index
                tile_system.current_image_index = best_index

            # Draw the belt repeatedly so that it covers the entire main_area.
            x = - (belt_offset % total_width)
            if x > 0:
                x -= total_width
            while x < main_area.width:
                for surf, w in belt_surfaces:
                    pos_x = main_area.left + x
                    screen.blit(surf, (pos_x, main_area.top))
                    x += w
                    if x >= main_area.width:
                        break
        else:
            if transition_active:
                current_time = pygame.time.get_ticks() / 1000.0
                progress = (current_time - transition_start_time) / transition_duration
                if progress >= 1.0:
                    transition_active = False
                    final_surface = transition_new_surface
                    if final_surface is not None:
                        rect = final_surface.get_rect(center=main_area.center)
                        screen.blit(final_surface, rect.topleft)
                else:
                    M_x, M_y = main_area.center
                    W = main_area.width
                    if transition_direction == 1:
                        old_center_x = M_x - progress * W
                        new_center_x = M_x + W - progress * W
                    else:
                        old_center_x = M_x + progress * W
                        new_center_x = M_x - W + progress * W
                    if transition_old_surface is not None and transition_new_surface is not None:
                        old_rect = transition_old_surface.get_rect(center=(old_center_x, M_y))
                        new_rect = transition_new_surface.get_rect(center=(new_center_x, M_y))
                        screen.blit(transition_old_surface, old_rect.topleft)
                        screen.blit(transition_new_surface, new_rect.topleft)
            else:
                img_cv2 = current_tile.get_current_image(tile_system.current_image_index)
                if img_cv2 is not None:
                    ih, iw = img_cv2.shape[:2]
                    sf = min(main_area.width / iw, main_area.height / ih)
                    if sf <= 0:
                        sf = 1
                    new_w = int(iw * sf)
                    new_h = int(ih * sf)
                    scaled_cv2 = cv2.resize(img_cv2, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    scaled_surf = cv2_to_pygame(scaled_cv2)
                    if scaled_surf:
                        r = scaled_surf.get_rect(center=main_area.center)
                        screen.blit(scaled_surf, r.topleft)

    manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
