#!/usr/bin/env python3

"""
Black GUI
A simple application with a black background.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import cv2
import threading
from PIL import Image, ImageTk
import numpy as np
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from picamera2 import Picamera2

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
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.cap = None
        self.is_detecting = False
        self.detection_thread = None
        
        # Threat detection variables
        self.threat_detected = False
        self.threat_start_time = None
        self.threat_duration = 60  # seconds
        
        # Known parameters for distance estimation
        self.known_face_width = 0.15  # Average face width in meters
        self.known_distance = 1.0     # Calibration distance in meters
        self.known_pixels = 200       # Calibration pixels at known distance
        self.focal_length = (self.known_pixels * self.known_distance) / self.known_face_width
        
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
        
        self.picam2 = None
    
    def calculate_distance(self, face_width_pixels):
        # Using the formula: distance = (known_face_width * focal_length) / face_width_pixels
        distance = (self.known_face_width * self.focal_length) / face_width_pixels
        return distance
        
    def start_face_detection(self):
        try:
            # Initialize Pi Camera
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(2)  # Camera warm-up

            self.is_detecting = True
            
            while self.is_detecting:
                try:
                    # Capture frame from Pi Camera
                    frame = self.picam2.capture_array()
                    
                    # Convert to grayscale for face detection
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    # Check if threat timer has expired
                    if self.threat_detected and self.threat_start_time is not None:
                        elapsed_time = time.time() - self.threat_start_time
                        if elapsed_time >= self.threat_duration:
                            self.threat_detected = False
                            self.threat_start_time = None
                    
                    # Draw rectangle around faces and show distance
                    for (x, y, w, h) in faces:
                        # Calculate distance
                        distance = self.calculate_distance(w)
                        
                        # Update threat status
                        if distance < 1.0 and not self.threat_detected:
                            self.threat_detected = True
                            self.threat_start_time = time.time()
                            self.send_threat_email()  # Send email alert
                        
                        # Set color based on threat status
                        box_color = (0, 0, 255) if self.threat_detected else (0, 255, 0)
                        text_color = (0, 0, 255) if self.threat_detected else (0, 255, 0)
                        
                        # Draw rectangle
                        cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)
                        
                        # Add distance text
                        distance_text = f"Distance: {distance:.2f}m"
                        cv2.putText(frame, distance_text, (x, y-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1.5, text_color, 3)
                        
                        # Add threat warning if threat is detected
                        if self.threat_detected:
                            threat_text = "THREAT DETECTED"
                            # Get text size for centering
                            text_size = cv2.getTextSize(threat_text, cv2.FONT_HERSHEY_SIMPLEX, 2, 3)[0]
                            text_x = (frame.shape[1] - text_size[0]) // 2
                            cv2.putText(frame, threat_text, (text_x, 50),
                                      cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    
                    # Convert frame to PhotoImage
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                    
                    # Update video label
                    self.video_label.configure(image=photo)
                    self.video_label.image = photo
                    
                    # Update GUI
                    self.root.update()
                    
                except Exception as e:
                    print(f"Error in capture loop: {str(e)}")
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to initialize camera: {str(e)}")
            self.status_indicator.configure(text="OFFLINE", style="Red.TLabel")
            self.is_detecting = False
        finally:
            if self.picam2 is not None:
                self.picam2.close()
                self.picam2 = None
    
    def stop_face_detection(self):
        self.is_detecting = False
        if self.picam2 is not None:
            self.picam2.close()
            self.picam2 = None
        if self.detection_thread is not None and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        self.video_label.configure(image='')
        cv2.destroyAllWindows()  # Clean up any OpenCV windows
        
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
            # Reset the video frame
            self.video_label.configure(image='')

    def send_threat_email(self):
        sender_email = "MattheuPi@programmer.net"
        receiver_email = "mattheujimenez@gmail.com"  # or any email you want to notify
        password = "4h#qzwZHTx*P!MS"  # Use an app password if 2FA is enabled

        subject = "Threat Detected Alert"
        body = "A threat has been detected by your Motion Tracking Software."

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Threat alert email sent!")
        except Exception as e:
            print(f"Failed to send email: {e}")

def main():
    root = tk.Tk()
    app = BlackGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
