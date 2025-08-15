import cv2
import numpy as np
import mediapipe as mp

win_name = "Smart Mirror (MVP)"

BG_COLOR = (0, 255, 0)

# initialize mediapipe
mp_selfie = mp.solutions.selfie_segmentation
mp_pose = mp.solutions.pose

# make frame fullscreen
cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(
    win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Camera not found")
        return
    with mp_selfie.SelfieSegmentation(model_selection=1) as seg, mp_pose.Pose(model_complexity=1) as pose:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Camera not found")
                break

            # flip frame to make it mirror the image
            frame = cv2.flip(frame, 1)

            # Process frame
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = seg.process(rgb)

            condition = np.stack(
                (results.segmentation_mask,) * 3, axis=-1) > 0.1

            output_image = np.where(
                condition, frame, cv2.GaussianBlur(frame, (55, 55), 0))

            cv2.imshow(win_name, output_image)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
