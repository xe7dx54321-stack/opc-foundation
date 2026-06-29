# M3C-5A Quick URL Check Script

param(
    [int]$Timeout = 15
)

$urls = @(
    # DNS failure candidates
    "https://research.bofa.com",
    "https://www.bankofamerica.com/market-insights",
    "https://www.bankofamerica.com/research",
    "https://www.citiinstitute.com",
    "https://www.citi.com/insights",
    "https://www.citi.com/citi-gps",
    "https://www.chinafundnews.com",
    "https://www.chnfund.com",
    "https://www.hkstockresearch.com",
    
    # 404 sources
    "https://www.goldmansachs.com/greater-china/our-views",
    "https://www.goldmansachs.com/insights/china",
    "https://www.goldmansachs.com/greater-china",
    "https://www.barclays.com/research",
    "https://www.barclays.com/insights",
    "https://www.barclays.com/investment-bank/insights",
    "https://www.goldmansachs.com/podcasts/exchanges",
    "https://www.goldmansachs.com/insights/podcasts/exchanges",
    "https://www.goldmansachs.com/insights/podcasts",
    "https://www.goldmansachs.com/conferences/communacopia",
    "https://www.goldmansachs.com/events/communacopia",
    "https://www.goldmansachs.com/events",
    "https://www.ti.com/investor",
    "https://investor.ti.com",
    "https://ir.ti.com",
    "https://www.merck.com/investor",
    "https://www.merck.com/investors",
    "https://investors.merck.com",
    "https://www.benzinga.com/analytics/ratings",
    "https://www.benzinga.com/analyst-ratings",
    "https://www.benzinga.com",
    "https://wallstreetcn.com/vip",
    "https://wallstreetcn.com/news",
    "https://wallstreetcn.com",
    
    # 403 sources
    "https://www.investing.com/equities/ratings",
    "https://www.investing.com/analysts/ratings",
    "https://www.investing.com",
    
    # 401 sources
    "https://www.reuters.com",
    "https://www.reuters.com/news",
    "https://www.marketwatch.com",
    "https://www.wsj.com",
    
    # timeout source
    "https://www.quanshang.cn",
    
    # browser UA test
    "https://www.streetinsider.com",
    "https://www.tipranks.com"
)

$browserUA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

Write-Host "======================================================================"
Write-Host "M3C-5A Quick URL Check"
Write-Host "URL count: $($urls.Count)"
Write-Host "======================================================================"
Write-Host ""

$results = @()

foreach ($url in $urls) {
    Write-Host -NoNewline "Checking: $url "
    
    try {
        # Default UA
        $response = curl.exe -s -w "%{http_code}" --max-time $Timeout -L -o NUL $url 2>$null
        $status = [int]$response
        
        # Browser UA
        $response2 = curl.exe -s -w "%{http_code}" --max-time $Timeout -L -A $browserUA -o NUL $url 2>$null
        $status2 = [int]$response2
        
        $result = @{
            url = $url
            default_status = $status
            browser_status = $status2
        }
        $results += $result
        
        $color = "Red"
        if ($status -ge 200 -and $status -lt 400) { $color = "Green" }
        elseif ($status -ge 400 -and $status -lt 500) { $color = "Yellow" }
        
        Write-Host -ForegroundColor $color "default=$status browser=$status2"
    }
    catch {
        Write-Host -ForegroundColor Red "FAILED: $_"
        $results += @{ url = $url; default_status = 0; browser_status = 0 }
    }
}

Write-Host ""
Write-Host "======================================================================"
Write-Host "Check complete!"
Write-Host "======================================================================"

# Save results
$outputDir = Join-Path $PSScriptRoot "..\data\foundation_trial\url_recovery"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$outputFile = Join-Path $outputDir "quick_check_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"

$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8
Write-Host "Results saved to: $outputFile"
