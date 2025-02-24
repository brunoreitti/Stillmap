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

import tile_system_view as tile_system

pygame.init()
pygame.mixer.init()

# Initialize joystick module
pygame.joystick.init()

sound_effects_enabled = True
pan_sound = pygame.mixer.Sound("pan.mp3")
step_sound = pygame.mixer.Sound("step.mp3")
sound_effects_toggle = None

root = Tk()
root.withdraw()

###############################################################################
# CONSTANTS & GLOBALS
###############################################################################
EXTRA_TITLEBAR_HEIGHT = 30
tile_window_bottom_bar_height = 40

pan_effect_enabled = False
belt_fade_enabled = True
gamepad_enabled = True  # Default to On

settings_popup = None
pan_effect_toggle = None
belt_fade_toggle = None
gamepad_toggle = None

transition_active = False
transition_start_time = 0.0
transition_duration = 0.25
transition_direction = 0
transition_old_index = None
transition_new_index = None
transition_old_surface = None
transition_new_surface = None

belt_mode_active = False
belt_dragging = False
belt_drag_start_x = None
belt_offset = None
belt_surfaces = []
belt_surfaces_faded = []
OVERLAP_FRACTION = 0.10

last_tile_coord = None
belt_view_fraction = None

linked_json_to_load = None
if len(sys.argv) > 1:
    linked_json_to_load = sys.argv[1]
    print(f"[view_page] Received argument => {linked_json_to_load}")
else:
    print("[view_page] No argument passed => no immediate load")

# Gamepad setup
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"[view_page] Gamepad detected: {joystick.get_name()}")
else:
    print("[view_page] No gamepad detected")

###############################################################################
# HELPER FUNCTIONS
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

def get_faded_surface(surf, overlap_fraction):
    faded = surf.copy().convert_alpha()
    w, h = faded.get_size()
    overlap = int(w * overlap_fraction)
    for x in range(overlap):
        alpha_factor = x / overlap
        for y in range(h):
            color = faded.get_at((x, y))
            new_alpha = int(color.a * alpha_factor)
            color.a = new_alpha
            faded.set_at((x, y), color)
    for x in range(w - overlap, w):
        alpha_factor = (w - x) / overlap
        for y in range(h):
            color = faded.get_at((x, y))
            new_alpha = int(color.a * alpha_factor)
            color.a = new_alpha
            faded.set_at((x, y), color)
    return faded

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

tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame
tile_system.SQUARE_SIZE = 36
tile_system.initialize()
tile_system.sub_grid_visible = False

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
settings_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((250, 10), (100, 40)),
    text="Settings",
    manager=manager,
    container=bottom_bar_panel
)

def create_settings_popup():
    global settings_popup, pan_effect_toggle, belt_fade_toggle, sound_effects_toggle, gamepad_toggle
    settings_popup = pygame_gui.elements.UIWindow(
        rect=pygame.Rect((screen_width // 2 - 150, screen_height // 2 - 115), (300, 230)),
        manager=manager,
        window_display_title="Settings",
        object_id="#settings_popup"
    )
    pan_effect_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((20, 20), (260, 30)),
        text="Pan Effect: On" if pan_effect_enabled else "Pan Effect: Off",
        manager=manager,
        container=settings_popup
    )
    belt_fade_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((20, 70), (260, 30)),
        text="Belt Fade: On" if belt_fade_enabled else "Belt Fade: Off",
        manager=manager,
        container=settings_popup
    )
    sound_effects_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((20, 120), (260, 30)),
        text="Sound Effects: On" if sound_effects_enabled else "Sound Effects: Off",
        manager=manager,
        container=settings_popup
    )
    gamepad_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((20, 170), (260, 30)),
        text="Gamepad: On" if gamepad_enabled else "Gamepad: Off",
        manager=manager,
        container=settings_popup
    )

tile_window = None
tile_image = None
tile_window_bottom_bar = None
reset_view_button = None
maximize_button = None
tile_window_width = tile_system.SQUARE_SIZE * 9
tile_window_height = tile_system.SQUARE_SIZE * 9

def create_map_window():
    global tile_window, tile_image, tile_window_bottom_bar, reset_view_button, maximize_button
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
    window_container = tile_window.get_container()
    container_size = window_container.get_size()
    tile_image_height = container_size[1] - tile_window_bottom_bar_height
    tile_image_surf = pygame.Surface((tile_window_width, tile_image_height), pygame.SRCALPHA)
    tile_image = pygame_gui.elements.UIImage(
        relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_image_height)),
        image_surface=tile_image_surf,
        manager=manager,
        container=window_container
    )
    tile_window_bottom_bar = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect((0, tile_image_height), (tile_window_width, tile_window_bottom_bar_height)),
        manager=manager,
        container=window_container,
        object_id="#tile_window_bottom_bar"
    )
    tile_window_button_padding = 5
    tile_window_button_width = (tile_window_width - (3 * tile_window_button_padding)) // 2
    tile_window_button_height = tile_window_bottom_bar_height - (2 * tile_window_button_padding)
    reset_view_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((tile_window_button_padding, tile_window_button_padding),
                                  (tile_window_button_width, tile_window_button_height)),
        text="Reset View",
        manager=manager,
        container=tile_window_bottom_bar
    )
    maximize_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((2 * tile_window_button_padding + tile_window_button_width, tile_window_button_padding),
                                  (tile_window_button_width, tile_window_button_height)),
        text="Maximize",
        manager=manager,
        container=tile_window_bottom_bar
    )

create_map_window()
tile_window_maximized = False
tile_window_visible = True

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

def start_image_transition(key):
    global transition_active, transition_start_time, transition_direction
    global transition_old_index, transition_new_index, transition_old_surface, transition_new_surface
    current_tile = tile_system.get_current_tile()
    if current_tile is None or not current_tile.image_filenames:
        return
    transition_old_index = tile_system.current_image_index
    if key == pygame.K_RIGHT:
        tile_system.save_current_state_to_history()
        tile_system.rotate_player(pygame.K_RIGHT)
        transition_direction = 1
    elif key == pygame.K_LEFT:
        tile_system.save_current_state_to_history()
        tile_system.rotate_player(pygame.K_LEFT)
        transition_direction = -1
    transition_new_index = tile_system.current_image_index
    old_cv2 = current_tile.get_current_image(transition_old_index)
    new_cv2 = current_tile.get_current_image(transition_new_index)
    if old_cv2 is None or new_cv2 is None:
        return
    main_area_rect = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    ih_old, iw_old = old_cv2.shape[:2]
    scale_factor_old = min(main_area_rect.width / iw_old, main_area_rect.height / ih_old)
    new_w_old = int(iw_old * scale_factor_old)
    new_h_old = int(ih_old * scale_factor_old)
    scaled_old_cv2 = cv2.resize(old_cv2, (new_w_old, new_h_old), interpolation=cv2.INTER_AREA)
    transition_old_surface = cv2_to_pygame(scaled_old_cv2)
    ih_new, iw_new = new_cv2.shape[:2]
    scale_factor_new = min(main_area_rect.width / iw_new, main_area_rect.height / ih_new)
    new_w_new = int(iw_new * scale_factor_new)
    new_h_new = int(ih_new * scale_factor_new)
    scaled_new_cv2 = cv2.resize(new_cv2, (new_w_new, new_h_new), interpolation=cv2.INTER_AREA)
    transition_new_surface = cv2_to_pygame(scaled_new_cv2)
    transition_start_time = pygame.time.get_ticks() / 1000.0
    transition_active = True

restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",
    manager=manager,
    object_id="#restore_tile_window_button"
)

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
pan_start_pos = None
click_count = 0

# Track gamepad states
dpad_states = {pygame.K_UP: False, pygame.K_DOWN: False}
stick_states = {pygame.K_LEFT: False, pygame.K_RIGHT: False}
left_stick_states = {"up": False, "down": False, "left": False, "right": False}
STICK_THRESHOLD = 0.5

while running:
    time_delta = clock.tick(60) / 1000.0
    screen.fill(MAIN_BG_COLOR)
    mouse_pos = pygame.mouse.get_pos()

    # Handle gamepad input if enabled
    if gamepad_enabled and joystick:
        for event in pygame.event.get():
            if event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = joystick.get_hat(0)
                new_dpad_states = {
                    pygame.K_UP: hat_y == 1,
                    pygame.K_DOWN: hat_y == -1
                }
                for key, new_state in new_dpad_states.items():
                    if new_state and not dpad_states[key]:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
                    dpad_states[key] = new_state
            elif event.type == pygame.JOYAXISMOTION:
                # Right stick (panning)
                if event.axis == 2:  # Right stick X-axis
                    axis_value = event.value
                    new_stick_states = {
                        pygame.K_LEFT: axis_value < -STICK_THRESHOLD,
                        pygame.K_RIGHT: axis_value > STICK_THRESHOLD
                    }
                    for key, new_state in new_stick_states.items():
                        if new_state and not stick_states[key]:
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
                        stick_states[key] = new_state
                # Left stick (movement)
                elif event.axis in (0, 1):  # Left stick X (0) and Y (1)
                    stick_x = joystick.get_axis(0)
                    stick_y = joystick.get_axis(1)
                    # Define movement directions relative to player_direction
                    direction = tile_system.player_direction % 8
                    moves = {
                        0: {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)},  # Up
                        1: {"up": (-1, 1), "down": (1, -1), "left": (-1, -1), "right": (1, 1)},  # Up-Right
                        2: {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)},  # Right
                        3: {"up": (1, 1), "down": (-1, -1), "left": (-1, 1), "right": (1, -1)},  # Down-Right
                        4: {"up": (1, 0), "down": (-1, 0), "left": (0, 1), "right": (0, -1)},  # Down
                        5: {"up": (1, -1), "down": (-1, 1), "left": (1, 1), "right": (-1, -1)},  # Down-Left
                        6: {"up": (0, -1), "down": (0, 1), "left": (1, 0), "right": (-1, 0)},  # Left
                        7: {"up": (-1, -1), "down": (1, 1), "left": (1, -1), "right": (-1, 1)}  # Up-Left
                    }
                    new_left_stick = {
                        "up": stick_y < -STICK_THRESHOLD,
                        "down": stick_y > STICK_THRESHOLD,
                        "left": stick_x < -STICK_THRESHOLD,
                        "right": stick_x > STICK_THRESHOLD
                    }
                    for dir_key, new_state in new_left_stick.items():
                        if new_state and not left_stick_states[dir_key]:
                            d_row, d_col = moves[direction][dir_key]
                            new_pos = [tile_system.player_pos[0] + d_row, tile_system.player_pos[1] + d_col]
                            tile = tile_system.get_tile(new_pos[0], new_pos[1])
                            if tile and tile.active:
                                tile_system.save_current_state_to_history()
                                tile_system.player_pos = new_pos
                                if tile.image_filenames:
                                    tile_system.current_image_index = tile_system.player_direction % len(tile.image_filenames)
                                else:
                                    tile_system.current_image_index = 0
                                if follow_player:
                                    reset_map_view()
                                if sound_effects_enabled:
                                    step_sound.play()
                                print(f"[view_page] Moved to tile {new_pos} via Left Stick {dir_key}")
                        left_stick_states[dir_key] = new_state
            else:
                pygame.event.post(event)
    else:
        events = pygame.event.get()
        for event in events:
            pygame.event.post(event)

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
                    tile_window_bottom_bar.set_relative_position((0, new_h))
                    tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))
        elif event.type == pygame.KEYDOWN:
            if belt_mode_active and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                belt_mode_active = False
                belt_dragging = False
                belt_offset = None
                belt_surfaces = []
                belt_surfaces_faded = []
                if pan_effect_enabled:
                    start_image_transition(event.key)
                    if sound_effects_enabled:
                        pan_sound.play()
                else:
                    if event.key == pygame.K_LEFT:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_LEFT)
                    elif event.key == pygame.K_RIGHT:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_RIGHT)
                    if sound_effects_enabled:
                        pan_sound.play()
            else:
                if event.key == pygame.K_LEFT:
                    if pan_effect_enabled:
                        start_image_transition(event.key)
                        if sound_effects_enabled:
                            pan_sound.play()
                    else:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_LEFT)
                        if sound_effects_enabled:
                            pan_sound.play()
                elif event.key == pygame.K_RIGHT:
                    if pan_effect_enabled:
                        start_image_transition(event.key)
                        if sound_effects_enabled:
                            pan_sound.play()
                    else:
                        tile_system.save_current_state_to_history()
                        tile_system.rotate_player(pygame.K_RIGHT)
                        if sound_effects_enabled:
                            pan_sound.play()
                elif event.key == pygame.K_UP:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=True)
                    if follow_player:
                        reset_map_view()
                    if sound_effects_enabled:
                        step_sound.play()
                elif event.key == pygame.K_DOWN:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=False)
                    if follow_player:
                        reset_map_view()
                    if sound_effects_enabled:
                        step_sound.play()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and settings_popup is not None and settings_popup.visible and settings_popup.get_abs_rect().collidepoint(event.pos):
                pass
            else:
                tile_window_active = tile_window and tile_window.visible and tile_image is not None
                tw_abs_rect = tile_window.get_abs_rect() if tile_window_active else None
                
                if event.button == 4:
                    old_z = zoom_factor
                    zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
                    adjust_zoom(old_z, zoom_factor)
                elif event.button == 5:
                    old_z = zoom_factor
                    zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
                    adjust_zoom(old_z, zoom_factor)
                elif event.button == 1:
                    main_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    
                    if tile_window_active and tw_abs_rect.collidepoint(event.pos):
                        ti_rel_rect = tile_image.get_relative_rect()
                        local_x = event.pos[0] - tw_abs_rect.left - ti_rel_rect.left
                        local_y = event.pos[1] - tw_abs_rect.top - ti_rel_rect.top - EXTRA_TITLEBAR_HEIGHT
                        if 0 <= local_x < ti_rel_rect.width and 0 <= local_y < ti_rel_rect.height:
                            scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
                            col = int((local_x - tile_system.map_offset[0]) / scaled_sq)
                            row = int((local_y - tile_system.map_offset[1]) / scaled_sq)
                            tile = tile_system.get_tile(row, col)
                            
                            current_time = pygame.time.get_ticks()
                            click_count += 1
                            
                            if click_count == 1:
                                if tile and tile.active:
                                    current_direction = tile_system.player_direction
                                    tile_system.save_current_state_to_history()
                                    tile_system.player_pos = [row, col]
                                    tile_system.player_direction = current_direction
                                    if tile.image_filenames:
                                        tile_system.current_image_index = current_direction % len(tile.image_filenames)
                                    else:
                                        tile_system.current_image_index = 0
                                    if follow_player:
                                        reset_map_view()
                                    print(f"[view_page] Jumped to tile ({row}, {col}) with direction {current_direction}")
                                else:
                                    print(f"[view_page] No active tile at ({row}, {col}) for jump")
                                last_click_time = current_time
                                last_click_pos = event.pos
                                panning = True
                                pan_start_pos = event.pos
                                follow_player = False
                            elif click_count == 2 and (current_time - last_click_time) < DOUBLE_CLICK_TIME and \
                                 abs(event.pos[0] - last_click_pos[0]) < 10 and abs(event.pos[1] - last_click_pos[1]) < 10:
                                if tile and tile.active:
                                    tile_system.save_current_state_to_history()
                                    tile_system.move_player_to_tile(row, col)
                                    if follow_player:
                                        reset_map_view()
                                    print(f"[view_page] Double-click jumped to tile ({row}, {col})")
                                else:
                                    print(f"[view_page] No active tile at ({row}, {col}) for double-click")
                                click_count = 0
                                panning = False
                            else:
                                click_count = 1
                                last_click_time = current_time
                                last_click_pos = event.pos
                                panning = True
                                pan_start_pos = event.pos
                                follow_player = False
                    elif main_area.collidepoint(event.pos):
                        if not belt_mode_active:
                            belt_mode_active = True
                            belt_dragging = True
                            belt_drag_start_x = event.pos[0]
                            belt_offset = None
                            belt_surfaces = []
                            belt_surfaces_faded = []
                        else:
                            belt_dragging = True
                            belt_drag_start_x = event.pos[0]
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                panning = False
                pan_start_pos = None
                click_count = 0
                if belt_mode_active:
                    belt_dragging = False
        elif event.type == pygame.MOUSEMOTION:
            tile_window_active = tile_window and tile_window.visible and tile_image is not None
            tw_abs_rect = tile_window.get_abs_rect() if tile_window_active else None
            
            if panning and tile_window_active and tw_abs_rect.collidepoint(event.pos):
                if pan_start_pos is not None:
                    dx = event.pos[0] - pan_start_pos[0]
                    dy = event.pos[1] - pan_start_pos[1]
                    tile_system.map_offset[0] += dx
                    tile_system.map_offset[1] += dy
                    pan_start_pos = event.pos
            elif belt_mode_active and belt_dragging and (not tile_window_active or not tw_abs_rect.collidepoint(event.pos)):
                dx = event.pos[0] - belt_drag_start_x
                if belt_offset is None:
                    belt_offset = 0
                belt_offset -= dx
                belt_drag_start_x = event.pos[0]
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == pan_effect_toggle:
                pan_effect_enabled = not pan_effect_enabled
                pan_effect_toggle.set_text("Pan Effect: On" if pan_effect_enabled else "Pan Effect: Off")
            elif event.ui_element == belt_fade_toggle:
                belt_fade_enabled = not belt_fade_enabled
                belt_fade_toggle.set_text("Belt Fade: On" if belt_fade_enabled else "Belt Fade: Off")
                belt_surfaces_faded = []
            elif event.ui_element == sound_effects_toggle:
                sound_effects_enabled = not sound_effects_enabled
                sound_effects_toggle.set_text("Sound Effects: On" if sound_effects_enabled else "Sound Effects: Off")
            elif event.ui_element == gamepad_toggle:
                gamepad_enabled = not gamepad_enabled
                gamepad_toggle.set_text("Gamepad: On" if gamepad_enabled else "Gamepad: Off")
                print(f"[view_page] Gamepad controls {'enabled' if gamepad_enabled else 'disabled'}")
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
                        tile_window_bottom_bar.set_relative_position((0, new_h))
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
                belt_fade_toggle = None
                sound_effects_toggle = None
                gamepad_toggle = None
            elif tile_window and event.ui_element == tile_window:
                tile_window.kill()
                tile_window = None
                tile_image = None
                reset_view_button = None
                maximize_button = None
                tile_window_maximized = False
        manager.process_events(event)

    manager.update(time_delta)
    main_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, main_area)
    
    if tile_window and tile_window.visible and tile_image is not None:
        tile_image.image.fill((0, 0, 0, 0))
        tw_abs_rect = tile_window.get_abs_rect()
        local_mouse_x = mouse_pos[0] - tw_abs_rect.left - tile_image.get_relative_rect().left
        local_mouse_y = mouse_pos[1] - tw_abs_rect.top - tile_image.get_relative_rect().top - EXTRA_TITLEBAR_HEIGHT
        mouse_in_tile = (0 <= local_mouse_x < tile_image.get_relative_rect().width and 
                         0 <= local_mouse_y < tile_image.get_relative_rect().height)
        tile_system.draw_board((local_mouse_x, local_mouse_y) if mouse_in_tile else None,
                               tile_system.map_offset[0], tile_system.map_offset[1],
                               tile_image.image, tile_image.get_relative_rect(), zoom_factor)
        tile_system.draw_player(tile_system.map_offset[0], tile_system.map_offset[1],
                                tile_image.image, zoom_factor)
    
    current_tile = tile_system.get_current_tile()
    if current_tile and current_tile.image_filenames:
        current_tile_coord = (current_tile.row, current_tile.col)
        if last_tile_coord != current_tile_coord:
            if belt_surfaces:
                old_total_width = sum(w for (_, w) in belt_surfaces)
                belt_view_fraction = (belt_offset + main_area.width/2) / old_total_width if old_total_width > 0 else None
            else:
                belt_view_fraction = None
            belt_surfaces = []
            belt_surfaces_faded = []
            belt_offset = None
            last_tile_coord = current_tile_coord

        if belt_mode_active:
            if not belt_surfaces:
                belt_surfaces = []
                for i in range(len(current_tile.image_filenames)):
                    cv2_img = current_tile.get_current_image(i)
                    if cv2_img is not None:
                        ih, iw = cv2_img.shape[:2]
                        scale_factor = main_area.height / ih
                        new_w = int(iw * scale_factor)
                        new_h = main_area.height
                        scaled_cv2 = cv2.resize(cv2_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        surf = cv2_to_pygame(scaled_cv2)
                        belt_surfaces.append((surf, new_w))

            total_width = sum(w for (_, w) in belt_surfaces)
            if belt_offset is None:
                if belt_view_fraction is not None:
                    belt_offset = belt_view_fraction * total_width - main_area.width / 2
                else:
                    current_idx = tile_system.current_image_index % len(belt_surfaces)
                    cum_width = sum(belt_surfaces[i][1] for i in range(current_idx))
                    belt_offset = cum_width + belt_surfaces[current_idx][1] / 2 - main_area.width / 2

            normalized_offset = belt_offset % total_width
            if normalized_offset < 0:
                normalized_offset += total_width

            if belt_fade_enabled:
                if not belt_surfaces_faded:
                    belt_surfaces_faded = []
                    for (surf, w) in belt_surfaces:
                        faded = get_faded_surface(surf, OVERLAP_FRACTION)
                        belt_surfaces_faded.append((faded, w))
                
                overlap = int(belt_surfaces[0][1] * OVERLAP_FRACTION)
                effective_step = [w - overlap for (_, w) in belt_surfaces]
                total_effective_width = sum(effective_step)

                normalized_fade_offset = belt_offset % total_effective_width
                if normalized_fade_offset < 0:
                    normalized_fade_offset += total_effective_width

                viewport_left = normalized_fade_offset
                viewport_right = normalized_fade_offset + main_area.width
                image_positions = []
                x = 0
                for i, step in enumerate(effective_step):
                    image_left = x
                    image_right = x + step + overlap
                    image_positions.append((i, image_left, image_right))
                    x += step

                max_visible_area = 0
                best_index = 0
                for i, left_x, right_x in image_positions:
                    for offset in [0, total_effective_width]:
                        adj_left = left_x + offset
                        adj_right = right_x + offset
                        visible_left = max(adj_left, viewport_left)
                        visible_right = min(adj_right, viewport_right)
                        visible_width = max(0, visible_right - visible_left)
                        if visible_width > max_visible_area:
                            max_visible_area = visible_width
                            best_index = i

                tile_system.player_direction = best_index % 8
                tile_system.current_image_index = best_index % len(belt_surfaces)

                x = -normalized_fade_offset
                start_x = x
                while x < main_area.width:
                    for i, ((_, w), (faded_surf, _)) in enumerate(zip(belt_surfaces, belt_surfaces_faded)):
                        pos_x = main_area.left + x
                        screen.blit(faded_surf, (pos_x, main_area.top))
                        x += effective_step[i]
                    if x < start_x + total_effective_width and total_effective_width > main_area.width:
                        x = start_x + total_effective_width
            else:
                viewport_left = normalized_offset
                viewport_right = normalized_offset + main_area.width
                image_positions = []
                x = 0
                for i, (_, w) in enumerate(belt_surfaces):
                    image_left = x
                    image_right = x + w
                    image_positions.append((i, image_left, image_right))
                    x += w

                max_visible_area = 0
                best_index = 0
                for i, left_x, right_x in image_positions:
                    for offset in [0, total_width]:
                        adj_left = left_x + offset
                        adj_right = right_x + offset
                        visible_left = max(adj_left, viewport_left)
                        visible_right = min(adj_right, viewport_right)
                        visible_width = max(0, visible_right - visible_left)
                        if visible_width > max_visible_area:
                            max_visible_area = visible_width
                            best_index = i

                tile_system.player_direction = best_index % 8
                tile_system.current_image_index = best_index % len(belt_surfaces)

                x = -normalized_offset
                start_x = x
                while x < main_area.width:
                    for i, (surf, w) in enumerate(belt_surfaces):
                        pos_x = main_area.left + x
                        screen.blit(surf, (pos_x, main_area.top))
                        x += w
                    if x < start_x + total_width and total_width > main_area.width:
                        x = start_x + total_width

            belt_view_fraction = (belt_offset + main_area.width / 2) / total_width if total_width > 0 else None

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
