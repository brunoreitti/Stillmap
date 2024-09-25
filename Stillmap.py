import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, Menu
import os
import json
from PIL import Image, ImageTk
import subprocess

# Constants
BOARD_SIZE = 300  # Size of the board
ROWS, COLS = 9, 9  # Size of the board
SQUARE_SIZE = BOARD_SIZE // COLS  # Size of each square
NUM_BOARDS = 3  # Number of 9x9 boards in each direction (3x3 grid)

# Colors
COLOR1 = "#282A36"
COLOR2 = "#44475A"
WHITE = "#FFFFFF"
BLACK = "#000000"
BLUE = "#0000FF"
MAIN_BG_COLOR = "#44475A"
IMAGE_BG_COLOR = "#282A36"
HOVER_COLOR = "#00FF00"  # Green color for hover effect

# Initialize Tkinter root
class ViewalkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewalk Software")
        self.geometry("1200x800")
        try:
            self.iconbitmap('viewalk.ico')
        except:
            # If 'viewalk.ico' is not found, skip setting the icon
            pass

        # Game state variables
        self.player_pos = [ROWS // 2, COLS // 2]
        self.player_direction = 0  # Direction the player is facing (0-7)
        self.current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]
        self.current_loaded_file = None
        self.edit_mode = False
        self.json_link_mode = False
        self.clear_json_link_mode = False
        self.link_area_mode = False  # New mode for adding link areas

        # Game state directory
        self.save_directory = "saved_game_states"
        os.makedirs(self.save_directory, exist_ok=True)

        # Create frames
        self.create_frames()

        # Create widgets
        self.create_widgets()

        # Create the board with Tile objects
        self.create_boards()

        # Bind events
        self.bind_events()

        # Start the update loop
        self.update_loop()

    def create_frames(self):
        # Main frame to hold canvas and buttons
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for drawing
        self.canvas = tk.Canvas(self.main_frame, bg=MAIN_BG_COLOR)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Buttons frame
        self.buttons_frame = tk.Frame(self.main_frame)
        self.buttons_frame.pack(side=tk.TOP, fill=tk.X)

    def create_widgets(self):
        # Buttons in the buttons_frame
        self.load_button = tk.Button(
            self.buttons_frame, text="Load Game",
            command=self.load_game_state)
        self.load_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.save_button = tk.Button(
            self.buttons_frame, text="Save Game",
            command=self.save_game_state)
        self.save_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.edit_button = tk.Button(
            self.buttons_frame, text="Edit Mode: OFF",
            command=self.toggle_edit_mode)
        self.edit_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.image_button = tk.Button(
            self.buttons_frame, text="Select Image Folder",
            command=self.select_image_folder)
        self.image_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.delete_button = tk.Button(
            self.buttons_frame, text="Remove Image Folder",
            command=self.remove_current_tile_folder)
        self.delete_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.edit_text_button = tk.Button(
            self.buttons_frame, text="Edit Description",
            command=self.edit_text)
        self.edit_text_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.json_link_button = tk.Button(
            self.buttons_frame, text="Manage JSON Links: OFF",
            command=self.toggle_json_link_mode)
        self.json_link_button.pack(pady=5, padx=5, side=tk.LEFT)

        self.clear_json_link_button = tk.Button(
            self.buttons_frame, text="Clear JSON Links: OFF",
            command=self.toggle_clear_json_link_mode)
        self.clear_json_link_button.pack(pady=5, padx=5, side=tk.LEFT)

        # Add the "Show Description" button
        self.show_description_button = tk.Button(
            self.buttons_frame, text="Show Description",
            command=self.show_description)
        self.show_description_button.pack(pady=5, padx=5, side=tk.LEFT)

        # New button to toggle Link Area Mode
        self.add_link_area_button = tk.Button(
            self.buttons_frame, text="Add Link Area: OFF",
            command=self.toggle_link_area_mode)
        self.add_link_area_button.pack(pady=5, padx=5, side=tk.LEFT)

        # Button to clear link areas
        self.clear_link_areas_button = tk.Button(
            self.buttons_frame, text="Clear Link Areas",
            command=self.clear_link_areas)
        self.clear_link_areas_button.pack(pady=5, padx=5, side=tk.LEFT)

    def create_boards(self):
        # Create the boards
        self.boards = [[[
            [Tile(row, col, SQUARE_SIZE, self.canvas)
             for col in range(COLS)]
            for row in range(ROWS)]
            for _ in range(NUM_BOARDS)]
            for _ in range(NUM_BOARDS)]

    def bind_events(self):
        # Keyboard events
        self.bind("<Key>", self.on_key_press)
        # Mouse events on canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_button_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_button_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        # Resize event
        self.canvas.bind("<Configure>", self.on_canvas_resize)

    def on_key_press(self, event):
        if event.keysym == 'Up':
            self.move_player(forward=True)
        elif event.keysym == 'Down':
            self.move_player(forward=False)
        elif event.keysym == 'Left':
            self.rotate_player(left=True)
        elif event.keysym == 'Right':
            self.rotate_player(left=False)
        elif event.char == 'e':
            self.toggle_edit_mode()
        elif event.char == 'j':
            self.toggle_json_link_mode()
        elif event.char == 'c':
            self.toggle_clear_json_link_mode()
        elif event.char == 'i':
            self.show_image_popup()  # Press 'i' to show image popup
        elif event.char == 'v':
            self.open_folder_link()  # Press 'v' to open folder link

    def on_canvas_resize(self, event):
        # Update image display area on canvas resize
        self.canvas.delete("image_display_area")
        self.canvas.create_rectangle(
            10, 10, event.width - 20, event.height - 20,
            fill=IMAGE_BG_COLOR, outline="", tags="image_display_area"
        )

    def update_loop(self):
        try:
            # Main update loop
            self.draw_canvas()
        except Exception as e:
            print(f"Exception in update_loop: {e}")
        self.after(50, self.update_loop)  # Adjust the delay as needed

    def draw_canvas(self):
        try:
            # Clear the canvas
            self.canvas.delete("all")
            # Draw the image display area
            self.canvas.create_rectangle(
                10, 10, self.canvas.winfo_width() - 20,
                self.canvas.winfo_height() - 20, fill=IMAGE_BG_COLOR,
                outline=""
            )
            # Draw the current image if available
            self.draw_current_image()
            # Draw the board
            self.draw_board()
            # Draw the player
            self.draw_player()
            # Draw the link areas on top
            self.draw_link_areas()
            # Update hover state
            self.update_hover_state()
        except Exception as e:
            print(f"Exception in draw_canvas: {e}")

    def draw_current_image(self):
        try:
            current_tile = self.get_current_tile()
            if current_tile.image_filenames:
                if len(current_tile.image_filenames) == 8:
                    # Map player's direction to image index
                    image_index = self.player_direction
                else:
                    # If fewer images, default to the first image
                    image_index = 0
                current_image = current_tile.get_current_image(
                    image_index)
                if current_image:
                    # Resize image to fit the display area
                    img_width, img_height = current_image.size
                    display_width = self.canvas.winfo_width() - 40
                    display_height = self.canvas.winfo_height() - 40
                    scale_factor = min(
                        display_width / img_width,
                        display_height / img_height)
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    resized_image = current_image.resize(
                        (new_width, new_height), Image.LANCZOS)
                    self.photo_image = ImageTk.PhotoImage(resized_image)
                    # Calculate position
                    x = (display_width - new_width) // 2 + 10
                    y = (display_height - new_height) // 2 + 10
                    self.canvas.create_image(
                        x, y, anchor=tk.NW, image=self.photo_image)
                    # Store the image area coordinates
                    self.image_area_coords = (
                        x, y, x + new_width, y + new_height)
                else:
                    print("No current image to display.")
            else:
                print("No image filenames available for the current tile.")
        except Exception as e:
            print(f"Exception in draw_current_image: {e}")

    def draw_board(self):
        try:
            # Adjusted offset since sidebar is removed
            offset_x = self.canvas.winfo_width() - BOARD_SIZE - 10
            offset_y = 60
            board = self.get_current_board()
            for row in board:
                for tile in row:
                    tile.draw(
                        self.canvas, offset_x, offset_y,
                        self.edit_mode, self.json_link_mode,
                        self.clear_json_link_mode)
        except Exception as e:
            print(f"Exception in draw_board: {e}")

    def draw_player(self):
        try:
            # Adjusted offset since sidebar is removed
            offset_x = self.canvas.winfo_width() - BOARD_SIZE - 10
            offset_y = 60
            player_rect = (
                self.player_pos[1] * SQUARE_SIZE + offset_x,
                self.player_pos[0] * SQUARE_SIZE + offset_y,
                SQUARE_SIZE, SQUARE_SIZE,
            )
            x, y, w, h = player_rect
            # Draw player rectangle
            self.canvas.create_rectangle(
                x, y, x + w, y + h, fill=COLOR2)
            # Draw direction arrow
            center_x = x + w / 2
            center_y = y + h / 2
            arrow_length = SQUARE_SIZE // 2
            direction = self.player_direction
            points = []
            if direction == 0:  # Up
                points = [
                    center_x, center_y - arrow_length,
                    center_x - 10, center_y + 10,
                    center_x + 10, center_y + 10]
            elif direction == 1:  # Up-right
                points = [
                    center_x + arrow_length, center_y - arrow_length,
                    center_x - 10, center_y + 10,
                    center_x + 10, center_y + 10]
            elif direction == 2:  # Right
                points = [
                    center_x + arrow_length, center_y,
                    center_x - 10, center_y - 10,
                    center_x - 10, center_y + 10]
            elif direction == 3:  # Down-right
                points = [
                    center_x + arrow_length, center_y + arrow_length,
                    center_x - 10, center_y + 10,
                    center_x + 10, center_y - 10]
            elif direction == 4:  # Down
                points = [
                    center_x, center_y + arrow_length,
                    center_x - 10, center_y - 10,
                    center_x + 10, center_y - 10]
            elif direction == 5:  # Down-left
                points = [
                    center_x - arrow_length, center_y + arrow_length,
                    center_x + 10, center_y + 10,
                    center_x - 10, center_y - 10]
            elif direction == 6:  # Left
                points = [
                    center_x - arrow_length, center_y,
                    center_x + 10, center_y - 10,
                    center_x + 10, center_y + 10]
            elif direction == 7:  # Up-left
                points = [
                    center_x - arrow_length, center_y - arrow_length,
                    center_x + 10, center_y + 10,
                    center_x - 10, center_y + 10]
            if points:
                self.canvas.create_polygon(points, fill=WHITE)
            else:
                # If points are empty, draw a small circle
                self.canvas.create_oval(
                    center_x - 5, center_y - 5,
                    center_x + 5, center_y + 5, fill=WHITE)
        except Exception as e:
            print(f"Exception in draw_player: {e}")

    def draw_link_areas(self):
        try:
            current_tile = self.get_current_tile()
            if not current_tile.link_areas:
                return
            self.link_area_rects = []
            for idx, area in enumerate(current_tile.link_areas):
                rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                x0 = self.image_area_coords[0] + rel_x0 * (
                    self.image_area_coords[2]
                    - self.image_area_coords[0])
                y0 = self.image_area_coords[1] + rel_y0 * (
                    self.image_area_coords[3]
                    - self.image_area_coords[1])
                x1 = self.image_area_coords[0] + rel_x1 * (
                    self.image_area_coords[2]
                    - self.image_area_coords[0])
                y1 = self.image_area_coords[1] + rel_y1 * (
                    self.image_area_coords[3]
                    - self.image_area_coords[1])
                # Create a semi-transparent fill using stipple
                rect_id = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline='', fill='gray12', stipple='gray25',
                    tags=f"link_area_{idx}"
                )
                # Bind events to the rectangle
                self.canvas.tag_bind(
                    rect_id, "<Enter>",
                    lambda e, idx=idx: self.on_link_area_hover(idx, True))
                self.canvas.tag_bind(
                    rect_id, "<Leave>",
                    lambda e, idx=idx: self.on_link_area_hover(idx, False))
                self.canvas.tag_bind(
                    rect_id, "<Button-1>",
                    lambda e, idx=idx: self.open_link_area_by_index(idx))
                # Store rectangle info
                self.link_area_rects.append({
                    'id': rect_id,
                    'area_index': idx,
                    'coords': (x0, y0, x1, y1)
                })
        except Exception as e:
            print(f"Exception in draw_link_areas: {e}")

    def on_link_area_hover(self, idx, is_hover):
        try:
            rect = self.link_area_rects[idx]
            rect_id = rect['id']
            if is_hover:
                self.canvas.itemconfig(rect_id, outline=HOVER_COLOR, width=2)
            else:
                self.canvas.itemconfig(rect_id, outline='', width=1)
        except Exception as e:
            print(f"Exception in on_link_area_hover: {e}")

    def update_hover_state(self):
        # This method can be kept empty or used for additional hover logic
        pass  # Since hover is handled via tag bindings

    def on_canvas_click(self, event):
        # The click is already handled via tag_bind on rectangles
        # This can be used for other click functionalities if needed
        pass  # No action needed here for link areas

    def handle_board_click(self, event):
        # Adjusted offset since sidebar is removed
        offset_x = self.canvas.winfo_width() - BOARD_SIZE - 10
        offset_y = 60
        x = event.x - offset_x
        y = event.y - offset_y
        if x < 0 or y < 0:
            return
        col = int(x // SQUARE_SIZE)
        row = int(y // SQUARE_SIZE)
        if 0 <= row < ROWS and 0 <= col < COLS:
            tile = self.get_current_board()[row][col]
            if self.edit_mode:
                tile.toggle_active()
            elif self.json_link_mode:
                selected_file = filedialog.askopenfilename(
                    title="Select a JSON file",
                    initialdir=self.save_directory,
                    filetypes=[("JSON files", "*.json")])
                if selected_file:
                    tile.set_json_file(selected_file)
            elif self.clear_json_link_mode:
                tile.clear_json_file()
                tile.color = WHITE  # Reset color to indicate no link
            else:
                # In normal mode, maybe select the tile or perform actions
                pass

    def on_canvas_button_press(self, event):
        if self.link_area_mode:
            # Check if click is within image area
            if hasattr(self, 'image_area_coords'):
                x0, y0, x1, y1 = self.image_area_coords
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    # Record the starting position
                    self.link_area_start = (event.x, event.y)
                    # Create a temporary rectangle
                    self.temp_rect = self.canvas.create_rectangle(
                        event.x, event.y, event.x, event.y,
                        outline='red', dash=(2, 2))
                else:
                    self.link_area_start = None
            else:
                self.link_area_start = None

    def on_canvas_mouse_move(self, event):
        if self.link_area_mode and hasattr(
                self, 'temp_rect') and self.link_area_start:
            # Update the temporary rectangle
            self.canvas.coords(
                self.temp_rect, self.link_area_start[0],
                self.link_area_start[1], event.x, event.y)

    def on_canvas_button_release(self, event):
        if self.link_area_mode and hasattr(
                self, 'temp_rect') and self.link_area_start:
            # Finalize the rectangle
            x0, y0 = self.link_area_start
            x1, y1 = event.x, event.y
            # Remove the temporary rectangle
            self.canvas.delete(self.temp_rect)
            delattr(self, 'temp_rect')

            # Ensure coordinates are in the correct order
            x0, x1 = sorted([x0, x1])
            y0, y1 = sorted([y0, y1])

            # Store the rectangle coordinates relative to the image
            if hasattr(self, 'image_area_coords'):
                img_x0, img_y0, img_x1, img_y1 = self.image_area_coords
                # Ensure the rectangle is within the image area
                x0 = max(x0, img_x0)
                y0 = max(y0, img_y0)
                x1 = min(x1, img_x1)
                y1 = min(y1, img_y1)
                # Convert to relative coordinates (0 to 1)
                rel_x0 = (x0 - img_x0) / (img_x1 - img_x0)
                rel_y0 = (y0 - img_y0) / (img_y1 - img_y0)
                rel_x1 = (x1 - img_x0) / (img_x1 - img_x0)
                rel_y1 = (y1 - img_y0) / (img_y1 - img_y0)
                # Store in current tile
                current_tile = self.get_current_tile()
                # Create a new link area without a link yet
                current_tile.add_link_area({
                    'coords': (rel_x0, rel_y0, rel_x1, rel_y1),
                    'link': None})
            else:
                messagebox.showwarning(
                    "Add Link Area",
                    "No image available to add link area.")
            self.link_area_start = None
            self.draw_canvas()  # Redraw to show the new link area

    def on_canvas_right_click(self, event):
        if self.link_area_mode:
            # Check if right-click is on a link area
            for rect_info in getattr(self, 'link_area_rects', []):
                x0, y0, x1, y1 = rect_info['coords']
                area_index = rect_info['area_index']
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    # Right-clicked inside this link area
                    self.show_context_menu(event, area_index)
                    return  # No need to check other areas
        else:
            # Handle other right-click events if necessary
            pass

    def show_context_menu(self, event, area_index):
        # Create a context menu
        context_menu = Menu(self, tearoff=0)
        context_menu.add_command(
            label="Add link to this",
            command=lambda idx=area_index: self.add_link_to_area(idx))
        context_menu.post(event.x_root, event.y_root)

    def add_link_to_area(self, area_index):
        directory = filedialog.askdirectory()
        if directory:
            current_tile = self.get_current_tile()
            area = current_tile.link_areas[area_index]
            area['link'] = directory
            print(f"Assigned link to area: {area}")
            self.draw_canvas()  # Redraw to reflect the added link

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.edit_button.config(
            text=f"Edit Mode: {'ON' if self.edit_mode else 'OFF'}")
        # Turn off other modes
        if self.edit_mode:
            self.link_area_mode = False
            self.json_link_mode = False
            self.clear_json_link_mode = False
            self.add_link_area_button.config(text="Add Link Area: OFF")
            self.json_link_button.config(text="Manage JSON Links: OFF")
            self.clear_json_link_button.config(
                text="Clear JSON Links: OFF")

    def toggle_json_link_mode(self):
        self.json_link_mode = not self.json_link_mode
        self.clear_json_link_mode = False
        self.json_link_button.config(
            text=f"Manage JSON Links: {'ON' if self.json_link_mode else 'OFF'}")
        self.clear_json_link_button.config(
            text="Clear JSON Links: OFF")
        # Turn off other modes
        if self.json_link_mode:
            self.edit_mode = False
            self.link_area_mode = False
            self.edit_button.config(text="Edit Mode: OFF")
            self.add_link_area_button.config(text="Add Link Area: OFF")

    def toggle_clear_json_link_mode(self):
        self.clear_json_link_mode = not self.clear_json_link_mode
        self.json_link_mode = False
        self.clear_json_link_button.config(
            text=f"Clear JSON Links: {'ON' if self.clear_json_link_mode else 'OFF'}")
        self.json_link_button.config(text="Manage JSON Links: OFF")
        # Turn off other modes
        if self.clear_json_link_mode:
            self.edit_mode = False
            self.link_area_mode = False
            self.edit_button.config(text="Edit Mode: OFF")
            self.add_link_area_button.config(text="Add Link Area: OFF")

    def toggle_link_area_mode(self):
        self.link_area_mode = not self.link_area_mode
        self.add_link_area_button.config(
            text=f"Add Link Area: {'ON' if self.link_area_mode else 'OFF'}")
        # Turn off other modes
        if self.link_area_mode:
            self.edit_mode = False
            self.json_link_mode = False
            self.clear_json_link_mode = False
            self.edit_button.config(text="Edit Mode: OFF")
            self.json_link_button.config(text="Manage JSON Links: OFF")
            self.clear_json_link_button.config(
                text="Clear JSON Links: OFF")

    def clear_link_areas(self):
        current_tile = self.get_current_tile()
        current_tile.clear_link_areas()
        self.draw_canvas()  # Redraw to reflect the changes

    def move_player(self, forward=True):
        new_pos = self.player_pos[:]
        direction = self.player_direction if forward else (
            self.player_direction + 4) % 8  # Adjust for backward

        if direction == 0:  # Up
            new_pos[0] -= 1
        elif direction == 1:  # Up-right
            new_pos[0] -= 1
            new_pos[1] += 1
        elif direction == 2:  # Right
            new_pos[1] += 1
        elif direction == 3:  # Down-right
            new_pos[0] += 1
            new_pos[1] += 1
        elif direction == 4:  # Down
            new_pos[0] += 1
        elif direction == 5:  # Down-left
            new_pos[0] += 1
            new_pos[1] -= 1
        elif direction == 6:  # Left
            new_pos[1] -= 1
        elif direction == 7:  # Up-left
            new_pos[0] -= 1
            new_pos[1] -= 1

        new_board = self.current_board[:]
        print(f"Attempting to move to position: {new_pos} on board: "
              f"{new_board}")

        # Check for board transitions
        if new_pos[0] < 0:
            if self.current_board[0] > 0:
                new_pos[0] = ROWS - 1
                new_board[0] -= 1
            else:
                new_pos[0] = 0
        elif new_pos[0] >= ROWS:
            if self.current_board[0] < NUM_BOARDS - 1:
                new_pos[0] = 0
                new_board[0] += 1
            else:
                new_pos[0] = ROWS - 1
        if new_pos[1] < 0:
            if self.current_board[1] > 0:
                new_pos[1] = COLS - 1
                new_board[1] -= 1
            else:
                new_pos[1] = 0
        elif new_pos[1] >= COLS:
            if self.current_board[1] < NUM_BOARDS - 1:
                new_pos[1] = 0
                new_board[1] += 1
            else:
                new_pos[1] = COLS - 1

        # Check if the new position is in an active tile
        if new_board != self.current_board:
            if self.boards[new_board[0]][new_board[1]][new_pos[0]][
                    new_pos[1]].active:
                self.current_board[:] = new_board
                self.player_pos[:] = new_pos
                print(f"Moved to new board: {new_board}, new position: "
                      f"{new_pos}")
            else:
                print("Cannot move to inactive tile.")
        else:
            if self.get_current_board()[new_pos[0]][new_pos[1]].active:
                self.player_pos[:] = new_pos
                print(f"Moved to position: {new_pos}")
            else:
                print("Cannot move to inactive tile.")

    def rotate_player(self, left=True):
        if left:
            self.player_direction = (self.player_direction - 1) % 8
        else:
            self.player_direction = (self.player_direction + 1) % 8
        self.current_image_index = self.player_direction  # Sync image index

    def select_image_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            current_tile = self.get_current_tile()
            current_tile.set_directory(directory)
            self.current_image_index = self.player_direction

    def remove_current_tile_folder(self):
        current_tile = self.get_current_tile()
        current_tile.clear_directory()
        self.draw_canvas()  # Redraw to reflect the changes

    def edit_text(self):
        current_tile = self.get_current_tile()
        new_text = simpledialog.askstring(
            "Edit Description", "Enter new text:",
            initialvalue=current_tile.text_content)
        if new_text is not None:
            current_tile.text_content = new_text

    def show_description(self):
        current_tile = self.get_current_tile()
        description_window = tk.Toplevel(self)
        description_window.title("Tile Description")
        description_window.geometry("400x300")

        text_widget = tk.Text(description_window, wrap=tk.WORD)
        text_widget.pack(expand=True, fill=tk.BOTH)

        # Insert text content
        text_content = current_tile.text_content or "No description."
        text_widget.insert(tk.END, text_content)

        # Add folder link if exists
        if current_tile.folder_link:
            text_widget.insert(tk.END, "\nFolder Link:\n")
            text_widget.insert(
                tk.END, current_tile.folder_link + "\n", ("link",))
            text_widget.tag_configure(
                "link", foreground="blue", underline=True)
            text_widget.tag_bind(
                "link", "<Button-1>", lambda e: self.open_folder_link())

        # Display link areas and their links
        if current_tile.link_areas:
            text_widget.insert(tk.END, "\nLink Areas:\n")
            for idx, area in enumerate(current_tile.link_areas):
                link = area.get('link')
                if link:
                    tag_name = f"link_area_{idx}"
                    text_widget.insert(
                        tk.END, f"Area {idx + 1}: {link}\n", (tag_name,))
                    # Bind each link to open the folder
                    text_widget.tag_configure(
                        tag_name, foreground="blue", underline=True)
                    text_widget.tag_bind(
                        tag_name, "<Button-1>",
                        lambda e, idx=idx:
                        self.open_link_area_by_index(idx))
                else:
                    text_widget.insert(
                        tk.END, f"Area {idx + 1}: No link assigned\n")

        text_widget.config(state=tk.DISABLED)

    def open_folder_link(self):
        current_tile = self.get_current_tile()
        link = current_tile.folder_link
        if link and os.path.isdir(link):
            try:
                # Replace 'python' with 'python3' if necessary
                subprocess.Popen(['python', 'image_viewer.py', link])
            except Exception as e:
                print(f"Error opening folder link: {e}")
        else:
            messagebox.showwarning(
                "Folder Link", "No valid folder link found for this tile.")

    def open_link_area(self, area):
        link = area.get('link')
        print(f"Attempting to open link: {link}")
        if link and os.path.isdir(link):
            try:
                subprocess.Popen(['python', 'image_viewer.py', link])
            except Exception as e:
                print(f"Error opening folder link: {e}")
        else:
            print(f"No valid folder link found for this area: {link}")
            messagebox.showwarning(
                "Folder Link", "No valid folder link found for this area.")

    def open_link_area_by_index(self, area_index):
        current_tile = self.get_current_tile()
        area = current_tile.link_areas[area_index]
        self.open_link_area(area)

    def save_game_state(self):
        if self.current_loaded_file is None:
            filename = simpledialog.askstring(
                "Save Game", "Enter the save file name:")
            if not filename:
                messagebox.showwarning(
                    "Save Game", "Save file name cannot be empty.")
                return
            self.current_loaded_file = os.path.join(
                self.save_directory, f"{filename}.json")

        game_state = {
            "player_position": self.player_pos,
            "player_direction": self.player_direction,
            "current_board": self.current_board,
            "tiles": []
        }

        for board_row in self.boards:
            for board in board_row:
                for row in board:
                    for tile in row:
                        tile_data = {
                            "row": tile.row,
                            "col": tile.col,
                            "board_row": self.boards.index(board_row),
                            "board_col": board_row.index(board),
                            "active": tile.active,
                            "directory": tile.directory,
                            "json_file": tile.json_file,
                            "text_content": tile.text_content,
                            "folder_link": tile.folder_link,
                            "link_areas": tile.link_areas  # Save link areas
                        }
                        game_state["tiles"].append(tile_data)

        with open(self.current_loaded_file, "w") as file:
            json.dump(game_state, file, indent=4)
        print("Game state saved.")

    def load_game_state(self):
        files = [f for f in os.listdir(
            self.save_directory) if f.endswith(".json")]
        if not files:
            messagebox.showwarning(
                "Load Game", "No saved games found.")
            return

        selected_file = filedialog.askopenfilename(
            title="Select a saved game",
            initialdir=self.save_directory,
            filetypes=[("JSON files", "*.json")]
        )

        if not selected_file:
            return

        self.current_loaded_file = selected_file
        self.load_game_state_from_file(selected_file)

    def load_game_state_from_file(self, filepath):
        try:
            with open(filepath, "r") as file:
                game_state = json.load(file)

            self.player_pos = game_state["player_position"]
            self.player_direction = game_state["player_direction"]
            self.current_board = game_state["current_board"]

            # Validate player position and current board
            self.player_pos[0] = max(
                0, min(self.player_pos[0], ROWS - 1))
            self.player_pos[1] = max(
                0, min(self.player_pos[1], COLS - 1))
            self.current_board[0] = max(
                0, min(self.current_board[0], NUM_BOARDS - 1))
            self.current_board[1] = max(
                0, min(self.current_board[1], NUM_BOARDS - 1))

            # Clear the current game state
            for board_row in self.boards:
                for board in board_row:
                    for row in board:
                        for tile in row:
                            tile.active = True
                            tile.clear_directory()
                            tile.clear_json_file()
                            tile.text_content = ""
                            tile.folder_link = None
                            tile.clear_link_areas()

            for tile_data in game_state["tiles"]:
                board_row = tile_data["board_row"]
                board_col = tile_data["board_col"]
                row = tile_data["row"]
                col = tile_data["col"]
                tile = self.boards[board_row][board_col][row][col]
                tile_active = tile_data.get("active", True)
                tile.active = bool(tile_active)
                tile.set_directory(tile_data.get("directory"))
                tile.json_file = tile_data.get("json_file")
                tile.text_content = tile_data.get("text_content", "")
                tile.folder_link = tile_data.get("folder_link", None)
                tile.link_areas = tile_data.get("link_areas", [])

            self.current_image_index = self.player_direction
            print("Game state loaded.")

        except Exception as e:
            print(f"Error loading game state: {e}")
            messagebox.showerror(
                "Load Game", f"Error loading game state: {e}")

    def get_current_board(self):
        return self.boards[self.current_board[0]][self.current_board[1]]

    def get_current_tile(self):
        return self.get_current_board()[self.player_pos[0]][
            self.player_pos[1]]

    def draw_link_areas(self):
        try:
            current_tile = self.get_current_tile()
            if not current_tile.link_areas:
                return
            self.link_area_rects = []
            for idx, area in enumerate(current_tile.link_areas):
                rel_x0, rel_y0, rel_x1, rel_y1 = area['coords']
                x0 = self.image_area_coords[0] + rel_x0 * (
                    self.image_area_coords[2]
                    - self.image_area_coords[0])
                y0 = self.image_area_coords[1] + rel_y0 * (
                    self.image_area_coords[3]
                    - self.image_area_coords[1])
                x1 = self.image_area_coords[0] + rel_x1 * (
                    self.image_area_coords[2]
                    - self.image_area_coords[0])
                y1 = self.image_area_coords[1] + rel_y1 * (
                    self.image_area_coords[3]
                    - self.image_area_coords[1])
                # Create a semi-transparent fill using stipple
                rect_id = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline='', fill='gray12', stipple='gray25',
                    tags=f"link_area_{idx}"
                )
                # Bind events to the rectangle
                self.canvas.tag_bind(
                    rect_id, "<Enter>",
                    lambda e, idx=idx: self.on_link_area_hover(idx, True))
                self.canvas.tag_bind(
                    rect_id, "<Leave>",
                    lambda e, idx=idx: self.on_link_area_hover(idx, False))
                self.canvas.tag_bind(
                    rect_id, "<Button-1>",
                    lambda e, idx=idx: self.open_link_area_by_index(idx))
                # Store rectangle info
                self.link_area_rects.append({
                    'id': rect_id,
                    'area_index': idx,
                    'coords': (x0, y0, x1, y1)
                })
        except Exception as e:
            print(f"Exception in draw_link_areas: {e}")

    def on_link_area_hover(self, idx, is_hover):
        try:
            rect = self.link_area_rects[idx]
            rect_id = rect['id']
            if is_hover:
                self.canvas.itemconfig(rect_id, outline=HOVER_COLOR, width=2)
            else:
                self.canvas.itemconfig(rect_id, outline='', width=1)
        except Exception as e:
            print(f"Exception in on_link_area_hover: {e}")

    def update_hover_state(self):
        # This method can be kept empty or used for additional hover logic
        pass  # Since hover is handled via tag bindings

    def on_canvas_click(self, event):
        # The click is already handled via tag_bind on rectangles
        # This can be used for other click functionalities if needed
        pass  # No action needed here for link areas

    def handle_board_click(self, event):
        # Adjusted offset since sidebar is removed
        offset_x = self.canvas.winfo_width() - BOARD_SIZE - 10
        offset_y = 60
        x = event.x - offset_x
        y = event.y - offset_y
        if x < 0 or y < 0:
            return
        col = int(x // SQUARE_SIZE)
        row = int(y // SQUARE_SIZE)
        if 0 <= row < ROWS and 0 <= col < COLS:
            tile = self.get_current_board()[row][col]
            if self.edit_mode:
                tile.toggle_active()
            elif self.json_link_mode:
                selected_file = filedialog.askopenfilename(
                    title="Select a JSON file",
                    initialdir=self.save_directory,
                    filetypes=[("JSON files", "*.json")])
                if selected_file:
                    tile.set_json_file(selected_file)
            elif self.clear_json_link_mode:
                tile.clear_json_file()
                tile.color = WHITE  # Reset color to indicate no link
            else:
                # In normal mode, maybe select the tile or perform actions
                pass

    def show_image_popup(self):
        # Open a popup window to display the image
        try:
            current_tile = self.get_current_tile()
            if current_tile.image_filenames:
                if len(current_tile.image_filenames) == 8:
                    image_index = self.player_direction
                else:
                    image_index = 0
                current_image = current_tile.get_current_image(
                    image_index)
                if current_image:
                    image_window = tk.Toplevel(self)
                    image_window.title("Image Viewer")
                    image_window.geometry("800x600")
                    # Resize image to fit the popup window
                    img_width, img_height = current_image.size
                    scale_factor = min(800 / img_width, 600 / img_height)
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    resized_image = current_image.resize(
                        (new_width, new_height), Image.LANCZOS)
                    photo_image = ImageTk.PhotoImage(resized_image)
                    image_label = tk.Label(
                        image_window, image=photo_image)
                    image_label.image = photo_image  # Keep reference
                    image_label.pack(expand=True, fill=tk.BOTH)
                else:
                    messagebox.showinfo(
                        "Image Viewer", "No image to display.")
            else:
                messagebox.showinfo(
                    "Image Viewer",
                    "No images available for the current tile.")
        except Exception as e:
            print(f"Exception in show_image_popup: {e}")

# Define the Tile class
class Tile:
    def __init__(self, row, col, size, canvas):
        self.row = row
        self.col = col
        self.size = size
        self.canvas = canvas
        self.rect = None
        self.color = COLOR2
        self.active = True  # Tile is active (can be moved to)
        self.directory = None
        self.image_filenames = []
        self.json_file = None
        self.text_content = ""
        self.folder_link = None
        self.link_areas = []  # List of dictionaries with 'coords' and 'link'

    def draw(self, canvas, offset_x, offset_y, edit_mode,
             json_link_mode, clear_json_link_mode):
        x = self.col * self.size + offset_x
        y = self.row * self.size + offset_y
        x1 = x + self.size
        y1 = y + self.size
        if self.json_file:
            fill_color = BLUE
        else:
            fill_color = COLOR1 if self.active else BLACK
        self.rect = canvas.create_rectangle(
            x, y, x1, y1, fill=fill_color, outline=COLOR2)
        # If in edit mode and mouse over tile, change color
        if edit_mode or json_link_mode or clear_json_link_mode:
            canvas.tag_bind(
                self.rect, "<Enter>",
                lambda e: canvas.itemconfig(self.rect, fill=BLACK))
            canvas.tag_bind(
                self.rect, "<Leave>",
                lambda e: canvas.itemconfig(self.rect, fill=fill_color))

    def toggle_active(self):
        self.active = not self.active

    def set_directory(self, directory):
        self.directory = directory
        if directory:
            self.image_filenames = [
                f for f in os.listdir(directory) if f.lower().endswith(
                    ('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            self.image_filenames.sort()  # Ensure consistent order
        else:
            self.image_filenames = []

    def clear_directory(self):
        self.directory = None
        self.image_filenames = []

    def set_json_file(self, json_file):
        self.json_file = json_file

    def clear_json_file(self):
        self.json_file = None

    def add_link_area(self, area):
        self.link_areas.append(area)

    def clear_link_areas(self):
        self.link_areas = []

    def get_current_image(self, index):
        if not self.directory or index >= len(self.image_filenames):
            return None
        filepath = os.path.join(self.directory,
                                self.image_filenames[index])
        print(f"Loading image at: {filepath}")  # Debug statement
        image = self.load_image(filepath)
        if image is not None:
            return image
        return None

    def load_image(self, filepath):
        try:
            image = Image.open(filepath)
            return image
        except Exception as e:
            print(f"Failed to load image {filepath}: {e}")
            return None

# Run the application
if __name__ == "__main__":
    app = ViewalkApp()
    app.mainloop()
