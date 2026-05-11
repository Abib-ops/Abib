; Inno Setup Compiler for Abib distribution.
; ------------------------------------------

[Setup]
AppId={{9CBC6105-153E-49F5-912C-2F08A72A774B}} 
AppName=Abib
AppVersion=416.07
WizardStyle=modern dynamic
WizardImageBackColor=clWhite
WizardImageBackColorDynamicDark=#2b2b2b
DefaultDirName={autopf}\Abib
DefaultGroupName=Abib
OutputBaseFilename=Abib_setup_416.07_win
UninstallDisplayIcon={app}\images\abib_icon0.ico
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

; John Gill commentary
Source: "dist\source\gill.cmt.sqlite"; DestDir: "{app}"; Flags: ignoreversion

; Curated Other Works you ship (user-added files in this folder remain untouched)
Source: "dist\source\Other Works\*.txt"; DestDir: "{app}\Other Works"; Flags: ignoreversion

; Other Works companion files you ship (user-added files in this folder remain untouched)
Source: "dist\source\Other Works companions\*.gz"; DestDir: "{app}\Other Works companions"; Flags: ignoreversion

; Abib\core folder
Source: "dist\source\core\navigation.py"; DestDir: "{app}\core"; Flags: ignoreversion

; Abib\domain folder
Source: "dist\source\domain\__init__.py"; DestDir: "{app}\domain"; Flags: ignoreversion
Source: "dist\source\domain\reading_plans.py"; DestDir: "{app}\domain"; Flags: ignoreversion
Source: "dist\source\domain\scripture_refs.py"; DestDir: "{app}\domain"; Flags: ignoreversion

; Abib\font folder
Source: "dist\source\font\CascadiaMono.ttf"; DestDir: "{app}\font"; Flags: ignoreversion

; Abib\images folder
Source: "dist\source\images\Abib_barley.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\abib_icon0.ico"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\about.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\blue-folder-open-document.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\close.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\details.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\document-copy.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\exit.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\github.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\license.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\printer.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\question.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\selection-input.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\settings.png"; DestDir: "{app}\images"; Flags: ignoreversion
Source: "dist\source\images\update.png"; DestDir: "{app}\images"; Flags: ignoreversion

; Abib\services folder
Source: "dist\source\services\__init__.py"; DestDir: "{app}\services"; Flags: ignoreversion
Source: "dist\source\services\audio.py"; DestDir: "{app}\services"; Flags: ignoreversion
Source: "dist\source\services\data_loader.py"; DestDir: "{app}\services"; Flags: ignoreversion
Source: "dist\source\services\printing.py"; DestDir: "{app}\services"; Flags: ignoreversion
Source: "dist\source\services\search_service.py"; DestDir: "{app}\services"; Flags: ignoreversion
Source: "dist\source\services\settings.py"; DestDir: "{app}\services"; Flags: ignoreversion

; Abib\tools folder
Source: "dist\source\tools\check_refs.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\csv_report.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\find_tabs.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\find_unknown_bible_abbrevs.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\fix_folder.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\normalize_apostrophes.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\source\tools\precompute_refs.py"; DestDir: "{app}\tools"; Flags: ignoreversion

; Abib\ui folder
Source: "dist\source\ui\__init__.py"; DestDir: "{app}\ui"; Flags: ignoreversion
Source: "dist\source\ui\actions.py"; DestDir: "{app}\ui"; Flags: ignoreversion
Source: "dist\source\ui\themes.py"; DestDir: "{app}\ui"; Flags: ignoreversion

; Abib folder
Source: "dist\source\.gitattributes"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\.gitignore"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\Abib.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\ABOUT.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\Amap.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\bible_data.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\fcs.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\find.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\find.ui"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\find_dialog.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\find_dict.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\HELP.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\history.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\Info.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\KJB_PCE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\KJB_PCE_stripped.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\COPYING"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\list_dict.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\list_lowdict.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\lower_dict.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\morning_evening.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\PCE-find.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\PCE-lower.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\PCE-stripped.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\PCE-stripped_lower.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\Screenshot.jpg"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\scripture.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\settings_dialog.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\shared.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\sound.wav"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\stripped_dict.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\strpd_low_dict.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\text_window.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\ui_find.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\ui_helpers.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\updater.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\source\windows.py"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\Calvin"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\tests"
Type: filesandordirs; Name: "{app}\Calvin"

[Icons]
Name: "{group}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; IconFilename: "{app}\images\abib_icon0.ico"; Comment: "Abib"
Name: "{commondesktop}\Abib"; Filename: "{app}\Abib.exe"; WorkingDir: "{app}"; IconFilename: "{app}\images\abib_icon0.ico"; Comment: "Abib"