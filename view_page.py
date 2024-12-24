# view_page.py

import pygame
import pygame_gui
import ctypes
import sys
import os
import subprocess
import tile_system_view  # <-- Our read-only tile system

pygame.init()

##############################################################################
# Basic Window Setup
##############################################################################
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("MAPPIC Viewer")

icon = pygame.image.load('mappiclogo.ico')
pygame.display.set_icon(icon)

# Maximize the window on Windows systems
window_handle = pygame.display.get_wm_info()["window"]
SW_MAXIMIZE = 3
user32 = ctypes.windll.user32
user32.ShowWindow(window_handle, SW_MAXIMIZE)

# Current screen dimensions
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

manager = pygame_gui.UIManager((screen_width, screen_height))

MAIN_BG_COLOR = (68, 71, 90)   # Main background color
IMAGE_BG_COLOR = (40, 42, 54)  # Secondary background color (dark display frame)

##############################################################################
# Dark Display Frame (like in main.py)
##############################################################################
image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - 20)

##############################################################################
# Single "Home" Button
##############################################################################
home_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((15, 15), (60, 40)),
    text="Home",
    manager=manager,
    object_id="#home_button"
)

##############################################################################
# "Restore" Button in top-right corner
##############################################################################
restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",
    manager=manager,
    object_id="#restore_button"
)

##############################################################################
# The Tile Window (placed on the right side)
##############################################################################
tile_window_width = tile_system_view.SQUARE_SIZE * 9
tile_window_height = tile_system_view.SQUARE_SIZE * 9

# Increased bottom bar height for bigger buttons
tile_window_bottom_bar_height = 80  

tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect(
        (screen_width - tile_window_width - 10, 10),
        (tile_window_width, tile_window_height + tile_window_bottom_bar_height)
    ),
    manager=manager,
    window_display_title="Map Viewer",
    object_id="#tile_window"
)

##############################################################################
# The main tile image area
##############################################################################
tile_image_width = tile_window_width
tile_image_height = tile_window_height
tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)

tile_image = pygame_gui.elements.UIImage(
    relative_rect=pygame.Rect((0, 0), (tile_image_width, tile_image_height)),
    image_surface=tile_image_surface,
    manager=manager,
    container=tile_window
)

##############################################################################
# Bottom bar with "Reset View" and "Maximize" (now taller)
##############################################################################
tile_window_bottom_bar = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect(
        (0, tile_window_height),
        (tile_window_width, tile_window_bottom_bar_height)
    ),
    manager=manager,
    container=tile_window,
    object_id="#tile_window_bottom_bar"
)

# Adjust button dimensions accordingly
tile_window_button_padding = 10
# If you want bigger or more spaced-out buttons, tweak these:
tile_window_button_width = (tile_window_width - tile_window_button_padding * 3) // 2
tile_window_button_height = tile_window_bottom_bar_height - tile_window_button_padding * 2

reset_zoom_button = pygame_gui.elements.UIButton(
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
        (tile_window_button_padding * 2 + tile_window_button_width, tile_window_button_padding),
        (tile_window_button_width, tile_window_button_height)
    ),
    text="Maximize",
    manager=manager,
    container=tile_window_bottom_bar
)

tile_window_visible = True
tile_window_maximized = False

##############################################################################
# Zoom & View
##############################################################################
zoom_factor = 1.0
MIN_ZOOM = 0.5
MAX_ZOOM = 3.0

##############################################################################
# Main Loop
##############################################################################
clock = pygame.time.Clock()
running = True

while running:
    time_delta = clock.tick(60) / 1000.0

    # Fill background
    screen.fill(MAIN_BG_COLOR)

    # Draw the dark display frame
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            manager.set_window_resolution((screen_width, screen_height))

            # Update the dark frame
            image_display_area.width = screen_width - 20
            image_display_area.height = screen_height - 20

            # Reposition the restore button in the top-right corner
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))

            if tile_window_maximized:
                tile_window.set_relative_position((image_display_area.left + 10, image_display_area.top + 10))
                tile_window.set_dimensions((image_display_area.width - 20,
                                            image_display_area.height - 20))
                new_w = tile_window.get_relative_rect().width
                new_h = tile_window.get_relative_rect().height - tile_window_bottom_bar_height
                tile_image.set_dimensions((new_w, new_h))
                tile_image_surface = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                tile_image.set_image(tile_image_surface)

                tile_window_bottom_bar.set_relative_position((0, new_h))
                tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))
            else:
                tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == home_button:
                subprocess.Popen(["python", "home_page.py"])
                pygame.quit()
                sys.exit()

            elif event.ui_element == restore_tile_window_button:
                # Toggle show/hide or re-create tile window
                if tile_window is None:
                    tile_window = pygame_gui.elements.UIWindow(
                        rect=pygame.Rect(
                            (screen_width - tile_window_width - 10, 10),
                            (tile_window_width, tile_window_height + tile_window_bottom_bar_height)
                        ),
                        manager=manager,
                        window_display_title="Map Viewer",
                        object_id="#tile_window"
                    )
                    # Re-create tile_image
                    tile_image_surface = pygame.Surface((tile_image_width, tile_image_height), pygame.SRCALPHA)
                    tile_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect((0, 0), (tile_image_width, tile_image_height)),
                        image_surface=tile_image_surface,
                        manager=manager,
                        container=tile_window
                    )
                    # Re-create bottom bar, reset & maximize
                    tile_window_bottom_bar = pygame_gui.elements.UIPanel(
                        relative_rect=pygame.Rect(
                            (0, tile_window_height),
                            (tile_window_width, tile_window_bottom_bar_height)
                        ),
                        manager=manager,
                        container=tile_window,
                        object_id="#tile_window_bottom_bar"
                    )
                    reset_zoom_button = pygame_gui.elements.UIButton(
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
                            (tile_window_button_padding*2 + tile_window_button_width, tile_window_button_padding),
                            (tile_window_button_width, tile_window_button_height)
                        ),
                        text="Maximize",
                        manager=manager,
                        container=tile_window_bottom_bar
                    )
                else:
                    if tile_window.visible:
                        tile_window.hide()
                    else:
                        tile_window.show()

            elif event.ui_element == reset_zoom_button:
                tile_system_view.reset_map_view()
                zoom_factor = 1.0

            elif event.ui_element == maximize_button:
                tile_window_maximized = not tile_window_maximized
                if tile_window_maximized:
                    maximize_button.set_text("Restore")
                    tile_window.set_relative_position((image_display_area.left + 10, image_display_area.top + 10))
                    tile_window.set_dimensions((image_display_area.width - 20,
                                                image_display_area.height - 20))
                    new_w = tile_window.get_relative_rect().width
                    new_h = tile_window.get_relative_rect().height - tile_window_bottom_bar_height
                    tile_image.set_dimensions((new_w, new_h))
                    tile_image_surface = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)

                    tile_window_bottom_bar.set_relative_position((0, new_h))
                    tile_window_bottom_bar.set_dimensions((new_w, tile_window_bottom_bar_height))
                else:
                    maximize_button.set_text("Maximize")
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                    tile_window.set_dimensions((tile_window_width, tile_window_height + tile_window_bottom_bar_height))

                    tile_image.set_dimensions((tile_window_width, tile_window_height))
                    tile_image_surface = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)

                    tile_window_bottom_bar.set_relative_position((0, tile_window_height))
                    tile_window_bottom_bar.set_dimensions((tile_window_width, tile_window_bottom_bar_height))

        manager.process_events(event)

    manager.update(time_delta)

    # Draw the map if tile_window is present
    if tile_window is not None:
        tile_image.image.fill((0, 0, 0, 0))

        tile_image_rect = tile_image.get_abs_rect()
        local_mouse_pos = pygame.mouse.get_pos()
        local_mouse_pos = (
            local_mouse_pos[0] - tile_image_rect.left,
            local_mouse_pos[1] - tile_image_rect.top
        )
        visible_area = pygame.Rect(0, 0, tile_image_rect.width, tile_image_rect.height)

        tile_system_view.draw_board(
            local_mouse_pos,
            tile_system_view.map_offset[0],
            tile_system_view.map_offset[1],
            tile_image.image,
            visible_area,
            zoom_factor
        )
        tile_system_view.draw_player(
            tile_system_view.map_offset[0],
            tile_system_view.map_offset[1],
            tile_image.image,
            zoom_factor
        )

        tile_image_surface.blit(tile_image.image, (0, 0))

    manager.draw_ui(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
