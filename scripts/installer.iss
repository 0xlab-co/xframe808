; xFRAME808 — Inno Setup 6 installer script
;
; Consumes the PyInstaller onedir output at dist\xFRAME808\ and produces
; dist\installer\xFRAME808-Windows-Setup.exe. Version is injected from the
; build pipeline via /DAppVersion=x.y.z so each tag stamps its own number.
;
; Local use (after running scripts\build_win.bat):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=3.1.0 scripts\installer.iss

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

[Setup]
; AppId 是這個應用在系統上的唯一識別碼（控制台「新增移除程式」靠它配對）。
; 一旦發佈就不要再改，否則會被當成不同程式而無法升級覆蓋。
AppId={{7A3E4C82-2D9F-4A1C-B8B3-7F5E0E2C1D01}
AppName=xFRAME808
AppVersion={#AppVersion}
AppVerName=xFRAME808 {#AppVersion}
AppPublisher=0xlab
AppPublisherURL=https://github.com/0xlab-co/xframe808
AppSupportURL=https://github.com/0xlab-co/xframe808/issues
AppUpdatesURL=https://github.com/0xlab-co/xframe808/releases
DefaultDirName={autopf}\xFRAME808
DefaultGroupName=xFRAME808
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=xFRAME808-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; x64compatible 同時覆蓋原生 x64 與 ARM64 上的 x64 模擬環境（Inno 6.3+）。
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 預設要 admin 安裝到 Program Files，若使用者選「只為我安裝」則降到 AppData\Local。
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName=xFRAME808
UninstallDisplayIcon={app}\xFRAME808.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.CreateDesktopIcon=Create a &desktop icon
english.LaunchProgram=Launch xFRAME808

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "Additional icons:"

[Files]
; 整個 PyInstaller onedir 輸出照樣搬進 {app}，包含 _internal 子資料夾。
Source: "..\dist\xFRAME808\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\xFRAME808"; Filename: "{app}\xFRAME808.exe"
Name: "{group}\Uninstall xFRAME808"; Filename: "{uninstallexe}"
Name: "{autodesktop}\xFRAME808"; Filename: "{app}\xFRAME808.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\xFRAME808.exe"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent
