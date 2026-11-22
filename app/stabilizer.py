from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np


class StabilizeWorker(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, source_path, output_dir, smoothing, crop_percent, upscale, high_quality):
        super().__init__()
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.smoothing = int(smoothing)
        self.crop_percent = float(crop_percent)
        self.upscale = float(upscale)
        self.high_quality = bool(high_quality)

    def run(self):
        try:
            self.process()
        except Exception as exc:
            self.failed.emit(f"Erreur : {exc}")

    def process(self):
        capture = cv2.VideoCapture(str(self.source_path))
        if not capture.isOpened():
            raise RuntimeError("Impossible d’ouvrir la vidéo source.")

        fps = capture.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        total = max(total, 1)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{self.source_path.stem}_stabilized.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_width = int(round(width * self.upscale))
        out_height = int(round(height * self.upscale))
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (out_width, out_height))

        if not writer.isOpened():
            capture.release()
            raise RuntimeError("Impossible de créer le fichier MP4 de sortie.")

        orb = cv2.ORB_create(nfeatures=3000, scaleFactor=1.2, nlevels=8)
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        ok, previous = capture.read()
        if not ok:
            capture.release()
            writer.release()
            raise RuntimeError("La vidéo ne contient aucune image lisible.")

        previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
        transforms = [np.eye(3, dtype=np.float64)]

        self.message.emit("Analyse du mouvement…")
        index = 1
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            kp1, des1 = orb.detectAndCompute(previous_gray, None)
            kp2, des2 = orb.detectAndCompute(gray, None)

            if des1 is None or des2 is None or len(kp1) < 12 or len(kp2) < 12:
                transform = np.eye(3, dtype=np.float64)
            else:
                matches = matcher.match(des1, des2)
                if len(matches) < 12:
                    transform = np.eye(3, dtype=np.float64)
                else:
                    matches = sorted(matches, key=lambda m: m.distance)[:500]
                    src = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
                    dst = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
                    matrix, mask = cv2.estimateAffinePartial2D(
                        src, dst, method=cv2.RANSAC,
                        ransacReprojThreshold=3.0, maxIters=5000, confidence=0.995
                    )
                    if matrix is None:
                        transform = np.eye(3, dtype=np.float64)
                    else:
                        transform = np.vstack([matrix, [0.0, 0.0, 1.0]])

            transforms.append(transform.astype(np.float64))
            previous_gray = gray
            index += 1
            self.progress.emit(int(45 * index / total))

        capture.release()

        # Conversion en trajectoire cumulée puis lissage.
        trajectories = []
        current = np.eye(3, dtype=np.float64)
        for transform in transforms:
            current = current @ transform
            trajectories.append(current.copy())

        trajectories = np.array(trajectories)
        smoothed = self.smooth_trajectories(trajectories, self.smoothing)

        self.message.emit("Génération de la vidéo stabilisée…")
        capture = cv2.VideoCapture(str(self.source_path))
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (out_width, out_height))

        crop_x = int(width * self.crop_percent / 100.0)
        crop_y = int(height * self.crop_percent / 100.0)
        crop_width = max(width - 2 * crop_x, 32)
        crop_height = max(height - 2 * crop_y, 32)

        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            matrix = smoothed[index][:2, :]
            corrected = cv2.warpAffine(
                frame, matrix, (width, height),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_REFLECT
            )
            corrected = corrected[crop_y:crop_y + crop_height, crop_x:crop_x + crop_width]

            if self.upscale != 1.0:
                interpolation = cv2.INTER_LANCZOS4 if self.upscale > 1.0 else cv2.INTER_AREA
                corrected = cv2.resize(
                    corrected, (out_width, out_height), interpolation=interpolation
                )

            writer.write(corrected)
            index += 1
            self.progress.emit(45 + int(55 * index / total))

        capture.release()
        writer.release()

        if index == 0:
            raise RuntimeError("Aucune image n’a pu être exportée.")

        self.message.emit(f"Export terminé : {output_path}")
        self.finished_ok.emit(str(output_path))

    @staticmethod
    def smooth_trajectories(trajectories, window):
        if window <= 1:
            return trajectories

        kernel = np.ones(window, dtype=np.float64) / window
        smoothed = trajectories.copy()

        for i in range(3):
            for j in range(3):
                smoothed[:, i, j] = np.convolve(
                    trajectories[:, i, j], kernel, mode="same"
                )

        return smoothed
