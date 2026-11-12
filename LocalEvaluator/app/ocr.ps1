# Offline text recognition for scanned pages, using the OCR engine built into Windows.
# Input : a UTF-8 text file with one image path per line.
# Output: a UTF-8 JSON file: [{ "path": "...", "text": "..." }, ...]
param(
    [Parameter(Mandatory = $true)][string]$ListFile,
    [Parameter(Mandatory = $true)][string]$OutFile
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($operation, [Type]$resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait(-1) | Out-Null
    $task.Result
}

# Prefer Indonesian, then English, then whatever the user profile offers.
$engine = $null
foreach ($tag in 'id-ID', 'id', 'en-US', 'en-GB') {
    $lang = New-Object Windows.Globalization.Language $tag
    if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
        if ($engine) { break }
    }
}
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if (-not $engine) { throw 'No Windows OCR language is installed.' }

$results = New-Object System.Collections.ArrayList
foreach ($path in [System.IO.File]::ReadAllLines($ListFile, [System.Text.Encoding]::UTF8)) {
    if (-not $path) { continue }
    $text = ''
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $ocr = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $text = ($ocr.Lines | ForEach-Object { $_.Text }) -join "`n"
        $stream.Dispose()
    }
    catch { $text = '' }
    [void]$results.Add(@{ path = $path; text = $text })
}
$json = ConvertTo-Json -InputObject @($results) -Compress -Depth 3
[System.IO.File]::WriteAllText($OutFile, $json, (New-Object System.Text.UTF8Encoding($false)))
"OCR language: $($engine.RecognizerLanguage.LanguageTag); pages: $($results.Count)"
