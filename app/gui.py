from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QFileDialog, QDoubleSpinBox, QCheckBox,
    QProgressBar, QTextEdit, QLabel, QMessageBox, QGroupBox
)
from app.motion_transfer import MotionTransferWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MotionControlAI — Video Motion Transfer")
        self.resize(900, 660)
        self.worker = None

        def file_row(edit, button_text, method):
            row = QHBoxLayout()
            row.addWidget(edit)
            button = QPushButton(button_text)
            button.clicked.connect(method)
            row.addWidget(button)
            return row

        self.video_edit = QLineEdit()
        self.image_edit = QLineEdit()
        self.output_edit = QLineEdit()

        settings = QGroupBox("Paramètres")
        form = QFormLayout(settings)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.3, 3.0)
        self.scale.setSingleStep(0.05)
        self.scale.setValue(1.0)
        self.scale.setSuffix("x")
        form.addRow("Taille du personnage", self.scale)

        self.smooth = QDoubleSpinBox()
        self.smooth.setRange(0.0, 1.0)
        self.smooth.setSingleStep(0.05)
        self.smooth.setValue(0.65)
        form.addRow("Lissage du mouvement", self.smooth)

        self.overlay = QCheckBox("Garder la vidéo de référence en arrière-plan")
        self.overlay.setChecked(True)
        form.addRow("", self.overlay)

        self.start_button = QPushButton("Générer la vidéo")
        self.start_button.setMinimumHeight(44)
        self.start_button.clicked.connect(self.start)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("1. Vidéo de référence — personne dont le mouvement sera copié"))
        layout.addLayout(file_row(self.video_edit, "Choisir la vidéo…", self.choose_video))
        layout.addWidget(QLabel("2. Image source — personne à animer"))
        layout.addLayout(file_row(self.image_edit, "Choisir l’image…", self.choose_image))
        layout.addWidget(QLabel("3. Dossier de sortie"))
        layout.addLayout(file_row(self.output_edit, "Choisir le dossier…", self.choose_output))
        layout.addWidget(settings)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Journal"))
        layout.addWidget(self.log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def choose_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Vidéo de référence", "",
            "Vidéos (*.mp4 *.mov *.avi *.mkv *.m4v);;Tous les fichiers (*.*)"
        )
        if path:
            self.video_edit.setText(path)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Image de la personne", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;Tous les fichiers (*.*)"
        )
        if path:
            self.image_edit.setText(path)

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.output_edit.setText(path)

    def log_line(self, message):
        self.log.append(message)

    def start(self):
        video = self.video_edit.text().strip()
        image = self.image_edit.text().strip()
        output = self.output_edit.text().strip()

        if not video or not Path(video).is_file():
            QMessageBox.warning(self, "Vidéo manquante", "Sélectionnez une vidéo de référence valide.")
            return
        if not image or not Path(image).is_file():
            QMessageBox.warning(self, "Image manquante", "Sélectionnez une image valide.")
            return
        if not output or not Path(output).is_dir():
            QMessageBox.warning(self, "Dossier invalide", "Sélectionnez un dossier de sortie valide.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Traitement en cours", "Une génération est déjà en cours.")
            return

        self.log.clear()
        self.progress.setValue(0)
        self.start_button.setEnabled(False)

        self.worker = MotionTransferWorker(
            video_path=video,
            image_path=image,
            output_dir=output,
            person_scale=self.scale.value(),
            smoothing=self.smooth.value(),
            keep_background=self.overlay.isChecked()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.message.connect(self.log_line)
        self.worker.finished_ok.connect(self.done)
        self.worker.failed.connect(self.error)
        self.worker.start()

    def done(self, output_path):
        self.start_button.setEnabled(True)
        self.progress.setValue(100)
        QMessageBox.information(self, "Terminé", f"Vidéo générée :\n{output_path}")

    def error(self, message):
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "Erreur", message)
