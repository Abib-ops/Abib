# WinGet manifest

This directory contains a multi-file WinGet manifest for Abib v417.54. It
targets the x64 Inno Setup installer. The installer SHA-256 and release date
are placeholders until the v417.54 installer has been published; fill them in
before validating or submitting the manifest.

The manifests use schema version 1.12.0. Current `winget-pkgs` guidance
recommends 1.28.0, while noting that 1.12.0 is still accepted; check the
repository's current schema policy before submitting.

## Validate and test

On Windows with WinGet installed, validate the manifest set:

```powershell
winget validate --manifest .\winget\manifests\a\Abib-ops\Abib\417.54\
```

After uploading the v417.54 installer, run this one-line PowerShell command to
download it, calculate its SHA-256, and fill in the digest and today's release
date (adjust the date if the installer was published earlier; the command
writes ASCII without a byte-order mark):

```powershell
$installer = Join-Path $env:TEMP 'Abib_setup_417.54_win.exe'; curl.exe '--location' '--fail' '--silent' '--show-error' 'https://github.com/Abib-ops/Abib/releases/download/417.54/Abib_setup_417.54_win.exe' '--output' $installer; if ($LASTEXITCODE -ne 0) { throw 'Installer download failed.' }; $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash; $manifest = '.\winget\manifests\a\Abib-ops\Abib\417.54\Abib-ops.Abib.installer.yaml'; $text = [IO.File]::ReadAllText($manifest).Replace('REPLACE_WITH_SHA256', $hash).Replace('REPLACE_WITH_RELEASE_DATE', (Get-Date -Format 'yyyy-MM-dd')); [IO.File]::WriteAllText($manifest, $text, [Text.Encoding]::ASCII); Remove-Item -LiteralPath $installer
```

To test the local manifest, first enable local manifest installation from an
administrator terminal, then install it:

```powershell
winget settings --enable LocalManifestFiles
winget install --manifest .\winget\manifests\a\Abib-ops\Abib\417.54\
```

Local manifest installation should be tested in a disposable Windows VM when
possible. Disable local manifest installation afterward with
`winget settings --disable LocalManifestFiles`.

## Submit

Submit the manifest set to the Microsoft community repository,
[`microsoft/winget-pkgs`](https://github.com/microsoft/winget-pkgs), using its
contribution instructions. Preserve the package folder structure under
`manifests/a/Abib-ops/Abib/417.54/`. WinGetCreate can also help generate or update
manifests; validate the resulting files before opening a pull request.

## Update for a new release

For a later release, create a new version directory, update the package version,
installer URL, SHA-256 digest and release date, and refresh the release notes.
Check the current schema policy and update `ManifestVersion` in all three YAML
files if needed. Verify the digest against the published installer, then
validate and test the new manifest before submitting it.