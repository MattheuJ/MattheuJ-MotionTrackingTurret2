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
        # Try common locations for the haarcascade file
        possible_paths = [
            "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "haarcascade_frontalface_default.xml",  # In current directory
        ]
        cascade_path = None
        for path in possible_paths:
            if os.path.exists(path):
                cascade_path = path
                break
        if cascade_path is None:
            raise FileNotFoundError("Could not find haarcascade_frontalface_default.xml")
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
        self.text_frame.pack(side="left", fill="y", padx=20, pady=20)
        
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
        
        # Create a StringVar to track the entry text
        self.entry_text = tk.StringVar()
        
        self.text_entry = tk.Entry(entry_frame,
                                 font=("Courier", 40),
                                 bg="black",
                                 fg="white",
                                 insertbackground="white",  # Cursor color
                                 width=20,
                                 textvariable=self.entry_text)  # Use StringVar
        self.text_entry.pack(side="left")
        
        # Create video frame
        self.video_frame = ttk.Frame(self.main_frame, style="Black.TFrame")
        self.video_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Create and configure video label
        self.video_label = tk.Label(self.video_frame, bg="black", width=80, height=30)  # Set size in text units
        self.video_label.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Bind Enter key to check for ACTIVATE/DEACTIVATE
        self.text_entry.bind('<Return>', self.check_activation)
        
        # Make sure the text entry is enabled and focused
        self.text_entry.config(state='normal')
        self.text_entry.focus_set()
        
        self.picam2 = None
    
    def calculate_distance(self, face_width_pixels):
        # Using the formula: distance = (known_face_width * focal_length) / face_width_pixels
        distance = (self.known_face_width * self.focal_length) / face_width_pixels
        return distance
        
    def start_face_detection(self):
        try:
            print("Initializing Raspberry Pi Camera...")  # Debug print
            # Initialize Pi Camera with higher resolution
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (1920, 1080)},
                lores={"format": "YUV420", "size": (640, 480)}
            )
            self.picam2.configure(config)
            self.picam2.start()
            print("Camera started successfully")  # Debug print
            time.sleep(2)  # Camera warm-up

            self.is_detecting = True
            print("Starting detection loop...")  # Debug print
            print("Frame captured successfully")  # Moved here to only print once
            
            while self.is_detecting:
                try:
                    # Capture frame from Pi Camera
                    frame = self.picam2.capture_array()
                    if frame is None:
                        print("Failed to capture frame")  # Debug print
                        continue
                        
                    # Resize frame for processing while maintaining aspect ratio
                    height, width = frame.shape[:2]
                    scale = min(640/width, 480/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                    
                    # Apply image preprocessing
                    # Convert to grayscale
                    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                    
                    # Apply histogram equalization to improve contrast
                    gray = cv2.equalizeHist(gray)
                    
                    # Apply slight Gaussian blur to reduce noise
                    gray = cv2.GaussianBlur(gray, (5, 5), 0)
                    
                    # Detect faces with adjusted parameters
                    faces = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,     # Decreased from 1.15 to be even more sensitive
                        minNeighbors=3,      # Decreased from 4 to detect more faces
                        minSize=(30, 30),    # Decreased from 40 to detect smaller faces
                        maxSize=(400, 400),  # Increased maximum face size
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    
                    # Filter out false positives by checking face proportions
                    filtered_faces = []
                    for (x, y, w, h) in faces:
                        # Check if the face has reasonable proportions (width/height ratio)
                        aspect_ratio = w / float(h)
                        if 0.3 < aspect_ratio < 2.5:  # Much wider range for aspect ratio
                            filtered_faces.append((x, y, w, h))
                    
                    faces = filtered_faces
                    
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
                        
                        # Draw rectangle with thicker lines
                        cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 3)
                        
                        # Add distance text with improved visibility
                        distance_text = f"Distance: {distance:.2f}m"
                        cv2.putText(frame, distance_text, (x, y-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
                        
                        # Add threat warning if threat is detected
                        if self.threat_detected:
                            threat_text = "THREAT DETECTED"
                            # Get text size for centering
                            text_size = cv2.getTextSize(threat_text, cv2.FONT_HERSHEY_SIMPLEX, 2, 3)[0]
                            text_x = (frame.shape[1] - text_size[0]) // 2
                            cv2.putText(frame, threat_text, (text_x, 50),
                                      cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    
                    # Display the frame using OpenCV
                    cv2.imshow("Motion Tracking System", frame)
                    
                    # Check for 'q' key press to quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.is_detecting = False
                        break
                    
                except Exception as e:
                    print(f"Error in capture loop: {str(e)}")  # Debug print
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"Camera initialization error: {str(e)}")  # Debug print
            messagebox.showerror("Camera Error", f"Failed to initialize camera: {str(e)}")
            self.status_indicator.configure(text="OFFLINE", style="Red.TLabel")
            self.is_detecting = False
        finally:
            cv2.destroyAllWindows()
            if self.picam2 is not None:
                self.picam2.close()
                self.picam2 = None
    
    def stop_face_detection(self):
        self.is_detecting = False
        cv2.destroyAllWindows()
        if self.picam2 is not None:
            self.picam2.close()
            self.picam2 = None
        if self.detection_thread is not None and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        self.video_label.configure(image='')
    
    def check_activation(self, event):
        command = self.entry_text.get().upper()  # Get text from StringVar
        print(f"Received command: {command}")  # Debug print
        
        if command == "ACTIVATE":
            print("Activating system...")  # Debug print
            self.status_indicator.configure(text="ONLINE", style="Green.TLabel")
            self.entry_text.set("")  # Clear the entry field
            
            # Start face detection in a separate thread
            if self.detection_thread is None or not self.detection_thread.is_alive():
                print("Starting detection thread...")  # Debug print
                self.detection_thread = threading.Thread(target=self.start_face_detection)
                self.detection_thread.daemon = True
                self.detection_thread.start()
            else:
                print("Detection thread already running")  # Debug print
                
        elif command == "DEACTIVATE":
            print("Deactivating system and shutting down...")  # Debug print
            self.status_indicator.configure(text="OFFLINE", style="Red.TLabel")
            self.entry_text.set("")  # Clear the entry field
            self.stop_face_detection()
            # Clean up and exit
            cv2.destroyAllWindows()
            self.root.quit()
            self.root.destroy()
            os._exit(0)  # Force exit the program
        else:
            print(f"Unknown command: {command}")  # Debug print
            self.entry_text.set("")  # Clear the entry field

    def send_threat_email(self):
        try:
            # Email configuration for Gmail
            sender_email = "mattheujimenez@gmail.com"  # Your Gmail address
            receiver_email = "mattheujimenez@gmail.com"  # Where to send the alert
            password = "jtpf qrei viiy ccmu"  # Replace with your Gmail App Password

            # Create message
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = "THREAT DETECTED - Motion Tracking System Alert"

            # Create email body with timestamp
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body = f"""
            THREAT ALERT

            A potential threat has been detected by your Motion Tracking System.

            Details:
            - Time: {current_time}
            - Location: Motion Tracking System
            - Status: Active Threat

            Please check your system immediately.

            This is an automated message from your Motion Tracking System.
            """

            msg.attach(MIMEText(body, "plain"))

            # Connect to Gmail's SMTP server
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
                print("Threat alert email sent successfully!")
                
        except Exception as e:
            print(f"Failed to send threat alert email: {str(e)}")
            # You might want to add additional error handling here

    def update_video_label(self, frame):
        try:
            # This runs in the main thread
            # Resize frame to match the video label size
            frame = cv2.resize(frame, (640, 480))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PhotoImage
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            
            # Update the label
            self.video_label.configure(image=photo)
            self.video_label.image = photo  # Keep a reference!
            
            # Force update
            self.video_label.update()
            print("Frame updated in GUI")  # Debug print
            
        except Exception as e:
            print(f"Error updating video label: {str(e)}")  # Debug print

    def keep_focus(self):
        """Keep focus on the text entry widget"""
        self.text_entry.focus()
        self.root.after(100, self.keep_focus)

def main():
    root = tk.Tk()
    app = BlackGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
