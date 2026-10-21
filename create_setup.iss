#define AppName "OpenWallpaperEngine"
#define AppVer "1.0"
#define AppExe "OpenWallpaperEngine.exe"

[Setup]
AppId={{B7E2C1A4-5D3F-4E8A-9C61-0F2A7D4B8E13}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Mắt Thần team
AppPublisherURL=https://github.com/PhucPower300121
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=LICENSE.txt
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
WizardStyle=modern
OutputDir=installer
OutputBaseFilename={#AppName}_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=app.ico
UninstallDisplayIcon={app}\app.ico
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; tắt wallpaper đang chạy trước khi gỡ
Filename: "taskkill"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#AppName}"

[Registry]
; xoá autostart khi gỡ
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#AppName}"; Flags: uninsdeletevalue
