@echo off
pip install pyinstaller -r requirements.txt
pyinstaller --noconfirm --clean --onedir --windowed --icon app.ico --add-data "app.ico;." --name OpenWallpaperEngine ^
  --collect-all imageio_ffmpeg --collect-submodules comtypes --hidden-import pycaw.pycaw ^
  OpenWallpaperEngine.py
echo Xong: dist\OpenWallpaperEngine\OpenWallpaperEngine.exe
pause
