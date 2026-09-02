import os
import sys

# When running from source, both ASSET_ROOT and DATA_ROOT point to the project root
# (the directory containing 'common', 'models', 'videos', 'data').
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ASSET_ROOT points to where the read-only assets (models, videos) are located.
# If running as a PyInstaller executable, it points to the temporary extraction folder.
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ASSET_ROOT = sys._MEIPASS
else:
    ASSET_ROOT = _PROJECT_ROOT

# DATA_ROOT points to where user-specific read/write files (profiles, history) are located.
# If running as a PyInstaller executable, it points to the directory where the .exe is physically located.
if getattr(sys, 'frozen', False):
    DATA_ROOT = os.path.dirname(sys.executable)
else:
    DATA_ROOT = _PROJECT_ROOT
