; Strategy scaffold, not compiled or qualified. No network download directives.
#ifndef ReleaseApproved
  #error Commercial redistribution and clean Windows qualification must be approved before compiling.
#endif
#ifndef BundleDir
  #define BundleDir "..\dist\NoteTaker"
#endif
[Setup]
AppId={{D1C659D7-A226-45F9-9698-62A668290345}
AppName=NoteTaker
AppVersion=0.1.0
DefaultDirName={autopf}\NoteTaker
DefaultGroupName=NoteTaker
OutputDir=..\dist\installer
OutputBaseFilename=NoteTaker-Setup
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19045
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
DiskSpanning=no
WizardStyle=modern
UninstallDisplayIcon={app}\NoteTaker.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; Flags: unchecked
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\NoteTaker"; Filename: "{app}\NoteTaker.exe"
Name: "{autodesktop}\NoteTaker"; Filename: "{app}\NoteTaker.exe"; Tasks: desktopicon
; LocalAppData and municipal archives are deliberately outside the uninstall file list.
