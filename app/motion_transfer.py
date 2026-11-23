from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np
import mediapipe as mp


class MotionTransferWorker(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, image_path, output_dir, person_scale, smoothing, keep_background):
        super().__init__()
        self.video_path = Path(video_path)
        self.image_path = Path(image_path)
        self.output_dir = Path(output_dir)
        self.person_scale = float(person_scale)
        self.smoothing = float(smoothing)
        self.keep_background = bool(keep_background)

    def run(self):
        try:
            self.process()
        except Exception as exc:
            self.failed.emit(f"Erreur : {exc}")

    def extract_person(self, image_bgr):
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        with mp.ImageSizer() as segmenter:
            result = segmenter.process(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        mask = result.segmentationMask
        mask = (mask > 0.5).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        person = cv2.bitwise_and(image_bgr, image_bgr, mask=mask)
        alpha = mask.astype(np.float32) / 255.0
        rgba = np.dstack([person, alpha * 255]).astype(np.uint8)
        return rgba, mask

    def get_pose(self, frame, pose):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)
        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks.landmark
        h, w = frame.shape[:2]
        points = {}
        names = {
            "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
            "left_hip": 23, "right_hip": 24,
            "left_elbow": 13, "right_elbow": 14,
            "left_wrist": 15, "right_wrist": 16,
            "left_knee": 25, "right_knee": 26,
            "left_ankle": 27, "right_ankle": 28
        }
        for name, index in names.items():
            lm = landmarks[index]
            points[name] = np.array([lm.x * w, lm.y * h], dtype=np.float32)
        return points

    def target_transform(self, source_points, target_points, target_size, person_scale):
        source_center = (source_points["left_shoulder"] + source_points["right_shoulder"]) / 2
        target_center = (target_points["left_shoulder"] + target_points["right_shoulder"]) / 2

        source_width = np.linalg.norm(source_points["right_shoulder"] - source_points["left_shoulder"])
        target_width = np.linalg.norm(target_points["right_shoulder"] - target_points["left_shoulder"])

        if source_width < 1:
            source_width = 1
        scale = (target_width / source_width) * self.person_scale

        source_hip = (source_points["left_hip"] + source_points["right_hip"]) / 2
        target_hip = (target_points["left_hip"] + target_points["right_hip"]) / 2

        angle = np.arctan2(
            target_points["right_shoulder"][1] - target_points["left_shoulder"][1],
            target_points["right_shoulder"][0] - target_points["left_shoulder"][0]
        ) - np.arctan2(
            source_points["right_shoulder"][1] - source_points["left_shoulder"][1],
            source_points["right_shoulder"][0] - source_points["left_shoulder"][0]
        )

        center = target_hip
        matrix = cv2.getRotationMatrix2D(tuple(center), np.degrees(angle), scale)
        offset = target_center - source_center
        matrix[0, 2] += offset[0]
        matrix[1, 2] += offset[1]
        return matrix

    def process(self):
        self.message.emit("Chargement de l’image source…")
        image = cv2.imread(str(self.image_path))
        if image is None:
            raise RuntimeError("Impossible de lire l’image source.")

        rgba, _ = self.extract_person(image)
        ys, xs = np.where(rgba[:, :, 3] > 10)
        if len(xs) == 0:
            raise RuntimeError("Aucune personne détectée dans l’image source.")

        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        person = rgba[y1:y2 + 1, x1:x2 + 1]

        self.message.emit("Initialisation de MediaPipe Pose…")
        pose = mp.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        capture = cv2.VideoCapture(str(self.video_path))
        if not capture.isOpened():
            raise RuntimeError("Impossible d’ouvrir la vidéo de référence.")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = max(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 1)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{self.video_path.stem}_motion_transfer.mp4"
        writer = cv2.VideoWriter(
            str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            capture.release()
            raise RuntimeError("Impossible de créer le fichier MP4 de sortie.")

        # Pose de référence de l’image : posture neutre debout.
        image_height, image_width = image.shape[:2]
        source_points = {
            "nose": np.array([image_width / 2, image_height * 0.18], np.float32),
            "left_shoulder": np.array([image_width * 0.38, image_height * 0.32], np.float32),
            "right_shoulder": np.array([image_width * 0.62, image_height * 0.32], np.float32),
            "left_hip": np.array([image_width * 0.42, image_height * 0.62], np.float32),
            "right_hip": np.array([image_width * 0.58, image_height * 0.62], np.float32),
        }

        previous_matrix = None
        index = 0

        self.message.emit("Génération de la vidéo…")
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            target_points = self.get_pose(frame, pose)
            if target_points is None:
                if previous_matrix is None:
                    index += 1
                    continue
                matrix = previous_matrix
            else:
                matrix = self.target_transform(
                    source_points, target_points, (width, height), self.person_scale
                )
                if previous_matrix is not None:
                    matrix = previous_matrix * self.smoothing + matrix * (1 - self.smoothing)
                previous_matrix = matrix

            canvas = frame.copy() if self.keep_background else np.zeros_like(frame)

            transformed = cv2.warpAffine(
                person, matrix, (width, height),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )

            alpha = transformed[:, :, 3].astype(np.float32) / 255.0
            alpha = alpha[:, :, None]
            rgb = transformed[:, :, :3].astype(np.float32)
            canvas = canvas.astype(np.float32)
            canvas = rgb * alpha + canvas * (1 - alpha)
            canvas = canvas.astype(np.uint8)

            writer.write(canvas)
            index += 1
            self.progress.emit(int(100 * index / total))

        capture.release()
        writer.release()
        pose.close()

        if index == 0:
            raise RuntimeError("Aucune image exploitable n’a été trouvée dans la vidéo.")

        self.message.emit(f"Export terminé : {output_path}")
        self.finished_ok.emit(str(output_path))
