import csv,io
from fastapi import HTTPException
from fastapi.responses import Response
def export_review(obj):
    if obj.status not in ('completed','approved'):raise HTTPException(409,'计算完成后才可导出')
    source=getattr(obj,'source',None) or 'ledger'
    output=io.StringIO();w=csv.writer(output)
    w.writerow(['复核单',obj.id,'标题',obj.title,'状态',obj.status,'范围',obj.line,'数据来源','中心库（已对账批次）' if source=='center' else '台账（实时录入）'])
    if source=='center':
        m=obj.source_meta or {}
        w.writerow(['同步依据',f"仅含已对账完整批次，修复中批次已排除；追平至检验 #{m.get('inspection_checkpoint','—')}；对账报告 #{m.get('report_id') or '—'}；{m.get('as_of','')}"])
    for k in ['n','mean','std','q1','median','q3','iqr','lower','upper','checksum']:w.writerow([k,obj.result[k]])
    w.writerow(['签核人',obj.approved_by,'签核意见',obj.note])
    w.writerow(['样本编号','批次','产线','出粉率','水分','异常'])
    out={r['sample_code'] for r in obj.result['outliers']}
    for row in obj.snapshot:w.writerow([row['sample_code'],row['batch_code'],row['line'],row['flour_yield'],row['moisture'],'是' if row['sample_code'] in out else '否'])
    return Response('﻿'+output.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="mill-yield-review-{obj.id}.csv"'})
