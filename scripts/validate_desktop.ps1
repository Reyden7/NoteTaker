param([string]$BundleDirectory = 'dist\NoteTaker', [string]$ReportFile = 'docs\evidence\desktop-validation.json')
# Compiled UI startup smoke test on this developer PC, not clean Windows acceptance.
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class NoteTakerWindowProbe {
    private delegate bool EnumWindowProc(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowProc callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern IntPtr SendMessageTimeout(IntPtr window, uint message, IntPtr wparam, IntPtr lparam, uint flags, uint timeout, out IntPtr result);
    [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr window, uint message, IntPtr wparam, IntPtr lparam);
    public static string Title(IntPtr window) {
        var text = new StringBuilder(512);
        GetWindowText(window, text, text.Capacity);
        return text.ToString();
    }
    public static IntPtr Find(int processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((window, parameter) => {
            uint owner;
            GetWindowThreadProcessId(window, out owner);
            if (owner == (uint)processId && Title(window).StartsWith("NoteTaker")) {
                found = window;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
    public static bool Responsive(IntPtr window) {
        IntPtr result;
        return SendMessageTimeout(window, 0, IntPtr.Zero, IntPtr.Zero, 2, 1000, out result) != IntPtr.Zero;
    }
    public static bool Close(IntPtr window) { return PostMessage(window, 0x0010, IntPtr.Zero, IntPtr.Zero); }
}
'@
$notetakerRoot = Split-Path -Parent $PSScriptRoot
$notetakerExe = Join-Path (Join-Path $notetakerRoot $BundleDirectory) 'NoteTaker.exe'
$notetakerData = Join-Path $notetakerRoot ('output\desktop-validation\' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $notetakerData | Out-Null
$notetakerProcess = Start-Process -FilePath $notetakerExe -ArgumentList @('--data-dir', $notetakerData) -WorkingDirectory $notetakerData -WindowStyle Hidden -PassThru
$notetakerReady = $false
$notetakerClosed = $false
$notetakerTitle = ''
try {
    $notetakerDeadline = [DateTime]::UtcNow.AddSeconds(20)
    while ([DateTime]::UtcNow -lt $notetakerDeadline) {
        $notetakerProcess.Refresh()
        if ($notetakerProcess.HasExited) { throw 'Compiled UI exited before its main window became available' }
        $notetakerWindow = [NoteTakerWindowProbe]::Find($notetakerProcess.Id)
        if ($notetakerWindow -ne [IntPtr]::Zero -and [NoteTakerWindowProbe]::Responsive($notetakerWindow)) {
            $notetakerReady = $true
            $notetakerTitle = [NoteTakerWindowProbe]::Title($notetakerWindow)
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $notetakerReady) { throw 'Compiled UI window was not ready within 20 seconds' }
    if (-not [NoteTakerWindowProbe]::Close($notetakerWindow)) { throw 'Compiled UI did not accept a normal WM_CLOSE request' }
    $notetakerClosed = $notetakerProcess.WaitForExit(10000)
    if (-not $notetakerClosed -or $notetakerProcess.ExitCode -ne 0) { throw 'Compiled UI did not exit normally' }
    if (-not (Test-Path -LiteralPath (Join-Path $notetakerData 'notetaker.sqlite3'))) { throw 'Compiled UI did not initialize its data directory' }
    $notetakerReport = @{
        environment='developer PC; not clean Windows; host not disconnected'
        tested_at_utc=[DateTime]::UtcNow.ToString('o')
        executable_sha256=(Get-FileHash -LiteralPath $notetakerExe -Algorithm SHA256).Hash.ToLowerInvariant()
        window_title=$notetakerTitle
        responsive_main_window=$notetakerReady
        graceful_exit=$notetakerClosed
        isolated_data_directory=$notetakerData
        scope='compiled UI startup and normal shutdown only; no meeting or quality acceptance'
    }
    $notetakerReport | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $notetakerRoot $ReportFile)
    Write-Output 'Compiled UI opened a responsive main window, created its database and closed normally.'
} finally {
    $notetakerProcess.Refresh()
    if (-not $notetakerProcess.HasExited) { Stop-Process -Id $notetakerProcess.Id }
}
