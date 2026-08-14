 ; Inno Setup Compiler for Abib distribution.
; ------------------------------------------

[Setup]
AppId={{9CBC6105-153E-49F5-912C-2F08A72A774B}} 
AppName=Abib
AppVersion=417.26
WizardStyle=modern dynamic
WizardImageBackColor=clWhite
WizardImageBackColorDynamicDark=#2b2b2b
DefaultDirName={autopf}\Abib
DefaultGroupName=Abib
OutputBaseFilename=Abib_setup_417.26_win
UninstallDisplayIcon={app}\Abib.exe
Compression=lzma2
SolidCompression=yes
UsePreviousAppDir=yes
CloseApplications=yes
CloseApplicationsFilter=Abib.exe
RestartApplications=no
OutputDir=.\output
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Dirs]

[Files]
; App binary
Source: "dist\Abib.exe"; DestDir: "{app}"; DestName: "Abib.exe"; Flags: ignoreversion

; Assets and Data
; Source: "src\abib\data\*"; DestDir: "{app}\abib\data"; Flags: ignoreversion recursesubdirs
; Source: "src\abib\images\*"; DestDir: "{app}\abib\images"; Flags: ignoreversion recursesubdirs
; Source: "src\abib\font\*"; DestDir: "{app}\abib\font"; Flags: ignoreversion recursesubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\Calvin"
Type: files; Name: "{app}\uv.lock"
Type: files; Name: "{app}\Abib.spec"
Type: files; Name: "{app}\64Bit_for_Abib.iss"
Type: files; Name: "{app}\.gitignore"
Type: files; Name: "{app}\.gitattributes"
Type: files; Name: "{app}\README.md"
Type: files; Name: "{app}\pyproject.toml"
Type: filesandordirs; Name: "{app}\abib\data"
Type: filesandordirs; Name: "{app}\abib\images"
Type: filesandordirs; Name: "{app}\abib\font"
Type: filesandordirs; Name: "{app}\abib\core"
Type: filesandordirs; Name: "{app}\abib\domain"
Type: filesandordirs; Name: "{app}\abib\services"
Type: filesandordirs; Name: "{app}\abib\ui"
Type: filesandordirs; Name: "{app}\abib\utils"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\Calvin"
Type: files; Name: "{app}\uv.lock"
Type: files; Name: "{app}\Abib.spec"
Type: files; Name: "{app}\64Bit_for_Abib.iss"
Type: files; Name: "{app}\.gitignore"
Type: files; Name: "{app}\.gitattributes"
Type: files; Name: "{app}\README.md"
Type: files; Name: "{app}\pyproject.toml"
Type: filesandordirs; Name: "{app}\abib\data"
Type: filesandordirs; Name: "{app}\abib\images"
Type: filesandordirs; Name: "{app}\abib\font"
Type: filesandordirs; Name: "{app}\abib\core"
Type: filesandordirs; Name: "{app}\abib\domain"
Type: filesandordirs; Name: "{app}\abib\services"
Type: filesandordirs; Name: "{app}\abib\ui"
Type: filesandordirs; Name: "{app}\abib\utils"

[Icons]
Name: "{group}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; Comment: "Abib"
Name: "{commondesktop}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; Comment: "Abib"