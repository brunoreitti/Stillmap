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
import math
from pygame import Color
from tkinter import Tk, filedialog
import json  # For saving/loading thumbnails_data

pygame.init()
Tk().withdraw()  # Hide the main Tkinter window

##############################################################################
# Where we store thumbnail data
##############################################################################
THUMBNAILS_SAVE_FILE = "thumbnails_data.json"

def save_thumbnails_data(thumbnails_data):
    """
    Saves 'thumbnails_data' to a JSON file.
    """
    try:
        with open(THUMBNAILS_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(thumbnails_data, f, indent=4)
        print(f"Thumbnails data saved to '{THUMBNAILS_SAVE_FILE}'.")
    except Exception as e:
        print(f"Error saving thumbnails data: {e}")

def load_thumbnails_data():
    """
    Loads thumbnail data from JSON if it exists. Otherwise returns an empty list.
    """
    if not os.path.exists(THUMBNAILS_SAVE_FILE):
        print("No existing thumbnail data file found. Starting with an empty list.")
        return []
    try:
        with open(THUMBNAILS_SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Thumbnails data loaded from '{THUMBNAILS_SAVE_FILE}'.")
        return data
    except Exception as e:
        print(f"Error loading thumbnails data: {e}")
        return []

##############################################################################
# SVG and image loading helpers
##############################################################################

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
    if image is None:
        return None
    if len(image.shape) == 3 and image.shape[2] == 4:
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
        try:
            return pygame.image.load(filepath)
        except:
            print(f"Failed to load image {filepath}")
            return None

##############################################################################
# Load background SVG
##############################################################################
BACKGROUND_SVG_PATH = 'craybg2.svg'
background_cv2 = load_svg_image(BACKGROUND_SVG_PATH)
if background_cv2 is None:
    print(f"Could not load background image: {BACKGROUND_SVG_PATH}")
    sys.exit(1)

background_surface = cv2_to_pygame(background_cv2)

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

##############################################################################
# Bottom bar: "Back to Main" and "Save" buttons
##############################################################################
bottom_bar_height = 60
bottom_bar_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, screen_height - bottom_bar_height), (screen_width, bottom_bar_height)),
    manager=manager,
    object_id="#bottom_bar"
)

button_width = 120
button_height = 40
button_spacing = 20
total_width_for_two = button_width * 2 + button_spacing

back_button_x = (screen_width - total_width_for_two) // 2
back_button_y = (bottom_bar_height - button_height) // 2

back_to_main_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((back_button_x, back_button_y), (button_width, button_height)),
    text="Back to Main",
    manager=manager,
    container=bottom_bar_panel
)

save_button_x = back_button_x + button_width + button_spacing
save_button_y = back_button_y
save_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((save_button_x, save_button_y), (button_width, button_height)),
    text="Save",
    manager=manager,
    container=bottom_bar_panel
)

##############################################################################
# Thumbnails display area
##############################################################################
image_display_area = pygame.Rect(10, 10, screen_width - 20, screen_height - bottom_bar_height - 80)
thumbnails_panel = pygame_gui.elements.UIPanel(
    relative_rect=image_display_area,
    manager=manager,
    object_id="#thumbnails_panel"
)

page_nav_height = 40
page_nav_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect(10, image_display_area.bottom + 10, image_display_area.width, page_nav_height),
    manager=manager,
    object_id="#page_nav_panel"
)

thumb_padding = 10
per_row = 6
num_rows = 4
per_page = per_row * num_rows  # 24 per page

current_page = 0
popup_window = None
popup_associated_thumb = None
name_popup_window = None
name_text_entry = None

first_page_button = None
prev_page_button = None
next_page_button = None
last_page_button = None
page_buttons = []

##############################################################################
# DOUBLE-CLICK SUPPORT
##############################################################################
double_click_delay = 500  # milliseconds
last_click_time = 0
last_clicked_thumbnail = None

##############################################################################
# Load any previously saved thumbnails
##############################################################################
thumbnails_data = load_thumbnails_data()

# UI model: list of 6-tuples: (element, is_real, slash_button, img_ui, title_panel, title_label)
thumbnail_boxes = []

##############################################################################
# Thumbnail-building helper functions
##############################################################################

def load_pygame_image(filepath, width, height):
    try:
        img = pygame.image.load(filepath).convert_alpha()
        img = pygame.transform.smoothscale(img, (width, height))
        return img
    except:
        print(f"Failed to load or scale image {filepath}")
        return None

def create_add_box():
    # The "+" box is a separate UI element
    add_box = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((0,0), (100,50)),
        text="+",
        manager=manager,
        container=thumbnails_panel
    )
    return add_box

def create_real_box(data):
    panel = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect((0,0), (100,50)),
        manager=manager,
        container=thumbnails_panel,
        object_id="#real_box_panel"
    )

    panel.background_colour = Color(150, 150, 200)
    panel.rebuild()

    img_ui = None
    if data.get("img_path"):
        temp_surf = pygame.Surface((1,1), pygame.SRCALPHA)
        temp_surf.fill((0,0,0,0))
        img_ui = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((0,0),(50,50)),
            manager=manager,
            container=panel,
            image_surface=temp_surf
        )

    title_panel = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect((0,0),(50,40)),
        manager=manager,
        container=panel,
        object_id="#title_panel"
    )
    title_panel.background_colour = Color(255,255,255)
    title_panel.rebuild()

    title_text = data.get("name", "") if data.get("name") else ""
    title_label = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((5,0),(40,40)),
        text=title_text,
        manager=manager,
        container=title_panel
    )

    # The slash button is a separate UI element on top of the panel
    slash_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((0,0), (20,20)),
        text="/",
        manager=manager,
        container=panel
    )

    return panel, slash_button, img_ui, title_panel, title_label

def rebuild_thumbnail_boxes():
    # Clear old UI
    for (elem, ireal, sbtn, img_ui, tpanel, tlabel) in thumbnail_boxes:
        elem.kill()
        if sbtn:
            sbtn.kill()
        if img_ui:
            img_ui.kill()
        if tpanel:
            tpanel.kill()
        if tlabel:
            tlabel.kill()
    thumbnail_boxes.clear()

    # Build new UI for each saved thumbnail
    for d in thumbnails_data:
        panel, slash_button, img_ui, title_panel, title_label = create_real_box(d)
        thumbnail_boxes.append((panel, True, slash_button, img_ui, title_panel, title_label))

    # Add the "+" box at the end
    add_box = create_add_box()
    thumbnail_boxes.append((add_box, False, None, None, None, None))

def calculate_thumbnail_layout():
    panel_rect = thumbnails_panel.get_relative_rect()
    panel_width = panel_rect.width
    thumbnail_width = (panel_width - thumb_padding*(per_row+1)) // per_row
    thumbnail_height = int(thumbnail_width * 9/16)
    return thumbnail_width, thumbnail_height

def layout_thumbnails():
    for (element, is_real, slash_btn, img_ui, tpanel, tlabel) in thumbnail_boxes:
        element.hide()
        if slash_btn:
            slash_btn.hide()
        if img_ui:
            img_ui.hide()
        if tpanel:
            tpanel.hide()
        if tlabel:
            tlabel.hide()

    thumbnail_width, thumbnail_height = calculate_thumbnail_layout()

    total_thumbs = len(thumbnails_data) + 1  # one for the + box
    start_index = current_page * per_page
    end_index = start_index + per_page
    visible_boxes = thumbnail_boxes[start_index:end_index]

    x_start = thumb_padding
    y_start = thumb_padding
    x = x_start
    y = y_start
    count = 0

    for (element, is_real, slash_btn, img_ui, tpanel, tlabel) in visible_boxes:
        element.set_dimensions((thumbnail_width, thumbnail_height))
        element.set_relative_position((x, y))
        element.show()

        if tpanel and tlabel:
            tpanel.set_dimensions((thumbnail_width, 40))
            tpanel.set_relative_position((0, thumbnail_height - 40))
            tpanel.show()
            tlabel.set_dimensions((thumbnail_width - 10, 40))
            tlabel.set_relative_position((5,0))
            tlabel.show()

        if is_real:
            # This is a real thumbnail
            global_index = thumbnail_boxes.index((element, is_real, slash_btn, img_ui, tpanel, tlabel))
            data_index = global_index
            data = thumbnails_data[data_index]
            if img_ui and data.get("img_path"):
                img_surface = load_pygame_image(data["img_path"], thumbnail_width, thumbnail_height)
                if img_surface:
                    img_ui.set_dimensions((thumbnail_width, thumbnail_height))
                    img_ui.set_relative_position((0,0))
                    img_ui.set_image(img_surface)
                    img_ui.show()
                else:
                    img_ui.hide()

        if slash_btn:
            slash_btn_width = 20
            slash_btn_height = 20
            slash_x = thumbnail_width - slash_btn_width - 5
            slash_y = 5
            slash_btn.set_dimensions((slash_btn_width, slash_btn_height))
            slash_btn.set_relative_position((slash_x, slash_y))
            slash_btn.show()
            slash_btn.change_layer(999)

        x += thumbnail_width + thumb_padding
        count += 1
        if count >= per_row:
            count = 0
            x = x_start
            y += thumbnail_height + thumb_padding

    update_page_navigation()

def update_page_navigation():
    global page_buttons, first_page_button, prev_page_button, next_page_button, last_page_button
    for btn in page_buttons:
        btn.kill()
    page_buttons.clear()
    if first_page_button:
        first_page_button.kill()
        first_page_button = None
    if prev_page_button:
        prev_page_button.kill()
        prev_page_button = None
    if next_page_button:
        next_page_button.kill()
        next_page_button = None
    if last_page_button:
        last_page_button.kill()
        last_page_button = None

    total_thumbs = len(thumbnails_data) + 1
    total_pages = math.ceil(total_thumbs / per_page) if total_thumbs > 0 else 1
    button_width = 40
    button_height = 30
    spacing = 5
    total_fixed_buttons = 4
    total_buttons = total_fixed_buttons + total_pages
    number_of_gaps = total_buttons - 1
    total_width = total_buttons * button_width + number_of_gaps * spacing
    panel_width = page_nav_panel.get_relative_rect().width
    start_x = (panel_width - total_width) // 2
    y_pos = (page_nav_panel.get_relative_rect().height - button_height)//2

    def create_nav_button(x, text):
        return pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x, y_pos, button_width, button_height),
            text=text,
            manager=manager,
            container=page_nav_panel
        )

    current_x = start_x
    first_page_button = create_nav_button(current_x, "<<")
    current_x += button_width + spacing
    prev_page_button = create_nav_button(current_x, "<")
    current_x += button_width + spacing

    for p in range(total_pages):
        ptext = str(p+1)
        btn = create_nav_button(current_x, ptext)
        current_x += button_width + spacing
        page_buttons.append(btn)

    next_page_button = create_nav_button(current_x, ">")
    current_x += button_width + spacing
    last_page_button = create_nav_button(current_x, ">>")

    current_page_index = current_page
    if 0 <= current_page_index < len(page_buttons):
        page_buttons[current_page_index].set_text("["+str(current_page_index+1)+"]")

##############################################################################
# Popup logic
##############################################################################
def open_popup(associated_button, associated_panel):
    """
    We'll pass in slash_button, panel so we know which panel to modify.
    """
    global popup_window, popup_associated_thumb
    if popup_window is not None:
        popup_window.kill()
        popup_window = None
        popup_associated_thumb = None

    slash_abs_rect = associated_button.get_abs_rect()
    popup_x = slash_abs_rect.right + 10
    popup_y = slash_abs_rect.top
    window_width = 200
    window_height = 190  # Enough room for the new button
    popup_window_rect = pygame.Rect(popup_x, popup_y, window_width, window_height)

    popup_window_obj = pygame_gui.elements.UIWindow(
        rect=popup_window_rect,
        manager=manager,
        window_display_title="Options",
        object_id="#popup_window",
        resizable=False,
        draggable=False
    )

    change_name_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, 10), (180, 30)),
        text="Change Name",
        manager=manager,
        container=popup_window_obj
    )

    thumbnail_image_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, 50), (180, 30)),
        text="Thumbnail Image",
        manager=manager,
        container=popup_window_obj
    )

    delete_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, 90), (180, 30)),
        text="Delete Thumbnail",
        manager=manager,
        container=popup_window_obj
    )

    link_to_map_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, 130), (180, 30)),
        text="Link To Map",
        manager=manager,
        container=popup_window_obj
    )

    popup_window = popup_window_obj
    popup_associated_thumb = associated_panel

def goto_page(page_index):
    global current_page
    total_thumbs = len(thumbnails_data) + 1
    total_pages = math.ceil(total_thumbs / per_page) if total_thumbs > 0 else 1
    current_page = max(0, min(page_index, total_pages - 1))
    layout_thumbnails()

def add_new_thumbnail():
    thumbnails_data.append({"img_path": None, "name": None})
    rebuild_thumbnail_boxes()
    goto_page(current_page)

def delete_thumbnail(panel_to_delete):
    for i, (elem, ireal, sbtn, img_ui, tpanel, tlabel) in enumerate(thumbnail_boxes[:-1]):
        if elem == panel_to_delete:
            thumbnails_data.pop(i)
            rebuild_thumbnail_boxes()
            goto_page(current_page)
            return

def change_thumbnail_image(panel_to_change):
    for i, (elem, ireal, sbtn, img_ui, tpanel, tlabel) in enumerate(thumbnail_boxes[:-1]):
        if elem == panel_to_change:
            filetypes = [('Image files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif'), ('All files', '*.*')]
            filename = filedialog.askopenfilename(
                title='Select an image',
                initialdir=os.getcwd(),
                filetypes=filetypes
            )
            if filename:
                thumbnails_data[i]['img_path'] = filename
                rebuild_thumbnail_boxes()
                goto_page(current_page)
            return

def open_name_popup(panel_to_change):
    global name_popup_window, name_text_entry, popup_associated_thumb
    if name_popup_window is not None:
        name_popup_window.kill()
        name_popup_window = None
        name_text_entry = None

    win_width = 300
    win_height = 150
    center_x = screen_width // 2 - win_width // 2
    center_y = screen_height // 2 - win_height // 2

    name_popup_window = pygame_gui.elements.UIWindow(
        rect=pygame.Rect(center_x, center_y, win_width, win_height),
        manager=manager,
        window_display_title="Change Name",
        resizable=False,
        draggable=False
    )

    name_text_entry = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect((10,10),(280,30)),
        manager=manager,
        container=name_popup_window
    )

    ok_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10,50),(80,30)),
        text="OK",
        manager=manager,
        container=name_popup_window
    )

    cancel_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((100,50),(80,30)),
        text="Cancel",
        manager=manager,
        container=name_popup_window
    )

    popup_associated_thumb = panel_to_change

def set_thumbnail_name(panel_to_change, new_name):
    for i, (elem, ireal, sbtn, img_ui, tpanel, tlabel) in enumerate(thumbnail_boxes[:-1]):
        if elem == panel_to_change:
            thumbnails_data[i]['name'] = new_name
            rebuild_thumbnail_boxes()
            goto_page(current_page)
            return

# Build + layout the UI
rebuild_thumbnail_boxes()
goto_page(0)

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
            manager.set_window_resolution((screen_width, screen_height))

            bottom_bar_panel.set_relative_position((0, screen_height - bottom_bar_height))
            bottom_bar_panel.set_dimensions((screen_width, bottom_bar_height))

            total_width_for_two = button_width * 2 + button_spacing
            back_button_x = (screen_width - total_width_for_two) // 2
            back_button_y = (bottom_bar_height - button_height) // 2
            back_to_main_button.set_relative_position((back_button_x, back_button_y))

            save_button_x = back_button_x + button_width + button_spacing
            save_button_y = back_button_y
            save_button.set_relative_position((save_button_x, save_button_y))

            image_display_area.width = screen_width - 20
            image_display_area.height = screen_height - bottom_bar_height - 80
            thumbnails_panel.set_relative_position((image_display_area.left, image_display_area.top))
            thumbnails_panel.set_dimensions((image_display_area.width, image_display_area.height))

            page_nav_panel.set_relative_position((10, image_display_area.bottom + 10))
            page_nav_panel.set_dimensions((image_display_area.width, 40))

            goto_page(current_page)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            # 1) "Back to Main"
            if event.ui_element == back_to_main_button:
                subprocess.Popen(["python", "main.py"])
                pygame.quit()
                sys.exit()

            # 2) "Save"
            elif event.ui_element == save_button:
                save_thumbnails_data(thumbnails_data)

            # 3) Pagination
            elif event.ui_element in page_buttons:
                idx = page_buttons.index(event.ui_element)
                goto_page(idx)
            elif first_page_button and event.ui_element == first_page_button:
                goto_page(0)
            elif prev_page_button and event.ui_element == prev_page_button:
                goto_page(current_page - 1)
            elif next_page_button and event.ui_element == next_page_button:
                goto_page(current_page + 1)
            elif last_page_button and event.ui_element == last_page_button:
                total_thumbs = len(thumbnails_data) + 1
                total_pages = math.ceil(total_thumbs / per_page) if total_thumbs > 0 else 1
                goto_page(total_pages - 1)

            # 4) Check if the user pressed the "+" box or slash button
            else:
                # Because the last item in thumbnail_boxes is the + box, we can check:
                add_box_tuple = thumbnail_boxes[-1]  # (add_box, False, None, None, None, None)
                add_box_element = add_box_tuple[0]

                # If it's the plus box:
                if event.ui_element == add_box_element:
                    print("Pressed the + box => add_new_thumbnail()")
                    add_new_thumbnail()
                else:
                    # Maybe a slash button?
                    for (panel, is_real, slash_btn, img_ui, tpanel, tlabel) in thumbnail_boxes:
                        if is_real and slash_btn and event.ui_element == slash_btn:
                            print("Pressed slash button => open popup")
                            open_popup(slash_btn, panel)
                            break

                # If a popup is open, handle the popup window's buttons
                if popup_window is not None:
                    if event.ui_element.text == "Delete Thumbnail" and popup_associated_thumb is not None:
                        delete_thumbnail(popup_associated_thumb)
                        popup_window.kill()
                        popup_window = None
                        popup_associated_thumb = None

                    elif event.ui_element.text == "Thumbnail Image" and popup_associated_thumb is not None:
                        change_thumbnail_image(popup_associated_thumb)
                        if popup_window:
                            popup_window.kill()
                            popup_window = None
                            popup_associated_thumb = None

                    elif event.ui_element.text == "Change Name" and popup_associated_thumb is not None:
                        open_name_popup(popup_associated_thumb)
                        popup_window.kill()
                        popup_window = None

                    elif event.ui_element.text == "Link To Map" and popup_associated_thumb is not None:
                        filetypes = [('JSON files', '*.json'), ('All files', '*.*')]
                        selected_json = filedialog.askopenfilename(
                            title="Select a JSON file for Map",
                            initialdir=os.getcwd(),
                            filetypes=filetypes
                        )
                        if selected_json:
                            for i, (elem, ireal, sbtn, img_ui, tpanel, tlabel) in enumerate(thumbnail_boxes[:-1]):
                                if elem == popup_associated_thumb:
                                    thumbnails_data[i]["linked_map"] = selected_json
                                    save_thumbnails_data(thumbnails_data)
                                    print(f"Assigned JSON to thumbnail {i}: {selected_json}")
                                    break

                        if popup_window:
                            popup_window.kill()
                            popup_window = None
                            popup_associated_thumb = None

                # If a name popup is open, handle its buttons
                elif name_popup_window is not None:
                    if event.ui_element.text == "OK" and popup_associated_thumb is not None and name_text_entry is not None:
                        new_name = name_text_entry.get_text()
                        set_thumbnail_name(popup_associated_thumb, new_name)
                        name_popup_window.kill()
                        name_popup_window = None
                        name_text_entry = None
                        popup_associated_thumb = None

                    elif event.ui_element.text == "Cancel":
                        if name_popup_window:
                            name_popup_window.kill()
                            name_popup_window = None
                            name_text_entry = None
                            popup_associated_thumb = None

        # Single/double click logic for real thumbnail panels
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                current_time = pygame.time.get_ticks()
                mouse_pos = event.pos

                # We'll see if the user clicked a "panel" that is is_real = True
                clicked_index = None
                for i, (element, is_real, slash_btn, img_ui, tpanel, tlabel) in enumerate(thumbnail_boxes):
                    # Only treat it as a panel click if is_real
                    if is_real:
                        if element.get_abs_rect().collidepoint(mouse_pos):
                            clicked_index = i
                            break

                if clicked_index is not None:
                    time_diff = current_time - last_click_time
                    if last_clicked_thumbnail == clicked_index and time_diff < double_click_delay:
                        # Double-click on a real thumbnail
                        print(f"Double-click on thumbnail {clicked_index}, time diff = {time_diff} ms")
                        if clicked_index < len(thumbnails_data):
                            if "linked_map" in thumbnails_data[clicked_index]:
                                linked_json = thumbnails_data[clicked_index]["linked_map"]
                                if os.path.isfile(linked_json):
                                    print(f"Launching view_page.py with {linked_json}")
                                    subprocess.Popen(["python", "view_page.py", linked_json])
                                else:
                                    print("Linked JSON file not found or invalid.")
                            else:
                                print("No 'linked_map' assigned to this thumbnail.")
                        # Reset double-click detection
                        last_clicked_thumbnail = None
                        last_click_time = 0
                    else:
                        # Single click on a real thumbnail
                        print(f"Single click on thumbnail {clicked_index} time diff={time_diff} ms")
                        last_clicked_thumbnail = clicked_index
                        last_click_time = current_time
                else:
                    # Possibly we clicked outside or on the + box or slash button,
                    # but those are handled in UI_BUTTON_PRESSED, so do nothing here.
                    pass

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == popup_window:
                popup_window = None
                popup_associated_thumb = None
            elif event.ui_element == name_popup_window:
                name_popup_window = None
                name_text_entry = None
                popup_associated_thumb = None

        manager.process_events(event)

    manager.update(time_delta)

    # ========== DRAW ==========

    screen.fill(MAIN_BG_COLOR)
    pygame.draw.rect(screen, IMAGE_BG_COLOR, image_display_area)

    # Scale background to fit image_display_area
    img_width, img_height = background_surface.get_size()
    image_display_width = image_display_area.width
    image_display_height = image_display_area.height
    scale_factor = min(image_display_width / img_width, image_display_height / img_height)
    if scale_factor <= 0:
        scale_factor = 1
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    if new_width > 0 and new_height > 0:
        scaled_background = pygame.transform.smoothscale(background_surface, (new_width, new_height))
        background_rect = scaled_background.get_rect(center=image_display_area.center)
        screen.blit(scaled_background, background_rect)

    manager.draw_ui(screen)

    # Check hover for clickable items
    mouse_pos = pygame.mouse.get_pos()
    is_over_something_clickable = False
    # Check slash buttons, real thumbnail panels, plus box
    for (element, is_real, slash_btn, img_ui, tpanel, tlabel) in thumbnail_boxes:
        if element.get_abs_rect().collidepoint(mouse_pos):
            is_over_something_clickable = True
            break
        if slash_btn and slash_btn.get_abs_rect().collidepoint(mouse_pos):
            is_over_something_clickable = True
            break

    if is_over_something_clickable:
        pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_ARROW)

    pygame.display.flip()

pygame.quit()
sys.exit()
