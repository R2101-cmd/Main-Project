$ErrorActionPreference = 'Stop'
$xlsx = 'C:\Users\Admin\Desktop\Main Project\data\raw\job_ad_dataset.xlsx'
$output = 'C:\Users\Admin\Desktop\Main Project\data\annotations\job_ad_authorization_evaluation.jsonl'
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Read-ZipText($zip, $name) { $e=$zip.GetEntry($name); $r=[IO.StreamReader]::new($e.Open()); try{return $r.ReadToEnd()}finally{$r.Dispose()} }
function ColNum($ref) { $letters=$ref -replace '\d',''; $n=0; foreach($c in $letters.ToCharArray()){$n=$n*26+([int][char]$c-[int][char]'A'+1)}; return $n }
function Read-Sheet($zip, $number) {
    [xml]$x=Read-ZipText $zip ("xl/worksheets/sheet$number.xml"); $rows=@()
    foreach($row in $x.worksheet.sheetData.row){$v=@{}; foreach($c in $row.c){$value=if($c.t -eq 'inlineStr'){($c.is.t -join '')}elseif($null -ne $c.v){[string]$c.v}else{''};$v[(ColNum $c.r)]=$value};$max=($v.Keys|Measure-Object -Maximum).Maximum;$a=@();for($i=1;$i -le $max;$i++){$a+=($(if($v.ContainsKey($i)){$v[$i]}else{''}))};$rows+=,$a}
    $h=$rows[0];$out=@();foreach($a in $rows[1..($rows.Count-1)]){$o=[ordered]@{};for($i=0;$i -lt $h.Count;$i++){$o[$h[$i]]=if($i -lt $a.Count){$a[$i]}else{''}};$out+=[pscustomobject]$o};return $out
}

$zip=[IO.Compression.ZipFile]::OpenRead($xlsx);try{$ads=Read-Sheet $zip 2;$gts=Read-Sheet $zip 3;$evs=Read-Sheet $zip 4;$lins=Read-Sheet $zip 5}finally{$zip.Dispose()}
$gtBy=@{};foreach($g in $gts){$gtBy[$g.case_id]=$g}
$evBy=@{};foreach($e in $evs){if(-not $evBy.ContainsKey($e.case_id)){$evBy[$e.case_id]=@()};$evBy[$e.case_id]+=$e}
$linBy=@{};foreach($l in $lins){$linBy[$l.case_id]=$l}
$records=@()
foreach($ad in $ads){
    $case=$ad.case_id;$gt=$gtBy[$case];$lin=$linBy[$case];$group=$lin.lineage_group_id
    $groupNumber=0;if($group -match '(\d+)$'){$groupNumber=[int]$Matches[1]};$mod=$groupNumber%10;$partition=if($mod -lt 7){'train'}elseif($mod -lt 9){'validation'}else{'test'}
    $evidence=@();foreach($e in $evBy[$case]){$retrieval=if($e.evidence_state -eq 'unavailable'){'unavailable'}elseif($e.evidence_state -eq 'unverified'){'available_at_observation'}else{'available_at_observation'};$evidence+=([ordered]@{id=$e.evidence_id;evidence_state=$e.evidence_state;source_url=$e.source_url;source_type=$e.source_type;retrieval_status=$retrieval;lineage_group=$group;summary=$e.evidence_rationale;rationale=$e.evidence_rationale})}
    $records+=([ordered]@{id=$case;vacancy_group=$group;partition=$partition;text=($ad.job_title+'. '+$ad.employer_name+'. '+$ad.location_text+'. '+$ad.job_description_summary);authorization_label=$gt.vacancy_authorization_label;employer_identity=$gt.employer_identity_label;synthetic=$false;annotation_status='provisional_reviewed_from_current_evidence';annotation_rationale=$gt.label_rationale;evidence=$evidence})
}
[IO.File]::WriteAllLines($output, @($records|ForEach-Object{$_|ConvertTo-Json -Compress -Depth 6}), [Text.UTF8Encoding]::new($false))
Write-Output $output
