import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import os
import math

# Load and resize texture function
def load_texture(image_path, max_size=8192):  # Increased max size to 8192 for higher resolution textures
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file {image_path} not found.")
    
    try:
        # Load the image using Pygame
        texture_surface = pygame.image.load(image_path)
        original_width = texture_surface.get_width()
        original_height = texture_surface.get_height()
        print(f"Original texture size: {original_width}x{original_height}")

        # Scale the texture down if it's too large
        if original_width > max_size or original_height > max_size:
            scale_factor = min(max_size / original_width, max_size / original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            print(f"Resizing texture to {new_width}x{new_height}")
            texture_surface = pygame.transform.scale(texture_surface, (new_width, new_height))
        else:
            print("No resizing needed.")
        
        # Convert the texture data
        texture_data = pygame.image.tostring(texture_surface, "RGB", 1)
        width = texture_surface.get_width()
        height = texture_surface.get_height()
    except Exception as e:
        print(f"Failed to load texture: {e}")
        return None
    
    # Generate and bind the OpenGL texture
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)

    # Set texture filtering to GL_NEAREST for crisper quality
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)  # Set to GL_NEAREST for sharp quality
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)  # Set to GL_NEAREST for sharp quality
    glBindTexture(GL_TEXTURE_2D, 0)
    
    print(f"Texture loaded and bound with ID: {texture_id}")
    return texture_id

# Draw the cylindrical panorama with even closer view and taller height
def draw_cylinder(texture, num_segments=100, radius=10, height=10):
    glBindTexture(GL_TEXTURE_2D, texture)
    glBegin(GL_QUAD_STRIP)
    
    for i in range(num_segments + 1):
        theta = (i / float(num_segments)) * 2.0 * math.pi
        x = radius * math.cos(theta)
        z = radius * math.sin(theta)
        u = i / float(num_segments)  # Horizontal texture coordinate
        
        # Flipping the image vertically by swapping texture coordinates
        glTexCoord2f(u, 1)  # Flipped top
        glVertex3f(x, height, z)
        glTexCoord2f(u, 0)  # Flipped bottom
        glVertex3f(x, -height, z)
    
    glEnd()

# Initialize pygame and OpenGL
def main():
    print("Initializing Pygame...")
    pygame.init()
    
    # Get the current screen's size
    screen_info = pygame.display.Info()
    display_width = screen_info.current_w
    display_height = screen_info.current_h

    # Create a window slightly smaller than full screen
    display = (int(display_width * 0.9), int(display_height * 0.9))
    pygame.display.set_mode(display, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
    pygame.display.set_caption("High-Quality Cylindrical Panorama Viewer")
    
    print("Window created. Display size:", display)
    
    # Set up the projection matrix with a wide but flatter FOV
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(80, (display[0] / display[1]), 0.1, 50.0)  # Moderate FOV to show more of the image but flatter
    
    # Set up the modelview matrix
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -0.7)  # Moved camera extremely close to the cylinder

    # Enable depth testing and textures
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)  # Enable texture mapping
    glClearColor(0.0, 0.0, 0.0, 1.0)

    print("OpenGL setup completed.")

    # Load and resize the texture (max size set to 8192 pixels for higher quality)
    texture = load_texture('C:\\Users\\bruno\\Downloads\\pannellum-2.5.6 (1)\\pannellum-2.5.6\\build\\IMG_1606.JPG', max_size=8192)
    if texture is None:
        print("Failed to load texture. Exiting...")
        return

    print("Texture loaded successfully. Starting event loop...")
    
    # Variables for dragging the panorama
    angle = 0
    dragging = False
    prev_mouse_pos = (0, 0)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Quit event detected. Exiting...")
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button down
                dragging = True
                prev_mouse_pos = pygame.mouse.get_pos()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left mouse button up
                dragging = False

        # Handle dragging logic when left mouse button is pressed
        if dragging:
            current_mouse_pos = pygame.mouse.get_pos()
            delta_x = current_mouse_pos[0] - prev_mouse_pos[0]
            angle -= delta_x * 0.1  # Flipped the direction of the dragging by using negative delta
            prev_mouse_pos = current_mouse_pos

        # Clear the screen and depth buffer
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Apply the rotation for the panoramic view
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -0.7)  # Moved camera extremely close to the cylinder
        glRotatef(angle, 0, 1, 0)

        # Draw the flipped cylindrical panorama
        draw_cylinder(texture)

        # Swap buffers
        pygame.display.flip()
        pygame.time.wait(10)
    
    # Clean up
    print("Cleaning up and quitting...")
    glDeleteTextures([texture])
    pygame.quit()

if __name__ == "__main__":
    main()
