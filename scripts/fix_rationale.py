from pathlib import Path
p = Path('src/evidence/collector.py')
s = p.read_text(encoding='utf-8')
old = '        rationale = "Vacancy attributes correspond, but employer/source authority or independence is not sufficiently established."\n    else:'
new = '        rationale = "Vacancy attributes correspond, but employer/source authority or independence is not sufficiently established; authorization is unresolved."\n    else:'
if old not in s:
    raise SystemExit('not found')
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('ok')
