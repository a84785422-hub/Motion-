# MotionControlAI

Application Windows 64 bits de **motion transfer vidéo**.

Vous fournissez :
1. une **vidéo de référence** contenant une personne en mouvement ;
2. une **image** contenant une personne à animer.

L’application analyse la pose de la personne dans la vidéo, découpe la personne de l’image, puis l’anime image par image en suivant le mouvement détecté. Le résultat est exporté en MP4.

## Fonctionnement

- Détection de pose avec MediaPipe Pose.
- Découpage de la personne de l’image avec MediaPipe Selfie Segmentation.
- Suivi des points clés : tête, épaules, hanches, bras et jambes.
- Animation par transformations affines du personnage importé.
- Composition sur la vidéo de référence.
- Export MP4.

## Important

Cette version produit une **animation 2D de type cut-out / marionnette** : la personne de l’image est déplacée, tournée, redimensionnée et positionnée selon la pose de la vidéo.

Ce n’est pas un modèle de génération vidéo photoréaliste de type AnimateAnyone, MimicMotion ou Viggle. Pour un résultat photoréaliste complet, il faut un modèle IA lourd, idéalement avec GPU NVIDIA, ce qui rend l’exécutable beaucoup plus volumineux et dépendant du matériel.

## Utilisation

1. Lancez `MotionControlAI.exe`.
2. Choisissez la vidéo de référence.
3. Choisissez l’image de la personne.
4. Choisissez le dossier de sortie.
5. Cliquez sur **Générer la vidéo**.

## Compilation GitHub

Le workflow `.github/workflows/build-windows-exe.yml` compile automatiquement `MotionControlAI.exe` pour Windows 64 bits.

Il crée un artefact nommé :

```text
MotionControlAI-Windows-x64
```

contenant :

```text
MotionControlAI-Windows-x64.zip
└── MotionControlAI.exe
```

## Compilation locale

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onefile --name MotionControlAI --collect-all mediapipe app/main.py
```

## Dépendances

- Python 3.10 ou 3.11
- PyQt6
- OpenCV
- NumPy
- MediaPipe
