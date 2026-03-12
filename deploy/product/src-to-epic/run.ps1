param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [Parameter(Mandatory = $true)]
    [string]$SpecPath
)

$ErrorActionPreference = "Stop"
python -m lee.cli.main run product.src-to-epic --project-dir $ProjectDir --spec $SpecPath --skip-plan
