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

def update_message_box():
    current_tile = tile_system.get_current_tile()
    message_box.html_text = f"<font color='#000000'>{current_tile.text_content}</font>"

    # Add the folder link to the message box if it exists
    if current_tile.folder_link:
        message_box.html_text += f"<br><a href='{current_tile.folder_link}'><font color='#0000FF'>{os.path.basename(current_tile.folder_link)}</font></a>"

    message_box.rebuild()  # Rebuild to apply changes

# Function to handle adding a folder and displaying a link in the text box
def add_folder():
    directory = open_file_explorer()
    if directory:
        current_tile = tile_system.get_current_tile()
        current_tile.set_folder_link(directory)
        update_message_box()
        bring_window_to_front()  # Ensure window is brought to the front after loading

# Function to handle clicking on a link in the message box
def handle_link_click(link):
    if os.path.isdir(link):
        subprocess.Popen(['explorer', link])

# Assign functions in tile_system that need access to functions in main.py
tile_system.update_message_box = update_message_box
tile_system.bring_window_to_front = bring_window_to_front
tile_system.load_image = load_image

# Set the SQUARE_SIZE and initialize the tile system
SQUARE_SIZE = 36  # Set square size to 36 pixels
tile_system.SQUARE_SIZE = SQUARE_SIZE  # Set in tile_system
tile_system.BOARD_SIZE = SQUARE_SIZE * tile_system.COLS  # Set BOARD_SIZE in tile_system
tile_system.initialize()  # Initialize the boards now that SQUARE_SIZE is set

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
num_buttons = 9
button_width = (screen_width - (num_buttons + 1) * button_padding) // num_buttons

# List of button texts
button_texts = ["Load Game", "Save Game", "Edit Mode", "Select Image Folder", "Remove Image Folder", "Add Folder Link", "Edit Description", "Manage JSON Links", "Clear JSON Links"]
buttons = []
for i, text in enumerate(button_texts):
    button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((button_padding + i * (button_width + button_padding), (bottom_bar_height - button_height) // 2), (button_width, button_height)),
        text=text,
        manager=manager,
        container=bottom_bar_panel
    )
    buttons.append(button)

# Assign buttons to variables
load_button = buttons[0]
save_button = buttons[1]
edit_button = buttons[2]
image_button = buttons[3]
delete_button = buttons[4]
add_folder_button = buttons[5]
edit_text_button = buttons[6]
json_link_button = buttons[7]
clear_json_link_button = buttons[8]

# Add a scrollable text area to display text content
message_box_height = 120
message_box_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((10, screen_height - bottom_bar_height - message_box_height - 20), (screen_width - 20, message_box_height)),
    manager=manager,
    object_id="#message_box_panel"
)
message_box_panel.background_colour = pygame.Color("#FFFFFF")  # Set the background color to white

message_box = pygame_gui.elements.UITextBox(
    html_text="<font color='#D3D3D3'>no text description in image</font>",
    relative_rect=pygame.Rect((0, 0), (screen_width - 20, message_box_height)),
    container=message_box_panel,
    manager=manager,
    object_id="#message_box"
)
message_box.background_colour = pygame.Color("#FFFFFF")  # Set the background color to white
message_box.text_colour = pygame.Color("#000000")  # Set the text color to black
message_box.rebuild()  # Ensure the text box is rebuilt with the new settings

# Adjust tile window size to match the tileboard size
tile_window_width = SQUARE_SIZE * tile_system.COLS  # 36 * 9 = 324
tile_window_height = SQUARE_SIZE * tile_system.ROWS  # 36 * 9 = 324

# Create the tile window in the top right corner
tile_window = pygame_gui.elements.UIWindow(
    rect=pygame.Rect((screen_width - tile_window_width - 10, 10), (tile_window_width, tile_window_height)),
    manager=manager,
    window_display_title="Tile System",
    object_id="#tile_window"
)

# Create a UIImage inside the tile window to display the tiles
tile_image_surface = pygame.Surface((tile_window_width, tile_window_height))
tile_image = pygame_gui.elements.UIImage(
    relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_window_height)),
    image_surface=tile_image_surface,
    manager=manager,
    container=tile_window
)

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

# Create the restore button in the top right corner
restore_tile_window_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((screen_width - 50, 10), (40, 40)),
    text="↓",  # Downward arrow
    manager=manager,
    object_id="#restore_button"
)

tile_window_visible = True  # Flag to track if the tile window is visible

# Main game loop
running = True
confirmation_button = None  # To store the current confirmation button
confirmation_end_time = 0  # To track when to revert the button text

while running:
    time_delta = clock.tick(60) / 1000.0  # Limits the frame rate to 60 FPS
    screen.fill(MAIN_BG_COLOR)  # Fill the main area with the main background color

    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            # Update screen dimensions
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
            # Update bottom bar position and size
            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))
            # Update message box position and size
            message_box_panel.set_relative_position((10, screen_height - bottom_bar_height - message_box_height - 20))
            message_box_panel.set_dimensions((screen_width - 20, message_box_height))
            message_box.set_dimensions((screen_width - 20, message_box_height))
            # Update restore button position
            restore_tile_window_button.set_relative_position((screen_width - 50, 10))
            # Update tile window position if it's visible
            if tile_window is not None:
                tile_window.set_relative_position((screen_width - tile_window_width - 10, 10))
        elif event.type == pygame.KEYDOWN:
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
                tile_system.move_player(forward=True)
                update_message_box()
            elif event.key == pygame.K_DOWN:
                tile_system.move_player(forward=False)
                update_message_box()
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                tile_system.rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if tile_window is not None:
                # Get the mouse position relative to the tile window
                tile_window_rect = tile_window.get_abs_rect()
                tile_image_rect = tile_image.get_abs_rect()
                if tile_image_rect.collidepoint(event.pos):
                    local_pos = (event.pos[0] - tile_image_rect.left, event.pos[1] - tile_image_rect.top)
                    offset_x = 0
                    offset_y = 0
                    board = tile_system.get_current_board()
                    for row in board:
                        for tile in row:
                            adjusted_rect = tile.rect.move(offset_x, offset_y)
                            if adjusted_rect.collidepoint(local_pos):
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
                                    tile.color = WHITE  # Reset color to white to indicate no link
                                    update_message_box()  # Update the message box
                                break
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == load_button:
                tile_system.load_game_state()
                update_message_box()
            elif event.ui_element == save_button:
                tile_system.save_game_state()
            elif event.ui_element == edit_button:
                tile_system.toggle_edit_mode()
                edit_button.set_text(f"Edit Mode: {'ON' if tile_system.edit_mode else 'OFF'}")
            elif event.ui_element == image_button:
                directory = open_file_explorer()
                if directory:
                    current_tile = tile_system.get_current_tile()
                    current_tile.set_directory(directory)
                    tile_system.current_image_index = 0  # Reset image index when a new folder is assigned
                    bring_window_to_front()  # Ensure window is brought to the front after loading
            elif event.ui_element == delete_button:
                current_tile = tile_system.get_current_tile()
                current_tile.clear_directory()
                update_message_box()  # Update the message box after removing the folder
                print(f"Removed folder association from the current tile.")
            elif event.ui_element == add_folder_button:
                add_folder()
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
                    update_message_box()  # Update the message box with the new text
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
                    tile_image_surface = pygame.Surface((tile_window_width, tile_window_height))
                    tile_image = pygame_gui.elements.UIImage(
                        relative_rect=pygame.Rect((0, 0), (tile_window_width, tile_window_height)),
                        image_surface=tile_image_surface,
                        manager=manager,
                        container=tile_window
                    )
                    tile_window_visible = True
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == tile_window:
                tile_window = None
                tile_window_visible = False

        manager.process_events(event)

        # Check for clicks on links in the message box
        if event.type == pygame_gui.UI_TEXT_BOX_LINK_CLICKED:
            link_target = event.link_target
            handle_link_click(link_target)

    # Revert the button text after the duration has passed
    if confirmation_button and pygame.time.get_ticks() > confirmation_end_time:
        confirmation_button.set_text(original_button_texts[confirmation_button])
        confirmation_button = None
        print("Button confirmation hidden")

    manager.update(time_delta)

    # Draw the image display area
    image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - message_box_height - 40)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

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

    # Update the tile image if the tile window is visible
    if tile_window is not None:
        tile_image.image.fill((0, 0, 0))  # Clear the surface
        local_mouse_pos = pygame.mouse.get_pos()
        tile_image_rect = tile_image.get_abs_rect()
        local_mouse_pos = (local_mouse_pos[0] - tile_image_rect.left, local_mouse_pos[1] - tile_image_rect.top)
        tile_system.draw_board(local_mouse_pos, 0, 0, tile_image.image)
        tile_system.draw_player(0, 0, tile_image.image)
        tile_image_surface.blit(tile_image.image, (0, 0))  # Update the UIImage's surface

    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
