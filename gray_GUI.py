import tkinter as tk

def main():
    # Create the main window
    root = tk.Tk()
    root.title("Sample GUI")
    root.state('zoomed')

    # Set the size of the window
    width = root.winfo_screenwidth() // 1.2  # Width is 1/1.2 of the screen width
    height = root.winfo_screenheight() // 1.2  # Height is 1/1.2 of the screen height
    root.geometry(f'{int(width)}x{int(height)}')

    # Set the background color for the main window
    root.configure(background='gray')

    # Create a sidebar on the left side of the window
    sidebar_width = int(width * 0.2)  # Sidebar takes up 20% of the window width
    sidebar = tk.Frame(root, width=sidebar_width, height=height, bg='#4B4B4B')  # A darker shade of gray
    sidebar.pack(side='left', fill='y')

    # Buttons for the sidebar
    maps_button = tk.Button(sidebar, text="Maps", bg="#6A6A6A", fg="white")
    maps_button.pack(padx=10, pady=10, fill='x')  # Adding padding and expanding to fit the width of the sidebar

    maps_maker_button = tk.Button(sidebar, text="Maps Maker", bg="#6A6A6A", fg="white")
    maps_maker_button.pack(padx=10, pady=10, fill='x')  # Similarly adding padding and expanding

    # Placeholder for a 2D map module at the bottom of the sidebar
    map_placeholder_size = sidebar_width  # Making the placeholder a perfect square
    map_placeholder = tk.Frame(sidebar, width=map_placeholder_size,
                               height=map_placeholder_size, bg='black')  # Black to distinguish from the sidebar
    map_placeholder.pack(side='bottom', fill='both')

    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main()
