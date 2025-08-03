# ...[imports remain unchanged]...
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

IMAGE_DIR = "images"
OUTPUT_DIR = "labels"
IMG_SIZE = 640
ZOOM_STEP = 1.1
CLASSES = [
    ("Blue Cone", 0),
    ("Large Orange Cone", 1),
    ("Small Orange Cone", 2),
    ("Yellow Cone", 3)
]

class ImageLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("YOLO Cone Labeling Tool")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self.image_paths = sorted([
            os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        self.image_index = 0
        self.class_index = 0
        self.annotations = []

        self.zoom_level = 1.0
        self.editing_existing_box = False

        # UI
        self.frame = ttk.Frame(root, padding=10)
        self.frame.grid(row=0, column=0, sticky="nsew")

        self.canvas = tk.Canvas(self.frame, bg="black", width=IMG_SIZE, height=IMG_SIZE)
        self.canvas.grid(row=0, column=0, columnspan=4)

        self.hbar = ttk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.hbar.grid(row=1, column=0, columnspan=4, sticky="ew")
        self.vbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.vbar.grid(row=0, column=4, sticky="ns")
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        # Mode Selector Dropdown
        self.mode_var = tk.StringVar(value="Manual")
        ttk.Label(self.frame, text="Mode:").grid(row=2, column=0, sticky="w", padx=5)
        self.mode_selector = ttk.Combobox(self.frame, textvariable=self.mode_var, values=["Manual", "Model Magic Label"], state="readonly")
        self.mode_selector.grid(row=2, column=1, sticky="w")

        self.status = ttk.Label(self.frame, font=("Arial", 12))
        self.status.grid(row=2, column=2, columnspan=1, sticky="w", pady=5)

        self.done_button = ttk.Button(self.frame, text="Done (Next Class/Image)", command=self.next_class_or_image)
        self.done_button.grid(row=2, column=3, sticky="e", pady=5)

        self.boxes = []

        self.canvas.bind("<Button-1>", self.mouse_click)
        self.canvas.bind("<B1-Motion>", self.draw_box)
        self.canvas.bind("<ButtonRelease-1>", self.end_box)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_image()

    def on_close(self):
        self.save_annotations()
        self.root.destroy()

    def load_image(self):
        if self.image_index >= len(self.image_paths):
            self.status.config(text="✅ All images labeled.")
            self.canvas.delete("all")
            return

        if self.image_index > 0:
            self.save_annotations()

        self.boxes = []
        self.annotations = []
        self.class_index = 0
        self.zoom_level = 1.0

        path = self.image_paths[self.image_index]
        self.image_name = os.path.splitext(os.path.basename(path))[0]
        self.image_orig = Image.open(path)
        self.update_status()

        if self.mode_var.get() == "Model Magic Label":
            self.run_model_prediction(self.image_orig)

        self.update_zoom_image()

    def run_model_prediction(self, image):
        print("🔮 Model Magic Label Mode - placeholder model running...")
        # You’ll later replace this with actual YOLO inference
        # Here’s where you would run inference and populate `self.annotations`
        # For now we simulate one box
        dummy_annotation = (1, 0.5, 0.5, 0.2, 0.2)
        self.annotations.append(dummy_annotation)

    def update_zoom_image(self):
        if self.image_orig:
            new_size = int(IMG_SIZE * self.zoom_level)
            resized = self.image_orig.resize((new_size, new_size), Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
            self.canvas.config(scrollregion=(0, 0, new_size, new_size))
            self.draw_all_boxes()

    def editAnnotationBox(self, event, box_id, ann_index):
        editbox = tk.Toplevel(self.root)
        editbox.wm_title("Edit Annotation")
        editbox.geometry(f"+{event.x_root}+{event.y_root}")
        ttk.Label(editbox, text="Label:").pack(padx=5, pady=5)

        class_var = tk.StringVar()
        class_names = [name for name, _ in CLASSES]
        current_class_id = self.annotations[ann_index][0]
        class_var.set(class_names[current_class_id])

        dropdown = ttk.Combobox(editbox, textvariable=class_var, values=class_names, state="readonly")
        dropdown.pack(padx=5, pady=5)

        def apply_label_change():
            new_class_name = class_var.get()
            new_class_id = dict(CLASSES)[new_class_name]
            old_ann = self.annotations[ann_index]
            self.annotations[ann_index] = (new_class_id, *old_ann[1:])
            self.update_zoom_image()
            editbox.destroy()

        def delete_annotation():
            self.canvas.delete(box_id)
            del self.annotations[ann_index]
            self.boxes = [(bid, i) for bid, i in self.boxes if bid != box_id]
            self.boxes = [(bid, idx) for idx, (bid, _) in enumerate(self.boxes)]
            self.update_zoom_image()
            editbox.destroy()

        ttk.Button(editbox, text="Apply", command=apply_label_change).pack(padx=5, pady=5)
        ttk.Button(editbox, text="Delete", command=delete_annotation).pack(padx=5, pady=5)

    def mouse_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        for box_id, ann_index in reversed(self.boxes):
            coords = self.canvas.coords(box_id)
            if coords and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                self.editing_existing_box = True
                self.editAnnotationBox(event, box_id, ann_index)
                return

        self.editing_existing_box = False
        self.start_x, self.start_y = x, y
        self.current_box = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="lime", width=2
        )

    def draw_box(self, event):
        if self.current_box and not self.editing_existing_box:
            curr_x = self.canvas.canvasx(event.x)
            curr_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.current_box, self.start_x, self.start_y, curr_x, curr_y)

    def end_box(self, event):
        if self.editing_existing_box:
            return

        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        x0, y0 = min(self.start_x, end_x), min(self.start_y, end_y)
        x1, y1 = max(self.start_x, end_x), max(self.start_y, end_y)

        zoomed_size = IMG_SIZE * self.zoom_level
        x_center = ((x0 + x1) / 2) / zoomed_size
        y_center = ((y0 + y1) / 2) / zoomed_size
        width = (x1 - x0) / zoomed_size
        height = (y1 - y0) / zoomed_size

        _, class_id = CLASSES[self.class_index]
        annotation = (class_id, x_center, y_center, width, height)
        self.annotations.append(annotation)

        box_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="lime", width=2)
        self.boxes.append((box_id, len(self.annotations) - 1))
        self.current_box = None

    def draw_all_boxes(self):
        self.boxes = []
        zoomed_size = IMG_SIZE * self.zoom_level
        for i, (class_id, xc, yc, w, h) in enumerate(self.annotations):
            x0 = (xc - w/2) * zoomed_size
            y0 = (yc - h/2) * zoomed_size
            x1 = (xc + w/2) * zoomed_size
            y1 = (yc + h/2) * zoomed_size
            box_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="lime", width=2)
            class_name = [name for name, cid in CLASSES if cid == class_id][0]
            self.canvas.create_text(x0 + 4, y0 + 4, anchor="nw", text=class_name, fill="white", font=("Arial", 10))
            self.boxes.append((box_id, i))

    def zoom(self, event):
        factor = ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP
        old_zoom = self.zoom_level
        self.zoom_level *= factor
        self.zoom_level = max(0.2, min(self.zoom_level, 10))
        if self.zoom_level != old_zoom:
            self.update_zoom_image()

    def update_status(self):
        class_name, _ = CLASSES[self.class_index]
        image_text = f"Image {self.image_index + 1}/{len(self.image_paths)}"
        self.root.title(f"Labeling - {self.image_name}")
        self.status.config(text=f"{image_text} | Label: {class_name} | Zoom: {self.zoom_level:.2f}x")

    def next_class_or_image(self):
        self.class_index += 1
        if self.class_index >= len(CLASSES):
            self.save_annotations()
            self.image_index += 1
            self.load_image()
        else:
            self.update_status()

    def save_annotations(self):
        if not self.annotations:
            return
        txt_path = os.path.splitext(self.image_paths[self.image_index])[0] + ".txt"
        with open(txt_path, 'w') as f:
            for class_id, xc, yc, w, h in self.annotations:
                f.write(f"{class_id} {xc:.7f} {yc:.7f} {w:.7f} {h:.7f}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageLabeler(root)
    root.mainloop()



# import os
# import tkinter as tk
# from tkinter import ttk
# from PIL import Image, ImageTk

# # Configuration
# IMAGE_DIR = "images"
# OUTPUT_DIR = "labels"
# IMG_SIZE = 640
# ZOOM_STEP = 1.1
# CLASSES = [
#     ("Blue Cone", 0),
#     ("Large Orange Cone", 1),
#     ("Small Orange Cone", 2),
#     ("Yellow Cone", 3)
# ]



# class ImageLabeler:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("YOLO Cone Labeling Tool")

#         os.makedirs(OUTPUT_DIR, exist_ok=True)
#         self.image_paths = sorted([
#             os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
#             if f.lower().endswith(('.png', '.jpg', '.jpeg'))
#         ])
#         self.image_index = 0
#         self.class_index = 0
#         self.annotations = []

#         self.zoom_level = 1.0
#         self.editing_existing_box = False  # Flag to track whether we’re editing

#         # UI Setup
#         self.frame = ttk.Frame(root, padding=10)
#         self.frame.grid(row=0, column=0, sticky="nsew")

#         self.canvas = tk.Canvas(self.frame, bg="black", width=IMG_SIZE, height=IMG_SIZE)
#         self.canvas.grid(row=0, column=0, columnspan=3)

#         self.hbar = ttk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
#         self.hbar.grid(row=1, column=0, columnspan=3, sticky="ew")
#         self.vbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
#         self.vbar.grid(row=0, column=3, sticky="ns")
#         self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

#         self.status = ttk.Label(self.frame, font=("Arial", 12))
#         self.status.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

#         self.done_button = ttk.Button(self.frame, text="Done (Next Class/Image)", command=self.next_class_or_image)
#         self.done_button.grid(row=2, column=2, sticky="e", pady=5)
#         self.boxes = []

#         # Bindings
#         self.canvas.bind("<Button-1>", self.mouse_click)
#         self.canvas.bind("<B1-Motion>", self.draw_box)
#         self.canvas.bind("<ButtonRelease-1>", self.end_box)
#         self.canvas.bind("<MouseWheel>", self.zoom)
#         self.root.protocol("WM_DELETE_WINDOW", self.on_close)

#         self.load_image()

#     def on_close(self):
#         self.save_annotations()
#         self.root.destroy()

#     def load_image(self):
#         if self.image_index >= len(self.image_paths):
#             self.status.config(text="✅ All images labeled.")
#             self.canvas.delete("all")
#             return

#         if self.image_index > 0:
#             self.save_annotations()

#         self.boxes = []
#         self.annotations = []
#         self.class_index = 0
#         self.zoom_level = 1.0

#         path = self.image_paths[self.image_index]
#         self.image_name = os.path.splitext(os.path.basename(path))[0]
#         self.image_orig = Image.open(path)
#         self.update_status()
#         self.update_zoom_image()

#     def update_zoom_image(self):
#         if self.image_orig:
#             new_size = int(IMG_SIZE * self.zoom_level)
#             resized = self.image_orig.resize((new_size, new_size), Image.Resampling.LANCZOS)
#             self.tk_image = ImageTk.PhotoImage(resized)
#             self.canvas.delete("all")
#             self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
#             self.canvas.config(scrollregion=(0, 0, new_size, new_size))
#             self.draw_all_boxes()

#     def editAnnotationBox(self, event, box_id, ann_index):
#         editbox = tk.Toplevel(self.root)
#         editbox.wm_title("Edit Annotation")
#         editbox.geometry(f"+{event.x_root}+{event.y_root}")
#         ttk.Label(editbox, text="Label:").pack(padx=5, pady=5)

#         class_var = tk.StringVar()
#         class_names = [name for name, _ in CLASSES]
#         current_class_id = self.annotations[ann_index][0]
#         class_var.set(class_names[current_class_id])

#         dropdown = ttk.Combobox(editbox, textvariable=class_var, values=class_names, state="readonly")
#         dropdown.pack(padx=5, pady=5)

#         def apply_label_change():
#             new_class_name = class_var.get()
#             new_class_id = dict(CLASSES)[new_class_name]
#             old_ann = self.annotations[ann_index]
#             self.annotations[ann_index] = (new_class_id, *old_ann[1:])
#             self.update_zoom_image()
#             editbox.destroy()

#         def delete_annotation():
#             self.canvas.delete(box_id)
#             del self.annotations[ann_index]
#             self.boxes = [(bid, i) for bid, i in self.boxes if bid != box_id]
#             self.boxes = [(bid, idx) for idx, (bid, _) in enumerate(self.boxes)]
#             self.update_zoom_image()
#             editbox.destroy()

#         ttk.Button(editbox, text="Apply", command=apply_label_change).pack(padx=5, pady=5)
#         ttk.Button(editbox, text="Delete", command=delete_annotation).pack(padx=5, pady=5)

#     def mouse_click(self, event):
#         x = self.canvas.canvasx(event.x)
#         y = self.canvas.canvasy(event.y)
#         for box_id, ann_index in reversed(self.boxes):
#             coords = self.canvas.coords(box_id)
#             if coords and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
#                 self.editing_existing_box = True
#                 self.editAnnotationBox(event, box_id, ann_index)
#                 return

#         self.editing_existing_box = False
#         self.start_x, self.start_y = x, y
#         self.current_box = self.canvas.create_rectangle(
#             self.start_x, self.start_y, self.start_x, self.start_y,
#             outline="lime", width=2
#         )

#     def draw_box(self, event):
#         if self.current_box and not self.editing_existing_box:
#             curr_x = self.canvas.canvasx(event.x)
#             curr_y = self.canvas.canvasy(event.y)
#             self.canvas.coords(self.current_box, self.start_x, self.start_y, curr_x, curr_y)

#     def end_box(self, event):
#         if self.editing_existing_box:
#             return

#         end_x = self.canvas.canvasx(event.x)
#         end_y = self.canvas.canvasy(event.y)
#         x0, y0 = min(self.start_x, end_x), min(self.start_y, end_y)
#         x1, y1 = max(self.start_x, end_x), max(self.start_y, end_y)

#         zoomed_size = IMG_SIZE * self.zoom_level
#         x_center = ((x0 + x1) / 2) / zoomed_size
#         y_center = ((y0 + y1) / 2) / zoomed_size
#         width = (x1 - x0) / zoomed_size
#         height = (y1 - y0) / zoomed_size

#         _, class_id = CLASSES[self.class_index]
#         annotation = (class_id, x_center, y_center, width, height)
#         self.annotations.append(annotation)

#         box_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="lime", width=2)
#         self.boxes.append((box_id, len(self.annotations) - 1))
#         self.current_box = None

#     def draw_all_boxes(self):
#         self.boxes = []
#         zoomed_size = IMG_SIZE * self.zoom_level
#         for i, (class_id, xc, yc, w, h) in enumerate(self.annotations):
#             x0 = (xc - w/2) * zoomed_size
#             y0 = (yc - h/2) * zoomed_size
#             x1 = (xc + w/2) * zoomed_size
#             y1 = (yc + h/2) * zoomed_size
#             box_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="lime", width=2)
#             class_name = [name for name, cid in CLASSES if cid == class_id][0]
#             self.canvas.create_text(x0 + 4, y0 + 4, anchor="nw", text=class_name, fill="white", font=("Arial", 10))
#             self.boxes.append((box_id, i))

#     def zoom(self, event):
#         factor = ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP
#         old_zoom = self.zoom_level
#         self.zoom_level *= factor
#         self.zoom_level = max(0.2, min(self.zoom_level, 10))
#         if self.zoom_level != old_zoom:
#             self.update_zoom_image()

#     def update_status(self):
#         class_name, _ = CLASSES[self.class_index]
#         image_text = f"Image {self.image_index + 1}/{len(self.image_paths)}"
#         self.root.title(f"Labeling - {self.image_name}")
#         self.status.config(text=f"{image_text} | Label: {class_name} | Zoom: {self.zoom_level:.2f}x")

#     def next_class_or_image(self):
#         self.class_index += 1
#         if self.class_index >= len(CLASSES):
#             self.save_annotations()
#             self.image_index += 1
#             self.load_image()
#         else:
#             self.update_status()

#     def save_annotations(self):
#         if not self.annotations:
#             return
#         txt_path = os.path.splitext(self.image_paths[self.image_index])[0] + ".txt"
#         with open(txt_path, 'w') as f:
#             for class_id, xc, yc, w, h in self.annotations:
#                 f.write(f"{class_id} {xc:.7f} {yc:.7f} {w:.7f} {h:.7f}\n")

# if __name__ == "__main__":
#     root = tk.Tk()
#     app = ImageLabeler(root)
#     root.mainloop()
