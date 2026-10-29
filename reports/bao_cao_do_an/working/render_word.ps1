$reportRoot = 'D:\chatbot-law\reports\bao_cao_do_an'
$reportPath = Join-Path $reportRoot 'Bao_cao_Hoc_phan_Ung_dung_AI_Mai_Tran_Thien_Tam.docx'
$reportWord = New-Object -ComObject Word.Application
$reportWord.Visible = $false
$reportWord.DisplayAlerts = 0
try {
    $reportDocument = $reportWord.Documents.Open($reportPath, $false, $false)
    $reportDocument.Repaginate()
    $null = $reportDocument.Fields.Update()
    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.Update() }
    foreach ($reportStyleId in -20,-21,-22) {
        $reportTocStyle = $reportDocument.Styles.Item($reportStyleId)
        $reportTocStyle.Font.Name = 'Times New Roman'
        $reportTocStyle.Font.Size = 14
        $reportTocStyle.ParagraphFormat.LineSpacingRule = 0
        $reportTocStyle.ParagraphFormat.SpaceAfter = 4
        $reportTocStyle.ParagraphFormat.SpaceBefore = 0
    }
    $reportDocument.Repaginate()
    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.UpdatePageNumbers() }
    $reportDocument.Save()
    $reportDocument.ExportAsFixedFormat((Join-Path $reportRoot 'working\bao_cao_qa.pdf'),17)
    $reportDocument.Content.Text | Set-Content -LiteralPath (Join-Path $reportRoot 'working\word_final_text.txt') -Encoding utf8
    Write-Output ('Word pages: ' + $reportDocument.ComputeStatistics(2))
    Write-Output ('TOC fields: ' + $reportDocument.TablesOfContents.Count)
    $reportDocument.Close(0)
} finally {
    $reportWord.Quit()
}
