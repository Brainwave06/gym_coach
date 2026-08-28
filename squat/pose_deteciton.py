"""
Step 1: Video Capture + Pose Detection (New Tasks API - MediaPipe >= 0.10 / 1.0)
----------------------------------------------------------------------------------
ده بيستخدم الـ Tasks API الجديد (mp.tasks) بدل الـ Legacy Solutions API
(mp.solutions) اللي اتشالت من MediaPipe 1.0.

قبل التشغيل: لازم يكون عندك ملف الموديل "pose_landmarker_lite.task"
في نفس مجلد المشروع (شوف تعليمات التحميل في الرسالة).

جرب الملف ده لوحده الأول. اضغط 'q' عشان تقفل الكاميرا.
"""

import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_PATH = "pose_landmarker_lite.task"

# لسته توصيلات الهيكل العظمي (skeleton) - أزواج من أرقام الـ landmarks
# اللي المفروض يتوصل بينهم بخط. الترقيم ده ثابت ومعروف من MediaPipe Pose
# (33 نقطة: 0=الأنف ... 11/12=الكتفين ... 23/24=الحوض ... 27/28=الكاحل).
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
]


def draw_landmarks(frame, landmarks):
    """
    بترسم الـ skeleton يدويًا بـ OpenCV بدل ما نعتمد على drawing_utils
    القديمة (اللي اتشالت). landmarks هنا هي pose_landmarks_list[0]
    الراجعة من نتيجة الكشف، كل نقطة فيها x,y بين 0 و 1 (نسبة للصورة).
    """
    h, w, _ = frame.shape
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    # الخطوط (العظام)
    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx < len(points) and end_idx < len(points):
            cv2.line(frame, points[start_idx], points[end_idx], (255, 255, 255), 2)

    # النقاط (المفاصل)
    for point in points:
        cv2.circle(frame, point, 4, (0, 255, 0), -1)


def main():
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,  # وضع الفيديو: كل فريم بنبعته ومعاه timestamp
        num_poses=1,
    )

    landmarker = mp_vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("مقدرتش أفتح الكاميرا. جرب تغيّر الرقم من 0 لـ 1.")
        return

    start_time = time.time()

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("فشل في قراءة فريم من الكاميرا.")
            break

        frame = cv2.flip(frame, 1)  # عشان يبقى زي المرآة

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # في وضع الفيديو (VIDEO mode) لازم نبعت timestamp بالميلي ثانية،
        # ولازم يكون تصاعدي دايمًا (كل فريم أكبر من اللي قبله)
        timestamp_ms = int((time.time() - start_time) * 1000)

        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            # result.pose_landmarks ممكن يبقى فيه أكتر من جسم، إحنا بنشتغل بأول واحد بس
            draw_landmarks(frame, result.pose_landmarks[0])
        else:
            cv2.putText(
                frame, "Body not detected", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
            )

        cv2.imshow("Step 1 - Pose Detection (Tasks API)", frame)

        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

    landmarker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()