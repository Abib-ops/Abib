 ; Inno Setup Compiler for Abib distribution.
; ------------------------------------------

[Setup]
AppId={{9CBC6105-153E-49F5-912C-2F08A72A774B}} 
AppName=Abib
AppVersion=417.03
WizardStyle=modern dynamic
WizardImageBackColor=clWhite
WizardImageBackColorDynamicDark=#2b2b2b
DefaultDirName={autopf}\Abib
DefaultGroupName=Abib
OutputBaseFilename=Abib_setup_417.03_win
UninstallDisplayIcon={app}\abib\images\abib_icon0.ico
Compression=lzma2
SolidCompression=yes
UsePreviousAppDir=yes
CloseApplications=yes
CloseApplicationsFilter=Abib.exe
RestartApplications=no
OutputDir=c:\output
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Dirs]

[Files]
; App binary
Source: "dist\Abib.exe"; DestDir: "{app}"; DestName: "Abib.exe"; Flags: ignoreversion

; Assets and Data
Source: "src\abib\data\*"; DestDir: "{app}\abib\data"; Flags: ignoreversion recursesubdirs
Source: "src\abib\images\*"; DestDir: "{app}\abib\images"; Flags: ignoreversion recursesubdirs
Source: "src\abib\font\*"; DestDir: "{app}\abib\font"; Flags: ignoreversion recursesubdirs

; Source code - package structure
Source: "src\abib\*.py"; DestDir: "{app}\abib"; Flags: ignoreversion
Source: "src\abib\core\*.py"; DestDir: "{app}\abib\core"; Flags: ignoreversion
Source: "src\abib\domain\*.py"; DestDir: "{app}\abib\domain"; Flags: ignoreversion
Source: "src\abib\services\*.py"; DestDir: "{app}\abib\services"; Flags: ignoreversion
Source: "src\abib\ui\*.py"; DestDir: "{app}\abib\ui"; Flags: ignoreversion
Source: "src\abib\ui\*.ui"; DestDir: "{app}\abib\ui"; Flags: ignoreversion
Source: "src\abib\utils\*.py"; DestDir: "{app}\abib\utils"; Flags: ignoreversion

; Tools
Source: "tools\*.py"; DestDir: "{app}\tools"; Flags: ignoreversion

; Project metadata and configuration
Source: "pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "uv.lock"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "Abib.spec"; DestDir: "{app}"; Flags: ignoreversion
Source: "64Bit_for_Abib.iss"; DestDir: "{app}"; Flags: ignoreversion
Source: ".gitattributes"; DestDir: "{app}"; Flags: ignoreversion
Source: ".gitignore"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\Calvin"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\Calvin"

[Icons]
Name: "{group}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; IconFilename: "{app}\abib\images\abib_icon0.ico"; Comment: "Abib"
Name: "{commondesktop}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; IconFilename: "{app}\abib\images\abib_icon0.ico"; Comment: "Abib"