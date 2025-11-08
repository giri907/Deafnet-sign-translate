import speech_recognition as sr
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

# Initialize recognizer
recognizer = sr.Recognizer()
is_listening = False

# Start Listening Function
def start_listening():
    global is_listening
    is_listening = True
    output_box.insert(tk.END, "🎤 Listening started...\n")
    threading.Thread(target=listen_microphone).start()

# Stop Listening Function
def stop_listening():
    global is_listening
    is_listening = False
    output_box.insert(tk.END, "🛑 Listening stopped.\n")

# Speech Recognition Function
def listen_microphone():
    global is_listening
    while is_listening:
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio)
                output_box.insert(tk.END, "🗣️ " + text + "\n")
                output_box.see(tk.END)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            output_box.insert(tk.END, "⚠️ Could not understand audio\n")
        except Exception as e:
            output_box.insert(tk.END, f"❌ Error: {e}\n")

# Save Notes Function
def save_text():
    text = output_box.get("1.0", tk.END).strip()
    if text:
        with open("DeafNet_Notes.txt", "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("Saved", "✅ Notes saved as DeafNet_Notes.txt")
    else:
        messagebox.showwarning("Empty", "No text to save!")

# Tkinter GUI Setup
root = tk.Tk()
root.title("DeafNet Lite - Speech to Text Assistant")
root.geometry("500x400")
root.resizable(False, False)

tk.Label(root, text="🎧 DeafNet Lite", font=("Arial", 16, "bold")).pack(pady=10)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, font=("Arial", 10))
output_box.pack(padx=10, pady=10)

frame = tk.Frame(root)
frame.pack()

tk.Button(frame, text="▶️ Start Listening", command=start_listening, bg="green", fg="white", width=15).grid(row=0, column=0, padx=5)
tk.Button(frame, text="⏹ Stop Listening", command=stop_listening, bg="red", fg="white", width=15).grid(row=0, column=1, padx=5)
tk.Button(frame, text="💾 Save Notes", command=save_text, bg="blue", fg="white", width=15).grid(row=0, column=2, padx=5)

root.mainloop()