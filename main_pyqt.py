import sys
import cv2
import face_recognition
import numpy as np
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer


class ClassroomAttendanceApp(QWidget):
    def __init__(self):
        super().__init__()

        # Student Data
        self.student_images = {
            "Bresto k Benny": "images/222507.jpg",
            "Bestwin Paul": "images/222725.jpg",
            "Christo Sojan": "images/222907.jpg",
            "Christopher Biju": "images/222909.jpg",
        }
        self.known_encodings, self.student_names = self.encode_student_faces()

        # Attendance Data
        self.absent_students = set()
        self.permitted_outside = set()
        self.alert_timestamps = {}

        # Class Schedule
        self.schedule = [
            ("80:38", "08:39"), ("08:39", "08:40"), ("09:00", "09:01"), ("09:01", "09:02"),

            ("09:02", "09:03"), ("09:03", "09:04"), ("10:04", "10:05"),("10:28", "10:29"),

            ("10:35", "10:38"), ("10:38", "10:39"),("10:39", "10:40"), ("10:40", "10:41"),

            ("10:41", "10:42"), ("10:42", "10:43"),("10:43", "10:44"), ("10:44", "10:45"),

            ("10:46", "10:47"),("10:47", "10:48"), ("10:48", "10:49"),  ("10:49", "10:50"),

            ("10:50", "10:51"), ("10:51", "10:52"), ("10:52", "10:53"), ("10:53", "10:54"),

            ("10:54", "10:55"), ("10:55", "10:56"), ("10:56", "10:57"), ("10:57", "10:58"),
        ]
        self.breaks = [("01:45", "02:00"), ("02:45", "02:50"), ("17:00", "17:20")]

        self.current_class = None
        self.class_reminder_shown = False
        self.break_time_shown = False
        self.camera_active = False  # Monitoring starts only after attendance is submitted

        # GUI Setup
        self.init_ui()

        # Reminder Timer (Checks Every Second)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_class_start)
        self.reminder_timer.start(1000)  # Check every second

        # Camera Timer (For Face Recognition)
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.monitor_outside_camera)
        self.camera_timer.start(1000)  # Check every second

        # OpenCV Camera
        self.cap = cv2.VideoCapture(0)

    def encode_student_faces(self):
        """Load known face encodings from student images."""
        known_encodings = []
        student_names = []
        
        for name, image_path in self.student_images.items():
            image = face_recognition.load_image_file(image_path)
            encoding = face_recognition.face_encodings(image)
            if encoding:
                known_encodings.append(encoding[0])
                student_names.append(name)
            else:
                print(f"Warning: No face found in {image_path}")
        
        return known_encodings, student_names

    def init_ui(self):
        """Initialize the GUI layout."""
        self.setWindowTitle("Classroom Attendance System")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        # Title
        self.title_label = QLabel("Classroom Attendance System", self)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        layout.addWidget(self.title_label)

        # Table for Attendance
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Student Name", "Present", "Permission"])
        self.table.setRowCount(len(self.student_names))

        self.checkboxes_attendance = {}
        self.checkboxes_permission = {}

        for row, student in enumerate(self.student_names):
            self.table.setItem(row, 0, QTableWidgetItem(student))

            attendance_checkbox = QCheckBox()
            permission_checkbox = QCheckBox()

            self.table.setCellWidget(row, 1, attendance_checkbox)
            self.table.setCellWidget(row, 2, permission_checkbox)

            self.checkboxes_attendance[student] = attendance_checkbox
            self.checkboxes_permission[student] = permission_checkbox

        layout.addWidget(self.table)

        # Submit Button
        self.submit_button = QPushButton("Submit Attendance", self)
        self.submit_button.clicked.connect(self.submit_attendance)
        layout.addWidget(self.submit_button)

        # Camera Feed Label
        self.camera_label = QLabel(self)
        layout.addWidget(self.camera_label)

        self.setLayout(layout)

    def submit_attendance(self):
        """Record attendance and permissions from checkboxes."""
        self.absent_students.clear()
        self.permitted_outside.clear()

        for student in self.student_names:
            if not self.checkboxes_attendance[student].isChecked():
                self.absent_students.add(student)

            if self.checkboxes_permission[student].isChecked():
                self.permitted_outside.add(student)

        self.camera_active = True  # Start monitoring only after attendance submission
        print("✅ Attendance Submitted! Monitoring started.")

    def is_break_time(self):
        """Check if the current time is within a break period."""
        current_time = datetime.now().strftime("%H:%M")
        return any(start <= current_time < end for start, end in self.breaks)

    def check_class_start(self):
        """Check if a new class has started and show a reminder."""
        current_time = datetime.now().strftime("%H:%M")
        new_class = next((start for start, _ in self.schedule if start <= current_time < _), None)

        if new_class != self.current_class:
            self.current_class = new_class
            self.class_reminder_shown = False  # Reset reminder flag for new class

        if self.current_class and not self.class_reminder_shown:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Class Reminder")
            msg.setText("⏰ A new class has started! Please mark the students present or absent.")
            msg.exec_()
            self.class_reminder_shown = True  # Don't show again in this class

    def monitor_outside_camera(self):
        """Monitor the camera for absent students found outside and update the camera feed."""
        if not self.camera_active:
            return  # Don't run monitoring if attendance isn't submitted

        current_time = datetime.now().strftime("%H:%M")

        if self.is_break_time():
            if not self.break_time_shown:
                print("⏳ Break Time: Skipping monitoring.")
                self.break_time_shown = True  # Show message only once per break
            return
        else:
            self.break_time_shown = False  # Reset flag when break ends

        ret, frame = self.cap.read()
        if not ret:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(q_img))

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.5)
            name = "Unknown"
            if True in matches:
                first_match_index = matches.index(True)
                name = self.student_names[first_match_index]

            if name in self.absent_students and name not in self.permitted_outside:
                if self.alert_timestamps.get(name) != self.current_class:
                    print(f"🚨 ALERT: {name} was marked absent but found outside without permission!")
                    self.alert_timestamps[name] = self.current_class

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClassroomAttendanceApp()
    window.show()
    sys.exit(app.exec_())
