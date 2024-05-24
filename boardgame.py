import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 300, 300  # Size of the window
ROWS, COLS = 3, 3
SQUARE_SIZE = WIDTH // COLS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)

# Create the screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("3x3 Checkerboard Game")

# Player's starting position and direction (0: up, 1: up-right, 2: right, 3: down-right, 4: down, 5: down-left, 6: left, 7: up-left)
player_pos = [2, 0]
player_direction = 0

class Tile:
    def __init__(self, row, col, size):
        self.row = row
        self.col = col
        self.size = size
        self.rect = pygame.Rect(col * size, row * size, size, size)
        self.color = WHITE

    def draw(self, screen, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.color = LIGHT_GRAY
        else:
            self.color = WHITE
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 1)

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
    if player_direction == 0:  # Up
        if forward and player_pos[0] > 0:
            player_pos[0] -= 1
        elif not forward and player_pos[0] < ROWS - 1:
            player_pos[0] += 1
    elif player_direction == 1:  # Up-right
        if forward and player_pos[0] > 0 and player_pos[1] < COLS - 1:
            player_pos[0] -= 1
            player_pos[1] += 1
        elif not forward and player_pos[0] < ROWS - 1 and player_pos[1] > 0:
            player_pos[0] += 1
            player_pos[1] -= 1
    elif player_direction == 2:  # Right
        if forward and player_pos[1] < COLS - 1:
            player_pos[1] += 1
        elif not forward and player_pos[1] > 0:
            player_pos[1] -= 1
    elif player_direction == 3:  # Down-right
        if forward and player_pos[0] < ROWS - 1 and player_pos[1] < COLS - 1:
            player_pos[0] += 1
            player_pos[1] += 1
        elif not forward and player_pos[0] > 0 and player_pos[1] > 0:
            player_pos[0] -= 1
            player_pos[1] -= 1
    elif player_direction == 4:  # Down
        if forward and player_pos[0] < ROWS - 1:
            player_pos[0] += 1
        elif not forward and player_pos[0] > 0:
            player_pos[0] -= 1
    elif player_direction == 5:  # Down-left
        if forward and player_pos[0] < ROWS - 1 and player_pos[1] > 0:
            player_pos[0] += 1
            player_pos[1] -= 1
        elif not forward and player_pos[0] > 0 and player_pos[1] < COLS - 1:
            player_pos[0] -= 1
            player_pos[1] += 1
    elif player_direction == 6:  # Left
        if forward and player_pos[1] > 0:
            player_pos[1] -= 1
        elif not forward and player_pos[1] < COLS - 1:
            player_pos[1] += 1
    elif player_direction == 7:  # Up-left
        if forward and player_pos[0] > 0 and player_pos[1] > 0:
            player_pos[0] -= 1
            player_pos[1] -= 1
        elif not forward and player_pos[0] < ROWS - 1 and player_pos[1] < COLS - 1:
            player_pos[0] += 1
            player_pos[1] += 1

def rotate_player(key):
    global player_direction
    if key == pygame.K_LEFT:
        player_direction = (player_direction - 1) % 8
    elif key == pygame.K_RIGHT:
        player_direction = (player_direction + 1) % 8

# Main game loop
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                move_player(forward=True)
            elif event.key == pygame.K_DOWN:
                move_player(forward=False)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                rotate_player(event.key)

    draw_board(mouse_pos)
    draw_player()
    pygame.display.flip()

pygame.quit()
sys.exit()
