import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ExifTags
from datetime import datetime

def get_image_date(image_path):
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    if decoded == "DateTimeOriginal":
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
    return None

def resize_image(input_path, output_path, target_width, target_height):
    with Image.open(input_path) as img:
        # Correct orientation based on EXIF data
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = img._getexif()
        if exif is not None:
            orientation = exif.get(orientation, 1)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)

        img_ratio = img.width / img.height
        target_ratio = target_width / target_height

        if img_ratio > target_ratio:
            # Image is wider than target aspect ratio
            new_width = target_width
            new_height = int(target_width / img_ratio)
        else:
            # Image is taller than target aspect ratio
            new_height = target_height
            new_width = int(target_height * img_ratio)

        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        resized_img.save(output_path)

def organize_photos(input_directory):
    # Get all files in the input directory along with their creation dates
    files = []
    for f in os.listdir(input_directory):
        file_path = os.path.join(input_directory, f)
        if os.path.isfile(file_path):
            # Try to get the EXIF date
            exif_date = get_image_date(file_path)
            if exif_date:
                files.append((f, exif_date.timestamp()))
            else:
                # Fall back to file system dates
                creation_date = os.path.getctime(file_path)
                modification_date = os.path.getmtime(file_path)
                # Use the earliest date available
                files.append((f, min(creation_date, modification_date)))

    # Sort files by date
    files.sort(key=lambda x: x[1])
    sorted_files = [f[0] for f in files]
    
    # Create output directory if not exists
    output_directory = os.path.join(input_directory, "organized_photos")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Process files in batches of 8
    batch_size = 8
    for i in range(0, len(sorted_files), batch_size):
        # Create a new folder for each batch
        folder_name = str((i // batch_size) + 1)
        new_folder_path = os.path.join(output_directory, folder_name)
        os.makedirs(new_folder_path, exist_ok=True)
        
        # Rename, resize and move files into the new folder
        for j in range(batch_size):
            if i + j < len(sorted_files):
                src_file = os.path.join(input_directory, sorted_files[i + j])
                dst_file = os.path.join(new_folder_path, f"{j + 1}.jpg")
                resize_image(src_file, dst_file, 1920, 1080)

    messagebox.showinfo("Success", f"Photos organized and resized into folders in: {output_directory}")

def select_directory():
    input_directory = filedialog.askdirectory()
    if input_directory:
        organize_photos(input_directory)

def create_gui():
    root = tk.Tk()
    root.title("Photo Organizer")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(padx=10, pady=10)

    select_button = tk.Button(frame, text="Select Folder", command=select_directory, padx=10, pady=5)
    select_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
