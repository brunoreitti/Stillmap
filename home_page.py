# home_page.py

import pygame
import pygame_gui
import sys
import os
import cv2
import numpy as np
import cairosvg
import subprocess
import ctypes

pygame.init()

def load_svg_image(svg_path, output_width=None, output_height=None):
    try:
        png_data = cairosvg.svg2png(url=svg_path, output_width=output_width, output_height=output_height)
        nparr = np.frombuffer(png_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        return image
    except Exception as e:
        print(f"Failed to load SVG {svg_path}: {e}")
        return None

def cv2_to_pygame(image):
    if image.shape[2] == 4:
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        return pygame.image.frombuffer(image_rgba.tobytes(), image_rgba.shape[1::-1], 'RGBA')
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')

def load_image(filepath):
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext == '.svg':
        return load_svg_image(filepath)
    else:
        return None  # For simplicity, handle only SVG here

BACKGROUND_SVG_PATH = 'craybg2.svg'
background_cv2 = load_image(BACKGROUND_SVG_PATH)
if background_cv2 is None:
    print(f"Could not load background image: {BACKGROUND_SVG_PATH}")
    sys.exit(1)

background_surface = cv2_to_pygame(background_cv2)

# Create a resizable window and maximize it
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("MAPPIC Home Page")

icon = pygame.image.load('mappiclogo.ico')
pygame.display.set_icon(icon)

window_handle = pygame.display.get_wm_info()["window"]
SW_MAXIMIZE = 3
user32 = ctypes.windll.user32
user32.ShowWindow(window_handle, SW_MAXIMIZE)
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

manager = pygame_gui.UIManager((screen_width, screen_height))

MAIN_BG_COLOR = (68, 71, 90)
IMAGE_BG_COLOR = (40, 42, 54)

bottom_bar_height = 60
bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

# Back to Main button in top-left corner
back_to_main_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 10), (120, 50)),
    text="Back to Main",
    manager=manager
)

clock = pygame.time.Clock()
running = True

while running:
    time_delta = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            back_to_main_button.set_relative_position((10, 10))
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == back_to_main_button:
                # Launch main.py and close this home_page.py
                subprocess.Popen(["python", "main.py"])
                pygame.quit()
                sys.exit()

        manager.process_events(event)

    manager.update(time_delta)

    screen.fill(MAIN_BG_COLOR)
    # Draw image display area (like in main.py)
    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    # Scale and center the background image in the same manner as main.py
    img_width, img_height = background_surface.get_size()
    scale_factor = min(image_display_area.width / img_width, image_display_area.height / img_height)
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    scaled_background = pygame.transform.smoothscale(background_surface, (new_width, new_height))
    background_rect = scaled_background.get_rect(center=image_display_area.center)
    screen.blit(scaled_background, background_rect)

    manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
