import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
BOARD_SIZE = 600  # Size of the board
WINDOW_WIDTH, WINDOW_HEIGHT = 600, 650  # Size of the window
ROWS, COLS = 8, 8  # Size of the board
SQUARE_SIZE = BOARD_SIZE // COLS  # Size of each square

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 0, 255)

# Create the screen
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("8x8 Checkerboard Game")

# Player's starting position and direction (0: up, 1: up-right, 2: right, 3: down-right, 4: down, 5: down-left, 6: left, 7: up-left)
player_pos = [7, 0]
player_direction = 0

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

    def draw(self, screen, mouse_pos):
        if self.rect.collidepoint(mouse_pos) and edit_mode:
            self.color = LIGHT_GRAY
        else:
            self.color = WHITE if self.active else DARK_GRAY
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 1)

    def toggle_active(self):
        self.active = not self.active
        self.color = WHITE if self.active else BLACK

# Create the board with Tile objects
board = [[Tile(row, col, SQUARE_SIZE) for col in range(COLS)] for row in range(ROWS)]

def draw_board(mouse_pos):
    screen.fill(WHITE)
    for row in range(ROWS):
        for col in range(COLS):
            board[row][col].draw(screen, mouse_pos)

def draw_player():
    player_rect = pygame.Rect(player_pos[1] * SQUARE_SIZE, player_pos[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
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

    # Check if the new position is within bounds and active
    if 0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and board[new_pos[0]][new_pos[1]].active:
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
    button_rect = pygame.Rect(200, 605, 200, 40)
    pygame.draw.rect(screen, button_color, button_rect)
    font = pygame.font.Font(None, 36)
    text = font.render(button_text, True, BLACK)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)
    return button_rect

# Main game loop
running = True
while running:
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
                for row in range(ROWS):
                    for col in range(COLS):
                        if board[row][col].rect.collidepoint(event.pos):
                            board[row][col].toggle_active()

    draw_board(mouse_pos)
    draw_player()
    edit_button_rect = draw_edit_button()
    pygame.display.flip()

pygame.quit()
sys.exit()
