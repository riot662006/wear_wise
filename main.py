import cv2

win_name = "Smart Mirror (MVP)"


def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Camera not found")
        return

    while True:
        ret, frame = cap.read()

        if not ret: 
            print("Camera not found")
            break

        frame = cv2.flip(frame, 1) # flip frame to make it mirror the image

        # make frame fullscreen
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        cv2.imshow("Smart Mirror (MVP)", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
