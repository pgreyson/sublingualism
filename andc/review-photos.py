#!/usr/bin/env python3
"""
Photo reviewer for solstice/equinox photos.
Shows each photo and lets you thumbs up or thumbs down.

Keys: y=yes, n=no, left/right=navigate, q=quit
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps
import os
import sys

INPUT_FILE = "/Volumes/Workspace/sublingualism/andc/solstice-equinox-photos.txt"
SELECTED_FILE = "/Volumes/Workspace/sublingualism/andc/selected-photos.txt"
REJECTED_FILE = "/Volumes/Workspace/sublingualism/andc/rejected-photos.txt"

class PhotoReviewer:
    def __init__(self, root):
        self.root = root
        self.root.title("ANDC Photo Reviewer")
        self.root.geometry("1200x900")

        # Load photos
        self.photos = self.load_photos()
        self.current_index = self.find_start_index()

        # Track selections
        self.selected = set(self.load_existing(SELECTED_FILE))
        self.rejected = set(self.load_existing(REJECTED_FILE))

        # Setup UI
        self.setup_ui()
        self.show_current()

        # Keyboard bindings
        self.root.bind('<Left>', lambda e: self.prev_photo())
        self.root.bind('<Right>', lambda e: self.next_photo())
        self.root.bind('<Up>', lambda e: self.thumbs_up())
        self.root.bind('<Down>', lambda e: self.thumbs_down())
        self.root.bind('y', lambda e: self.thumbs_up())
        self.root.bind('n', lambda e: self.thumbs_down())
        self.root.bind('q', lambda e: self.quit())

    def load_photos(self):
        if not os.path.exists(INPUT_FILE):
            print(f"Input file not found: {INPUT_FILE}")
            sys.exit(1)
        with open(INPUT_FILE, 'r') as f:
            photos = [line.strip() for line in f if line.strip() and os.path.exists(line.strip())]
        print(f"Loaded {len(photos)} photos")
        return photos

    def load_existing(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def find_start_index(self):
        """Start after the last reviewed photo"""
        reviewed = set(self.load_existing(SELECTED_FILE) + self.load_existing(REJECTED_FILE))
        for i, photo in enumerate(self.photos):
            if photo not in reviewed:
                return i
        return 0

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Status bar
        self.status = ttk.Label(main_frame, text="", font=('Helvetica', 14))
        self.status.pack(pady=10)

        # Image display
        self.image_label = ttk.Label(main_frame)
        self.image_label.pack(expand=True, fill='both', padx=20, pady=10)

        # Filename
        self.filename_label = ttk.Label(main_frame, text="", font=('Helvetica', 10),
                                        wraplength=1100)
        self.filename_label.pack(pady=5)

        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="NO (n)", command=self.thumbs_down).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="< Prev", command=self.prev_photo).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Next >", command=self.next_photo).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="YES (y)", command=self.thumbs_up).pack(side='left', padx=10)

    def show_current(self):
        if not self.photos:
            self.status.config(text="No photos to review")
            return

        photo_path = self.photos[self.current_index]

        # Update status
        status_text = f"{self.current_index + 1} / {len(self.photos)}"
        status_text += f"  |  Yes: {len(self.selected)}  No: {len(self.rejected)}"
        if photo_path in self.selected:
            status_text += "  [SELECTED]"
        elif photo_path in self.rejected:
            status_text += "  [REJECTED]"
        self.status.config(text=status_text)

        # Update filename
        self.filename_label.config(text=photo_path)

        # Load and display image
        try:
            img = Image.open(photo_path)
            # Fix orientation based on EXIF data
            img = ImageOps.exif_transpose(img)
            # Resize to fit window while maintaining aspect ratio
            img.thumbnail((1100, 700), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo_image)
        except Exception as e:
            self.image_label.config(image='', text=f"Error loading image:\n{e}")

    def thumbs_up(self):
        if not self.photos:
            return
        photo = self.photos[self.current_index]
        self.selected.add(photo)
        self.rejected.discard(photo)
        self.save_lists()
        self.next_photo()

    def thumbs_down(self):
        if not self.photos:
            return
        photo = self.photos[self.current_index]
        self.rejected.add(photo)
        self.selected.discard(photo)
        self.save_lists()
        self.next_photo()

    def next_photo(self):
        if self.current_index < len(self.photos) - 1:
            self.current_index += 1
            self.show_current()

    def prev_photo(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current()

    def save_lists(self):
        with open(SELECTED_FILE, 'w') as f:
            f.write('\n'.join(sorted(self.selected)))
        with open(REJECTED_FILE, 'w') as f:
            f.write('\n'.join(sorted(self.rejected)))

    def quit(self):
        self.save_lists()
        self.root.quit()

if __name__ == '__main__':
    root = tk.Tk()
    app = PhotoReviewer(root)
    root.mainloop()
