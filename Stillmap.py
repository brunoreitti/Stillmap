# main.py

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

# Import the tile_system module
import tile_system

# Initialize Pygame and Pygame GUI
pygame.init()

# Create a resizable Pygame window
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("viewalk software")

icon = pygame.image.load('viewalk.ico')
pygame.display.set_icon(icon)

# Get the handle of the Pygame window
window_handle = pygame.display.get_wm_info()["window"]

# Define constants for Windows messages
SW_MAXIMIZE = 3

# Define the user32 library for sending messages to the window
user32 = ctypes.windll.user32

# Maximize the window
user32.ShowWindow(window_handle, SW_MAXIMIZE)

# Get the screen dimensions after maximizing
screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# Bring window to the foreground
def bring_window_to_front():
    user32.SetForegroundWindow(window_handle)

# Colors
MAIN_BG_COLOR = (68, 71, 90)
IMAGE_BG_COLOR = (40, 42, 54)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Initialize Tkinter root and hide the main window
root = Tk()
root.withdraw()

# Function to open file explorer
def open_file_explorer():
    directory = filedialog.askdirectory()
    return directory

def open_image_file_explorer():
    filetypes = (
        ('Image files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif'),
        ('All files', '*.*')
    )
    filename = filedialog.askopenfilename(
        title='Open an image',
        initialdir=os.getcwd(),
        filetypes=filetypes)
    return filename

def load_image_with_orientation(filepath):
    image = cv2.imread(filepath)
    if image is None:
        raise ValueError("Image not found or unable to load")
    try:
        # Handle EXIF orientation if necessary
        from PIL import Image, ExifTags

        pil_image = Image.open(filepath)
        exif = pil_image._getexif()
        if exif is not None:
            orientation_key = next(
                (key for key, val in ExifTags.TAGS.items() if val == 'Orientation'), None)
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
    """Convert an OpenCV image to a Pygame surface."""
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')

# Function to handle clicking on a link in the message box
def handle_link_click(link):
    if os.path.isdir(link):
        subprocess.Popen(['explorer', link])
    elif os.path.isfile(link):
        try:
            with open(link, 'r') as file:
                data = json.load(file)
                # Display JSON content in a message box or handle as needed
                messagebox.showinfo("JSON Content", json.dumps(data, indent=2))
        except Exception as e:
            messagebox.showerror("JSON Error", f"Failed to load JSON: {e}")

# Assign functions in tile_system that need access to functions in main.py
tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image
tile_system.cv2_to_pygame = cv2_to_pygame  # Assign cv2_to_pygame function

# Set the SQUARE_SIZE and initialize the tile system
SQUARE_SIZE = 36  # Set square size to 36 pixels
tile_system.SQUARE_SIZE = SQUARE_SIZE  # Set in tile_system
tile_system.initialize()  # Initialize the tiles now that SQUARE_SIZE is set

# Function to load link areas for images in image viewing mode
def load_image_viewing_link_areas():
    global image_viewing_link_areas
    image_viewing_link_areas = {}
    link_areas_file = os.path.join(image_viewing_directory, 'link_areas.json')
    if os.path.exists(link_areas_file):
        try:
            with open(link_areas_file, 'r') as f:
                data = json.load(f)
                # Convert keys back to absolute image paths
                for image_name, areas in data.items():
                    image_path = os.path.join(image_viewing_directory, image_name)
                    image_viewing_link_areas[image_path] = areas
            print(f"Loaded link areas from {link_areas_file}")
        except Exception as e:
            print(f"Failed to load link areas: {e}")
    else:
        print(f"No link_areas.json found in {image_viewing_directory}")

# Function to save link areas for images in image viewing mode
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

# Setup pygame_gui manager
manager = pygame_gui.UIManager((screen_width, screen_height))

# Create Bottom Bar
bottom_bar_height = 60

bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

# Create buttons and add them to the bottom bar
button_padding = 10
button_height = 40
button_texts = ["Load Game", "Save Game", "Edit Mode", "Select Image Folder", "Remove Image Folder",
                "Edit Description", "Manage JSON Links", "Clear JSON Links", "Add Link Area", "Assign Link Folder", "Assign JSON Area", "Show Links"]
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

# Assign buttons to variables
(load_button, save_button, edit_button, image_button, delete_button,
 edit_text_button, json_link_button,
 clear_json_link_button, add_link_area_button, assign_link_folder_button, assign_json_area_button, show_links_button) = buttons

# Adjust tile window size to match the original size
tile_window_width = SQUARE_SIZE * 9  # Original width (e.g., 324 pixels)
tile_window_height = SQUARE_SIZE * 9  # Original height (e.g., 324 pixels)

# Create the tile window in the top right corner
tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect((screen_width - tile_window_width - 10, 10), (tile_window_width, tile_window_height)),
    manager=manager,
    window_display_title="Tile System",
    object_id="#tile_window"
)

# Create a UIImage inside the tile window to display the tiles
tile_image_surface = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
tile_image = pygame_gui.elements.UIImage(
    relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_window_height)),
    image_surface=tile_image_surface,
    manager=manager,
    container=tile_window
)

tile_window_visible = True  # Flag to track if the tile window is visible
tile_window_maximized = False  # Flag to track if the tile window is maximized

# Introduce zoom_factor
zoom_factor = 1.0  # Default zoom level

# Define minimum and maximum zoom levels
MIN_ZOOM = 0.5
MAX_ZOOM = 3.0

# Add Reset Zoom Button to the tile window's title bar
reset_zoom_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((-240, 0), (80, 30)),  # Adjusted position
    text="Reset Zoom",
    manager=manager,
    container=tile_window,
    anchors={
        'left': 'right',
        'right': 'right',
        'top': 'top',
        'bottom': 'top'
    }
)

# Add Maximize/Restore Button to the tile window's title bar
maximize_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((-160, 0), (80, 30)),  # Adjusted position
    text="Maximize",
    manager=manager,
    container=tile_window,
    anchors={
        'left': 'right',
        'right': 'right',
        'top': 'top',
        'bottom': 'top'
    }
)

# Add Set Background Button to the tile window's title bar
set_bg_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((-80, 0), (80, 30)),  # Adjusted position
    text="Set BG",
    manager=manager,
    container=tile_window,
    anchors={
        'left': 'right',
        'right': 'right',
        'top': 'top',
        'bottom': 'top'
    }
)

# Add Grid Toggle Button to the tile window's title bar
grid_toggle_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((-320, 0), (80, 30)),  # Adjusted position
    text="Grid: ON",
    manager=manager,
    container=tile_window,
    anchors={
        'left': 'right',
        'right': 'right',
        'top': 'top',
        'bottom': 'top'
    }
)

# Create the restore button in the top right corner
restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",  # Downward arrow
    manager=manager,
    object_id="#restore_button"
)

# Variables for drawing link areas
drawing_link_area = False
link_area_start_pos = None
link_area_rect = None

# Variables for image viewing mode
image_viewing_mode = False
image_viewing_images = []
image_viewing_index = 0
image_viewing_directory = ''
get_back_button = None  # Button to exit image viewing mode

# Variables for assign modes
assign_link_folder_mode = False
assign_json_area_mode = False

# Variable to show or hide link areas
show_link_areas = False

# Variable for the description popup window
description_popup_window = None
description_text_box = None  # To store the text box inside the popup

# Create the back and forward buttons in the top left corner
back_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 10), (50, 50)),
    text="<",
    manager=manager,
    object_id="#back_button"
)

forward_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((70, 10), (50, 50)),
    text=">",
    manager=manager,
    object_id="#forward_button"
)

# Ensure link_area_mode is initialized
link_area_mode = False

# Variables for managing link areas in image viewing mode
image_viewing_link_areas = {}  # Key: image path, Value: list of link areas

clock = pygame.time.Clock()

# Dictionary to store original button texts
original_button_texts = {}

# Function to show confirmation on a button
def show_button_confirmation(button, confirmation_text, duration=2000):
    global original_button_texts, confirmation_end_time, confirmation_button
    original_button_texts[button] = button.text
    button.set_text(confirmation_text)
    confirmation_end_time = pygame.time.get_ticks() + duration
    confirmation_button = button
    print("Button confirmation displayed:", confirmation_text)

# Main game loop
running = True
confirmation_button = None  # To store the current confirmation button
confirmation_end_time = 0  # To track when to revert the button text

# Variables to store the original size and position of the tile window
original_tile_window_rect = tile_window.get_relative_rect().copy()

while running:
    time_delta = clock.tick(60) / 1000.0  # Limits the frame rate to 60 FPS
    screen.fill(MAIN_BG_COLOR)  # Fill the main area with the main background color

    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Before exiting, save link areas in image viewing mode if any
            if image_viewing_mode:
                save_image_viewing_link_areas()
            running = False
        elif event.type == pygame.VIDEORESIZE:
            # Update screen dimensions
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            # Update bottom bar position and size
            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            # Update restore button position
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))
            # Update tile window position if it's visible
            if tile_window is not None:
                if tile_window_maximized:
                    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    tile_window.set_relative_position((image_display_area.left, image_display_area.top))
                    tile_window.set_dimensions((image_display_area.width, image_display_area.height))
                    tile_image.set_dimensions((image_display_area.width, image_display_area.height))
                    tile_image_surface = pygame.Surface((image_display_area.width, image_display_area.height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                else:
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
            # Update get back button position
            if get_back_button is not None:
                get_back_button.set_relative_position((10, 70))  # Adjusted position
            # Update back and forward buttons position
            back_button.set_relative_position((10, 10))
            forward_button.set_relative_position((70, 10))
        elif event.type == pygame.KEYDOWN:
            if image_viewing_mode:
                if event.key == pygame.K_ESCAPE:
                    # Save link areas before exiting image viewing mode
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
                if event.key == pygame.K_e:  # Toggle edit mode with 'E' key
                    tile_system.toggle_edit_mode()
                    edit_button.set_text(f"Edit Mode: {'ON' if tile_system.edit_mode else 'OFF'}")
                elif event.key == pygame.K_j:  # Toggle JSON link mode with 'J' key
                    tile_system.toggle_json_link_mode()
                    json_link_button.set_text(f"Manage JSON Links: {'ON' if tile_system.json_link_mode else 'OFF'}")
                elif event.key == pygame.K_c:  # Toggle clear JSON link mode with 'C' key
                    tile_system.toggle_clear_json_link_mode()
                    clear_json_link_button.set_text(f"Clear JSON Links: {'ON' if tile_system.clear_json_link_mode else 'OFF'}")
                elif event.key == pygame.K_UP:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=True)
                elif event.key == pygame.K_DOWN:
                    tile_system.save_current_state_to_history()
                    tile_system.move_player(forward=False)
                elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    tile_system.save_current_state_to_history()
                    tile_system.rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Mouse wheel up
                zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)
            elif event.button == 5:  # Mouse wheel down
                zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)
            elif event.button == 8:  # Backward mouse button
                tile_system.go_back()
                bring_window_to_front()
            elif event.button == 9:  # Forward mouse button
                tile_system.go_forward()
                bring_window_to_front()
            elif image_viewing_mode:
                if 'image_rect' in locals() and image_rect.collidepoint(event.pos):
                    if (link_area_mode or assign_link_folder_mode or assign_json_area_mode) and event.button == 1:
                        link_area_start_pos = event.pos
                        drawing_link_area = True
                    # Handle closing the description popup when clicking outside
                    if description_popup_window is not None:
                        popup_rect = description_popup_window.get_abs_rect()
                        if not popup_rect.collidepoint(event.pos):
                            description_popup_window.kill()
                            description_popup_window = None
                            description_text_box = None
                else:
                    # Handle closing the description popup when clicking outside
                    if description_popup_window is not None:
                        popup_rect = description_popup_window.get_abs_rect()
                        if not popup_rect.collidepoint(event.pos):
                            description_popup_window.kill()
                            description_popup_window = None
                            description_text_box = None
            else:
                if tile_window is not None:
                    # Get the mouse position relative to the tile window
                    tile_window_rect = tile_window.get_abs_rect()
                    tile_image_rect = tile_image.get_abs_rect()
                    if tile_image_rect.collidepoint(event.pos):
                        local_pos = (event.pos[0] - tile_image_rect.left, event.pos[1] - tile_image_rect.top)
                        # Calculate which tile was clicked
                        scaled_square_size = SQUARE_SIZE * zoom_factor
                        offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
                        offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
                        tile_col = int((local_pos[0] - offset_x) // scaled_square_size)
                        tile_row = int((local_pos[1] - offset_y) // scaled_square_size)
                        tile = tile_system.get_tile(tile_row, tile_col)
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
                            # Assign image folder to the clicked tile
                            directory = open_file_explorer()
                            if directory:
                                tile.set_directory(directory)
                                bring_window_to_front()
                    # Handle closing the description popup when clicking outside
                    if description_popup_window is not None:
                        popup_rect = description_popup_window.get_abs_rect()
                        if not popup_rect.collidepoint(event.pos):
                            description_popup_window.kill()
                            description_popup_window = None
                            description_text_box = None
        elif event.type == pygame.MOUSEBUTTONUP:
            if drawing_link_area and event.button == 1:
                drawing_link_area = False
                if link_area_rect is not None:
                    # Ensure the rectangle is within the image area
                    link_area_rect = link_area_rect.clip(image_rect)
                    # Calculate relative coordinates
                    img_x0, img_y0 = image_rect.topleft
                    img_width, img_height = image_rect.size
                    rel_x0 = (link_area_rect.left - img_x0) / img_width
                    rel_y0 = (link_area_rect.top - img_y0) / img_height
                    rel_x1 = (link_area_rect.right - img_x0) / img_width
                    rel_y1 = (link_area_rect.bottom - img_y0) / img_height
                    # Store in the appropriate data structure
                    if image_viewing_mode:
                        image_path = image_viewing_images[image_viewing_index]
                        if image_path not in image_viewing_link_areas:
                            image_viewing_link_areas[image_path] = []
                        area = {'coords': [rel_x0, rel_y0, rel_x1, rel_y1], 'link': None, 'json': None}
                        image_viewing_link_areas[image_path].append(area)
                        print(f"Added link area to image {image_path}: {area}")
                    else:
                        current_tile = tile_system.get_current_tile()
                        image_index = tile_system.current_image_index
                        area = {'coords': [rel_x0, rel_y0, rel_x1, rel_y1], 'link': None, 'json': None}
                        current_tile.add_link_area(image_index, area)
                    # Reset the rectangle variables
                    link_area_rect = None
                    link_area_start_pos = None
            elif drawing_link_area:
                drawing_link_area = False
                link_area_rect = None
        elif event.type == pygame.MOUSEMOTION:
            if drawing_link_area:
                x0, y0 = link_area_start_pos
                x1, y1 = event.pos
                link_area_rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == load_button:
                tile_system.save_current_state_to_history()
                tile_system.load_game_state()
            elif event.ui_element == save_button:
                tile_system.save_game_state()
                # Save link areas in image viewing mode
                if image_viewing_mode:
                    save_image_viewing_link_areas()
            elif event.ui_element == edit_button:
                tile_system.toggle_edit_mode()
                edit_button.set_text(f"Edit Mode: {'ON' if tile_system.edit_mode else 'OFF'}")
            elif event.ui_element == image_button:
                directory = open_file_explorer()
                if directory:
                    # Assign image folder to the current tile
                    current_tile = tile_system.get_current_tile()
                    current_tile.set_directory(directory)
                    bring_window_to_front()
            elif event.ui_element == delete_button:
                current_tile = tile_system.get_current_tile()
                current_tile.clear_directory()
                print(f"Removed folder association from the current tile.")
            elif event.ui_element == json_link_button:
                tile_system.toggle_json_link_mode()
                json_link_button.set_text(f"Manage JSON Links: {'ON' if tile_system.json_link_mode else 'OFF'}")
            elif event.ui_element == clear_json_link_button:
                tile_system.toggle_clear_json_link_mode()
                clear_json_link_button.set_text(f"Clear JSON Links: {'ON' if tile_system.clear_json_link_mode else 'OFF'}")
            elif event.ui_element == edit_text_button:
                current_tile = tile_system.get_current_tile()
                new_text = simpledialog.askstring("Edit Description", "Enter new text:", initialvalue=current_tile.text_content)
                if new_text is not None:
                    current_tile.text_content = new_text
                    # Update the popup window if it's open
                    if description_popup_window is not None and description_text_box is not None:
                        description_text_box.set_text(f"<font color='#000000'>{current_tile.text_content}</font>")
                        description_text_box.rebuild()
            elif event.ui_element == add_link_area_button:
                tile_system.link_area_mode = not tile_system.link_area_mode
                add_link_area_button.set_text(f"Add Link Area: {'ON' if tile_system.link_area_mode else 'OFF'}")
                # Also set the local link_area_mode for image viewing mode
                link_area_mode = tile_system.link_area_mode
                # Turn off other modes if necessary
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
                # Turn off other modes if necessary
                if assign_link_folder_mode:
                    tile_system.edit_mode = False
                    tile_system.json_link_mode = False
                    tile_system.clear_json_link_mode = False
                    tile_system.link_area_mode = False
                    link_area_mode = False
                    assign_json_area_mode = False
                    drawing_link_area = False  # Ensure drawing is not active
                    edit_button.set_text("Edit Mode: OFF")
                    json_link_button.set_text("Manage JSON Links: OFF")
                    clear_json_link_button.set_text("Clear JSON Links: OFF")
                    add_link_area_button.set_text("Add Link Area: OFF")
                    assign_json_area_button.set_text("Assign JSON Area: OFF")
            elif event.ui_element == assign_json_area_button:
                assign_json_area_mode = not assign_json_area_mode
                assign_json_area_button.set_text(f"Assign JSON Area: {'ON' if assign_json_area_mode else 'OFF'}")
                # Turn off other modes if necessary
                if assign_json_area_mode:
                    tile_system.edit_mode = False
                    tile_system.json_link_mode = False
                    tile_system.clear_json_link_mode = False
                    tile_system.link_area_mode = False
                    link_area_mode = False
                    assign_link_folder_mode = False
                    drawing_link_area = False  # Ensure drawing is not active
                    edit_button.set_text("Edit Mode: OFF")
                    json_link_button.set_text("Manage JSON Links: OFF")
                    clear_json_link_button.set_text("Clear JSON Links: OFF")
                    add_link_area_button.set_text("Add Link Area: OFF")
                    assign_link_folder_button.set_text("Assign Link Folder: OFF")
            elif event.ui_element == show_links_button:
                show_link_areas = not show_link_areas
                show_links_button.set_text(f"Show Links: {'ON' if show_link_areas else 'OFF'}")
            elif event.ui_element == grid_toggle_button:
                tile_system.grid_visible = not tile_system.grid_visible
                grid_toggle_button.set_text(f"Grid: {'ON' if tile_system.grid_visible else 'OFF'}")
            elif event.ui_element == reset_zoom_button:
                zoom_factor = 1.0  # Reset zoom to default
            elif event.ui_element == maximize_button:
                tile_window_maximized = not tile_window_maximized
                if tile_window_maximized:
                    # Maximize the tile window to the image display area
                    maximize_button.set_text("Restore")
                    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
                    tile_window.set_relative_position((image_display_area.left, image_display_area.top))
                    tile_window.set_dimensions((image_display_area.width, image_display_area.height))
                    tile_image.set_dimensions((image_display_area.width, image_display_area.height))
                    tile_image_surface = pygame.Surface((image_display_area.width, image_display_area.height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
                else:
                    # Restore the tile window to its original size and position
                    maximize_button.set_text("Maximize")
                    tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
                    tile_window.set_dimensions((tile_window_width, tile_window_height))
                    tile_image.set_dimensions((tile_window_width, tile_window_height))
                    tile_image_surface = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
                    tile_image.set_image(tile_image_surface)
            elif event.ui_element == set_bg_button:
                # Open file dialog to select background image
                bg_image_path = open_image_file_explorer()
                if bg_image_path:
                    background_image_cv2 = load_image(bg_image_path)
                    if background_image_cv2 is not None:
                        background_image_surface = cv2_to_pygame(background_image_cv2)
                        tile_system.set_background_image(background_image_surface, bg_image_path)  # Pass both arguments
                bring_window_to_front()
            elif event.ui_element == restore_tile_window_button:
                if tile_window is None:
                    # Recreate the tile window
                    tile_window = pygame_gui.elements.UIWindow(
                        rect=pygame.Rect((screen_width - tile_window_width - 10, 10), (tile_window_width, tile_window_height)),
                        manager=manager,
                        window_display_title="Tile System",
                        object_id="#tile_window"
                    )
                    # Recreate the tile_image inside the tile window
                    tile_image_surface = pygame.Surface((tile_window_width, tile_window_height), pygame.SRCALPHA)
                    tile_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_window_height)),
                        image_surface=tile_image_surface,
                        manager=manager,
                        container=tile_window
                    )
                    # Add Reset Zoom Button to the tile window's title bar
                    reset_zoom_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((-240, 0), (80, 30)),
                        text="Reset Zoom",
                        manager=manager,
                        container=tile_window,
                        anchors={
                            'left': 'right',
                            'right': 'right',
                            'top': 'top',
                            'bottom': 'top'
                        }
                    )
                    # Add Maximize/Restore Button to the tile window's title bar
                    maximize_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((-160, 0), (80, 30)),
                        text="Maximize",
                        manager=manager,
                        container=tile_window,
                        anchors={
                            'left': 'right',
                            'right': 'right',
                            'top': 'top',
                            'bottom': 'top'
                        }
                    )
                    # Add Set Background Button to the tile window's title bar
                    set_bg_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((-80, 0), (80, 30)),
                        text="Set BG",
                        manager=manager,
                        container=tile_window,
                        anchors={
                            'left': 'right',
                            'right': 'right',
                            'top': 'top',
                            'bottom': 'top'
                        }
                    )
                    # Add Grid Toggle Button to the tile window's title bar
                    grid_toggle_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((-320, 0), (80, 30)),
                        text="Grid: ON",
                        manager=manager,
                        container=tile_window,
                        anchors={
                            'left': 'right',
                            'right': 'right',
                            'top': 'top',
                            'bottom': 'top'
                        }
                    )
                    tile_window_visible = True
            elif event.ui_element == get_back_button:
                # Save link areas before exiting image viewing mode
                save_image_viewing_link_areas()
                image_viewing_mode = False
                if get_back_button is not None:
                    get_back_button.kill()
                    get_back_button = None
            elif event.ui_element == back_button:
                tile_system.go_back()
                bring_window_to_front()
            elif event.ui_element == forward_button:
                tile_system.go_forward()
                bring_window_to_front()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == tile_window:
                tile_window = None
                tile_window_visible = False
                tile_window_maximized = False
            elif event.ui_element == description_popup_window:
                description_popup_window = None
                description_text_box = None

        manager.process_events(event)

        # Check for clicks on links in the message box
        if event.type == pygame_gui.UI_TEXT_BOX_LINK_CLICKED:
            link_target = event.link_target
            handle_link_click(link_target)

        # Handle clicks on link areas and right-click on image area
        if event.type == pygame.MOUSEBUTTONDOWN:
            if 'image_rect' in locals() and image_rect.collidepoint(event.pos):
                x, y = event.pos
                rel_x = (x - image_rect.left) / image_rect.width
                rel_y = (y - image_rect.top) / image_rect.height
                found_area = None
                if image_viewing_mode:
                    image_path = image_viewing_images[image_viewing_index]
                    link_areas = image_viewing_link_areas.get(image_path, [])
                else:
                    current_tile = tile_system.get_current_tile()
                    image_index = tile_system.current_image_index
                    link_areas = current_tile.link_areas.get(image_index, [])
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
                            # Save link areas after assignment
                            if image_viewing_mode:
                                save_image_viewing_link_areas()
                            else:
                                tile_system.save_game_state()
                        assign_link_folder_mode = False
                        assign_link_folder_button.set_text("Assign Link Folder: OFF")
                        # Ensure no unintended drawing starts
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
                            # Save link areas after assignment
                            if image_viewing_mode:
                                save_image_viewing_link_areas()
                            else:
                                tile_system.save_game_state()
                        assign_json_area_mode = False
                        assign_json_area_button.set_text("Assign JSON Area: OFF")
                        # Ensure no unintended drawing starts
                        drawing_link_area = False
                        link_area_start_pos = None
                        link_area_rect = None
                    else:
                        if event.button == 1:  # Left-click
                            # Check if area has a link or json
                            if 'json' in found_area and found_area['json']:
                                json_file = found_area['json']
                                # Save current state to history
                                tile_system.save_current_state_to_history()
                                # Load the game state from the JSON file
                                tile_system.load_game_state_from_file(json_file)
                                bring_window_to_front()
                                # Exit image viewing mode if needed
                                image_viewing_mode = False
                                if get_back_button is not None:
                                    get_back_button.kill()
                                    get_back_button = None
                            elif 'link' in found_area and found_area['link']:
                                link = found_area['link']
                                if link and os.path.isdir(link):
                                    # Save current link areas before navigating
                                    if image_viewing_mode:
                                        save_image_viewing_link_areas()
                                    # Enter image viewing mode
                                    image_viewing_mode = True
                                    image_viewing_directory = link
                                    image_viewing_images = [os.path.join(link, f) for f in os.listdir(link)
                                                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
                                    image_viewing_images.sort()
                                    image_viewing_index = 0
                                    # Load link areas from the directory's link_areas.json
                                    load_image_viewing_link_areas()
                                    # Create the get back button
                                    if get_back_button is None:
                                        get_back_button = pygame_gui.elements.UIButton(
                                            relative_rect=pygame.Rect((10, 70), (50, 50)),
                                            text="Back",
                                            manager=manager
                                        )
                                else:
                                    messagebox.showwarning("Folder Link", "No valid folder link found for this area.")
                            else:
                                messagebox.showwarning("No Link Assigned", "No link or JSON assigned to this area.")
                        elif event.button == 3 and not (assign_link_folder_mode or assign_json_area_mode):  # Right-click
                            # Open context menu or handle right-click if needed
                            pass
                else:
                    if event.button == 3:  # Right-click on image area
                        # Create the description popup window at the mouse position
                        if description_popup_window is None:
                            window_width = 200  # Adjust as needed
                            window_height = window_width * 3  # 3:1 ratio
                            x, y = event.pos
                            # Ensure the window doesn't go off-screen
                            if x + window_width > screen_width:
                                x = screen_width - window_width
                            if y + window_height > screen_height:
                                y = screen_height - window_height
                            description_popup_window = pygame_gui.elements.UIWindow(
                                rect=pygame.Rect((x, y), (window_width, window_height)),
                                manager=manager,
                                window_display_title="Description",
                                object_id="#description_popup"
                            )
                            # Create a UITextBox inside the window
                            if image_viewing_mode:
                                # For image viewing mode, you might store descriptions differently
                                # For this example, we'll just display a placeholder
                                text_content = "Image Description"
                            else:
                                text_content = current_tile.text_content
                            description_text_box = pygame_gui.elements.UITextBox(
                                html_text=f"<font color='#000000'>{text_content}</font>",
                                relative_rect=pygame.Rect((0, 0), (window_width - 20, window_height - 20)),
                                manager=manager,
                                container=description_popup_window,
                                object_id="#description_text_box"
                            )
                            description_text_box.background_colour = pygame.Color("#FFFFFF")
                            description_text_box.text_colour = pygame.Color("#000000")
                            description_text_box.rebuild()

    # Revert the button text after the duration has passed
    if confirmation_button and pygame.time.get_ticks() > confirmation_end_time:
        confirmation_button.set_text(original_button_texts[confirmation_button])
        confirmation_button = None
        print("Button confirmation hidden")

    manager.update(time_delta)

    # Draw the image display area
    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 20)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    if image_viewing_mode:
        # Display the image from image_viewing_images
        if image_viewing_images:
            image_path = image_viewing_images[image_viewing_index]
            current_image = load_image(image_path)
            if current_image is not None:
                img_height, img_width = current_image.shape[:2]

                display_width, display_height = image_display_area.width, image_display_area.height

                # Calculate scale factors and new dimensions
                scale_factor = min(display_width / img_width, display_height / img_height)
                new_width = int(img_width * scale_factor)
                new_height = int(img_height * scale_factor)

                scaled_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                scaled_image_pygame = cv2_to_pygame(scaled_image)
                image_rect = scaled_image_pygame.get_rect(center=image_display_area.center)

                screen.blit(scaled_image_pygame, image_rect.topleft)

                # Draw link areas if show_link_areas is True
                if show_link_areas:
                    link_areas = image_viewing_link_areas.get(image_path, [])
                    for area in link_areas:
                        rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                        x0 = image_rect.left + rel_x0 * image_rect.width
                        y0 = image_rect.top + rel_y0 * image_rect.height
                        x1 = image_rect.left + rel_x1 * image_rect.width
                        y1 = image_rect.top + rel_y1 * image_rect.height
                        rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
                        pygame.draw.rect(screen, (255, 0, 0), rect, 2)  # Red rectangle

                # Draw the rectangle being drawn
                if drawing_link_area and link_area_rect is not None:
                    pygame.draw.rect(screen, (0, 255, 0), link_area_rect, 1)  # Green rectangle
    else:
        # Display the selected image if the current tile has images
        current_tile = tile_system.get_current_tile()
        if current_tile.image_filenames:
            current_image = current_tile.get_current_image(tile_system.current_image_index)
            if current_image is not None:
                img_height, img_width = current_image.shape[:2]

                display_width, display_height = image_display_area.width, image_display_area.height

                # Calculate scale factors and new dimensions
                scale_factor = min(display_width / img_width, display_height / img_height)
                new_width = int(img_width * scale_factor)
                new_height = int(img_height * scale_factor)

                scaled_image = cv2.resize(current_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                scaled_image_pygame = cv2_to_pygame(scaled_image)
                image_rect = scaled_image_pygame.get_rect(center=image_display_area.center)

                screen.blit(scaled_image_pygame, image_rect.topleft)

                # Draw link areas if show_link_areas is True
                if show_link_areas:
                    image_index = tile_system.current_image_index
                    link_areas = current_tile.link_areas.get(image_index, [])
                    for area in link_areas:
                        rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                        x0 = image_rect.left + rel_x0 * image_rect.width
                        y0 = image_rect.top + rel_y0 * image_rect.height
                        x1 = image_rect.left + rel_x1 * image_rect.width
                        y1 = image_rect.top + rel_y1 * image_rect.height
                        rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
                        pygame.draw.rect(screen, (255, 0, 0), rect, 2)  # Red rectangle

                # Draw the rectangle being drawn
                if drawing_link_area and link_area_rect is not None:
                    pygame.draw.rect(screen, (0, 255, 0), link_area_rect, 1)  # Green rectangle

    # Update the tile image if the tile window is visible and not in image viewing mode
    if tile_window is not None and not image_viewing_mode:
        tile_image.image.fill((0, 0, 0, 0))  # Clear the surface with transparency
        local_mouse_pos = pygame.mouse.get_pos()
        tile_image_rect = tile_image.get_abs_rect()
        local_mouse_pos = (local_mouse_pos[0] - tile_image_rect.left, local_mouse_pos[1] - tile_image_rect.top)
        # Calculate visible area
        visible_area = pygame.Rect(0, 0, tile_image_rect.width, tile_image_rect.height)
        # Draw the board centered on the player
        scaled_square_size = SQUARE_SIZE * zoom_factor
        offset_x = tile_image_rect.width // 2 - tile_system.player_pos[1] * scaled_square_size
        offset_y = tile_image_rect.height // 2 - tile_system.player_pos[0] * scaled_square_size
        tile_system.draw_board(local_mouse_pos, offset_x, offset_y, tile_image.image, visible_area, zoom_factor)
        tile_system.draw_player(offset_x, offset_y, tile_image.image, zoom_factor)
        tile_image_surface.blit(tile_image.image, (0, 0))  # Update the UIImage's surface

    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
