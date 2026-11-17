$ErrorActionPreference = 'Stop'

$inputPath = 'C:\Users\Admin\Downloads\job_ad_dataset.xlsx'
$outputPath = 'C:\Users\Admin\Desktop\Main Project\job_ad_dataset_project_ready.xlsx'

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Read-ZipText($zip, $name) {
    $entry = $zip.GetEntry($name)
    if (-not $entry) { return '' }
    $reader = [IO.StreamReader]::new($entry.Open())
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Get-ColumnNumber([string]$reference) {
    $letters = $reference -replace '\d', ''
    $number = 0
    foreach ($letter in $letters.ToCharArray()) { $number = $number * 26 + ([int][char]$letter - [int][char]'A' + 1) }
    return $number
}

function Read-SheetRows($zip, [int]$sheetNumber) {
    [xml]$xml = Read-ZipText $zip ("xl/worksheets/sheet{0}.xml" -f $sheetNumber)
    $rows = @()
    foreach ($row in $xml.worksheet.sheetData.row) {
        $values = @{}
        foreach ($cell in $row.c) {
            $value = ''
            if ($cell.t -eq 'inlineStr') { $value = ($cell.is.t -join '') }
            elseif ($null -ne $cell.v) { $value = [string]$cell.v }
            $values[(Get-ColumnNumber $cell.r)] = $value
        }
        $max = if ($values.Count) { ($values.Keys | Measure-Object -Maximum).Maximum } else { 0 }
        $array = @()
        for ($i = 1; $i -le $max; $i++) { $array += $(if ($values.ContainsKey($i)) { $values[$i] } else { '' }) }
        $rows += ,$array
    }
    $headers = $rows[0]
    $objects = @()
    foreach ($array in $rows[1..($rows.Count - 1)]) {
        $object = [ordered]@{}
        for ($i = 0; $i -lt $headers.Count; $i++) { $object[$headers[$i]] = if ($i -lt $array.Count) { $array[$i] } else { '' } }
        $objects += [pscustomobject]$object
    }
    return $objects
}

function Normalize-Employer($name) {
    $n = $name -replace '\s+', ' '
    $n = $n -replace '\s*\([^)]*\)', ''
    return $n.Trim()
}

function First-Url($text) {
    if ($text -match 'https?://[^\s)]+') { return $Matches[0] }
    return ''
}

function Infer-Status($description, $caseId) {
    if ($caseId -eq 'JA004' -or $description -match 'no longer accepting') { return 'closed' }
    if ($description -match 'open at capture') { return 'open_at_capture' }
    if ($description -match 'last date|last registration|apply by|valid through|deadline|until ') { return 'deadline_stated' }
    if ($description -match '2022|2024|2025|~1 year old|posted ~2 months') { return 'likely_expired' }
    return 'unknown'
}

function Infer-Deadline($description) {
    if ($description -match '(?i)(?:last date|last registration|apply until|apply by|valid through|deadline)\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}\s+[A-Za-z]+)') { return $Matches[1] }
    return ''
}

function New-Record([string[]]$headers, [hashtable]$values) {
    $record = [ordered]@{}
    foreach ($header in $headers) { $record[$header] = if ($values.ContainsKey($header)) { [string]$values[$header] } else { '' } }
    return [pscustomobject]$record
}

function Add-RowXml($writer, $rowIndex, $headers, $record) {
    $writer.WriteStartElement('row'); $writer.WriteAttributeString('r', [string]$rowIndex)
    for ($i = 0; $i -lt $headers.Count; $i++) {
        $column = ''; $n = $i + 1
        while ($n -gt 0) { $remainder = ($n - 1) % 26; $column = [char]([int](65 + $remainder)) + $column; $n = [math]::Floor(($n - 1) / 26) }
        $value = [string]$record.($headers[$i])
        $writer.WriteStartElement('c'); $writer.WriteAttributeString('r', "$column$rowIndex"); $writer.WriteAttributeString('t', 'inlineStr')
        $writer.WriteStartElement('is'); $writer.WriteStartElement('t'); $writer.WriteString($value); $writer.WriteEndElement(); $writer.WriteEndElement(); $writer.WriteEndElement()
    }
    $writer.WriteEndElement()
}

function New-SheetXml($headers, $records) {
    $settings = [Xml.XmlWriterSettings]::new(); $settings.Encoding = [Text.UTF8Encoding]::new($false); $settings.OmitXmlDeclaration = $false
    $stream = [IO.MemoryStream]::new(); $writer = [Xml.XmlWriter]::Create($stream, $settings)
    $writer.WriteStartDocument(); $writer.WriteStartElement('worksheet', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'); $writer.WriteStartElement('sheetData')
    $headerRecord = [ordered]@{}; foreach ($h in $headers) { $headerRecord[$h] = $h }; Add-RowXml $writer 1 $headers ([pscustomobject]$headerRecord)
    $row = 2; foreach ($record in $records) { Add-RowXml $writer $row $headers $record; $row++ }
    $writer.WriteEndElement(); $writer.WriteEndElement(); $writer.WriteEndDocument(); $writer.Flush(); $writer.Dispose(); return [Text.Encoding]::UTF8.GetString($stream.ToArray())
}

function Write-ZipEntry($zip, $name, $content) {
    $entry = $zip.CreateEntry($name); $stream = $entry.Open(); $bytes = [Text.UTF8Encoding]::new($false).GetBytes($content); $stream.Write($bytes, 0, $bytes.Length); $stream.Dispose()
}

$sourceZip = [IO.Compression.ZipFile]::OpenRead($inputPath)
try {
    $ads = Read-SheetRows $sourceZip 1
    $oldGround = Read-SheetRows $sourceZip 2
    $oldEvidence = Read-SheetRows $sourceZip 3
    $oldLineage = Read-SheetRows $sourceZip 4
} finally { $sourceZip.Dispose() }

$adHeaders = @('case_id','employer_id','employer_name','employer_name_normalized','job_title','job_description_summary','location_text','location_normalized','salary_text','salary_currency','salary_min','salary_max','salary_period','salary_is_estimate','contact_details_redacted','application_route_text','application_url_actual','advertisement_url','platform_type','input_type','observed_at','source_published_at','application_deadline','application_status','source_snapshot_ref','privacy_status','lineage_group_id')
$advertisements = @()
foreach ($ad in $ads) {
    $case = $ad.case_id; $desc = $ad.'job_description (summary; keep full snapshot separately)'; $deadline = Infer-Deadline $desc
    $salary = $ad.salary_text; $currency = if ($salary -match '(?i)INR|Rs\.?') { 'INR' } else { '' }
    $estimate = if ($salary -match '(?i)est\.|estimate|portal estimate|as listed') { 'true' } else { 'false' }
    $status = Infer-Status $desc $case
    $actualApp = First-Url $ad.application_url
    $group = switch ($case) { 'JA003' {'LG003'} 'JA004' {'LG003'} 'JA012' {'LG009'} 'JA013' {'LG009'} default { 'LGOLD' + ('{0:D3}' -f [int]($case.Substring(2))) } }
    $advertisements += New-Record $adHeaders @{ case_id=$case; employer_id=$ad.employer_id; employer_name=$ad.employer_name; employer_name_normalized=(Normalize-Employer $ad.employer_name); job_title=$ad.job_title; job_description_summary=$desc; location_text=$ad.location; location_normalized=$ad.location; salary_text=$salary; salary_currency=$currency; salary_min=''; salary_max=''; salary_period=''; salary_is_estimate=$estimate; contact_details_redacted=$ad.contact_details; application_route_text=$ad.application_url; application_url_actual=$actualApp; advertisement_url=$ad.advertisement_url; platform_type=$ad.platform_type; input_type=$ad.input_type; observed_at=($ad.observed_at + 'T00:00:00+05:30'); source_published_at=''; application_deadline=$deadline; application_status=$status; source_snapshot_ref=('SNAP-' + $case); privacy_status='redacted_or_not_provided'; lineage_group_id=$group }
}

# Live public records collected on 2026-10-22. These are kept conservative: source presence is
# recorded as evidence, while final fraud outcomes remain unresolved pending adjudication.
$liveAds = @(
    @{case='JA039'; employer_id='EMP024'; employer='Airbus India Private Limited'; title='Internship - India Innovation Center - Data Analyst Intern'; desc='Six-month internship supporting data collection, cleaning, exploratory analysis, data models, visualization, and machine-learning projects; requisition JR10446611; posted recently.'; location='Bangalore Area, India'; salary='Not disclosed'; route='Official Airbus Workday application'; app='https://ag.wd3.myworkdayjobs.com/Airbus/job/Bangalore-Area/Internship---India-Innovation-Center----Data-Analyst-Intern_JR10446611'; url='https://ag.wd3.myworkdayjobs.com/Airbus/job/Bangalore-Area/Internship---India-Innovation-Center----Data-Analyst-Intern_JR10446611'; platform='Official employer ATS'; published='recently'; deadline=''; status='open_at_capture'; group='LG039'},
    @{case='JA040'; employer_id='EMP025'; employer='Bear Systems'; title='Data Analytics Intern'; desc='On-site internship in Delhi NCR supporting SQL, dashboards, data cleaning, and reporting; student or early-career role; posted 1 October 2026; closes 19 January 2027.'; location='Delhi NCR, India'; salary='Not disclosed'; route='Official Bear Systems careers application'; app='https://bearsystems.in/careers/data-analytics-intern'; url='https://bearsystems.in/careers/data-analytics-intern'; platform='Official employer careers site'; published='2026-10-01'; deadline='2027-01-19'; status='open_at_capture'; group='LG040'},
    @{case='JA041'; employer_id='EMP026'; employer='Novartis Healthcare Private Limited'; title='Intern AI & Data Science'; desc='MTech/MS internship in India, Hyderabad office; SQL, Python/PySpark, data pipelines, ML and GenAI prototypes; job ID REQ-10089924; dated 16 October 2026.'; location='Hyderabad, India'; salary='Not disclosed'; route='Official Novartis careers application'; app='https://www.novartis.com/careers/career-search/job/details/req-10089924-intern-ai-data-science'; url='https://www.novartis.com/careers/career-search/job/details/req-10089924-intern-ai-data-science'; platform='Official employer careers site'; published='2026-10-16'; deadline=''; status='open_at_capture'; group='LG041'},
    @{case='JA042'; employer_id='EMP027'; employer='Portcast'; title='Data Analyst Intern'; desc='Remote internship across India locations supporting data integrations, data quality, anomaly checks, QA automation, Python, SQL, customer data queries, and dashboards.'; location='India - Bengaluru, Chennai, Delhi, Hyderabad, Kolkata or Mumbai; remote'; salary='Not disclosed'; route='Official Portcast Lever application'; app='https://jobs.lever.co/portcast/f18cc64e-c34a-416c-b213-62a39906260e'; url='https://jobs.lever.co/portcast/f18cc64e-c34a-416c-b213-62a39906260e'; platform='Official employer ATS'; published=''; deadline=''; status='open_at_capture'; group='LG042'},
    @{case='JA043'; employer_id='EMP028'; employer='Cynaris Solutions'; title='Data Analyst Intern'; desc='Hybrid internship in Bengaluru for students or freshers; Excel, SQL, Power BI/Tableau, Python and dashboard/reporting work; unpaid; 15 openings; deadline 31 December 2026.'; location='Bengaluru, India'; salary='Unpaid'; route='Official Cynaris Solutions application'; app='https://cynarissolutions.com/job/data-analyst-intern'; url='https://cynarissolutions.com/job/data-analyst-intern'; platform='Official employer careers site'; published=''; deadline='2026-12-31'; status='open_at_capture'; group='LG043'},
    @{case='JA044'; employer_id='EMP029'; employer='Sattva Consulting'; title='Data Intern - India Data Insights'; desc='Hybrid internship, minimum three months, supporting research, data collection, cleaning, validation, and public-dataset analysis; locations Delhi/Bangalore.'; location='Delhi or Bengaluru, India'; salary='Not disclosed'; route='Official Sattva Freshteam application'; app='https://sattva-talent.freshteam.com/jobs/6UKR2Farvd4o/data-intern-india-data-insights'; url='https://sattva-talent.freshteam.com/jobs/6UKR2Farvd4o/data-intern-india-data-insights'; platform='Official employer ATS'; published=''; deadline=''; status='open_at_capture'; group='LG044'},
    @{case='JA045'; employer_id='EMP030'; employer='Assurant'; title='Data Analytics Intern'; desc='Official India internships page lists a remote Data Analytics Intern opportunity involving reporting tools and Power BI insights, plus related data services, business integration, and data science internships.'; location='India; remote'; salary='Not disclosed'; route='Official Assurant internship page; follow Data Analytics Intern link'; app=''; url='https://jobs.assurant.com/en/assurant-internships-india/'; platform='Official employer careers site'; published=''; deadline=''; status='open_at_capture'; group='LG045'}
)
foreach ($live in $liveAds) {
    $advertisements += New-Record $adHeaders @{case_id=$live.case; employer_id=$live.employer_id; employer_name=$live.employer; employer_name_normalized=(Normalize-Employer $live.employer); job_title=$live.title; job_description_summary=$live.desc; location_text=$live.location; location_normalized=$live.location; salary_text=$live.salary; salary_currency=''; salary_min=''; salary_max=''; salary_period=''; salary_is_estimate='false'; contact_details_redacted='Not provided'; application_route_text=$live.route; application_url_actual=$live.app; advertisement_url=$live.url; platform_type=$live.platform; input_type='URL'; observed_at='2026-10-22T09:30:00+05:30'; source_published_at=$live.published; application_deadline=$live.deadline; application_status=$live.status; source_snapshot_ref=('SNAP-' + $live.case); privacy_status='redacted_or_not_provided'; lineage_group_id=$live.group }
}

# Additional current search-result candidates collected from public LinkedIn search pages on
# 2026-10-22. These are deliberately not treated as verified advertisements until their
# individual listing pages and employer authorization are captured.
$candidateRows = @(
 'Intern - Data Analyst|Tata CLiQ Fashion|Mumbai Metropolitan Region|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern|MTAB Technology Center P LTD - MTC|Chennai|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern|CoverSelf|Bengaluru|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern - Batch 2027|NeenOpal Inc.|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst|Zetheta Algorithms Private Limited|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern - Remote|Skillzenloop|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'DATA ANALYST INTERN|Devryxa|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'DATA ANALYST INTERN|Zenithbyte|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern - Remote|MediNex Workforce|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst / Business Analyst Intern|Softcrayons IT Education|Noida|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Entry & Analysis Intern|Animal Rights Fund|Bengaluru|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Healthcare Data Analyst Intern|Crossing Infotech|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern|Dexterz Technology|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Science Intern|ArcelorMittal Digital Consulting|Hyderabad|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'DATA ANALYST INTERN|Webs IT Solution|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Business Intelligence & Analytics Internship|Springer Capital|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Question-Answer Data Annotator|Indian Institute of Science|Bengaluru|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Intern & IT HR Project Coordinator Walkin|Global Consulting GC.|Mumbai|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Science Intern|Mico|Bengaluru|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Junior Quantitative Analyst|Finominal|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Annotator Intern|SeeWise.AI|Chennai|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst & IT Project & HR Coordinator Intern|Amptier Inc|India|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Intern|GE Vernova|Bengaluru|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Delivery & Program Associate Intern|Crossing Hurdles|Gurugram|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Science Intern - Remote|MediNex Workforce|India Remote|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Analyst Project Intern - Training & Quality|ByteDance|Gurgaon|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Engineer Intern|Huada Data Processing|Ajmer|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'ML Intern|ArcelorMittal Digital Consulting|Hyderabad|https://in.linkedin.com/jobs/data-analyst-intern-jobs',
 'Data Science Intern|Sony Research India|Bengaluru|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Applied Scientist|Meril|Bengaluru|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Investment Systems & Quant Research Intern|Aurrevia|Mumbai|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Intern - Data Analytics|AuthBridge|Gurugram|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Business Analytics Intern|Dexter''s Tech|India|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Entry & Analysis Intern|Animal Rights Fund|Bengaluru|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst|Zetheta Algorithms Private Limited|India|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst Intern|UM IT Private Limited|India|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Scientist|PhonePe|Bengaluru|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Engineer 1|Cummins India|Pune|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Engineer 12|Cummins India|Pune|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Engineer 2|Cummins India|Pune|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Annotator Intern|SeeWise.AI|Chennai|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst Intern|Portcast|Delhi|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst Intern|Portcast|Chennai|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst Intern|Portcast|Kolkata|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Healthcare Data Analyst Intern|Skillzenloop|India Remote|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Data Analyst Intern|MediNex Workforce|India Remote|https://in.linkedin.com/jobs/data-analysis-intern-jobs',
 'Product Analyst Intern|Bureau|Bengaluru|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Business Analytics Internship|Turtlemint|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Business Analytics Internship|Isourse|Dwarka|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Intern - Data Analytics - Radar and Flight|Red Balloon Aerospace|Vijayawada|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Business Analytics Internship|Openhouse|Gurgaon|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'MIS Intern|Vecmocon Technologies|Gurugram|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Campus - BI Consultant|Thoucentric|Bengaluru|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Decision Scientist Intern|The India Prosperity Initiative|Gurugram|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Supply Chain Intern|Purplle.com|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data & Strategy Intern|Ambak|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Finance/Investment Analyst-Intern|Kodo|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Customer Success Analyst- Intern|Fundamento|Delhi|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Marketing Analyst Intern|Unifynd Labs|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Power BI Developer Intern|Crossing Infotech|India Remote|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Evaluation & Insights Intern, AI Delivery|Blue Machines AI|Bengaluru|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Intern Analyst - Batch of 2028|Bain & Company|Gurugram|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Intern Analyst - Batch of 2028|Bain & Company|Delhi|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Intern - Technology|TRC Companies|Hyderabad|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Science Intern|Dexter''s Tech|India|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Marketing Analytics Intern|Transmission|Delhi NCR|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Analyst Intern|Vortenza Systems|India|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Analyst Intern|WebBoost Solutions by UM|India|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Analyst Intern|PV Doctor|India|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Science Intern|Vortenza Systems|India|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Science Intern|Mico|Bengaluru|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Data Analyst Intern|CoverSelf|Bengaluru|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'HR Analytics Intern|Daimler India Commercial Vehicles|Chennai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Media & Analytics Intern|Only Much Louder|Mumbai|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Decision Scientist Intern|The India Prosperity Initiative|Gurugram|https://in.linkedin.com/jobs/analytics-intern-jobs',
 'Machine Learning Intern|ERIC Robotics|Pune|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Intern - AI/ML|Tower Research Capital|Gurgaon|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Data Science Intern|Electronic Arts|Hyderabad|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|Sparks To Ideas|Amreli|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|Sparks To Ideas|Porbandar|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|MediNex Workforce|India Remote|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|Sparks To Ideas|Surat|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|Meril|Bengaluru|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Computer Vision Engineer Intern|Augle AI|Pune|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|ThinkNovaa|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI/ML Engineering Intern|Daice Labs|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|Crossing Infotech|India Remote|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI Machine Learning Intern|SkillNexGen|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Research Intern - AI|GE HealthCare|Bengaluru|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Machine Learning Intern|Unified Mentor Private Limited|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|ThinkNovaa|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|eTeam|Noida|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|TalentXM|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|Droisys|Noida|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Technical Intern|BharatGen|Mumbai|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI Engineer Intern|SARAS DYNAMICS|Coimbatore|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Artificial Intelligence Intern|India''s Future Investors|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Speech Recognition Intern|Sony Research India|Bengaluru|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'PhD Intern, Apple Ads - Machine Learning|Apple|Hyderabad|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI Intern|Faclon Labs|Mumbai|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI/ML Engineering Intern|Daice Labs|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Founders Office - Fullstack AI/ML Developer Intern|CraticAI|India|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'AI Research Internship|Lexsi Labs|Mumbai|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'LLM Research Intern|Sony Research India|Bengaluru|https://in.linkedin.com/jobs/machine-learning-internship-jobs',
 'Intern - Business Analyst|Aristok Technologies|Pune|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern|EFX Connect|Pune|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern 6 months|Sirma Business Consulting India|Bengaluru|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern|MediNex Workforce|India Remote|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern|Skillzenloop|India Remote|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'BDE/BA Intern|ViralChilly|Jaipur|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Strategy and Business Development Intern|PATH|Delhi NCR|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Sales & Business Development Intern|Pyvot|Kolkata|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Management Trainee Business Development|McGraw Hill|Bengaluru|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Sales & Business Development Intern|Briqen AI|Mumbai|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Product Analyst Intern|AuthBridge|Gurugram|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Product Analyst Intern|Snapdeal|Gurugram|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern|LinkedIn India|Bengaluru|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Business Analyst Intern|Analytics Career Connect|India Remote|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Product Analyst Intern|Amber|Pune|https://in.linkedin.com/jobs/business-analyst-intern-jobs',
 'Product Analyst Intern|Finifi|Bengaluru|https://in.linkedin.com/jobs/business-analyst-intern-jobs'
)
$candidateNumber = 46
foreach ($candidate in $candidateRows) {
    if ($candidateNumber -ge 146) { break }
    $parts = $candidate -split '\|', 4; $case = 'JA' + ('{0:D3}' -f $candidateNumber); $candidateNumber++
    $employer = $parts[1]; $location = $parts[2]; $source = $parts[3]; $employerId = 'CAND_' + (($employer -replace '[^A-Za-z0-9]', '').ToUpper())
    $advertisements += New-Record $adHeaders @{case_id=$case; employer_id=$employerId; employer_name=$employer; employer_name_normalized=(Normalize-Employer $employer); job_title=$parts[0]; job_description_summary='Candidate listing surfaced in a public LinkedIn India search result; individual advertisement page and employer authorization not yet captured.'; location_text=$location; location_normalized=$location; salary_text='Not captured'; salary_currency=''; salary_min=''; salary_max=''; salary_period=''; salary_is_estimate='false'; contact_details_redacted='Not provided'; application_route_text='LinkedIn search result; direct application URL not captured'; application_url_actual=''; advertisement_url=$source; platform_type='Public job-search listing'; input_type='URL'; observed_at='2026-10-22T09:30:00+05:30'; source_published_at='current search result'; application_deadline=''; application_status='candidate_unverified'; source_snapshot_ref=('SNAP-' + $case); privacy_status='redacted_or_not_provided'; lineage_group_id=('LG' + ('{0:D3}' -f $candidateNumber)) }
}

$gtHeaders = @('case_id','employer_identity_label','vacancy_authorization_label','fraud_outcome_label','label_rationale','label_evidence_refs','annotator_id','adjudication_status','label_confidence')
$groundTruth = @()
foreach ($gt in $oldGround) {
    $case = $gt.case_id
    if ($case -in @('JA010','JA035','JA036','JA037','JA038')) {
        $identity='verified'; $vacancy='supported'; $fraud='unresolved'; $confidence='medium'; $rationale='Official institutional domain supports employer identity and the existence of a posted vacancy; fraud outcome remains unresolved because legitimacy requires a completed multi-claim review.'
    } elseif ($case -in @('JA025','JA026','JA027','JA028','JA029','JA030','JA031','JA032','JA033','JA034')) {
        $identity='unresolved'; $vacancy='unresolved'; $fraud='unresolved'; $confidence='low'; $rationale='Third-party sources cite an official portal, but the official source was not directly captured or audited; do not promote this to verified or supported without direct evidence.'
    } else {
        $identity='unresolved'; $vacancy='unresolved'; $fraud='unresolved'; $confidence='low'; $rationale='Insufficient direct evidence to assign a claim label.'
    }
    $refs = if ($case -eq 'JA010') {'EV010'} elseif ($case -match '^JA0(25|26|27|28|29|30|31|32|33|34)$') {'EV' + $case.Substring(2)} elseif ($case -match '^JA0(35|36|37|38)$') {'EV' + $case.Substring(2)} else {''}
    $groundTruth += New-Record $gtHeaders @{case_id=$case; employer_identity_label=$identity; vacancy_authorization_label=$vacancy; fraud_outcome_label=$fraud; label_rationale=$rationale; label_evidence_refs=$refs; annotator_id=''; adjudication_status='pending_human_review'; label_confidence=$confidence}
}
foreach ($live in $liveAds) {
    $groundTruth += New-Record $gtHeaders @{case_id=$live.case; employer_identity_label='verified'; vacancy_authorization_label='supported'; fraud_outcome_label='unresolved'; label_rationale='Current advertisement was observed on an employer-controlled careers site or employer ATS. This supports employer identity and vacancy authorization at collection time; final fraud outcome remains unresolved pending human adjudication.'; label_evidence_refs=('EV' + $live.case.Substring(2)); annotator_id=''; adjudication_status='pending_human_review'; label_confidence='medium'}
}
for ($n=46; $n -lt $candidateNumber; $n++) {
    $case = 'JA' + ('{0:D3}' -f $n); $groundTruth += New-Record $gtHeaders @{case_id=$case; employer_identity_label='unresolved'; vacancy_authorization_label='unresolved'; fraud_outcome_label='unresolved'; label_rationale='Candidate surfaced in a public search listing; direct advertisement and employer authorization have not yet been independently captured.'; label_evidence_refs=('EV' + ('{0:D3}' -f $n)); annotator_id=''; adjudication_status='pending_human_review'; label_confidence='low'}
}

$evHeaders = @('evidence_id','case_id','claim_type','source_url','source_type','retrieved_at','source_published_at','evidence_state','matched_fields','contradiction_details','evidence_rationale','source_snapshot_ref')
$evidence = @()
foreach ($ev in $oldEvidence) {
    $state = $ev.evidence_state
    if ($ev.source_type -match '(?i)official employer source' -and $ev.claim_type -eq 'vacancy authorization') { $state='supported' }
    elseif ($ev.source_type -match '(?i)third-party aggregator citing official portal') { $state='unverified' }
    $contradiction = if ($state -eq 'contradicted') { $ev.evidence_rationale } else { '' }
    $evidence += New-Record $evHeaders @{evidence_id=$ev.evidence_id; case_id=$ev.case_id; claim_type=$ev.claim_type; source_url=$ev.'source_url / source'; source_type=$ev.source_type; retrieved_at=($ev.retrieved_at + 'T00:00:00+05:30'); source_published_at=''; evidence_state=$state; matched_fields=$ev.matched_fields; contradiction_details=$contradiction; evidence_rationale=$ev.evidence_rationale; source_snapshot_ref=('SNAP-' + $ev.case_id)}
}
foreach ($live in $liveAds) {
    $evidence += New-Record $evHeaders @{evidence_id=('EV' + $live.case.Substring(2)); case_id=$live.case; claim_type='vacancy authorization'; source_url=$live.url; source_type=$live.platform; retrieved_at='2026-10-22T09:30:00+05:30'; source_published_at=$live.published; evidence_state='supported'; matched_fields='employer, title, location, role details, application route'; contradiction_details=''; evidence_rationale='Current role details were directly observed on an employer-controlled careers page or employer ATS during collection.'; source_snapshot_ref=('SNAP-' + $live.case)}
}
for ($n=46; $n -lt $candidateNumber; $n++) { $case = 'JA' + ('{0:D3}' -f $n); $evidence += New-Record $evHeaders @{evidence_id=('EV' + ('{0:D3}' -f $n)); case_id=$case; claim_type='vacancy authorization'; source_url='public LinkedIn search listing'; source_type='Public job-search listing'; retrieved_at='2026-10-22T09:30:00+05:30'; source_published_at='current search result'; evidence_state='unverified'; matched_fields='title, employer, location as displayed in search result'; contradiction_details=''; evidence_rationale='Search-result candidate only; individual listing and employer source require follow-up.'; source_snapshot_ref=('SNAP-' + $case)} }

$linHeaders = @('lineage_group_id','case_id','source_relationship','related_case_ids','lineage_signals','lineage_review_status','lineage_rationale')
$lineage = @()
foreach ($line in $oldLineage) {
    $relationship = if ($line.case_id -in @('JA003','JA004','JA012','JA013')) {'copied_or_derived'} else {$line.source_relationship}
    $group = if ($line.case_id -in @('JA003','JA004')) {'LG003'} elseif ($line.case_id -in @('JA012','JA013')) {'LG009'} else {'LGOLD' + ('{0:D3}' -f [int]$line.case_id.Substring(2))}
    $lineage += New-Record $linHeaders @{lineage_group_id=$group; case_id=$line.case_id; source_relationship=$relationship; related_case_ids=$line.related_case_ids; lineage_signals=$line.lineage_signals; lineage_review_status=$line.lineage_review_status; lineage_rationale=$line.lineage_rationale}
}
foreach ($live in $liveAds) { $lineage += New-Record $linHeaders @{lineage_group_id=$live.group; case_id=$live.case; source_relationship='original'; related_case_ids=''; lineage_signals='new live collection'; lineage_review_status='manually reviewed'; lineage_rationale='No duplicate relationship identified during collection.'} }
for ($n=46; $n -lt $candidateNumber; $n++) { $case = 'JA' + ('{0:D3}' -f $n); $lineage += New-Record $linHeaders @{lineage_group_id=('LG' + ('{0:D3}' -f ($n + 1))); case_id=$case; source_relationship='unknown'; related_case_ids=''; lineage_signals='search-result candidate'; lineage_review_status='automated candidate'; lineage_rationale='Individual listing page not yet captured; duplicate relationship unresolved.'} }

$snapHeaders = @('source_snapshot_ref','case_id','source_url','snapshot_type','snapshot_status','captured_at','retention_note')
$snapshots = @(); foreach ($ad in $advertisements) { $snapshots += New-Record $snapHeaders @{source_snapshot_ref=$ad.source_snapshot_ref; case_id=$ad.case_id; source_url=$ad.advertisement_url; snapshot_type='html_or_pdf_or_image'; snapshot_status='not_collected'; captured_at=''; retention_note='Collect and retain only where legally permitted; otherwise retain a provenance record and hash.'} }

$dictHeaders = @('sheet_name','column_name','definition','allowed_values_or_format','required_for_training')
$dictionary = @(
    (New-Record $dictHeaders @{sheet_name='advertisements';column_name='case_id';definition='Unique advertisement instance identifier';allowed_values_or_format='JA###';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='advertisements';column_name='source_snapshot_ref';definition='Reference to the original captured source or documented absence';allowed_values_or_format='SNAP-JA###';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='ground_truth';column_name='employer_identity_label';definition='Whether the named employer identity is supported by evidence';allowed_values_or_format='verified, contradicted, unresolved';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='ground_truth';column_name='vacancy_authorization_label';definition='Whether the employer authorized this specific vacancy';allowed_values_or_format='supported, contradicted, unresolved';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='ground_truth';column_name='fraud_outcome_label';definition='Final fraud determination after adjudication';allowed_values_or_format='confirmed_fraudulent, confirmed_legitimate, unresolved';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='evidence';column_name='claim_type';definition='Claim addressed by an evidence item';allowed_values_or_format='employer identity, vacancy authorization, contact, application route';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='evidence';column_name='evidence_state';definition='How the evidence bears on the claim';allowed_values_or_format='supported, contradicted, unverified, unavailable';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='lineage';column_name='source_relationship';definition='Relationship of an ad to related advertisements';allowed_values_or_format='original, independent, copied_or_derived, unknown';required_for_training='yes'}),
    (New-Record $dictHeaders @{sheet_name='advertisements';column_name='application_status';definition='Operational status at collection or inferred from source';allowed_values_or_format='open_at_capture, closed, deadline_stated, likely_expired, unknown';required_for_training='no'}),
    (New-Record $dictHeaders @{sheet_name='advertisements';column_name='salary_is_estimate';definition='Whether salary is explicitly estimated or portal-derived';allowed_values_or_format='true,false';required_for_training='no'})
)

$guideHeaders = @('topic','rule')
$guide = @(
    (New-Record $guideHeaders @{topic='Employer identity';rule='Use verified only when a reliable source directly supports that the named employer exists and matches the advertisement.'}),
    (New-Record $guideHeaders @{topic='Vacancy authorization';rule='Evaluate the specific role separately from employer identity. A real employer can have an unauthorized or stale advertisement.'}),
    (New-Record $guideHeaders @{topic='Fraud outcome';rule='Use confirmed_fraudulent or confirmed_legitimate only after adjudication with sufficient evidence. Otherwise use unresolved.'}),
    (New-Record $guideHeaders @{topic='Expired ads';rule='Expired or closed does not mean fraudulent. Record application_status separately.'}),
    (New-Record $guideHeaders @{topic='Duplicates';rule='Keep reposts as separate advertisement instances but group them by lineage_group_id and use group-aware train/test splits.'}),
    (New-Record $guideHeaders @{topic='Privacy';rule='Redact personal contact details and retain only the minimum information needed for audit.'})
)

$reportHeaders = @('metric','value','interpretation')
$report = @(
    (New-Record $reportHeaders @{metric='advertisement_count';value=$advertisements.Count;interpretation='Collected advertisement instances'}),
    (New-Record $reportHeaders @{metric='evidence_count';value=$evidence.Count;interpretation='Evidence records linked by evidence_id'}),
    (New-Record $reportHeaders @{metric='confirmed_fraudulent_count';value=0;interpretation='No confirmed fraudulent examples are currently present'}),
    (New-Record $reportHeaders @{metric='confirmed_legitimate_count';value=0;interpretation='Conservative correction leaves legitimacy outcomes unresolved pending adjudication'}),
    (New-Record $reportHeaders @{metric='unresolved_outcome_count';value=($groundTruth | Where-Object {$_.fraud_outcome_label -eq 'unresolved'}).Count;interpretation='Requires human review before supervised training'}),
    (New-Record $reportHeaders @{metric='snapshot_status';value='not_collected';interpretation='Original source snapshots still need to be collected where permitted'}),
    (New-Record $reportHeaders @{metric='training_readiness';value='not_ready_for_supervised_fraud_classification';interpretation='Add adjudicated positive and negative labels and preserve snapshots first'})
)

$sheets = @(
    @{name='README'; headers=@('section','content'); records=@(
        (New-Record @('section','content') @{section='purpose';content='Project-ready schema for job advertisement authenticity research; labels are conservative and unresolved where evidence is insufficient.'}),
        (New-Record @('section','content') @{section='source_file';content=$inputPath}),
        (New-Record @('section','content') @{section='important_limit';content='This workbook is not yet suitable for supervised fraud classification because it contains no confirmed fraudulent outcomes and no original source snapshots.'}),
        (New-Record @('section','content') @{section='next_step';content='Collect permitted snapshots, directly verify official sources, adjudicate labels, and add confirmed fraudulent and legitimate examples.'})
    )},
    @{name='Advertisements';headers=$adHeaders;records=$advertisements},
    @{name='GroundTruth';headers=$gtHeaders;records=$groundTruth},
    @{name='Evidence';headers=$evHeaders;records=$evidence},
    @{name='Lineage';headers=$linHeaders;records=$lineage},
    @{name='SourceSnapshots';headers=$snapHeaders;records=$snapshots},
    @{name='DataDictionary';headers=$dictHeaders;records=$dictionary},
    @{name='AnnotationGuide';headers=$guideHeaders;records=$guide},
    @{name='QualityReport';headers=$reportHeaders;records=$report}
)

if (Test-Path $outputPath) { Remove-Item -LiteralPath $outputPath -Force }
$outZip = [IO.Compression.ZipFile]::Open($outputPath, [IO.Compression.ZipArchiveMode]::Create)
try {
    $contentTypes = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    for ($i=1;$i -le $sheets.Count;$i++) { $contentTypes += "<Override PartName=`"/xl/worksheets/sheet$i.xml`" ContentType=`"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml`"/>" }
    $contentTypes += '</Types>'
    Write-ZipEntry $outZip '[Content_Types].xml' $contentTypes
    Write-ZipEntry $outZip '_rels/.rels' '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    $workbook = '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
    $rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    for ($i=0;$i -lt $sheets.Count;$i++) { $id=$i+1; $workbook += "<sheet name=`"$($sheets[$i].name)`" sheetId=`"$id`" r:id=`"rId$id`"/>"; $rels += "<Relationship Id=`"rId$id`" Type=`"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet`" Target=`"worksheets/sheet$id.xml`"/>" }
    $workbook += '</sheets></workbook>'; $rels += '</Relationships>'
    Write-ZipEntry $outZip 'xl/workbook.xml' $workbook; Write-ZipEntry $outZip 'xl/_rels/workbook.xml.rels' $rels
    for ($i=0;$i -lt $sheets.Count;$i++) { Write-ZipEntry $outZip ("xl/worksheets/sheet{0}.xml" -f ($i+1)) (New-SheetXml $sheets[$i].headers $sheets[$i].records) }
} finally { $outZip.Dispose() }

Write-Output $outputPath
