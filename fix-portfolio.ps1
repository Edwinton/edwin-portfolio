# fix-portfolio.ps1  (v2)
# Usage:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\fix-portfolio.ps1            # apply
#   .\fix-portfolio.ps1 -WhatIf    # preview only

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
$ProgressPreference   = 'SilentlyContinue'

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "    OK  $m" -ForegroundColor Green }
function Write-Warn2($m){ Write-Host "    !!  $m" -ForegroundColor Yellow }
function Write-Info($m) { Write-Host "        $m" -ForegroundColor DarkGray }

function Backup-File([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    $bak = "$Path.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $Path -Destination $bak -Force
    Write-Info "backup -> $bak"
}

function Save-Text([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $norm = $Content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($Path, $norm, $utf8NoBom)
}

# ---------- 0. sanity ----------
if (-not (Test-Path (Join-Path $Root 'build.py'))) {
    throw "build.py not found in '$Root'. Run from the project root."
}
Set-Location $Root

# =====================================================================
# 1. Replace the maintenance redirect in every HTML file
# =====================================================================
Write-Step "1. Fixing client-side maintenance redirect (relative path)"

$newBlock = @'
  <!-- Maintenance Redirect (relative - works on Netlify AND GitHub Pages) -->
  <script>
    (function () {
      if (/maintenance\.html$/.test(location.pathname)) return;
      fetch('/api/site')
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (data) {
          if (data && data.site_config && data.site_config.maintenance_mode) {
            location.replace('maintenance.html');
          }
        })
        .catch(function () {});
    })();
  </script>
'@

# Match the WHOLE maintenance <script> block regardless of indentation.
# (?s) = dotall. Anchored on the comment + opening <script> + first line of JS.
$rx = [regex]'(?s)<!--\s*Maintenance Redirect\s*-->.*?<script>\s*if\s*\(window\.location\.pathname.*?</script>'

$files = @()
$files += Get-ChildItem -Path $Root -Filter '*.html' -File -Recurse |
          Where-Object { $_.FullName -notmatch '\\public\\' -and $_.FullName -notmatch '\\node_modules\\' }
if (Test-Path (Join-Path $Root 'templates')) {
    $files += Get-ChildItem -Path (Join-Path $Root 'templates') -Filter '*.html' -File -Recurse
}
$files = $files | Sort-Object FullName -Unique

$touched = 0
foreach ($f in $files) {
    $text = [System.IO.File]::ReadAllText($f.FullName)
    if ($text -notmatch 'window\.location\.pathname') { continue }
    $new = $rx.Replace($text, $newBlock, 1)
    if ($new -ne $text) {
        if ($PSCmdlet.ShouldProcess($f.FullName, 'replace maintenance redirect')) {
            Backup-File $f.FullName
            Save-Text $f.FullName $new
        }
        Write-Ok $f.FullName
        $touched++
    }
}
if ($touched -eq 0) {
    Write-Warn2 "No HTML file contained the old 'window.location.pathname' maintenance block."
    Write-Info  "Files scanned: $($files.Count)"
    Write-Info  "If your templates use a different comment, inspect one and adjust `$rx`."
}

# =====================================================================
# 2. Patch build.py so public/maintenance.html is always emitted
# =====================================================================
Write-Step "2. Patching build.py to always emit public/maintenance.html"

$buildPath = Join-Path $Root 'build.py'
$build = [System.IO.File]::ReadAllText($buildPath)
$changed = $false

# Case A: exact original block
$oldBuildBlock = @'
    # STANDALONE-MAINTENANCE: emit maintenance.html without base.html wrapper
    _maint = TEMPLATES / "maintenance.html"
    if _maint.exists():
        (OUT / "maintenance.html").write_text(_maint.read_text(encoding="utf-8"), encoding="utf-8")
        outputs.add("maintenance.html")
        print("  ok maintenance.html (standalone)")
'@

$newBuildBlock = @'
    # STANDALONE-MAINTENANCE: emit maintenance.html without base.html wrapper
    # Always emit it, even if the template is missing, so no redirect 404s.
    _maint = TEMPLATES / "maintenance.html"
    _maint_out = OUT / "maintenance.html"
    if _maint.exists():
        _maint_out.write_text(_maint.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        _maint_out.write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Maintenance</title>'
            '<div style="font-family:system-ui;text-align:center;padding:4rem">'
            '<h1>We will be right back</h1></div>',
            encoding="utf-8")
        print("  WARN: templates/maintenance.html missing - wrote fallback")
    outputs.add("maintenance.html")
    print("  ok maintenance.html (standalone)")
'@

if ($build.Contains($oldBuildBlock)) {
    $build = $build.Replace($oldBuildBlock, $newBuildBlock)
    $changed = $true
    Write-Ok "build.py: exact block replaced"
}
elseif ($build -match 'STANDALONE-MAINTENANCE') {
    # Case B: block present but edited. Replace just the `if _maint.exists():` body.
    # Use a single-line regex + Regex.Replace with a scriptblock-free, $-safe replacement string.
    $pattern = '(?s)(# STANDALONE-MAINTENANCE.*?_maint = TEMPLATES / "maintenance\.html"\r?\n)(\s*)(if _maint\.exists\(\):\r?\n\s*\(OUT / "maintenance\.html"\)\.write_text\(_maint\.read_text\(encoding="utf-8"\), encoding="utf-8"\)\r?\n\s*outputs\.add\("maintenance\.html"\)\r?\n\s*print\("  ok maintenance\.html \(standalone\)"\))'
    $m = [regex]::Match($build, $pattern)
    if ($m.Success) {
        $build = $build.Remove($m.Index, $m.Length).Insert($m.Index, $newBuildBlock)
        $changed = $true
        Write-Ok "build.py: block normalized via regex"
    } else {
        Write-Warn2 "build.py contains STANDALONE-MAINTENANCE but shape differs; skipping auto-patch."
        Write-Info  "Open build.py and manually replace the STANDALONE-MAINTENANCE section."
    }
}
else {
    # Case C: no block at all. Insert before the static-copy step, else before __main__.
    $marker = 'print("Copying static assets...")'
    $snippet = @'
    # --- ensure maintenance.html always exists (added by fix-portfolio.ps1) ---
    _maint = TEMPLATES / "maintenance.html"
    _maint_out = OUT / "maintenance.html"
    if _maint.exists():
        _maint_out.write_text(_maint.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        _maint_out.write_text(
            '<!doctype html><meta charset="utf-8"><title>Maintenance</title>'
            '<div style="font-family:system-ui;text-align:center;padding:4rem">'
            '<h1>We will be right back</h1></div>',
            encoding="utf-8")
        print("  WARN: templates/maintenance.html missing - wrote fallback")
    outputs.add("maintenance.html")
    print("  ok maintenance.html (standalone)")
    # --- end fix-portfolio snippet ---

'@
    if ($build.Contains($marker)) {
        $build = $build.Replace($marker, $snippet + $marker)
    } else {
        $build = $build -replace '(?m)^if __name__ == "__main__":', ($snippet + 'if __name__ == "__main__":')
    }
    $changed = $true
    Write-Ok "build.py: snippet appended"
}

if ($changed) {
    if ($PSCmdlet.ShouldProcess($buildPath, 'write patched build.py')) {
        Backup-File $buildPath
        Save-Text $buildPath $build
    }
} else {
    Write-Warn2 "build.py was not modified."
}

# =====================================================================
# 3. Fix data/site.json (CV PDF href + Fiverr placeholder)
# =====================================================================
Write-Step "3. Fixing data/site.json"

$sitePath = Join-Path $Root 'data\site.json'
if (Test-Path $sitePath) {
    $siteRaw = [System.IO.File]::ReadAllText($sitePath)
    $site = $siteRaw | ConvertFrom-Json
    $jsonChanged = $false

    $cvTpl = $site.section_templates.cv
    if ($cvTpl -and ($cvTpl -match 'Edwin_Tony_Resume\.pdf')) {
        $cvTpl = $cvTpl -replace '(?:/?[\w\-\./]*)?Edwin_Tony_Resume\.pdf', 'Edwin_Tony_CV.pdf'
        $site.section_templates.cv = $cvTpl
        $jsonChanged = $true
        Write-Ok "CV PDF href -> Edwin_Tony_CV.pdf"
    } else {
        Write-Info "CV PDF href already correct."
    }

    if ($site.pages.contact -and ($site.pages.contact.fiverr_url -match 'YOUR_USERNAME')) {
        $real = $site.fiverr_url
        if (-not $real -or $real -match 'YOUR_USERNAME') { $real = 'https://www.fiverr.com/edwintony141' }
        $site.pages.contact.fiverr_url = $real
        $jsonChanged = $true
        Write-Ok "contact.fiverr_url -> $real"
    } else {
        Write-Info "contact.fiverr_url already set."
    }

    if ($jsonChanged) {
        if ($PSCmdlet.ShouldProcess($sitePath, 'write site.json')) {
            Backup-File $sitePath
            $json = $site | ConvertTo-Json -Depth 100
            # Un-mangle JSON escapes for readability (safe: these chars have no special meaning in JSON values when literal)
            $json = $json -replace '\\u003c','<' -replace '\\u003e','>' -replace '\\u0026','&' -replace '\\u0027',"'"
            Save-Text $sitePath $json
        }
        Write-Ok "site.json updated"
    } else {
        Write-Warn2 "site.json unchanged."
    }
} else {
    Write-Warn2 "data/site.json not found."
}

# =====================================================================
# 4. Write public/_redirects (Netlify safety net)
# =====================================================================
Write-Step "4. Writing public/_redirects"

$publicDir = Join-Path $Root 'public'
if (Test-Path $publicDir) {
    $redirectsPath = Join-Path $publicDir '_redirects'
    $redirects = @'
# Strip the GitHub-Pages subpath so stale /edwin-portfolio/* links resolve on Netlify.
/edwin-portfolio/*  /:splat  200
'@
    if ($PSCmdlet.ShouldProcess($redirectsPath, 'write _redirects')) {
        Save-Text $redirectsPath $redirects
    }
    Write-Ok "public/_redirects written"
} else {
    Write-Warn2 "public/ not found. Run python build.py first, then re-run step 4."
}

# =====================================================================
# 5. templates/maintenance.html check
# =====================================================================
Write-Step "5. Checking templates/maintenance.html"

$maintTpl = Join-Path $Root 'templates\maintenance.html'
if (Test-Path $maintTpl) {
    Write-Ok "templates/maintenance.html exists"
} else {
    Write-Warn2 "templates/maintenance.html is MISSING - build.py will emit a fallback."
    $make = Read-Host "Create a minimal templates/maintenance.html now? (y/N)"
    if ($make -match '^[Yy]') {
        $fallback = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Under Maintenance - Edwin Tony</title>
  <style>
    body { margin:0; min-height:100vh; display:grid; place-items:center;
           font-family:system-ui,sans-serif; background:#faf9f7; color:#1a1a1a; }
    .card { text-align:center; padding:3rem 2rem; max-width:520px; }
    h1 { font-size:2rem; margin:0 0 .5rem; }
    p  { color:#4a4a4a; line-height:1.6; margin:0 0 1.5rem; }
    a  { display:inline-block; background:#ff7b00; color:#fff; text-decoration:none;
         padding:12px 24px; border-radius:6px; font-weight:600; }
  </style>
</head>
<body>
  <div class="card">
    <h1>We'll be right back</h1>
    <p>The site is under maintenance. Please check back soon.</p>
    <a href="index.html">Try again</a>
  </div>
</body>
</html>
'@
        if ($PSCmdlet.ShouldProcess($maintTpl, 'create fallback')) {
            Save-Text $maintTpl $fallback
        }
        Write-Ok "templates/maintenance.html created"
    }
}

# =====================================================================
# 6. Rebuild
# =====================================================================
Write-Step "6. Rebuilding site"

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) {
    if ($PSCmdlet.ShouldProcess('build.py', 'run')) {
        & $py.Source 'build.py'
        if ($LASTEXITCODE -ne 0) { Write-Warn2 "build.py exited with code $LASTEXITCODE" }
    }
    Write-Ok "build.py finished"
} else {
    Write-Warn2 "python not found in PATH - run 'python build.py' manually."
}

# =====================================================================
# 7. Verify
# =====================================================================
Write-Step "7. Verifying outputs"

$checks = @(
    @{ Path = (Join-Path $Root 'public\maintenance.html');  Desc = 'public/maintenance.html' },
    @{ Path = (Join-Path $Root 'public\Edwin_Tony_CV.pdf'); Desc = 'public/Edwin_Tony_CV.pdf' },
    @{ Path = (Join-Path $Root 'public\_redirects');        Desc = 'public/_redirects' }
)
foreach ($c in $checks) {
    if (Test-Path $c.Path) { Write-Ok $c.Desc } else { Write-Warn2 "$($c.Desc) MISSING" }
}

$leftover = Get-ChildItem -Path (Join-Path $Root 'public') -Filter '*.html' -Recurse -ErrorAction SilentlyContinue |
            Select-String -Pattern '/edwin-portfolio/maintenance\.html' -SimpleMatch -List
if ($leftover) {
    Write-Warn2 "Hardcoded maintenance path still in:"
    $leftover | ForEach-Object { Write-Info $_.Path }
} else {
    Write-Ok "No hardcoded maintenance redirects left in public/"
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green