import {esc,canEdit} from '../utils/format.js';import {sbadge,cbadge} from '../components/common/status.js';
const t=s=>s?String(s).slice(0,16).replace('T',' '):'—';
function diffDetail(e){
 const parts=[];
 if(e.batch_diffs.length)parts.push(`<p><strong>批次字段差异</strong></p><ul>${e.batch_diffs.map(d=>`<li>${esc(d.field)}：台账 ${esc(d.source)} → 中心 ${esc(d.center)}</li>`).join('')}</ul>`);
 if(e.missing_samples.length)parts.push(`<p><strong>中心缺失样本 ${e.missing_samples.length} 条</strong></p><p class="codes">${e.missing_samples.map(esc).join('、')}</p>`);
 if(e.extra_samples.length)parts.push(`<p><strong>中心多出样本 ${e.extra_samples.length} 条</strong></p><p class="codes">${e.extra_samples.map(esc).join('、')}</p>`);
 if(e.sample_diffs.length)parts.push(`<p><strong>样本内容差异 ${e.sample_diffs.length} 条</strong></p><ul>${e.sample_diffs.map(sd=>`<li>${esc(sd.sample_code)}：${sd.diffs.map(d=>`${esc(d.field)} 台账 ${esc(d.source)} → 中心 ${esc(d.center)}`).join('；')}</li>`).join('')}</ul>`);
 return parts.length?`<div class="diff-detail">${parts.join('')}</div>`:'<div class="diff-detail">该批与台账一致。</div>';
}
export function syncPage(s){
 const st=s.sync||{};const ok=st.center_ok;const run=st.active_run;const report=st.last_report;const edit=canEdit(s.user);
 const counts=st.counts||{};const bs=st.batch_status||{};const summary=report?.summary||{};
 const entries=report?[...report.details].sort((a,b)=>((a.status==='reconciled')-(b.status==='reconciled'))||String(a.code).localeCompare(String(b.code))):[];
 return `<header><p class="eyebrow">05 / CENTRAL LIBRARY</p><h1>中心库同步</h1><p>厂部质量中心独立保存检验副本：先全量接入批次与检验，再增量追平；逐批对账缺失、多出与内容差异，修复只改中心库，不动源台账。</p></header>
 <div class="workspace"><section class="paper"><h2>同步控制</h2>
 <div class="sync-state ${ok?'ok':'down'}">${ok?'中心库连接正常':'中心库不可用 — 台账录入与诊断不受影响，恢复后可补齐'}</div>
 <dl class="kv"><dt>追平断点</dt><dd>批次 #${st.checkpoints?.batch??'—'} · 检验 #${st.checkpoints?.inspection??'—'}</dd>
 <dt>台账 / 中心</dt><dd>${counts.source_batches??'—'} 批 / ${counts.center_batches??'—'} 批 · ${counts.source_inspections??'—'} / ${counts.center_inspections??'—'} 样本</dd>
 <dt>待同步</dt><dd>${ok?`${counts.pending_batches??0} 批 · ${counts.pending_inspections??0} 样本`:'—'}</dd>
 <dt>中心批次状态</dt><dd>已对账 ${bs.reconciled||0} · 待对账 ${bs.synced||0} · 有差异 ${bs.diverged||0} · 修复中 ${bs.repairing||0}</dd></dl>
 ${run?`<div class="run-active">${sbadge(run.status)}<p>阶段：${run.phase==='full'?'全量接入':'增量追平'} · 已复制 ${run.batches_copied} 批 / ${run.inspections_copied} 样本</p></div>`:''}
 <button class="primary" id="sync-run" ${edit&&!run?'':'disabled'}>启动同步 →</button>
 <button class="outline" id="sync-reconcile" ${edit&&ok&&!run?'':'disabled'}>开始对账</button>
 <button class="outline" id="sync-repair-all" ${edit&&ok&&!run&&report&&report.status==='diffs'?'':'disabled'}>修复全部差异</button>
 <p class="hint">同步为追加式：只补缺、不改写中心已有内容；多出与内容差异由对账列出、修复对齐。中断后从断点续跑，不会重复入库；中心不可用时任务失败留痕，恢复后重新发起即可补齐。</p>
 <h3>最近同步任务</h3><div class="review-list">${(st.recent_runs||[]).map(r=>`<div class="review-choice as-row"><strong>#${r.id} · ${r.phase==='full'?'全量接入':r.phase==='incremental'?'增量追平':'待启动'} ${sbadge(r.status)}</strong><small>${t(r.created_at)} UTC · 复制 ${r.batches_copied} 批 / ${r.inspections_copied} 样本${r.error?` · ${esc(r.error)}`:''}</small></div>`).join('')||'<div class="empty">尚未发起同步。</div>'}</div>
 </section>
 <section><div class="section-head"><h2>对账结果</h2><span>${report?`#${report.id} · ${report.kind==='repair'?'修复报告':'对账报告'} · ${t(report.created_at)} UTC · ${esc(report.created_by)}`:''}</span></div>
 ${report?`<div class="metrics"><div><small>已对账批次</small><b>${summary.reconciled??0}</b></div><div><small>中心缺失</small><b class="rust">${summary.missing_samples??0}<em>样</em></b></div><div><small>中心多出</small><b class="rust">${summary.extra_samples??0}<em>样</em></b></div><div><small>内容差异</small><b class="rust">${(summary.batch_diffs??0)+(summary.sample_diffs??0)}<em>项</em></b></div></div>
 ${summary.repaired?.length?`<div class="report-note"><strong>修复动作（仅作用于中心库，源台账未改动）</strong><p>${summary.repaired.map(esc).join('<br>')}</p></div>`:''}
 <div class="table-wrap"><table><thead><tr><th>批次</th><th>状态</th><th>缺失</th><th>多出</th><th>内容差异</th><th>操作</th></tr></thead><tbody>${entries.map(e=>`<tr><td><strong>${esc(e.code)}</strong><small>${esc(e.line)}</small></td><td>${cbadge(e.status)}</td><td>${e.missing_samples.length||'—'}</td><td>${e.extra_samples.length||'—'}</td><td>${e.batch_diffs.length+e.sample_diffs.length||'—'}</td><td class="ops">${e.status!=='reconciled'&&edit?`<button class="text" data-repair="${esc(e.code)}">修复</button>`:''}<button class="text" data-diff="${esc(e.code)}">${s.syncExpanded===e.code?'收起':'详情'}</button></td></tr>${s.syncExpanded===e.code?`<tr><td colspan="6">${diffDetail(e)}</td></tr>`:''}`).join('')}</tbody></table></div>`
 :'<div class="empty">尚未对账。先启动同步接入数据，再开始对账，逐批核对缺失、多出与内容差异。</div>'}</section></div>`;
}
