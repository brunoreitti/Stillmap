# tile_system_view.py
#
# A read-only version of tile_system.py for viewing maps without editing.
# All editing/creation functions are either removed or replaced with no-ops.

import os
import pygame
import json

##############################################################################
# Global Variables
##############################################################################

# Dictionary to store tiles with their positions as keys: {(row, col): Tile}
tiles = {}

# Player state
player_pos = [0, 0]           # Starting position of the player
player_direction = 0          # Starting direction (0-7, e.g., for 8-direction movement)
SQUARE_SIZE = 36              # Size of each map tile in pixels
map_offset = [0, 0]           # Used for panning/scrolling the map
sub_grid_visible = True       # Whether to show sub-grids within each tile

# Background image logic
background_image = None
background_image_path = None

# Vector lines (if you want to show them in the viewer)
vector_lines = []

##############################################################################
# Class Definitions
##############################################################################

class Tile:
    """
    Represents a single tile in the map grid.
    In the viewer version, any setters or editing logic are replaced with no-ops.
    """
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.active = True                    # Whether this tile is “active” or not
        self.directory = None                 # Directory containing images
        self.image_filenames = []             # List of image filenames
        self.json_file = None
        self.folder_link = None
        self.selected = False
        self.link_areas = {}                  # Key: image index, Value: list of link areas
        self.subgrid_occupied = [[False]*3 for _ in range(3)]
        # Make center subgrid square "occupied" (inactive)
        self.subgrid_occupied[1][1] = True

    def set_directory(self, directory):
        # No-op in viewer mode
        pass

    def clear_directory(self):
        # No-op in viewer mode
        pass

    def set_json_file(self, json_file):
        # No-op in viewer mode
        pass

    def clear_json_file(self):
        # No-op in viewer mode
        pass

    def toggle_active(self):
        # No-op in viewer mode
        pass

    def is_subgrid_square_free(self, sub_row, sub_col):
        return not self.subgrid_occupied[sub_row][sub_col]

    def set_subgrid_square_occupied(self, sub_row, sub_col, occupied=True):
        # In viewer mode, we can leave as is or no-op. Keeping it in case you want subgrid visuals.
        self.subgrid_occupied[sub_row][sub_col] = occupied

    def get_subgrid_square_center(self, sub_row, sub_col, offset_x, offset_y, zoom_factor):
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_pos_x = self.col * scaled_size + offset_x
        tile_pos_y = self.row * scaled_size + offset_y
        sub_square_size = scaled_size / 3
        center_x = tile_pos_x + sub_col * sub_square_size + sub_square_size / 2
        center_y = tile_pos_y + sub_row * sub_square_size + sub_square_size / 2
        return center_x, center_y

    def draw(self, surface, offset_x, offset_y, zoom_factor, mouse_pos):
        """
        Draw the tile’s outline (and optional sub-grid lines) in viewer mode.
        """
        scaled_size = SQUARE_SIZE * zoom_factor
        tile_pos_x = self.col * scaled_size + offset_x
        tile_pos_y = self.row * scaled_size + offset_y
        adjusted_rect = pygame.Rect(tile_pos_x, tile_pos_y, scaled_size, scaled_size)

        color = (0, 0, 0)  # black grid lines

        # Draw the tile border
        pygame.draw.rect(surface, color, adjusted_rect, 1)

        # Draw optional sub-grid lines
        if sub_grid_visible:
            sub_square_size = scaled_size / 3
            for i in range(1, 3):
                # horizontal sub-lines
                start_pos = (adjusted_rect.left, adjusted_rect.top + i * sub_square_size)
                end_pos = (adjusted_rect.right, adjusted_rect.top + i * sub_square_size)
                pygame.draw.line(surface, color, start_pos, end_pos, 1)

            for j in range(1, 3):
                # vertical sub-lines
                start_pos = (adjusted_rect.left + j * sub_square_size, adjusted_rect.top)
                end_pos = (adjusted_rect.left + j * sub_square_size, adjusted_rect.bottom)
                pygame.draw.line(surface, color, start_pos, end_pos, 1)

            # Highlight occupied subgrid squares
            for s_row in range(3):
                for s_col in range(3):
                    if self.subgrid_occupied[s_row][s_col]:
                        sub_rect = pygame.Rect(
                            adjusted_rect.left + s_col * sub_square_size,
                            adjusted_rect.top + s_row * sub_square_size,
                            sub_square_size,
                            sub_square_size
                        )
                        if s_row == 1 and s_col == 1:
                            # Center square, render differently if you want
                            pygame.draw.rect(surface, (128, 128, 128), sub_rect)
                        else:
                            pygame.draw.rect(surface, (0, 0, 255), sub_rect)

            # If mouse is over a sub-square, highlight it
            if adjusted_rect.collidepoint(mouse_pos):
                mouse_x, mouse_y = mouse_pos
                rel_x = mouse_x - adjusted_rect.left
                rel_y = mouse_y - adjusted_rect.top
                sub_col = int(rel_x // sub_square_size)
                sub_row = int(rel_y // sub_square_size)
                if 0 <= sub_row < 3 and 0 <= sub_col < 3:
                    if not self.subgrid_occupied[sub_row][sub_col]:
                        sub_rect = pygame.Rect(
                            adjusted_rect.left + sub_col * sub_square_size,
                            adjusted_rect.top + sub_row * sub_square_size,
                            sub_square_size,
                            sub_square_size
                        )
                        pygame.draw.rect(surface, (0, 255, 0), sub_rect, 2)

        # Draw a red outline if tile is "selected" (no-op in viewer mode)
        if self.selected:
            pygame.draw.rect(surface, (255, 0, 0), adjusted_rect, 3)

    def get_current_image(self, image_index):
        """
        In viewer mode, you can still display images if needed.
        """
        if self.directory and self.image_filenames:
            if 0 <= image_index < len(self.image_filenames):
                image_filename = self.image_filenames[image_index]
                image_path = os.path.join(self.directory, image_filename)
                # If you have a load_image function, call it here:
                try:
                    return load_image(image_path)
                except:
                    print(f"Failed to load image: {image_path}")
                    return None
        return None

    def add_link_area(self, image_index, area):
        # No-op or read-only in viewer mode
        pass


class VectorLine:
    """
    Represents a line between two subgrid squares in possibly different tiles.
    In viewer mode, we keep for display only.
    """
    def __init__(self, start_tile, start_subgrid_pos, end_tile=None, end_subgrid_pos=None):
        self.start_tile = start_tile
        self.start_subgrid_pos = start_subgrid_pos
        self.end_tile = end_tile
        self.end_subgrid_pos = end_subgrid_pos
        self.is_complete = end_tile is not None


##############################################################################
# Viewer Functions
##############################################################################

def initialize():
    """
    If needed, create a 'save' directory or do initial loading in viewer mode.
    You can also leave it empty if you prefer.
    """
    pass

def load_image(filepath):
    """
    Basic image loading for .png, .jpg, .jpeg, .bmp, .gif, etc.
    If you need PDF/SVG logic, you can replicate from your main code.
    """
    try:
        return pygame.image.load(filepath)
    except:
        print(f"Failed to load image {filepath}")
        return None

def draw_board(mouse_pos, offset_x, offset_y, surface, visible_area, zoom_factor):
    """
    Draws the background (if any) and the tiles in a read-only manner.
    """
    # Draw background image if it exists
    if background_image is not None:
        bg_width = background_image.get_width() * zoom_factor
        bg_height = background_image.get_height() * zoom_factor
        bg_image_scaled = pygame.transform.smoothscale(background_image, (int(bg_width), int(bg_height)))
        surface.blit(bg_image_scaled, (offset_x, offset_y))

    # Draw each tile
    for tile_key in tiles:
        tile = tiles[tile_key]
        tile.draw(surface, offset_x, offset_y, zoom_factor, mouse_pos)

def draw_player(offset_x, offset_y, surface, zoom_factor):
    """
    Draws the player’s arrow marker in read-only mode.
    """
    center_x = player_pos[1] * SQUARE_SIZE * zoom_factor + offset_x + SQUARE_SIZE * zoom_factor / 2
    center_y = player_pos[0] * SQUARE_SIZE * zoom_factor + offset_y + SQUARE_SIZE * zoom_factor / 2
    arrow_length = SQUARE_SIZE * zoom_factor / 2
    arrow_width = SQUARE_SIZE * zoom_factor / 4

    # Simple up arrow if direction == 0; adapt for other directions if needed
    # In your main code, you might handle 8 directions. Keep or adjust as you want.
    pygame.draw.polygon(surface, (255, 255, 255), [
        (center_x, center_y - arrow_length),
        (center_x - arrow_width, center_y),
        (center_x + arrow_width, center_y)
    ])

def reset_map_view():
    """
    Resets the map_offset to recenter the map around the player (or zero).
    """
    map_offset[0] = 0
    map_offset[1] = 0
    # If you want to recenter around the player, you could add logic here.

def set_background_image(image_surface, image_path_str):
    """
    Allows setting a background image in viewer mode (if you want).
    """
    global background_image, background_image_path
    background_image = image_surface
    background_image_path = image_path_str

def find_vector_with_end_point(tile, subgrid_pos):
    """
    If you display vector lines in the viewer, you can highlight them.
    """
    for vector in vector_lines:
        if vector.end_tile == tile and vector.end_subgrid_pos == subgrid_pos:
            return vector
    return None

def get_subgrid_square_at_pixel(x, y, offset_x, offset_y, zoom_factor):
    """
    Returns the tile and subgrid position at the given pixel, for highlighting.
    """
    scaled_size = SQUARE_SIZE * zoom_factor
    tile_col = int((x - offset_x) // scaled_size)
    tile_row = int((y - offset_y) // scaled_size)
    tile = tiles.get((tile_row, tile_col))
    if tile:
        rel_x = (x - offset_x) - tile_col * scaled_size
        rel_y = (y - offset_y) - tile_row * scaled_size
        sub_square_size = scaled_size / 3
        sub_col = int(rel_x // sub_square_size)
        sub_row = int(rel_y // sub_square_size)
        if 0 <= sub_row < 3 and 0 <= sub_col < 3:
            # Return None if center square is “inactive”
            if sub_row == 1 and sub_col == 1:
                return None, None
            return tile, (sub_row, sub_col)
    return None, None

##############################################################################
# No-Op Editing Functions
##############################################################################

def create_tile(row, col):
    # No-op
    pass

def delete_tile(row, col):
    # No-op
    pass

def get_tile(row, col):
    # If your viewer wants to look up a tile, we can keep this read-only.
    return tiles.get((row, col))

def get_current_tile():
    # If needed for referencing the player’s tile in viewer mode
    return tiles.get((player_pos[0], player_pos[1]))

def move_player(forward=True):
    # No-op
    pass

def rotate_player(key):
    # No-op
    pass

def move_player_to_tile(row, col):
    # No-op
    pass

def toggle_edit_mode():
    # No-op
    pass

def toggle_json_link_mode():
    # No-op
    pass

def toggle_clear_json_link_mode():
    # No-op
    pass

def remove_current_tile_folder():
    # No-op
    pass

def clear_current_tile_json_link():
    # No-op
    pass

def select_tile(row, col):
    # No-op
    pass

def deselect_tile():
    # No-op
    pass

def move_selected_tile_to(row, col):
    # No-op
    pass

def save_game_state():
    # No-op
    pass

def load_game_state():
    # No-op
    pass

def load_game_state_from_file(filepath):
    # No-op
    pass

def load_game_state_from_dict(game_state):
    # No-op
    pass

def serialize_game_state():
    # No-op
    pass

def save_current_state_to_history():
    # No-op
    pass

def go_back():
    # No-op
    pass

def go_forward():
    # No-op
    pass
