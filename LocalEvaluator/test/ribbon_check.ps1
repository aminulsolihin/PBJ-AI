# Reads Excel's ribbon through Windows UI Automation (names of controls only) and reports
# whether the Local Evaluator button and pane are present in each Excel window.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]
$Kind = [System.Windows.Automation.ControlType]
$deep = [System.Windows.Automation.TreeScope]::Descendants
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$windows = $AE::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,
    (New-Object System.Windows.Automation.PropertyCondition($AE::ClassNameProperty, 'XLMAIN')))
"Excel windows: $($windows.Count) at $(Get-Date -Format 'HH:mm:ss')"
foreach ($win in $windows) {
    "=== '$($win.Current.Name)' (process $($win.Current.ProcessId))"
    $all = $win.FindAll($deep, [System.Windows.Automation.Condition]::TrueCondition)
    $tabs = @($all | Where-Object { $_.Current.ControlType -eq $Kind::TabItem -and $_.Current.ClassName -match 'Ribbon' } | ForEach-Object { $_.Current.Name })
    "  ribbon tabs : $($tabs -join ' | ')"
    $groups = @($all | Where-Object { $_.Current.ControlType -eq $Kind::Group -and $_.Current.ClassName -eq 'NetUIChunk' } | ForEach-Object { $_.Current.Name } | Where-Object { $_ } | Select-Object -Unique)
    "  tab groups  : $($groups -join ' | ')"
    $mine = @($all | Where-Object { $_.Current.Name -eq 'Local Evaluator' })
    if (-not $mine.Count) { "  Local Evaluator: NOT FOUND in this window" }
    foreach ($el in $mine) {
        $parent = $walker.GetParent($el)
        "  Local Evaluator: [$($el.Current.ControlType.ProgrammaticName.Replace('ControlType.', ''))] $($el.Current.ClassName), inside '$($parent.Current.Name)', on screen=$(-not $el.Current.IsOffscreen)"
    }
}
