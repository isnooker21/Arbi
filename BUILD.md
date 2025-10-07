## Windows EXE Build Guide (PyInstaller)

This builds a single-file EXE for distribution without exposing source code.

### Prerequisites
- Python 3.10+ (same version as your runtime)
- PowerShell on Windows
- venv recommended

### 1) Install dependencies
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### 2) Build
Run the PowerShell script:
```powershell
pwsh -File build\build_exe.ps1
```

Outputs are in `dist/Arbi-1/` with a single `Arbi-1.exe`.

### 3) Files included
- `config/` and `data/` directories are bundled as read/write at runtime
- Logs write to `logs/` next to the EXE

### 4) CLI options
The EXE wraps `run.py`. Examples:
```powershell
./Arbi-1.exe --gui
./Arbi-1.exe --cli
```

### 5) Troubleshooting
- Missing module at runtime: add to hidden imports in `build/pyinstaller.spec`
- GUI fails due to tk: ensure `tkinter` is installed (Python for Windows includes it)
- Antivirus flags: sign the EXE or distribute as ZIP; avoid packing extra tools

### 6) Updating assets after build
If you need to change `config/*` or `data/*` without rebuilding, keep them external and pass a runtime flag to load from an external path. This bundle includes them inside the EXE for simplicity.


