import sqlite3
p=r'C:\Users\Admin\Desktop\Main Project\integration_review\schema_test\disposable_staging.sqlite3'
c=sqlite3.connect('file:'+p+'?mode=ro',uri=True)
ts=[x[0] for x in c.execute("select name from sqlite_master where type='table' order by name")]
print(ts)
for t in ts: print(t,c.execute('select count(1) from '+t).fetchone()[0])
for t in ['advertisements','lineage_candidates','missingness','evidence_records']:
 print(t,[x[1] for x in c.execute('pragma table_info('+t+')')])
print('missing retrieval',c.execute("select count(1) from missingness where field_name='retrieval_event_id'").fetchone()[0])
print('cohorts',c.execute('select * from cohorts').fetchall())
c.close()
