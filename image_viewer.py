# image_viewer.py
import pygame
import cv2
import os
import sys

def load_image(filepath):
    image = cv2.imread(filepath)
    if image is None:
        raise ValueError("Image not found or unable to load")
    return image

def cv2_to_pygame(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(image_rgb.tobytes(), image_rgb.shape[1::-1], 'RGB')

def display_images_in_new_window(directory):
    pygame.init()
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
    if not image_files:
        print("No images found in the selected folder.")
        return

    image_index = 0
    def load_next_image():
        nonlocal image_index
        image_index = (image_index + 1) % len(image_files)
        return load_image(os.path.join(directory, image_files[image_index]))

    def load_previous_image():
        nonlocal image_index
        image_index = (image_index - 1) % len(image_files)
        return load_image(os.path.join(directory, image_files[image_index]))

    # Position the window in the center of the screen
    window_info = pygame.display.Info()
    screen_width = window_info.current_w
    screen_height = window_info.current_h
    window_x = (screen_width - 800) // 2
    window_y = (screen_height - 600) // 2
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_x},{window_y}"

    # Create a new Pygame window
    image_window = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Image Viewer")

    running = True
    image = load_next_image()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    image = load_next_image()
                elif event.key == pygame.K_LEFT:
                    image = load_previous_image()

        if image is not None:
            img_height, img_width = image.shape[:2]
            display_width, display_height = image_window.get_size()

            # Calculate scale factors and new dimensions
            scale_factor = min(display_width / img_width, display_height / img_height)
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)

            scaled_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            scaled_image_pygame = cv2_to_pygame(scaled_image)
            image_rect = scaled_image_pygame.get_rect(center=(display_width // 2, display_height // 2))

            image_window.fill((100, 100, 100))  # IMAGE_BG_COLOR
            image_window.blit(scaled_image_pygame, image_rect.topleft)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        display_images_in_new_window(sys.argv[1])
    else:
        print("No directory provided.")
