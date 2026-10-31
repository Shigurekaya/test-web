param(
    [string]$Deliverables = (Join-Path (Split-Path -Parent $PSScriptRoot) "deliverables"),
    [string]$File = ""
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Deliverables)) { throw "Deliverables directory not found: $Deliverables" }
$pdfDir = Join-Path $Deliverables "pdf"
New-Item -ItemType Directory -Force -Path $pdfDir | Out-Null

if ($File) {
    $files = @(Get-Item -LiteralPath $File)
}
else {
    $files = @(Get-ChildItem -LiteralPath $Deliverables -Filter "*.docx" -File)
}

foreach ($item in $files) {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    try {
        Write-Host "Updating fields: $($item.Name)" -ForegroundColor Cyan
        $doc = $word.Documents.Open($item.FullName, $false, $false)
        $doc.Fields.Update() | Out-Null
        foreach ($toc in $doc.TablesOfContents) {
            $toc.Update() | Out-Null
        }
        $doc.Repaginate()
        $doc.Save()
        if ($item.Name -notmatch '^\d{2}-') {
            $pdfPath = Join-Path $pdfDir ($item.BaseName + ".pdf")
            $doc.ExportAsFixedFormat($pdfPath, 17)
            Write-Host "Exported PDF: $pdfPath" -ForegroundColor Green
        }
        $doc.Close($false)
    }
    catch {
        Write-Warning "Word failed for $($item.Name): $($_.Exception.Message)"
        try { if ($doc) { $doc.Close($false) } } catch {}
    }
    finally {
        try { $word.Quit() } catch {}
        try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null } catch {}
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}
Write-Host "Word field update pass completed." -ForegroundColor Green
