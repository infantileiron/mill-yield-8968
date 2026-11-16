import time,uuid
from datetime import datetime,timezone
from sqlalchemy import select,func,create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from redis import Redis
from src.config.settings import CENTER_DATABASE_URL,REDIS_URL
from src.config.database import Session
from src.models.entities import Batch,Inspection,SyncRun,ReconcileReport
from src.models.center import CenterBase,CenterBatch,CenterInspection,SyncState
from src.utils.serialize import record
# 分块提交 + 断点同事务落库：中断后续跑不重复；重叠回扫捕捉并发期间晚提交的行
CHUNK=200;OVERLAP=500;MAX_CHUNKS=1000;MAX_PASSES=10
LOCK='mill:center-ops'
ORPHAN='（未关联样本）'
queue=Redis.from_url(REDIS_URL,decode_responses=True)
_engine=None;_CenterSession=None
def center_engine():
    global _engine,_CenterSession
    if _engine is None:
        url=CENTER_DATABASE_URL
        args={'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'connect_args':{'connect_timeout':5}}
        _engine=create_engine(url,pool_pre_ping=True,**args)
        _CenterSession=sessionmaker(_engine,expire_on_commit=False)
    return _engine
def reset_center():
    global _engine,_CenterSession
    if _engine is not None:_engine.dispose()
    _engine=None;_CenterSession=None
def center_session():
    engine=center_engine()
    CenterBase.metadata.create_all(engine)
    return _CenterSession()
def now():return datetime.now(timezone.utc)
def _acquire(token,ttl=300):return queue.set(LOCK,token,nx=True,ex=ttl)
def _release(token):
    if queue.get(LOCK)==token:queue.delete(LOCK)
def _guard_idle(db):
    active=db.scalar(select(func.count()).select_from(SyncRun).where(SyncRun.status.in_(['queued','running'])))
    if active:raise HTTPException(409,'同步任务进行中，请等待完成后再对账或修复')
def enqueue_run(db,user):
    active=db.scalar(select(func.count()).select_from(SyncRun).where(SyncRun.status.in_(['queued','running'])))
    if active:raise HTTPException(409,'已有同步任务在进行中，请等待完成')
    run=SyncRun(created_by=user.email);db.add(run);db.commit()
    try:queue.rpush('mill:syncjobs',run.id)
    except Exception:
        run.status='failed';run.error='队列不可用，请恢复后重新发起同步';db.commit();raise HTTPException(503,run.error)
    return run
def _fail(run_id,msg):
    with Session() as db:
        run=db.get(SyncRun,run_id)
        if run:run.status='failed';run.error=msg;run.finished_at=now();db.commit()
def run_sync(run_id):
    with Session() as db:
        run=db.get(SyncRun,run_id)
        if not run or run.status not in ('queued','running'):return
        run.status='running';run.started_at=now();db.commit()
    try:center_session().close()
    except Exception:
        _fail(run_id,'中心库不可用：台账录入不受影响，中心恢复后重新发起同步即可补齐。');return
    token=uuid.uuid4().hex
    if not _acquire(token):
        time.sleep(2)
        with Session() as db:
            run=db.get(SyncRun,run_id)
            if run and run.status=='running':run.status='queued';db.commit()
        queue.rpush('mill:syncjobs',run_id)
        return
    try:_run_body(run_id)
    except Exception as e:_fail(run_id,f'同步中断（{e}）：断点已保存，重新发起即可续跑，不会重复入库。')
    finally:_release(token)
def _map_batch(r):return CenterBatch(source_id=r.id,code=r.code,line=r.line,supplier=r.supplier,tonnes=r.tonnes,received_date=r.received_date,status='synced')
def _map_inspection(r):return CenterInspection(source_id=r.id,sample_code=r.sample_code,batch_source_id=r.batch_id,flour_yield=r.flour_yield,moisture=r.moisture,inspector=r.inspector)
def _sync_entity(db,cdb,state,run,src,dst,ck_attr,mapfn,stats,prefix):
    inserted=0;chunks=0
    while chunks<MAX_CHUNKS:
        upper=db.scalar(select(func.max(src.id))) or 0
        ck=getattr(state,ck_attr)
        if ck>=upper:break
        rows=db.scalars(select(src).where(src.id>ck,src.id<=upper).order_by(src.id).limit(CHUNK)).all()
        if not rows:
            setattr(state,ck_attr,upper);cdb.commit();break
        existing=set(cdb.scalars(select(dst.source_id).where(dst.source_id.in_([r.id for r in rows]))))
        for r in rows:
            if r.id in existing:continue
            cdb.add(mapfn(r));stats[prefix+'_copied']+=1;inserted+=1
        setattr(state,ck_attr,rows[-1].id)
        stats[prefix+'_scanned']+=len(rows)
        cdb.commit()
        for k,v in stats.items():setattr(run,k,v)
        run.checkpoint_batch=state.batch_checkpoint;run.checkpoint_inspection=state.inspection_checkpoint
        db.commit()
        chunks+=1
    ck=getattr(state,ck_attr);lo=max(0,ck-OVERLAP)
    rows=db.scalars(select(src).where(src.id>lo,src.id<=ck)).all()
    if rows:
        existing=set(cdb.scalars(select(dst.source_id).where(dst.source_id.in_([r.id for r in rows]))))
        for r in rows:
            if r.id in existing:continue
            cdb.add(mapfn(r));stats[prefix+'_copied']+=1;inserted+=1
        cdb.commit()
    return inserted
def _run_body(run_id):
    stats={'batches_copied':0,'inspections_copied':0,'batches_scanned':0,'inspections_scanned':0}
    with Session() as db, center_session() as cdb:
        state=cdb.get(SyncState,1)
        if not state:
            state=SyncState(id=1);cdb.add(state);cdb.commit();cdb.refresh(state)
        run=db.get(SyncRun,run_id)
        run.phase='full' if state.batch_checkpoint==0 and state.inspection_checkpoint==0 else 'incremental'
        db.commit()
        for _ in range(MAX_PASSES):
            nb=_sync_entity(db,cdb,state,run,Batch,CenterBatch,'batch_checkpoint',_map_batch,stats,'batches')
            ni=_sync_entity(db,cdb,state,run,Inspection,CenterInspection,'inspection_checkpoint',_map_inspection,stats,'inspections')
            if nb==0 and ni==0:break
        run=db.get(SyncRun,run_id)
        run.status='completed';run.finished_at=now()
        run.checkpoint_batch=state.batch_checkpoint;run.checkpoint_inspection=state.inspection_checkpoint
        for k,v in stats.items():setattr(run,k,v)
        db.commit()
def _feq(a,b):return abs((a or 0)-(b or 0))<1e-9
def _compare(db,cdb):
    sb={b.code:b for b in db.scalars(select(Batch))}
    si={i.sample_code:i for i in db.scalars(select(Inspection))}
    cb={b.code:b for b in cdb.scalars(select(CenterBatch))}
    ci={i.sample_code:i for i in cdb.scalars(select(CenterInspection))}
    cb_by_sid={b.source_id:b.code for b in cb.values()}
    details=[]
    def sample_diffs(b,i,x):
        diffs=[]
        if not _feq(i.flour_yield,x.flour_yield):diffs.append({'field':'flour_yield','source':i.flour_yield,'center':x.flour_yield})
        if not _feq(i.moisture,x.moisture):diffs.append({'field':'moisture','source':i.moisture,'center':x.moisture})
        if i.inspector!=x.inspector:diffs.append({'field':'inspector','source':i.inspector,'center':x.inspector})
        if x.batch_source_id!=b.id:diffs.append({'field':'batch','source':b.code,'center':cb_by_sid.get(x.batch_source_id,'（未关联）')})
        return diffs
    for code in sorted(sb):
        b=sb[code];c=cb.get(code)
        entry={'code':code,'line':b.line,'status':'reconciled','batch_diffs':[],'missing_samples':[],'extra_samples':[],'sample_diffs':[]}
        if not c:
            entry['status']='missing'
            for s in sorted(s for s,i in si.items() if i.batch_id==b.id):
                x=ci.get(s)
                if not x:entry['missing_samples'].append(s)
                else:
                    diffs=sample_diffs(b,si[s],x)
                    if diffs:entry['sample_diffs'].append({'sample_code':s,'diffs':diffs})
        else:
            for f in ('line','supplier','received_date'):
                if getattr(b,f)!=getattr(c,f):entry['batch_diffs'].append({'field':f,'source':getattr(b,f),'center':getattr(c,f)})
            if not _feq(b.tonnes,c.tonnes):entry['batch_diffs'].append({'field':'tonnes','source':b.tonnes,'center':c.tonnes})
            for s in sorted(s for s,i in si.items() if i.batch_id==b.id):
                i=si[s];x=ci.get(s)
                if not x:entry['missing_samples'].append(s);continue
                diffs=sample_diffs(b,i,x)
                if diffs:entry['sample_diffs'].append({'sample_code':s,'diffs':diffs})
            entry['extra_samples']=sorted(s for s,x in ci.items() if x.batch_source_id==c.source_id and s not in si)
            if entry['batch_diffs'] or entry['missing_samples'] or entry['extra_samples'] or entry['sample_diffs']:entry['status']='diverged'
        details.append(entry)
    for code in sorted(cb):
        if code in sb:continue
        c=cb[code]
        details.append({'code':code,'line':c.line,'status':'extra','batch_diffs':[],'missing_samples':[],'extra_samples':sorted(s for s,x in ci.items() if x.batch_source_id==c.source_id and s not in si),'sample_diffs':[]})
    known={c.source_id for c in cb.values()}
    orphans=sorted(s for s,x in ci.items() if x.batch_source_id not in known and s not in si)
    if orphans:details.append({'code':ORPHAN,'line':'—','status':'extra','batch_diffs':[],'missing_samples':[],'extra_samples':orphans,'sample_diffs':[]})
    summary={'batches_source':len(sb),'batches_center':len(cb),
        'reconciled':sum(1 for e in details if e['status']=='reconciled'),
        'diverged':sum(1 for e in details if e['status']=='diverged'),
        'missing_batches':sum(1 for e in details if e['status']=='missing'),
        'extra_batches':sum(1 for e in details if e['status']=='extra'),
        'missing_samples':sum(len(e['missing_samples']) for e in details),
        'extra_samples':sum(len(e['extra_samples']) for e in details),
        'batch_diffs':sum(len(e['batch_diffs']) for e in details),
        'sample_diffs':sum(len(e['sample_diffs']) for e in details)}
    return details,summary
def _clean(summary):return not any(summary[k] for k in ('diverged','missing_batches','extra_batches','missing_samples','extra_samples','batch_diffs','sample_diffs'))
def _apply_statuses(cdb,details):
    by_code={e['code']:e['status'] for e in details}
    for c in cdb.scalars(select(CenterBatch)):
        c.status='reconciled' if by_code.get(c.code)=='reconciled' else 'diverged'
    cdb.commit()
def reconcile(db,user,kind='reconcile'):
    _guard_idle(db)
    token=uuid.uuid4().hex
    if not _acquire(token):raise HTTPException(409,'另一项中心库操作正在进行，请稍后重试')
    try:
        try:cdb=center_session()
        except Exception:raise HTTPException(503,'中心库暂不可用，无法对账；中心恢复后重试即可。')
        with cdb:
            details,summary=_compare(db,cdb)
            _apply_statuses(cdb,details)
            report=ReconcileReport(kind=kind,status='clean' if _clean(summary) else 'diffs',summary=summary,details=details,created_by=user.email)
            db.add(report);db.commit();db.refresh(report)
            return report
    finally:_release(token)
def repair(db,data,user):
    _guard_idle(db)
    token=uuid.uuid4().hex
    if not _acquire(token):raise HTTPException(409,'另一项中心库操作正在进行，请稍后重试')
    try:
        try:cdb=center_session()
        except Exception:raise HTTPException(503,'中心库暂不可用，无法修复；中心恢复后重试即可。')
        with cdb:
            details,_=_compare(db,cdb)
            by_code={e['code']:e for e in details}
            targets=[e['code'] for e in details if e['status']!='reconciled'] if data.all else list(dict.fromkeys(data.codes))
            unknown=[c for c in targets if c not in by_code]
            if unknown:raise HTTPException(404,'批次不在对账范围：'+'、'.join(unknown))
            already=[c for c in targets if by_code[c]['status']=='reconciled']
            targets=[c for c in targets if by_code[c]['status']!='reconciled']
            if not targets:raise HTTPException(422,'所选批次均已对账，无需修复')
            sb={b.code:b for b in db.scalars(select(Batch))}
            si={i.sample_code:i for i in db.scalars(select(Inspection))}
            cb={b.code:b for b in cdb.scalars(select(CenterBatch))}
            ci={i.sample_code:i for i in cdb.scalars(select(CenterInspection))}
            # 先置“修复中”并提交：诊断侧立即排除，修复完成前不会读到半批
            for code in targets:
                c=cb.get(code)
                if c:c.status='repairing'
            cdb.commit()
            actions=[]
            for code in targets:
                e=by_code[code]
                if e['status']=='missing':
                    b=sb[code]
                    cdb.add(CenterBatch(source_id=b.id,code=b.code,line=b.line,supplier=b.supplier,tonnes=b.tonnes,received_date=b.received_date,status='synced'))
                    for s in e['missing_samples']:
                        i=si[s];cdb.add(CenterInspection(source_id=i.id,sample_code=i.sample_code,batch_source_id=i.batch_id,flour_yield=i.flour_yield,moisture=i.moisture,inspector=i.inspector))
                    for sd in e['sample_diffs']:
                        i=si[sd['sample_code']];x=ci[sd['sample_code']]
                        x.flour_yield,x.moisture,x.inspector,x.batch_source_id=i.flour_yield,i.moisture,i.inspector,i.batch_id
                    actions.append(f'{code}：补录中心缺失批次，补样本 {len(e["missing_samples"])} 条、归位 {len(e["sample_diffs"])} 条')
                elif e['status']=='extra':
                    n=0
                    for s in e['extra_samples']:
                        x=ci.get(s)
                        if x:cdb.delete(x);n+=1
                    c=cb.get(code)
                    if c:cdb.delete(c);actions.append(f'{code}：移除中心多出批次及 {n} 条样本')
                    else:actions.append(f'{code}：清理 {n} 条未关联样本')
                else:
                    b=sb[code];c=cb[code]
                    c.line,c.supplier,c.tonnes,c.received_date=b.line,b.supplier,b.tonnes,b.received_date
                    for s in e['missing_samples']:
                        i=si[s];cdb.add(CenterInspection(source_id=i.id,sample_code=i.sample_code,batch_source_id=i.batch_id,flour_yield=i.flour_yield,moisture=i.moisture,inspector=i.inspector))
                    for s in e['extra_samples']:
                        x=ci.get(s)
                        if x:cdb.delete(x)
                    for sd in e['sample_diffs']:
                        i=si[sd['sample_code']];x=ci[sd['sample_code']]
                        x.flour_yield,x.moisture,x.inspector,x.batch_source_id=i.flour_yield,i.moisture,i.inspector,i.batch_id
                    actions.append(f'{code}：对齐批次字段 {len(e["batch_diffs"])} 项、补样本 {len(e["missing_samples"])} 条、删多出 {len(e["extra_samples"])} 条、改差异 {len(e["sample_diffs"])} 条')
                cdb.commit()
            details2,summary2=_compare(db,cdb)
            _apply_statuses(cdb,details2)
            summary2['repaired']=actions
            if already:summary2['skipped']=already
            report=ReconcileReport(kind='repair',status='clean' if _clean(summary2) else 'diffs',summary=summary2,details=details2,created_by=user.email)
            db.add(report);db.commit();db.refresh(report)
            return report
    finally:_release(token)
def status(db):
    out={'center_ok':False,'center_error':'','active_run':None,'recent_runs':[],'checkpoints':None,'counts':{},'batch_status':{},'last_report':None}
    runs=list(db.scalars(select(SyncRun).order_by(SyncRun.id.desc()).limit(5)))
    out['recent_runs']=[record(r) for r in runs]
    active=next((r for r in runs if r.status in ('queued','running')),None)
    out['active_run']=record(active) if active else None
    out['counts']['source_batches']=db.scalar(select(func.count()).select_from(Batch))
    out['counts']['source_inspections']=db.scalar(select(func.count()).select_from(Inspection))
    try:
        with center_session() as cdb:
            state=cdb.get(SyncState,1)
            ck_b=state.batch_checkpoint if state else 0
            ck_i=state.inspection_checkpoint if state else 0
            out['center_ok']=True
            out['checkpoints']={'batch':ck_b,'inspection':ck_i}
            out['counts']['center_batches']=cdb.scalar(select(func.count()).select_from(CenterBatch))
            out['counts']['center_inspections']=cdb.scalar(select(func.count()).select_from(CenterInspection))
            out['counts']['pending_batches']=db.scalar(select(func.count()).select_from(Batch).where(Batch.id>ck_b))
            out['counts']['pending_inspections']=db.scalar(select(func.count()).select_from(Inspection).where(Inspection.id>ck_i))
            for s,n in cdb.execute(select(CenterBatch.status,func.count()).group_by(CenterBatch.status)):out['batch_status'][s]=n
    except Exception:
        out['center_error']='中心库连接失败；台账录入与诊断不受影响'
    rep=db.scalars(select(ReconcileReport).order_by(ReconcileReport.id.desc()).limit(1)).first()
    if rep:out['last_report']=record(rep)
    return out
def center_diagnosis_rows(db,line):
    try:cdb=center_session()
    except Exception:raise HTTPException(503,'中心库暂不可用，请改用台账数据或稍后重试')
    with cdb:
        state=cdb.get(SyncState,1)
        q=select(CenterInspection,CenterBatch.code,CenterBatch.line).join(CenterBatch,CenterBatch.source_id==CenterInspection.batch_source_id).where(CenterBatch.status=='reconciled')
        if line!='全部':q=q.where(CenterBatch.line==line)
        rows=[{'sample_code':i.sample_code,'batch_code':code,'line':ln,'flour_yield':i.flour_yield,'moisture':i.moisture,'inspector':i.inspector} for i,code,ln in cdb.execute(q.order_by(CenterInspection.source_id))]
        meta={'basis':'中心库 · 仅纳入已对账的完整批次，修复中批次已排除',
            'inspection_checkpoint':state.inspection_checkpoint if state else 0,
            'batch_checkpoint':state.batch_checkpoint if state else 0,
            'reconciled_batches':len({r['batch_code'] for r in rows}),
            'as_of':now().isoformat()}
    meta['report_id']=db.scalar(select(func.max(ReconcileReport.id)))
    return rows,meta
