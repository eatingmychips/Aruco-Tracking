import cv2
import cv2.aruco as aruco
import threading
from pypylon import pylon
import numpy as np
import time
from datetime import datetime
import pandas as pd
import serial
import pygame
import os
import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
from tkinter import filedialog



# Global variable for recording state
#Test comment
recording = False
pose_data_list = []
arduino_data = None
directory_selected_flag = False

pygame.init()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

selected_directory = None




# GUI function to toggle recording
def toggle_recording():
    global recording, pose_data_list
    if recording:
        # Stop recording and save data to CSV
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = os.path.join(selected_directory, f"pose_data_{timestamp}.csv")
        
        # Save pose data to CSV
        df = pd.DataFrame(pose_data_list, columns=['time', 'pose', 'arduino_data'])
        df.to_csv(output_filename, index=False)
        
        print(f"Recording stopped. Data saved to {output_filename}")
        pose_data_list = []  # Reset list after saving
        recording = False
        record_button.config(text="Start Recording")
        style.configure('Recording.TButton', font=('Helvetica', 20), background = 'white', foreground = 'black')
    else:
        print("Started Recording")
        recording = True
        record_button.config(text="Stop Recording")
        style.configure('Recording.TButton', font=('Helvetica', 20), background = 'red', foreground = 'salmon')
        style.configure('Comport.TCombobox', background = 'white', foreground = 'white')


# definition of event handler class 
class TriggeredImage(pylon.ImageEventHandler):
    def __init__(self):
        super().__init__()
        self.grab_times = []
    def OnImageGrabbed(self, camera, grabResult):
        self.grab_times.append(grabResult.TimeStamp)

def read_arduino_data(ser):
    """Read data from Arduino via serial."""
    if ser.in_waiting > 0:
        try:
            data = ser.readline().decode('utf-8').strip()  # Read and decode the string
            return data  # Return the entire string (e.g., "Left, 50Hz, 500ms")
        except Exception as e:
            print(f"Error reading from serial: {e}")
    return None

def get_command(dur, freq, selection):
    dur_hex = hex(int(dur/10))[2:].zfill(2)
    freq_hex = hex(int(freq))[2:].zfill(2)
    prefix = "B1"
    # Command prefixes for each selection
    cmds = {
        "Both": "E0",
        "Left": "A0",
        "Right": "B0"
    }
    return prefix + cmds[selection] + dur_hex + freq_hex

def main():
    global recording, pose_data_list, selected_directory, last_control_time
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    camera.Open()
    pylon.FeaturePersistence.Load(r"G:\biorobotics\data\InvertedClimbing\ARUCO1200.pfs", camera.GetNodeMap())

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        # Initialize the previous button states correctly
    if joysticks:
        previous_button_states = [False] * joysticks[0].get_numbuttons()


    # Set up image converter for OpenCV
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    while not selected_port.get():
        com_port_dropdown.config(values=get_com_ports())
        com_port = None
    while not selected_directory: 
        pass

    com_port = selected_port.get()
    SerialObj = serial.Serial(com_port, 115200, timeout=0.1)  # Change 'COM3' to the correct port for your Arduino
    
    # Now Allow record button to work
    record_button.config(state="normal")
    
    # Set initial frequency to 10
    dur = 500
    try:
        while camera.IsGrabbing():
            com_port = selected_port.get()
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            
            if grab_result.GrabSucceeded():

                for joystick in joysticks:
                    # Iterate through each button to track state changes
                    
                    for button in range(joystick.get_numbuttons()):
                        current_button_state = joystick.get_button(button)
                        
                        if current_button_state and not previous_button_states[button]:                 
                            # Button was pressed (transition from not pressed to pressed)

                            if button == 0: # A Button
                                print("We have pressed button: 'A', stimulating both elytra")
                                side = "Both"
                                freq = int(frequency_var.get())
                                message = get_command(dur, freq, side)
                                SerialObj.write(message.encode('utf-8'))
                                data = (f"Both, {freq}")

                            elif button == 3: # Y Button
                                print("We have pressed button: 'Y', stimulating right antenna")
                                side = "Right"
                                freq = int(frequency_var.get())
                                message = get_command(dur, freq, side)
                                SerialObj.write(message.encode('utf-8'))
                                data = (f"Right, {freq}")

                            elif button == 2:  # X Button
                                print("We have pressed button: 'X', stimulating left antenna")
                                side = "Left"
                                freq = int(frequency_var.get())
                                message = get_command(dur, freq, side)
                                SerialObj.write(message.encode('utf-8'))
                                data = (f"Left, {freq}")

                            elif button == 1:  # B Button
                                print("We have pressed button: 'B', initiating backwards walking")
                                char = 'B'
                                SerialObj.write(str.encode(char))

                            elif button == 5: #Right Bumper
                                print("We have pressed Right Bumper, initiating Stop")
                                char = 'S'
                                SerialObj.write(str.encode(char))
                            
                        # Update the previous state for the next iteration
                        previous_button_states[button] = current_button_state

                # Access the image data
                image = converter.Convert(grab_result)
                img = image.GetArray()
                
                corners, ids, rejected = detector.detectMarkers(img)
                if ids is not None and 1 in ids:
                    idx = list(ids.flatten()).index(1)
                    marker_corners = corners[idx][0]
                    center = marker_corners.mean(axis=0)
                    dx, dy = marker_corners[1] - marker_corners[0]
                    angle = np.arctan2(dy, dx)
                    insect_pose = [center[0], center[1], angle]

                    # Optionally display
                    cv2.aruco.drawDetectedMarkers(img, [corners[idx]])
                    cv2.circle(img, tuple(center.astype(int)), 5, (0,255,0), -1)
                    cv2.putText(img, f"Angle: {angle:.1f}", tuple(center.astype(int)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
                cv2.imshow('Frame', img)
                
                if recording: 
                    # Only process if marker ID 1 is detected
                    pose_data_list.append((time.time(), insect_pose, data))
                
                # Reset data to empty list. 
                data = ""
                    
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    
    finally:
        # Stop grabbing and release resources
        camera.StopGrabbing()
        camera.Close()
        cv2.destroyAllWindows()

def start_main_thread():
    selected_com_port = selected_port.get()
    if selected_com_port(): 
        main_thread = threading.Thread(target=main)
        main_thread.start()
        record_button.config(state="normal")
    else: 
        record_button.config(state = 'disabled')

def directory_press(): 
    global selected_directory
    selected_directory = filedialog.askdirectory()
    


# GUI setup
root = tk.Tk()
root.geometry('650x400')
root.title("Recording Control")
style = ttk.Style()
style.configure('Recording.TButton', font=('Helvetica', 20))
style.configure('FileDirectory.TButton', font=('Helvetica', 10))

style.map('Comport.TCombobox',
    fieldbackground=[('readonly', 'red')],
    selectbackground=[('readonly', 'red')],
    selectforeground=[('readonly', 'white')]
)
style.configure('Comport.TCombobox',
    background='white',
    foreground='white',
    arrowcolor='white'
)


# Function to get available COM ports
def get_com_ports():
    return [port.device for port in serial.tools.list_ports.comports()]


# Create a frame for the left side
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, padx=10, pady=10)

# Create a frame for the right side
right_frame = tk.Frame(root)
right_frame.pack(side=tk.RIGHT, padx=10, pady=10)

# Add widgets to the left frame
selected_port = tk.StringVar()
com_port_label = ttk.Label(left_frame, text="Select COM Port:")
com_port_label.pack(pady=(20, 5))

com_port_dropdown = ttk.Combobox(left_frame, textvariable=selected_port, style='Comport.TCombobox', values=get_com_ports())
com_port_dropdown.pack(pady=(0, 20))

file_button = ttk.Button(left_frame, text="Choose Directory", style='FileDirectory.TButton', command=directory_press, state="normal")
file_button.pack(pady=20)

record_button = ttk.Button(left_frame, text="Start Recording", style='Recording.TButton', command = toggle_recording, state = "disabled")
record_button.pack(pady=(20, 5))


freq_row = tk.Frame(left_frame)
freq_row.pack(pady=(20, 5))

frequency_display = tk.Label(freq_row, text="Frequency (Hz):", font=('Helvetica', 10))
frequency_display.grid(row=0, column=0, padx=(0, 5))

frequency_var = tk.StringVar(value="10")
freq_entry = tk.Entry(freq_row, textvariable=frequency_var, width=5)
freq_entry.grid(row=0, column=1)


# Add instructions to the right frame
instructions_label = tk.Label(right_frame, text="Instructions:\n1. Select a COM port.\n2. Choose a directory to store recorded data.\n3. Start recording.",
                              justify=tk.LEFT, anchor='w', font=('Helvetica', 10), wraplength=300)
instructions_label.pack(pady=20, fill='x')

stimulation_instructions = tk.Label(right_frame, text="Press X to stimulate left antenna.\nPress Y to stimulate right antenna.\nPress A to stimulate both elytra.\nPress Start to increase frequency",
                                    justify=tk.LEFT, anchor='w', font=('Helvetica', 10), wraplength=300)
stimulation_instructions.pack(pady=20, fill='x')



main_thread = threading.Thread(target=main)
main_thread.start()

root.mainloop()