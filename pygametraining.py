import pygame
import pygame_gui
import sys
import os
from tkinter import Tk, Button, Label
from tkinter.filedialog import askdirectory
from PIL import Image, ImageTk

def load_images_from_directory(directory):
    images = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            filepath = os.path.join(directory, filename)
            image = pygame.image.load(filepath)
            images.append(image)
    return images

def scale_image(image, screen_width, screen_height):
    image_width, image_height = image.get_size()
    scale_factor = min(screen_width / image_width, screen_height / image_height)
    new_width = int(image_width * scale_factor)
    new_height = int(image_height * scale_factor)
    return pygame.transform.scale(image, (new_width, new_height))

def open_file_explorer():
    directory = askdirectory()
    if directory:
        root.destroy()
        start_pygame(directory)

def return_to_start_gui():
    pygame.quit()
    os.execl(sys.executable, sys.executable, *sys.argv)

def start_pygame(directory):
    # Initialize Pygame
    pygame.init()
    pygame.display.set_caption("Image Viewer")

    # Set Pygame to a windowed mode with the standard window frame
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    screen_width, screen_height = screen.get_size()

    # Load images from the selected directory
    images = load_images_from_directory(directory)
    if not images:
        print("No images found in the selected directory. Please run the program again.")
        sys.exit()

    # Set up the GUI manager
    manager = pygame_gui.UIManager((screen_width, screen_height))

    # Add a return button in the top bar
    return_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, 10), (100, 30)),
        text='Return',
        manager=manager
    )

    # Current image index
    current_image_index = 0

    # Main loop
    running = True
    while running:
        time_delta = pygame.time.Clock().tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    current_image_index = (current_image_index + 1) % len(images)
                elif event.key == pygame.K_LEFT:
                    current_image_index = (current_image_index - 1) % len(images)
                elif event.key == pygame.K_ESCAPE:
                    return_to_start_gui()
            elif event.type == pygame.VIDEORESIZE:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                manager.set_window_resolution((screen_width, screen_height))
            elif event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == return_button:
                        return_to_start_gui()

            manager.process_events(event)

        current_image = scale_image(images[current_image_index], screen_width, screen_height)
        x_pos = (screen_width - current_image.get_width()) // 2
        y_pos = (screen_height - current_image.get_height()) // 2

        screen.fill((0, 0, 0))
        screen.blit(current_image, (x_pos, y_pos))
        manager.update(time_delta)
        manager.draw_ui(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

# Initialize Tkinter and hide the main window
root = Tk()
root.title("Image Viewer")

# Maximize the Tkinter window
root.state('zoomed')

# Load the background image
bg_image_path = "C:/Users/bruno/Pictures/1xd.jpg"  # Update this to the path of your background image
bg_image = Image.open(bg_image_path)
bg_image = bg_image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.Resampling.LANCZOS)
bg_photo = ImageTk.PhotoImage(bg_image)

# Create a label to display the background image
bg_label = Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Create a button to open the file explorer
button = Button(root, text="Select Folder", command=open_file_explorer)
button.pack(pady=20)
button.place(relx=0.5, rely=0.5, anchor='center')

# Run the Tkinter main loop
root.mainloop()
