 
# Requires: opencv-python, pytesseract, Pillow, numpy
# And system Tesseract OCR installed.

import threading
import time
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
from PIL import Image, ImageTk, ImageOps
import cv2
import numpy as np
import pytesseract

# If tesseract is in a custom path on Windows, uncomment and set:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class DeafNetApp:
    def _init_(self, root):
        self.root = root
        self.root.title("DeafNet — Classroom OCR Assistant")
        self.root.geometry("1000x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Video capture variables
        self.cap = None
        self.running = False
        self.frame = None
        self.show_large_font = True

        # UI layout
        self.create_widgets()

    def create_widgets(self):
        # Left: video + controls
        left_frame = tk.Frame(self.root, padx=8, pady=8)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.video_label = tk.Label(left_frame, text="Camera feed will appear here", width=60, height=18, bd=2, relief=tk.SUNKEN)
        self.video_label.pack()

        ctrl_frame = tk.Frame(left_frame)
        ctrl_frame.pack(pady=8, fill=tk.X)

        self.start_btn = tk.Button(ctrl_frame, text="Start Camera", command=self.toggle_camera)
        self.start_btn.grid(row=0, column=0, padx=4, pady=2)

        self.capture_btn = tk.Button(ctrl_frame, text="Capture -> OCR", command=self.capture_ocr, state=tk.DISABLED)
        self.capture_btn.grid(row=0, column=1, padx=4, pady=2)

        self.load_img_btn = tk.Button(ctrl_frame, text="Load Image", command=self.load_image)
        self.load_img_btn.grid(row=0, column=2, padx=4, pady=2)

        self.live_ocr_var = tk.IntVar(value=0)
        self.live_check = tk.Checkbutton(ctrl_frame, text="Live OCR (every 2s)", variable=self.live_ocr_var, command=self.on_live_toggle)
        self.live_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        self.fontsize_label = tk.Label(ctrl_frame, text="Font size:")
        self.fontsize_label.grid(row=1, column=2, sticky="e")
        self.fontsize_scale = tk.Scale(ctrl_frame, from_=16, to=72, orient=tk.HORIZONTAL)
        self.fontsize_scale.set(36)
        self.fontsize_scale.grid(row=1, column=3, padx=4)

        # Right: OCR text display + save/export
        right_frame = tk.Frame(self.root, padx=8, pady=8)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_bar = tk.Frame(right_frame)
        top_bar.pack(fill=tk.X)

        self.clear_btn = tk.Button(top_bar, text="Clear Text", command=self.clear_text)
        self.clear_btn.pack(side=tk.LEFT, padx=4)

        self.save_note_btn = tk.Button(top_bar, text="Save Note", command=self.save_note)
        self.save_note_btn.pack(side=tk.LEFT, padx=4)

        self.export_btn = tk.Button(top_bar, text="Export .txt", command=self.export_text)
        self.export_btn.pack(side=tk.LEFT, padx=4)

        self.copy_btn = tk.Button(top_bar, text="Copy to Clipboard", command=self.copy_to_clipboard)
        self.copy_btn.pack(side=tk.LEFT, padx=4)

        # Large readable text area (for classroom view)
        self.large_text = tk.Label(right_frame, text="", anchor="nw", justify="left", bd=2, relief=tk.SUNKEN, padx=8, pady=8)
        self.large_text.pack(fill=tk.BOTH, expand=True, pady=6)

        # Hidden/secondary: full notes text area (scrollable)
        notes_label = tk.Label(right_frame, text="Notes / OCR history:")
        notes_label.pack(anchor="w")
        self.notes_area = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=8)
        self.notes_area.pack(fill=tk.BOTH, expand=False)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor="w")
        status.pack(side=tk.BOTTOM, fill=tk.X)

        # Start background loop for UI updates
        self.update_ui_loop()

    def toggle_camera(self):
        if not self.running:
            # start camera
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Camera error", "Cannot open camera. Check camera device.")
                return
            self.running = True
            self.start_btn.config(text="Stop Camera")
            self.capture_btn.config(state=tk.NORMAL)
            self.status_var.set("Camera started.")
            threading.Thread(target=self.video_loop, daemon=True).start()
        else:
            # stop camera
            self.running = False
            self.start_btn.config(text="Start Camera")
            self.capture_btn.config(state=tk.DISABLED)
            self.status_var.set("Camera stopped.")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            # clear video label image
            self.video_label.config(image="", text="Camera feed stopped")

    def video_loop(self):
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                self.status_var.set("Failed to read from camera.")
                break
            # flip for mirror
            frame = cv2.flip(frame, 1)
            self.frame = frame.copy()
            # convert to PIL for display
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(image)
            # resize to fit label
            pil = pil.resize((600, 400), Image.ANTIALIAS)
            imgtk = ImageTk.PhotoImage(image=pil)
            # need to keep reference
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk, text="")
            time.sleep(0.03)
        # release handled in toggle_camera

    def capture_ocr(self):
        if self.frame is None:
            messagebox.showinfo("No frame", "No camera frame available to OCR.")
            return
        self.status_var.set("Performing OCR...")
        threading.Thread(target=self._do_ocr_from_frame, args=(self.frame.copy(),), daemon=True).start()

    def _do_ocr_from_frame(self, frame):
        try:
            text = self.image_to_text(frame)
            self.append_text(text)
            self.status_var.set("OCR done from camera.")
        except Exception as e:
            self.status_var.set(f"OCR error: {e}")

    def load_image(self):
        fn = filedialog.askopenfilename(title="Select image", filetypes=[("Images",".png;.jpg;.jpeg;.bmp;.tiff"),("All files",".*")])
        if not fn:
            return
        try:
            pil = Image.open(fn)
        except Exception as e:
            messagebox.showerror("Open image", f"Cannot open image: {e}")
            return
        self.status_var.set("Performing OCR on image...")
        threading.Thread(target=self._do_ocr_from_pil, args=(pil,), daemon=True).start()

    def _do_ocr_from_pil(self, pil_img):
        try:
            img_arr = np.array(pil_img.convert("RGB"))
            text = self.image_to_text(img_arr)
            self.append_text(text)
            self.status_var.set("OCR done from image.")
        except Exception as e:
            self.status_var.set(f"OCR error: {e}")

    def image_to_text(self, img_arr):
        # img_arr: numpy array BGR or RGB
        # convert to gray + adaptive threshold to improve OCR
        if img_arr is None:
            return ""
        # ensure RGB ordering for PIL if needed
        if len(img_arr.shape) == 3 and img_arr.shape[2] == 3:
            # If it came from OpenCV BGR, convert
            # heuristic: if max > 250 in first channel maybe BGR -> convert
            # safer: assume it's BGR from cv2
            img = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)
        else:
            img = img_arr
        # Resize for better OCR
        h, w = img.shape[:2]
        scale = max(1, 1000 / max(w, h))
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        # denoise and threshold
        img = cv2.medianBlur(img, 3)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Convert to PIL Image for pytesseract
        pil = Image.fromarray(img)
        # OCR config: --psm 6 (assume a single uniform block of text)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(pil, config=custom_config)
        return text.strip()

    def append_text(self, text):
        if not text:
            text = "[No text detected]"
        # update large readable label (use selected font size)
        fs = int(self.fontsize_scale.get())
        # limit size of displayed text a bit
        display_text = text if len(text) <= 4000 else text[:4000] + "\n\n[Truncated]"
        # Use wrapping newline strategy for label
        self.large_text.config(text=display_text, font=("Helvetica", fs))
        # append to notes area with timestamp
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.notes_area.insert(tk.END, f"[{ts}]\n{display_text}\n\n")
        self.notes_area.see(tk.END)

    def clear_text(self):
        self.large_text.config(text="")
        self.notes_area.delete(1.0, tk.END)
        self.status_var.set("Cleared text.")

    def save_note(self):
        title = simpledialog.askstring("Save note", "Enter note title (optional):")
        base_dir = os.path.join(os.getcwd(), "deafnet_notes")
        os.makedirs(base_dir, exist_ok=True)
        fn = os.path.join(base_dir, f"{time.strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.notes_area.get(1.0, tk.END))
            messagebox.showinfo("Saved", f"Note saved to:\n{fn}")
            self.status_var.set(f"Note saved: {fn}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))
            self.status_var.set("Save failed.")

    def export_text(self):
        txt = self.notes_area.get(1.0, tk.END).strip()
        if not txt:
            messagebox.showinfo("No text", "Notes area is empty.")
            return
        fn = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files","*.txt")], title="Export text as")
        if not fn:
            return
        try:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(txt)
            messagebox.showinfo("Exported", f"Exported to:\n{fn}")
            self.status_var.set(f"Exported: {fn}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            self.status_var.set("Export failed.")

    def copy_to_clipboard(self):
        txt = self.notes_area.get(1.0, tk.END).strip()
        if not txt:
            messagebox.showinfo("No text", "Nothing to copy.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.status_var.set("Copied to clipboard.")

    def on_live_toggle(self):
        if self.live_ocr_var.get():
            self.status_var.set("Live OCR enabled.")
        else:
            self.status_var.set("Live OCR disabled.")

    def update_ui_loop(self):
        # runs every 1000ms to handle live OCR
        if self.live_ocr_var.get() and self.frame is not None:
            # do OCR in background
            # limit frequency: every ~2s
            if not hasattr(self, "_last_live_ocr") or (time.time() - self._last_live_ocr) > 2.0:
                self._last_live_ocr = time.time()
                threading.Thread(target=self._do_ocr_from_frame, args=(self.frame.copy(),), daemon=True).start()
        # schedule next
        self.root.after(1000, self.update_ui_loop)


    def on_close(self):
        if self.running:
            self.running = False
            time.sleep(0.2)
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DeafNetApp(root)
    root.mainloop()