import pygame
import ctypes
import sys

# Initialize Pygame
pygame.init()

# Create a resizable Pygame window
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Checkerboard Game")

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

# Constants
BOARD_SIZE = 300  # Size of the board
ROWS, COLS = 9, 9  # Size of the board
SQUARE_SIZE = BOARD_SIZE // COLS  # Size of each square
SIDEBAR_WIDTH = BOARD_SIZE + 20  # Width of the sidebar to house the board and button
NUM_BOARDS = 3  # Number of 9x9 boards in each direction (3x3 grid)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 0, 255)
MAIN_BG_COLOR = (50, 50, 50)
SIDEBAR_BG_COLOR = (150, 150, 150)

# Player's starting position in the center of the middle board
player_pos = [ROWS // 2, COLS // 2]
player_direction = 0

# Track which 9x9 board the player is currently in (starting in the center of the larger grid)
current_board = [NUM_BOARDS // 2, NUM_BOARDS // 2]

# Edit mode toggle
edit_mode = False

class Tile:
    def __init__(self, row, col, size):
        self.row = row
        self.col = col
        self.size = size
        self.rect = pygame.Rect(col * size, row * size, size, size)
        self.color = WHITE
        self.active = True  # Tile is active (can be moved to)

    def draw(self, screen, mouse_pos, offset_x, offset_y):
        adjusted_rect = self.rect.move(offset_x, offset_y)
        if adjusted_rect.collidepoint(mouse_pos) and edit_mode:
            self.color = LIGHT_GRAY
        else:
            self.color = WHITE if self.active else DARK_GRAY
        pygame.draw.rect(screen, self.color, adjusted_rect)
        pygame.draw.rect(screen, BLACK, adjusted_rect, 1)

    def toggle_active(self):
        self.active = not self.active
        self.color = WHITE if self.active else BLACK

# Create the board with Tile objects for each 9x9 grid in the 3x3 grid
boards = [[[Tile(row, col, SQUARE_SIZE) for col in range(COLS)] for row in range(ROWS)] for _ in range(NUM_BOARDS * NUM_BOARDS)]

def get_current_board():
    board_index = current_board[0] * NUM_BOARDS + current_board[1]
    return boards[board_index]

def draw_board(mouse_pos, offset_x, offset_y):
    board = get_current_board()
    for row in range(ROWS):
        for col in range(COLS):
            board[row][col].draw(screen, mouse_pos, offset_x, offset_y)

def draw_player(offset_x, offset_y):
    player_rect = pygame.Rect(player_pos[1] * SQUARE_SIZE, player_pos[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE).move(offset_x, offset_y)
    pygame.draw.rect(screen, GREEN, player_rect)
    
    # Draw direction arrow
    center_x = player_rect.centerx
    center_y = player_rect.centery
    arrow_length = SQUARE_SIZE // 2
    
    if player_direction == 0:  # Up
        pygame.draw.polygon(screen, RED, [(center_x, center_y - arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 1:  # Up-right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y - arrow_length), (center_x, center_y - 10), (center_x + 10, center_y)])
    elif player_direction == 2:  # Right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 3:  # Down-right
        pygame.draw.polygon(screen, RED, [(center_x + arrow_length, center_y + arrow_length), (center_x, center_y + 10), (center_x + 10, center_y)])
    elif player_direction == 4:  # Down
        pygame.draw.polygon(screen, RED, [(center_x, center_y + arrow_length), (center_x - 10, center_y), (center_x + 10, center_y)])
    elif player_direction == 5:  # Down-left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y + arrow_length), (center_x - 10, center_y), (center_x, center_y + 10)])
    elif player_direction == 6:  # Left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y), (center_x, center_y - 10), (center_x, center_y + 10)])
    elif player_direction == 7:  # Up-left
        pygame.draw.polygon(screen, RED, [(center_x - arrow_length, center_y - arrow_length), (center_x - 10, center_y), (center_x, center_y - 10)])

def move_player(forward=True):
    global current_board

    new_pos = player_pos[:]
    if player_direction == 0:  # Up
        new_pos[0] -= 1 if forward else 1
    elif player_direction == 1:  # Up-right
        new_pos[0] -= 1 if forward else 1
        new_pos[1] += 1 if forward else -1
    elif player_direction == 2:  # Right
        new_pos[1] += 1 if forward else -1
    elif player_direction == 3:  # Down-right
        new_pos[0] += 1 if forward else -1
        new_pos[1] += 1 if forward else -1
    elif player_direction == 4:  # Down
        new_pos[0] += 1 if forward else -1
    elif player_direction == 5:  # Down-left
        new_pos[0] += 1 if forward else -1
        new_pos[1] -= 1 if forward else 1
    elif player_direction == 6:  # Left
        new_pos[1] -= 1 if forward else 1
    elif player_direction == 7:  # Up-left
        new_pos[0] -= 1 if forward else 1
        new_pos[1] -= 1 if forward else 1

    # Check for board transitions
    if new_pos[0] < 0:
        if current_board[0] > 0:
            new_pos[0] = ROWS - 1
            current_board[0] -= 1
        else:
            new_pos[0] = 0
    elif new_pos[0] >= ROWS:
        if current_board[0] < NUM_BOARDS - 1:
            new_pos[0] = 0
            current_board[0] += 1
        else:
            new_pos[0] = ROWS - 1
    if new_pos[1] < 0:
        if current_board[1] > 0:
            new_pos[1] = COLS - 1
            current_board[1] -= 1
        else:
            new_pos[1] = 0
    elif new_pos[1] >= COLS:
        if current_board[1] < NUM_BOARDS - 1:
            new_pos[1] = 0
            current_board[1] += 1
        else:
            new_pos[1] = COLS - 1

    # Prevent moving into inactive tiles
    if get_current_board()[new_pos[0]][new_pos[1]].active:
        # Update the player's position
        player_pos[0], player_pos[1] = new_pos

def rotate_player(key):
    global player_direction
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8

def toggle_edit_mode():
    global edit_mode
    edit_mode = not edit_mode

def draw_edit_button():
    button_color = GREEN if edit_mode else RED
    button_text = "Edit Mode: ON" if edit_mode else "Edit Mode: OFF"
    button_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH + 10, 10, SIDEBAR_WIDTH - 20, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

# Main game loop
running = True
while running:
    screen.fill(MAIN_BG_COLOR)  # Fill the main area with the main background color

    # Draw the sidebar background
    sidebar_rect = pygame.Rect(screen_width - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, screen_height)
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)

    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:  # Toggle edit mode with 'E' key
                toggle_edit_mode()
            elif event.key == pygame.K_UP:
                move_player(forward=True)
            elif event.key == pygame.K_DOWN:
                move_player(forward=False)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                rotate_player(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if edit_button_rect.collidepoint(event.pos):
                    toggle_edit_mode()
            elif event.button == 3 and edit_mode:  # Right-click to toggle tile active/inactive in edit mode
                board = get_current_board()
                for row in range(ROWS):
                    for col in range(COLS):
                        adjusted_rect = board[row][col].rect.move(offset_x, offset_y)
                        if adjusted_rect.collidepoint(event.pos):
                            board[row][col].toggle_active()

    offset_x = screen_width - SIDEBAR_WIDTH + 10
    offset_y = 60

    draw_board(mouse_pos, offset_x, offset_y)
    draw_player(offset_x, offset_y)
    edit_button_rect = draw_edit_button()
    pygame.display.flip()

pygame.quit()
sys.exit()
