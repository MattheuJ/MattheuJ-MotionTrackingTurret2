#!/usr/bin/env python3

"""
Black GUI
A simple application with a black background.
"""

import tkinter as tk
from tkinter import ttk
import datetime
import cv2
import threading
from PIL import Image, ImageTk
import numpy as np
from picamera2 import Picamera2
from picamera2.previews import Preview

now = datetime.datetime.now()
date = now.strftime("%Y-%m-%d")

class BlackGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motion Tracking Software")
        
        # Set window size and position
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Initialize face detection variables
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.picam2 = None
        self.is_detecting = False
        self.detection_thread = None
        
        # Known parameters for distance estimation
        self.known_face_width = 0.15  # Average face width in meters
        self.known_distance = 1.0     # Calibration distance in meters
        self.known_pixels = 200       # Calibration pixels at known distance
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("Black.TFrame", background="black")
        self.style.configure("White.TLabel", 
                           foreground="white", 
                           background="black",
                           font=("Courier", 40))
        self.style.configure("Red.TLabel", 
                           foreground="red", 
                           background="black",
                           font=("Courier", 40))
        self.style.configure("Green.TLabel", 
                           foreground="green", 
                           background="black",
                           font=("Courier", 40))
        
        # Set background color
        self.root.configure(bg="black")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, style="Black.TFrame")
        self.main_frame.pack(fill="both", expand=True)
        
        # Create text frame for sentences
        self.text_frame = ttk.Frame(self.main_frame, style="Black.TFrame")
        self.text_frame.place(relx=0, rely=0, anchor="nw")
        
        # Random sentences
        sentences = [
            "Welcome to Mattheu's Spacial Defense System",
            "Created for CIS-5",
            f"Current Date {date}",
            "",  # Empty string for line break
        ]
        
        # Add sentences to the frame
        for sentence in sentences:
            label = ttk.Label(self.text_frame, 
                            text=sentence,
                            style="White.TLabel")
            label.pack(pady=10, anchor="w")
            
        # Add status message with different colors
        status_frame = ttk.Frame(self.text_frame, style="Black.TFrame")
        status_frame.pack(pady=10, anchor="w")
        
        status_label = ttk.Label(status_frame, 
                               text="SYSTEM STATUS: ",
                               style="White.TLabel")
        status_label.pack(side="left")
        
        self.status_indicator = ttk.Label(status_frame,
                                        text="OFFLINE",
                                        style="Red.TLabel")
        self.status_indicator.pack(side="left")
        
        # Add text entry
        entry_frame = ttk.Frame(self.text_frame, style="Black.TFrame")
        entry_frame.pack(pady=20, anchor="w")
        
        self.text_entry = tk.Entry(entry_frame,
                                 font=("Courier", 40),
                                 bg="black",
                                 fg="white",
                                 insertbackground="white",  # Cursor color
                                 width=20)
        self.text_entry.pack(side="left")
        
        # Create video frame
        self.video_frame = ttk.Frame(self.main_frame, style="Black.TFrame")
        self.video_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack()
        
        # Bind Enter key to check for ACTIVATE/DEACTIVATE
        self.text_entry.bind('<Return>', self.check_activation)
    
    def calculate_distance(self, face_width_pixels):
        # Using similar triangles principle
        # known_distance / known_pixels = actual_distance / face_width_pixels
        distance = (self.known_distance * face_width_pixels) / self.known_pixels
        return distance
        
    def start_face_detection(self):
        # Initialize Pi Camera
        self.picam2 = Picamera2()
        preview_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
        self.picam2.configure(preview_config)
        self.picam2.start()
        self.is_detecting = True
        
        while self.is_detecting:
            # Capture frame from Pi Camera
            frame = self.picam2.capture_array()
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Draw rectangle around faces and show distance
            for (x, y, w, h) in faces:
                # Calculate distance
                distance = self.calculate_distance(w)
                
                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add distance text
                distance_text = f"Distance: {distance:.2f}m"
                cv2.putText(frame, distance_text, (x, y-10),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            
            # Convert frame to PhotoImage
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
            
            # Update video label
            self.video_label.configure(image=photo)
            self.video_label.image = photo
            
            # Update GUI
            self.root.update()
        
        if self.picam2 is not None:
            self.picam2.stop()
    
    def stop_face_detection(self):
        self.is_detecting = False
        if self.picam2 is not None:
            self.picam2.stop()
        self.video_label.configure(image='')
        
    def check_activation(self, event):
        command = self.text_entry.get().upper()
        if command == "ACTIVATE":
            self.status_indicator.configure(text="ONLINE", style="Green.TLabel")
            self.text_entry.delete(0, tk.END)  # Clear the entry field
            # Start face detection in a separate thread
            self.detection_thread = threading.Thread(target=self.start_face_detection)
            self.detection_thread.daemon = True
            self.detection_thread.start()
        elif command == "DEACTIVATE":
            self.status_indicator.configure(text="OFFLINE", style="Red.TLabel")
            self.text_entry.delete(0, tk.END)  # Clear the entry field
            self.stop_face_detection()

def main():
    root = tk.Tk()
    app = BlackGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
