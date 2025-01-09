# view_page.py

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

# Import the "map module" clone
import tile_system_view as tile_system

pygame.init()
Tk().withdraw()

###############################################################################
# Check if a JSON map was passed as an argument
###############################################################################
linked_json_to_load = None
if len(sys.argv) > 1:
    linked_json_to_load = sys.argv[1]
    print(f"[view_page] Received argument => {linked_json_to_load}")
else:
    print("[view_page] No argument passed => no immediate load")

def load_image(filepath):
    """
    Minimal load: cv2.imread. If you want PDF/SVG logic, add it here.
    """
    path = os.path.normpath(filepath)
    print(f"[DEBUG load_image] Attempting cv2.imread => {path}")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return img

def cv2_to_pygame(img_cv2):
    """
    Convert BGR/BGRA -> pygame Surface
    """
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

# Set up screen
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

root = Tk()
root.withdraw()

# Provide references into tile_system
tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame
tile_system.SQUARE_SIZE = 36
tile_system.initialize()

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

tile_window_width = tile_system.SQUARE_SIZE * 9
tile_window_height = tile_system.SQUARE_SIZE * 9
tile_window_bottom_bar_height = 60

tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect((screen_width - tile_window_width - 10, 10),
                     (tile_window_width, tile_window_height + tile_window_bottom_bar_height)),
    manager=manager,
    window_display_title="Tile System"
)

tile_window_left_panel_width = 50
tile_window_left_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, 0), (tile_window_left_panel_width, tile_window_height)),
    manager=manager,
    container=tile_window
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
    container=tile_window
)

tile_window_button_width = (tile_window_width - 50) // 2
tile_window_button_height = tile_window_bottom_bar_height - 10
tile_window_button_padding = 10

reset_view_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding, 5), (tile_window_button_width, tile_window_button_height)),
    text="Reset View",
    manager=manager,
    container=tile_window_bottom_bar
)

maximize_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((tile_window_button_padding*2 + tile_window_button_width, 5),
                              (tile_window_button_width, tile_window_button_height)),
    text="Maximize",
    manager=manager,
    container=tile_window_bottom_bar
)

tile_window_maximized = False
zoom_factor = 1.0
MIN_ZOOM = 0.5
MAX_ZOOM = 3.0
follow_player = True
running = True

restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",
    manager=manager
)

clock = pygame.time.Clock()
last_click_time = 0
DOUBLE_CLICK_TIME = 500
last_click_pos = None

panning = False
pan_start_pos = None

def reset_map_view():
    global zoom_factor
    tile_image_rect = tile_image.get_abs_rect()
    scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
    tile_system.map_offset[0] = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_sq
    tile_system.map_offset[1] = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_sq
    print("[view_page] reset_map_view => map_offset updated for player pos")

def adjust_zoom(old_zoom, new_zoom):
    if follow_player:
        return
    tile_image_rect = tile_image.get_abs_rect()
    center_x = tile_image_rect.width / 2
    center_y = tile_image_rect.height / 2
    map_x_before = (center_x - tile_system.map_offset[0]) / (tile_system.SQUARE_SIZE * old_zoom)
    map_y_before = (center_y - tile_system.map_offset[1]) / (tile_system.SQUARE_SIZE * old_zoom)
    tile_system.map_offset[0] = center_x - map_x_before * tile_system.SQUARE_SIZE * new_zoom
    tile_system.map_offset[1] = center_y - map_y_before * tile_system.SQUARE_SIZE * new_zoom

###############################################################################
# AUTO-LOAD the JSON if we got one from sys.argv
###############################################################################
if linked_json_to_load and os.path.isfile(linked_json_to_load):
    print(f"[view_page] Auto-loading map => {linked_json_to_load}")
    tile_system.save_current_state_to_history()
    tile_system.load_game_state_from_file(linked_json_to_load)
    # Optionally reset or zoom:
    zoom_factor = 1.0
    reset_map_view()

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

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                tile_system.save_current_state_to_history()
                tile_system.rotate_player(pygame.K_LEFT)
                print("[view_page] rotate left => direction=", tile_system.player_direction)
            elif event.key == pygame.K_RIGHT:
                tile_system.save_current_state_to_history()
                tile_system.rotate_player(pygame.K_RIGHT)
                print("[view_page] rotate right => direction=", tile_system.player_direction)
            elif event.key == pygame.K_UP:
                tile_system.save_current_state_to_history()
                tile_system.move_player(forward=True)
                print("[view_page] move forward => pos=", tile_system.player_pos)
                if follow_player:
                    reset_map_view()
            elif event.key == pygame.K_DOWN:
                tile_system.save_current_state_to_history()
                tile_system.move_player(forward=False)
                print("[view_page] move backward => pos=", tile_system.player_pos)
                if follow_player:
                    reset_map_view()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # wheel up => zoom in
                old_z = zoom_factor
                zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
                adjust_zoom(old_z, zoom_factor)
            elif event.button == 5:  # wheel down => zoom out
                old_z = zoom_factor
                zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
                adjust_zoom(old_z, zoom_factor)
            elif event.button == 1:  # left click => tile select/double-click or panning
                tile_img_rect = tile_image.get_abs_rect()
                if tile_img_rect.collidepoint(event.pos):
                    local_x = event.pos[0] - tile_img_rect.left
                    local_y = event.pos[1] - tile_img_rect.top
                    current_time = pygame.time.get_ticks()

                    if (last_click_pos
                        and abs(event.pos[0] - last_click_pos[0]) < 10
                        and abs(event.pos[1] - last_click_pos[1]) < 10
                        and (current_time - last_click_time < DOUBLE_CLICK_TIME)):

                        # Double-click => move player to tile
                        scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
                        row = int((local_y - tile_system.map_offset[1]) // scaled_sq)
                        col = int((local_x - tile_system.map_offset[0]) // scaled_sq)
                        tile_system.save_current_state_to_history()
                        tile_system.move_player_to_tile(row, col)
                        print("[view_page] double-click => move player => pos=", tile_system.player_pos)
                        last_click_time = 0
                        last_click_pos = None
                        if follow_player:
                            reset_map_view()
                    else:
                        # Single-click => select tile
                        scaled_sq = tile_system.SQUARE_SIZE * zoom_factor
                        row = int((local_y - tile_system.map_offset[1]) // scaled_sq)
                        col = int((local_x - tile_system.map_offset[0]) // scaled_sq)
                        tile_system.select_tile(row, col)
                        print(f"[view_page] single-click => tile({row},{col}) selected")
                        last_click_time = current_time
                        last_click_pos = event.pos
                else:
                    # Left-click outside tile window => start panning
                    panning = True
                    pan_start_pos = event.pos
                    follow_player = False

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                panning = False

        elif event.type == pygame.MOUSEMOTION:
            if panning:
                dx = event.pos[0] - pan_start_pos[0]
                dy = event.pos[1] - pan_start_pos[1]
                tile_system.map_offset[0] += dx
                tile_system.map_offset[1] += dy
                pan_start_pos = event.pos

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == home_button:
                subprocess.Popen(["python", "home_page.py"])
                pygame.quit()
                sys.exit()
            elif event.ui_element == load_game_button:
                tile_system.save_current_state_to_history()
                tile_system.load_game_state()
                zoom_factor = 1.0
                reset_map_view()
                print("[view_page] load_game => loaded => player pos:", tile_system.player_pos)

            elif event.ui_element == reset_view_button:
                zoom_factor = 1.0
                reset_map_view()
                follow_player = True

            elif event.ui_element == maximize_button:
                tile_window_maximized = not tile_window_maximized
                if tile_window_maximized:
                    maximize_button.set_text("Restore")
                    tile_window.set_relative_position((10, 10))
                    tile_window.set_dimensions((screen_width - 20, screen_height - bottom_bar_height - 20))
                    new_w = tile_window.get_relative_rect().width
                    new_h = tile_window.get_relative_rect().height - tile_window_bottom_bar_height
                    tile_image.set_dimensions((new_w, new_h))
                    tile_image_surf = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surf)
                    tile_window_bottom_bar.set_relative_position((0, new_h))
                    tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))
                else:
                    maximize_button.set_text("Maximize")
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                    tile_window.set_dimensions((tile_window_width, tile_window_height + tile_window_bottom_bar_height))
                    tile_image.set_dimensions((tile_window_width, tile_window_height))
                    tile_image_surf = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surf)
                    tile_window_bottom_bar.set_relative_position((0, tile_window_height))
                    tile_window_bottom_bar.set_dimensions((tile_window_width, tile_window_bottom_bar_height))

            elif event.ui_element == restore_tile_window_button:
                if tile_window:
                    if tile_window.visible:
                        tile_window.hide()
                    else:
                        tile_window.show()

            elif event.ui_element == sub_button:
                tile_system.sub_grid_visible = not tile_system.sub_grid_visible
                sub_button.set_text(f"Sub: {'ON' if tile_system.sub_grid_visible else 'OFF'}")

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == tile_window:
                tile_window.hide()

        manager.process_events(event)

    manager.update(time_delta)

    # Fill main area
    main_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, main_area)

    # Tile window update
    if tile_window and tile_window.visible:
        tile_image.image.fill((0, 0, 0, 0))
        tile_img_rect = tile_image.get_abs_rect()
        local_mouse_pos = pygame.mouse.get_pos()
        local_mouse_pos = (local_mouse_pos[0] - tile_img_rect.left, local_mouse_pos[1] - tile_img_rect.top)
        visible_area = pygame.Rect(0, 0, tile_img_rect.width, tile_img_rect.height)
        scaled_sq = tile_system.SQUARE_SIZE * zoom_factor

        if follow_player:
            offset_x = tile_img_rect.width // 2 - tile_system.player_pos[1] * scaled_sq
            offset_y = tile_img_rect.height // 2 - tile_system.player_pos[0] * scaled_sq
        else:
            offset_x, offset_y = tile_system.map_offset

        tile_system.draw_board(local_mouse_pos, offset_x, offset_y,
                               tile_image.image, visible_area, zoom_factor)
        tile_system.draw_player(offset_x, offset_y, tile_image.image, zoom_factor)
        tile_image_surface.blit(tile_image.image, (0, 0))

    # Display current tile's image in main area
    current_tile = tile_system.get_current_tile()
    if current_tile and current_tile.image_filenames:
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
