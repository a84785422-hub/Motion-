# Video Motion Control

Application Windows 64 bits pour l’analyse et la stabilisation vidéo haute qualité.

Elle permet de :
- charger une vidéo (MP4, MOV, AVI, MKV, etc.) ;
- détecter le mouvement global image par image ;
- lisser la trajectoire pour réduire les secousses ;
- recadrer automatiquement pour éviter les bords noirs ;
- exporter en MP4 avec une qualité élevée ;
- afficher la progression et les statistiques de traitement.

Le projet est prêt pour GitHub et inclut un workflow GitHub Actions qui compile automatiquement un exécutable Windows 64 bits (`VideoMotionControl.exe`).

## Fonctionnalités

- Interface graphique PyQt6.
- Stabilisation par estimation de mouvement (ORB + RANSAC).
- Lissage de trajectoire par moyenne mobile.
- Recadrage intelligent configurable.
- Option de suréchantillonnage jusqu’à 2x avec interpolation Lanczos.
- Export MP4 haute qualité.
- Traitement par lots d’images avec barre de progression.
- Journal des opérations.

## Utilisation

1. Téléchargez l’artefact GitHub `VideoMotionControl-Windows-x64`.
2. Décompressez le fichier ZIP.
3. Lancez `VideoMotionControl.exe`.
4. Choisissez une vidéo source et un dossier de sortie.
5. Ajustez les paramètres si nécessaire.
6. Cliquez sur **Démarrer le traitement**.

## Paramètres recommandés

| Usage | Lissage | Recadrage | Suréchantillonnage |
|---|---:|---:|---:|
| Vidéo légèrement tremblante | 15 | 4 % | 1x |
| Caméra à main | 25 | 6 % | 1x |
| Très haute qualité | 20 | 5 % | 1.5x ou 2x |
| Action rapide | 10 | 3 % | 1x |

## Compilation locale

Sous Windows 64 bits :

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean video_motion_control.spec
```

L’exécutable est généré dans :

```text
dist\VideoMotionControl\VideoMotionControl.exe
```

## Workflow GitHub Actions

Le fichier `.github/workflows/build-windows-exe.yml` :

- démarre sur `windows-latest` ;
- installe Python 3.11 ;
- installe les dépendances ;
- compile avec PyInstaller ;
- crée une archive ZIP ;
- publie l’artefact dans la section **Actions** du dépôt.

Pour déclencher une compilation manuelle : **Actions > Build Windows EXE > Run workflow**.

## Limites

La stabilisation fonctionne mieux sur les vidéos présentant un mouvement global régulier. Les mouvements de caméra très rapides, les flous importants, les scènes très sombres ou les changements de plan peuvent réduire la qualité du résultat.
