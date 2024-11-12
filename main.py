import sys
import cv2
import mediapipe as mp
import pyautogui
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSlider, QGroupBox, QGridLayout
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt


class HandMouseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Hand Controlled Mouse')
        self.setGeometry(100, 100, 800, 600)

        # Initialize variables before calling initUI
        # Variables for stabilization and movement scaling
        self.prev_mouse_x, self.prev_mouse_y = None, None
        self.prev_positions = []
        self.smoothing_window_size = 7  # Number of frames to average over
        self.movement_threshold = 10    # Minimum movement in pixels to consider
        self.scaling_factor_x = 1.5     # Scaling factor for X-axis to expand movement range
        self.scaling_factor_y = 1.8     # Scaling factor for Y-axis to expand movement range
        self.dead_zone_radius = 5       # Radius of the dead zone in pixels

        # Variables for gesture detection
        self.index_thumb_touch_start_time = None
        self.index_thumb_touching = False
        self.middle_thumb_touch_start_time = None
        self.middle_thumb_touching = False
        self.drag_mode = False

        # Gesture feedback
        self.current_gesture = 'None'

        # Click threshold
        self.click_threshold = 40  # Default value

        self.is_running = False

        # Initialize Mediapipe Hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands

        # Initialize webcam
        self.cam = cv2.VideoCapture(0)

        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()

        # Set up Mediapipe Hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)

        # Timer for frame updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Now call initUI after initializing variables
        self.initUI()

    def initUI(self):
        # Create layout
        main_layout = QVBoxLayout()
        controls_layout = QHBoxLayout()

        # Video display
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.label)

        # Gesture label
        self.gesture_label = QLabel('Gesture: None')
        self.gesture_label.setAlignment(Qt.AlignCenter)
        font = self.gesture_label.font()
        font.setPointSize(14)
        self.gesture_label.setFont(font)
        main_layout.addWidget(self.gesture_label)

        # Cursor position label
        self.cursor_label = QLabel('Cursor Position: (0, 0)')
        self.cursor_label.setAlignment(Qt.AlignCenter)
        font = self.cursor_label.font()
        font.setPointSize(12)
        self.cursor_label.setFont(font)
        main_layout.addWidget(self.cursor_label)

        # Start button
        self.start_btn = QPushButton('Start', self)
        self.start_btn.clicked.connect(self.start_app)
        controls_layout.addWidget(self.start_btn)

        # Stop button
        self.stop_btn = QPushButton('Stop', self)
        self.stop_btn.clicked.connect(self.stop_app)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        main_layout.addLayout(controls_layout)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QGridLayout()

        # Sensitivity slider
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(30)
        self.sensitivity_slider.setValue(self.movement_threshold)
        self.sensitivity_slider.valueChanged.connect(self.change_sensitivity)
        settings_layout.addWidget(QLabel('Sensitivity'), 0, 0)
        settings_layout.addWidget(self.sensitivity_slider, 0, 1)

        # Scaling factor X slider
        self.scaling_x_slider = QSlider(Qt.Horizontal)
        self.scaling_x_slider.setMinimum(10)
        self.scaling_x_slider.setMaximum(50)
        self.scaling_x_slider.setValue(int(self.scaling_factor_x * 10))
        self.scaling_x_slider.valueChanged.connect(self.change_scaling_x)
        settings_layout.addWidget(QLabel('Scaling Factor X'), 1, 0)
        settings_layout.addWidget(self.scaling_x_slider, 1, 1)

        # Scaling factor Y slider
        self.scaling_y_slider = QSlider(Qt.Horizontal)
        self.scaling_y_slider.setMinimum(10)
        self.scaling_y_slider.setMaximum(50)
        self.scaling_y_slider.setValue(int(self.scaling_factor_y * 10))
        self.scaling_y_slider.valueChanged.connect(self.change_scaling_y)
        settings_layout.addWidget(QLabel('Scaling Factor Y'), 2, 0)
        settings_layout.addWidget(self.scaling_y_slider, 2, 1)

        # Click threshold slider
        self.click_threshold_slider = QSlider(Qt.Horizontal)
        self.click_threshold_slider.setMinimum(10)
        self.click_threshold_slider.setMaximum(100)
        self.click_threshold_slider.setValue(self.click_threshold)
        self.click_threshold_slider.valueChanged.connect(self.change_click_threshold)
        settings_layout.addWidget(QLabel('Click Threshold'), 3, 0)
        settings_layout.addWidget(self.click_threshold_slider, 3, 1)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        self.setLayout(main_layout)

    def start_app(self):
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.timer.start(1)

    def stop_app(self):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()

    def change_sensitivity(self, value):
        self.movement_threshold = value

    def change_scaling_x(self, value):
        self.scaling_factor_x = value / 10

    def change_scaling_y(self, value):
        self.scaling_factor_y = value / 10

    def change_click_threshold(self, value):
        self.click_threshold = value

    def update_frame(self):
        if not self.is_running:
            return

        success, frame = self.cam.read()
        if not success:
            return

        # Flip the frame for natural interaction
        frame = cv2.flip(frame, 1)
        frame_height, frame_width, _ = frame.shape

        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the image and find hands
        results = self.hands.process(rgb_frame)

        # Reset current gesture
        self.current_gesture = 'None'

        # If hands are detected
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]

            # Draw hand landmarks on the frame
            self.mp_drawing.draw_landmarks(
                frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

            # Get coordinates of index finger tip (landmark 8)
            index_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            x = int(index_finger_tip.x * frame_width)
            y = int(index_finger_tip.y * frame_height)

            # Get coordinates of thumb tip (landmark 4)
            thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
            thumb_x = int(thumb_tip.x * frame_width)
            thumb_y = int(thumb_tip.y * frame_height)

            # Get coordinates of middle finger tip (landmark 12)
            middle_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            middle_x = int(middle_finger_tip.x * frame_width)
            middle_y = int(middle_finger_tip.y * frame_height)

            # Convert to screen coordinates with scaling factors
            screen_x = (self.screen_width / frame_width) * x * self.scaling_factor_x
            screen_y = (self.screen_height / frame_height) * y * self.scaling_factor_y

            # Clip to screen bounds to prevent out of bounds movements
            screen_x = min(max(screen_x, 0), self.screen_width)
            screen_y = min(max(screen_y, 0), self.screen_height)

            # Add current position to the list for smoothing
            self.prev_positions.append((screen_x, screen_y))

            # Keep only the last N positions for smoothing
            if len(self.prev_positions) > self.smoothing_window_size:
                self.prev_positions.pop(0)

            # Calculate the average position
            avg_x = sum(pos[0] for pos in self.prev_positions) / len(self.prev_positions)
            avg_y = sum(pos[1] for pos in self.prev_positions) / len(self.prev_positions)

            # Initialize previous mouse position if None
            if self.prev_mouse_x is None and self.prev_mouse_y is None:
                self.prev_mouse_x, self.prev_mouse_y = avg_x, avg_y

            # Calculate movement distance
            movement = ((avg_x - self.prev_mouse_x) ** 2 + (avg_y - self.prev_mouse_y) ** 2) ** 0.5

            # Only move the mouse if movement exceeds the movement threshold
            if movement > self.movement_threshold:
                pyautogui.moveTo(avg_x, avg_y)
                self.prev_mouse_x, self.prev_mouse_y = avg_x, avg_y
            else:
                # Implement dead zone to prevent minor jitter
                if movement > self.dead_zone_radius:
                    pyautogui.moveTo(avg_x, avg_y)
                    self.prev_mouse_x, self.prev_mouse_y = avg_x, avg_y
                else:
                    # Do not update mouse position
                    pass

            # Update cursor position label
            self.cursor_label.setText(f'Cursor Position: ({int(avg_x)}, {int(avg_y)})')

            # Calculate distances between fingers
            distance_index_thumb = ((x - thumb_x) ** 2 + (y - thumb_y) ** 2) ** 0.5
            distance_middle_thumb = ((middle_x - thumb_x) ** 2 + (middle_y - thumb_y) ** 2) ** 0.5

            # Gesture detection for index finger and thumb (single click and drag)
            if distance_index_thumb < self.click_threshold:
                if not self.index_thumb_touching:
                    self.index_thumb_touching = True
                    self.index_thumb_touch_start_time = time.time()
                else:
                    if not self.drag_mode:
                        touch_duration = time.time() - self.index_thumb_touch_start_time
                        if touch_duration >= 0.5:
                            pyautogui.mouseDown()
                            self.drag_mode = True
                            self.current_gesture = 'Dragging'
            else:
                if self.index_thumb_touching:
                    self.index_thumb_touching = False
                    touch_duration = time.time() - self.index_thumb_touch_start_time
                    if self.drag_mode:
                        pyautogui.mouseUp()
                        self.drag_mode = False
                        self.current_gesture = 'Drag Ended'
                    else:
                        if touch_duration < 0.3:
                            pyautogui.click()
                            pyautogui.sleep(0.2)  # Delay to prevent multiple clicks
                            self.current_gesture = 'Click'

            # Gesture detection for middle finger and thumb (double click)
            if distance_middle_thumb < self.click_threshold:
                if not self.middle_thumb_touching:
                    self.middle_thumb_touching = True
                    self.middle_thumb_touch_start_time = time.time()
            else:
                if self.middle_thumb_touching:
                    self.middle_thumb_touching = False
                    touch_duration = time.time() - self.middle_thumb_touch_start_time
                    if touch_duration < 0.3:
                        pyautogui.doubleClick()
                        pyautogui.sleep(0.2)  # Delay to prevent multiple clicks
                        self.current_gesture = 'Double Click'

            # Visual feedback for the cursor position
            cv2.circle(frame, (x, y), 10, (255, 0, 255), -1)

        else:
            # Reset previous positions if no hand is detected
            self.prev_positions.clear()
            self.prev_mouse_x, self.prev_mouse_y = None, None
            self.index_thumb_touching = False
            self.middle_thumb_touching = False
            if self.drag_mode:
                pyautogui.mouseUp()
                self.drag_mode = False
                self.current_gesture = 'Drag Ended'

            # Update cursor position label
            self.cursor_label.setText('Cursor Position: (0, 0)')

        # Update gesture label
        self.gesture_label.setText(f'Gesture: {self.current_gesture}')

        # Convert the frame to QImage
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Display the image
        self.label.setPixmap(QPixmap.fromImage(qt_image))

    def closeEvent(self, event):
        self.stop_app()
        self.cam.release()
        self.hands.close()
        cv2.destroyAllWindows()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HandMouseApp()
    window.show()
    sys.exit(app.exec_())
