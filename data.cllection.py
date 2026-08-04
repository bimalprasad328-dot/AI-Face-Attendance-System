import cv2
import os
import pandas as pd

# Read student name from CSV
df = pd.read_csv("students.csv")
name = df.iloc[-1]["Name"]  # gets the latest registered student

# Create folder for student
save_path = f"dataset/{name}"
os.makedirs(save_path, exist_ok=True)

# Open camera
cam = cv2.VideoCapture(0)
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

count = 0
print(f"Capturing faces for: {name}. Look at the camera...")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        count += 1
        face_img = gray[y:y+h, x:x+w]
        cv2.imwrite(f"{save_path}/{count}.jpg", face_img)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame, f"Captured: {count}/50", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Face Collection - Press Q to quit", frame)

    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 50:
        break

cam.release()
cv2.destroyAllWindows()
cam.release()
cv2.destroyAllWindows()

print(f"Done! {count} images saved to {save_path}/")