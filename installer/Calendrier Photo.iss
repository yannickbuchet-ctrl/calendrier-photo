; Installateur de Calendrier Photo (Inno Setup 6).
;
; Construction (depuis le dossier du projet) :
;   $env:CONSTRUCTION = "dossier"; python -m PyInstaller --clean --noconfirm "Calendrier Photo.spec"
;   ISCC "installer\Calendrier Photo.iss"
; Résultat : dist\Calendrier-Photo-Installation-<version>.exe
;
; - La version est lue dans l'exécutable (informations de version écrites par la recette PyInstaller).
; - Installation pour l'utilisateur seul, sans droits d'administrateur (au choix : pour tous les utilisateurs).
; - Désinstallation par Paramètres → Applications, ou par le menu Démarrer.

#define AppName "Calendrier Photo"
#define AppExe "Calendrier Photo.exe"
#define AppDir "..\dist\Calendrier Photo"
#define AppVersion GetStringFileInfo(AppDir + "\" + AppExe, "ProductVersion")
#define AppPublisher "Yannick Buchet"
#define AppUrl "https://github.com/yannickbuchet-ctrl/applications"

[Setup]
; Identifiant permanent de l'application : ne jamais le changer (mises à jour et désinstallation).
AppId={{0A1587C8-2ABF-4EAA-8509-5749BDB5D61B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppCopyright=© 2026 {#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Installation de {#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
SetupIconFile=..\Calendrier Photo.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=Calendrier-Photo-Installation-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
