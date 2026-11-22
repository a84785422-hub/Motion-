from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QFileDialog, QSpinBox, QDoubleSpinBox,
    QProgressBar, QTextEdit, QLabel, QMessageBox, QCheckBox, QGroupBox
)
from app.stabilizer import StabilizeWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Motion Control — Stabilisation HD")
        self.resize(860, 620)
        self.worker = None

        source_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        self.source_button = QPushButton("Choisir une vidéo…")
        self.source_button.clicked.connect(self.choose_source)
        source_row.addWidget(self.source_edit)
        source_row.addWidget(self.source_button)

        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_button = QPushButton("Dossier de sortie…")
        self.output_button.clicked.connect(self.choose_output)
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_button)

        settings = QGroupBox("Paramètres de stabilisation")
        form = QFormLayout(settings)

        self.smoothing = QSpinBox()
        self.smoothing.setRange(1, 100)
        self.smoothing.setValue(20)
        form.addRow("Lissage de trajectoire", self.smoothing)

        self.crop = QDoubleSpinBox()
        self.crop.setRange(0.0, 20.0)
        self.crop.setSingleStep(0.5)
        self.crop.setValue(5.0)
        self.crop.setSuffix(" %")
        form.addRow("Recadrage de sécurité", self.crop)

        self.upscale = QDoubleSpinBox()
        self.upscale.setRange(1.0, 2.0)
        self.upscale.setSingleStep(0.25)
        self.upscale.setValue(1.0)
        self.upscale.setSuffix("x")
        form.addRow("Suréchantillonnage", self.upscale)

        self.high_quality = QCheckBox("Mode qualité maximale")
        self.high_quality.setChecked(True)
        form.addRow("", self.high_quality)

        self.start_button = QPushButton("Démarrer le traitement")
        self.start_button.clicked.connect(self.start)
        self.start_button.setMinimumHeight(42)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Vidéo source"))
        layout.addLayout(source_row)
        layout.addWidget(QLabel("Dossier de sortie"))
        layout.addLayout(output_row)
        layout.addWidget(settings)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Journal"))
        layout.addWidget(self.log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner une vidéo", "",
            "Vidéos (*.mp4 *.mov *.avi *.mkv *.m4v);;Tous les fichiers (*.*)"
        )
        if path:
            self.source_edit.setText(path)
            if not self.output_edit.text():
                self.output_edit.setText(str(Path(path).parent))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.output_edit.setText(path)

    def log_line(self, message):
        self.log.append(message)

    def start(self):
        source = self.source_edit.text().strip()
        output_dir = self.output_edit.text().strip()

        if not source or not Path(source).is_file():
            QMessageBox.warning(self, "Fichier manquant", "Sélectionnez une vidéo source valide.")
            return
        if not output_dir or not Path(output_dir).is_dir():
            QMessageBox.warning(self, "Dossier invalide", "Sélectionnez un dossier de sortie valide.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Traitement en cours", "Un traitement est déjà en cours.")
            return

        self.log.clear()
        self.progress.setValue(0)
        self.start_button.setEnabled(False)

        self.worker = StabilizeWorker(
            source_path=source,
            output_dir=output_dir,
            smoothing=self.smoothing.value(),
            crop_percent=self.crop.value(),
            upscale=self.upscale.value(),
            high_quality=self.high_quality.isChecked()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.message.connect(self.log_line)
        self.worker.finished_ok.connect(self.done)
        self.worker.failed.connect(self.error)
        self.worker.start()

    def done(self, output_path):
        self.start_button.setEnabled(True)
        self.progress.setValue(100)
        QMessageBox.information(self, "Terminé", f"Vidéo exportée :\n{output_path}")

    def error(self, message):
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "Erreur", message)
