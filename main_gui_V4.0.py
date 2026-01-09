import os
import time
import json
from tkinter import Tk, Label, Button, Entry, Checkbutton, IntVar, filedialog, StringVar, ttk
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF for text and image manipulation
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

# Configuration file path
CONFIG_FILE = "config.txt"

# Functions to perform watermark and merging
def add_background_to_pdf(pdf, background_image_path, opacity=1.0, bg_x=0, bg_y=0):
    if not os.path.exists(background_image_path):
        print("Background image not found, skipping background step.")
        return

    for page in pdf:
        # Get page dimensions
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Open and convert the background image
        bg_image = Image.open(background_image_path).convert("RGBA")
        
        # Calculate aspect ratio
        bg_width, bg_height = bg_image.size
        aspect_ratio = bg_width / bg_height
        
        # Calculate new dimensions while maintaining aspect ratio
        if aspect_ratio > page_width / page_height:
            # Background is wider than page
            new_bg_width = int(page_width)
            new_bg_height = int(page_width / aspect_ratio)
        else:
            # Background is taller than or equal to page
            new_bg_width = int(page_height * aspect_ratio)
            new_bg_height = int(page_height)

        # Resize the background image using LANCZOS filter
        bg_image = bg_image.resize((new_bg_width, new_bg_height), Image.LANCZOS)

        # Adjust opacity
        alpha = bg_image.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        bg_image.putalpha(alpha)
        
        # Save the adjusted background as a temporary file
        temp_bg_img_path = "temp_background.png"
        bg_image.save(temp_bg_img_path)
        
        # Calculate new position to center the background
        x_position = (page_width - new_bg_width) / 2 + bg_x
        y_position = (page_height - new_bg_height) / 2 + bg_y

        # Insert the image as the background
        page.insert_image(fitz.Rect(x_position, y_position, x_position + new_bg_width, y_position + new_bg_height), filename=temp_bg_img_path, overlay=True)
        
        # Remove the temporary image file
        os.remove(temp_bg_img_path)


def add_watermark_and_merge_pdfs(source_folder, other_pdf, destination_folder, image_path, text, image_x, image_y, image_opacity, text_x, text_y, text_opacity, background_image_path=None, background_opacity=1.0, bg_x=0, bg_y=0, add_bg=False, add_text=False, progress_callback=None):
    os.makedirs(destination_folder, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(source_folder) if f.endswith('.pdf')]
    total_files = len(pdf_files)

    for i, filename in enumerate(pdf_files, 1):
        source_pdf_path = os.path.join(source_folder, filename)
        watermarked_pdf_path = "temp_watermarked.pdf"
        destination_pdf_path = os.path.join(destination_folder, filename)
        
        # Load the source PDF and add watermarks
        source_pdf = fitz.open(source_pdf_path)
        
        if add_bg and background_image_path:
            add_background_to_pdf(source_pdf, background_image_path, background_opacity, bg_x, bg_y)
        
        if add_text:
            add_text_as_watermark(source_pdf, text, text_x, text_y, text_opacity)
        
        # Save the watermarked source PDF temporarily
        source_pdf.save(watermarked_pdf_path)
        source_pdf.close()
        
        # Now merge the watermarked source PDF with other_pdf
        watermarked_reader = PdfReader(watermarked_pdf_path)
        other_reader = PdfReader(other_pdf)
        writer = PdfWriter()
        
        # Add pages from other PDF first
        for page in other_reader.pages:
            writer.add_page(page)
        
        # Then add watermarked source PDF pages
        for page in watermarked_reader.pages:
            writer.add_page(page)
        
        # Save the merged PDF temporarily without flattening
        with open(destination_pdf_path, 'wb') as output_pdf:
            writer.write(output_pdf)
        
        # Clean up temporary files
        os.remove(watermarked_pdf_path)

        # Update progress bar
        if progress_callback:
            progress_callback(i / total_files * 100)
    
    # Show "Completed!" message once done
    completed_label.config(text="Completed!")


def add_text_as_watermark(pdf, text, x, y, opacity=1.0, font_path="arial.ttf", font_size=18):
    text_img = Image.new("RGBA", (500, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Failed to load font '{font_path}': {e}. Using default font.")
        font = ImageFont.load_default()
    draw.text((0, 0), text, fill=(0, 0, 0, int(255 * opacity)), font=font)
    temp_text_img_path = "temp_text_watermark.png"
    text_img.save(temp_text_img_path)
    for page in pdf:
        page.insert_image(
            fitz.Rect(x, y, x + text_img.width, y + text_img.height),
            filename=temp_text_img_path,
            overlay=True
        )
    os.remove(temp_text_img_path)


# Load or save configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)


# GUI Setup
def start_process():
    config = {
        "source_folder": source_folder.get(),
        "other_pdf": other_pdf.get(),
        "destination_folder": destination_folder.get(),
        "text": text.get(),
        "background_image": background_image.get()
    }
    save_config(config)

    completed_label.config(text="")  # Clear any previous "Completed!" message
    add_watermark_and_merge_pdfs(
        config["source_folder"], config["other_pdf"], config["destination_folder"], 
        image_path="", text=config["text"],
        image_x=220, image_y=-5, image_opacity=1.0, text_x=190, text_y=820, 
        text_opacity=1.0, background_image_path=config["background_image"],
        background_opacity=0.13, bg_x=0, bg_y=0, 
        add_bg=bg_var.get(), add_text=text_var.get(), 
        progress_callback=update_progress
    )


def update_progress(value):
    progress_bar["value"] = value
    root.update_idletasks()


# GUI Element Initialization
root = Tk()
root.title("PDF Watermark and Merge Tool")

# Load configuration
config = load_config()

Label(root, text="PDF Watermark and Merge Tool").pack(pady=10)

Label(root, text="Source Folder:").pack()
source_folder = StringVar(value=config.get("source_folder", ""))
Entry(root, textvariable=source_folder, width=40).pack()
Button(root, text="Browse", command=lambda: source_folder.set(filedialog.askdirectory())).pack(pady=2)

Label(root, text="Other PDF File:").pack()
other_pdf = StringVar(value=config.get("other_pdf", ""))
Entry(root, textvariable=other_pdf, width=40).pack()
Button(root, text="Browse", command=lambda: other_pdf.set(filedialog.askopenfilename())).pack(pady=2)

Label(root, text="Destination Folder:").pack()
destination_folder = StringVar(value=config.get("destination_folder", ""))
Entry(root, textvariable=destination_folder, width=40).pack()
Button(root, text="Browse", command=lambda: destination_folder.set(filedialog.askdirectory())).pack(pady=2)

Label(root, text="Text Watermark:").pack()
text = StringVar(value=config.get("text", ""))
Entry(root, textvariable=text, width=40).pack()

Label(root, text="Background Image:").pack()
background_image = StringVar(value=config.get("background_image", ""))
Entry(root, textvariable=background_image, width=40).pack()
Button(root, text="Browse", command=lambda: background_image.set(filedialog.askopenfilename())).pack(pady=2)

# Checkboxes for options
bg_var = IntVar()
text_var = IntVar()
Checkbutton(root, text="Add Background Image", variable=bg_var).pack()
Checkbutton(root, text="Add Text Watermark", variable=text_var).pack()

# Progress bar, Start Button, and Completion Message
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=10)
Button(root, text="Start Process", command=start_process).pack(pady=5)
completed_label = Label(root, text="", fg="green")
completed_label.pack()

root.mainloop()
