import {cohort,variable,relationship,cramers,csv} from './engine.mjs';
const $=s=>document.querySelector(s),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>x==null||!Number.isFinite(x)?'—':new Intl.NumberFormat('en-US',{maximumFractionDigits:Math.abs(x)<10?3:1}).format(x);
const integer=x=>new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(x||0);
const pct=x=>x==null?'—':(100*x).toFixed(2)+'%';
const label=id=>data.variables[id]?.label||id.replaceAll('_',' ');
let data,selected=[],current,cache={},currentPage='overview',currentVariable,variableMode='count',pairMode='rate',focused=null,support=50,request=0;
const datasets=new Map();let toastTimer;
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),2200);}
function download(name,rows){const blob=new Blob(['\uFEFF'+csv(rows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function getVariable(id){return cache[id]||(cache[id]=variable(data,id,current));}
function navigate(page){if(!data)return;currentPage=page;document.querySelectorAll('.page').forEach(e=>e.hidden=e.id!==page);document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===page));if(page==='variables')renderVariable();if(page==='relationships')renderRelationships();if(page==='quality')renderQuality();window.scrollTo({top:0,behavior:'smooth'});}

function barChart(groups,mode='count',{minN=0,baseline=null,active=null,unlabeled=false}={}){
  const width=800,left=205,right=75,row=28,height=groups.length*row+48,plot=width-left-right;
  const max=mode==='rate'?Math.max(.01,...groups.filter(g=>g.n).map(g=>g.ci?.[1]||0),baseline||0):Math.max(1,...groups.map(g=>g.n));
  const x=v=>left+v/max*plot;
  let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Variable ${mode==='rate'?'target rate with Wilson intervals':'distribution'}"><g font-family="Arial,sans-serif">`;
  for(let i=0;i<=4;i++){const value=max*i/4;svg+=`<line x1="${x(value)}" y1="14" x2="${x(value)}" y2="${height-32}" stroke="#edf1ef"/><text x="${x(value)}" y="${height-10}" text-anchor="middle" fill="#72847a" font-size="10">${mode==='rate'?pct(value):integer(value)}</text>`;}
  groups.forEach((g,i)=>{const y=i*row+18,small=g.n<minN,base=active===i?'#dce9e3':'transparent';svg+=`<g data-bin="${i}" tabindex="0" role="button" aria-label="${esc(g.label)}; records ${g.n}${unlabeled?'':'; target rate '+pct(g.rate)}"><title>${esc(g.label)}\nRecords: ${g.n}${unlabeled?'':'\nPositive: '+g.positive+'\nRate: '+pct(g.rate)+'\n95% Wilson: '+pct(g.ci?.[0])+' – '+pct(g.ci?.[1])}${small?'\nSmall group: interpret cautiously':''}</title><rect x="0" y="${y-11}" width="${width}" height="26" fill="${base}"/><text x="${left-12}" y="${y+6}" text-anchor="end" fill="${small?'#93a18d':'#536b60'}" font-size="11">${esc(g.label.length>29?g.label.slice(0,27)+'…':g.label)}</text>`;
    if(mode==='count'){svg+=`<rect x="${left}" y="${y-5}" width="${g.n/max*plot}" height="15" rx="2" fill="#d6e1dd"/><rect x="${left}" y="${y-5}" width="${g.positive/max*plot}" height="15" rx="2" fill="${small?'#a8bdb0':'#287f78'}"/>`;}
    else if(g.n){svg+=`<rect x="${left}" y="${y-5}" width="${g.rate/max*plot}" height="15" rx="2" fill="${small?'#c7d1c1':'#73a493'}"/><line x1="${x(g.ci[0])}" x2="${x(g.ci[1])}" y1="${y+2}" y2="${y+2}" stroke="#31594a" stroke-width="1.4"/><line x1="${x(g.ci[0])}" x2="${x(g.ci[0])}" y1="${y-2}" y2="${y+6}" stroke="#31594a"/><line x1="${x(g.ci[1])}" x2="${x(g.ci[1])}" y1="${y-2}" y2="${y+6}" stroke="#31594a"/>`;}
    svg+=`<text x="${width-5}" y="${y+6}" text-anchor="end" fill="#6d8274" font-size="10">${mode==='rate'?pct(g.rate):integer(g.n)}</text></g>`;});
  if(mode==='rate'&&baseline!=null)svg+=`<line x1="${x(baseline)}" x2="${x(baseline)}" y1="10" y2="${height-32}" stroke="#bc885b" stroke-dasharray="4 4"><title>Selected-cohort overall rate: ${pct(baseline)}</title></line>`;
  return svg+'</g></svg>';
}

function heatMap(left,right,cells,mode='rate',correlation=false){
  const width=Math.max(760,220+right.length*45),cell=Math.max(26,(width-220)/right.length),top=160,height=top+left.length*29+25;
  let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${correlation?'Full cohort correlation matrix':'Cohort relationship matrix'}"><g font-family="Arial,sans-serif">`;
  right.forEach((name,j)=>{svg+=`<text transform="translate(${205+j*cell+cell/2},145) rotate(-55)" font-size="9" fill="#6a7c66">${esc(name.length>31?name.slice(0,29)+'…':name)}</text>`;});
  const maxCount=Math.max(1,...cells.flat().map(c=>c.n||0));
  left.forEach((name,i)=>{svg+=`<text x="190" y="${top+i*29+19}" text-anchor="end" font-size="9" fill="#6a7c66">${esc(name.length>29?name.slice(0,27)+'…':name)}</text>`;
    right.forEach((_,j)=>{const c=cells[i][j],value=correlation?c.value:mode==='rate'?(c.n?c.positive/c.n:null):c.n/maxCount;
      let fill='#f2f3ef';if(value!=null){if(correlation){const a=Math.abs(value);fill=value>=0?`rgb(${Math.round(236-a*190)},${Math.round(245-a*120)},${Math.round(238-a*130)})`:`rgb(${Math.round(247-a*55)},${Math.round(238-a*100)},${Math.round(227-a*135)})`;}else{const a=mode==='rate'?Math.min(1,value/.4):value;fill=`rgb(${Math.round(235-a*192)},${Math.round(245-a*115)},${Math.round(236-a*115)})`;}}
      const display=correlation?(value==null?'—':value.toFixed(2)):mode==='count'?integer(c.n):c.n?pct(c.positive/c.n):'—';
      const title=correlation?`${left[i]} × ${right[j]}\n${value==null?'No defined coefficient':value.toFixed(6)}\nFull analyzed cohort, pairwise complete observations`:`${left[i]} × ${right[j]}\nRecords ${c.n}; positive ${c.positive}\nRate ${c.n?pct(c.positive/c.n):'undefined'}${c.n<support?'\nSmall group: interpret cautiously':''}`;
      svg+=`<rect x="${200+j*cell}" y="${top+i*29}" width="${cell-2}" height="27" rx="2" fill="${fill}"><title>${esc(title)}</title></rect><text x="${200+j*cell+cell/2}" y="${top+i*29+18}" text-anchor="middle" fill="${value!=null&&Math.abs(value)>.65?'#edf7ed':'#596f55'}" font-size="8" pointer-events="none">${display}</text>`;
    });});return svg+'</g></svg>';
}

function renderFilters(){
  $('#filters').innerHTML=data.filters.map((filter,j)=>`<label>${esc(filter.id.replaceAll('_',' '))}<select data-filter="${j}" aria-label="Filter ${esc(filter.id)}"><option value="-1">All groups</option>${filter.levels.map((value,i)=>`<option value="${i}" ${selected[j]===i?'selected':''}>${esc(value)}</option>`).join('')}</select></label>`).join('');
}
function renderKPIs(){
  $('#kpi-n').textContent=integer(current.n);$('#kpi-coverage').textContent=pct(current.n/data.rows)+' of analyzed dataset';
  $('#kpi-positive-label').textContent=data.meta.positive_label.toUpperCase();$('#kpi-positive').textContent=integer(current.positive);$('#kpi-unit').textContent=data.meta.unit;
  $('#kpi-rate').textContent=pct(current.rate);$('#kpi-ci').textContent=current.n?'95% Wilson '+pct(current.ci[0])+' – '+pct(current.ci[1]):'No records match these filters';
  const missing=Object.keys(data.variables).reduce((sum,id)=>sum+getVariable(id).missing,0);
  $('#kpi-missing').textContent=current.n?pct(missing/(current.n*Object.keys(data.variables).length)):'—';
  const active=selected.filter(x=>x>=0).length;$('#filter-scope').textContent=active?active+' active filter'+(active===1?'':'s'):'All analyzed records';
  $('#small-warning').hidden=current.n>=100;$('#small-warning').textContent=current.n?'This cohort has fewer than 100 records. Rates and associations can be unstable; inspect counts and intervals.':'No records match these filters. Reset one or more filters to continue.';
}
function renderOverview(){
  const id=$('#overview-variable').value||data.featured_numeric[0],v=getVariable(id);$('#overview-chart-title').textContent=label(id)+' profile';$('#overview-chart').innerHTML=barChart(v.groups,'count');
  const rate=current.rate||0,circumference=2*Math.PI*48;$('#outcome-ring').innerHTML=`<svg viewBox="0 0 170 150" role="img" aria-label="Observed target rate ${pct(current.rate)}"><circle cx="85" cy="69" r="48" fill="none" stroke="#dde8dd" stroke-width="13"/><circle cx="85" cy="69" r="48" fill="none" stroke="#2c8575" stroke-width="13" stroke-dasharray="${rate*circumference} ${circumference}" transform="rotate(-90 85 69)"/><text x="85" y="69" text-anchor="middle" font-size="23" font-family="Arial" fill="#42725c">${pct(current.rate)}</text><text x="85" y="89" text-anchor="middle" font-size="8" font-family="Arial" fill="#92a18a">OBSERVED TARGET</text></svg>`;
  const delta=current.rate==null?null:100*(current.rate-data.positive/data.rows);
  $('#cohort-story').textContent=current.n?`${integer(current.positive)} of ${integer(current.n)} records have ${data.meta.target}. The selected rate is ${delta>=0?'+':''}${delta.toFixed(2)} percentage points from the full-cohort rate of ${pct(data.positive/data.rows)}. This is an unadjusted descriptive comparison.`:'The selected cohort is empty. No target rate is defined.';
  const redundant=new Set(data.project==='bank'?['month','pdays']:['DAYS_BIRTH','DAYS_EMPLOYED']);
  const associations=Object.keys(data.variables).filter(id=>!redundant.has(id)).map(id=>({id,value:cramers(getVariable(id).groups)})).filter(x=>x.value!=null).sort((a,b)=>b.value-a.value).slice(0,7);
  $('#associations').innerHTML=associations.length?associations.map(a=>`<button class="assoc-row" data-variable="${esc(a.id)}"><span>${esc(a.id.length>25?a.id.slice(0,23)+'…':a.id)}</span><span class="track"><i style="width:${Math.min(100,a.value*100)}%"></i></span><span>${a.value.toFixed(3)}</span></button>`).join(''):'<div class="empty">Not enough variation to estimate associations.</div>';
  $('#coverage').innerHTML=`<div class="coverage-grid"><div><strong>${data.source_profile.length}</strong><small>source columns<br>profiled</small></div><div><strong>${Object.keys(data.variables).length}</strong><small>analytical variables<br>explorable</small></div><div><strong>${data.pairs.length}</strong><small>cohort relationship<br>views</small></div></div>`;
  $('#quality-notes').innerHTML=data.meta.quality_notes.map(n=>'<p>'+esc(n)+'</p>').join('');
}
function renderVariableList(){const q=$('#variable-search').value.toLowerCase();$('#variable-list').innerHTML=Object.values(data.variables).filter(v=>(v.id+' '+v.label).toLowerCase().includes(q)).map(v=>`<button class="field-button ${v.id===currentVariable?'active':''}" data-variable="${esc(v.id)}">${esc(v.label)}<small>${esc(v.kind)} · ${pct(v.profile.missing/data.rows)} missing</small></button>`).join('')||'<div class="empty">No matching variable.</div>';}
function renderVariable(){
  const v=getVariable(currentVariable);$('#variable-title').textContent=v.label;$('#variable-kind').textContent=v.kind.toUpperCase();$('#variable-note').textContent=v.note+(v.numeric?` Full-cohort reference (unfiltered): min ${fmt(v.profile.minimum)}, Q1 ${fmt(v.profile.q1)}, median ${fmt(v.profile.median)}, Q3 ${fmt(v.profile.q3)}, max ${fmt(v.profile.maximum)}.`:'');
  const stats=[['RECORDS',integer(current.n)],['MISSING / N.A.',pct(current.n?v.missing/current.n:null)],...(v.numeric?[['MEAN (NONMISSING)',fmt(v.numeric.mean)],['SAMPLE STD. DEV.',fmt(v.numeric.std)]]:[['SOURCE LEVELS',integer(v.profile.unique)],['DISPLAY GROUPS',integer(v.bins.length)]])];
  if(v.numeric)stats.push(['IQR-FLAGGED (RETAINED)',integer(v.numeric.outliers)]);
  $('#variable-stats').innerHTML=stats.map(([key,value])=>`<div><label>${key}</label><strong>${value}</strong></div>`).join('');
  $('#variable-chart').innerHTML=barChart(v.groups,variableMode,{minN:support,baseline:current.rate,active:focused});
  $('#variable-chart-note').textContent=variableMode==='rate'?'Observed rates with Wilson 95% intervals. Dashed line: selected-cohort overall rate. Small groups are muted, not removed. Click a group for details.':'Population bars show target 1 in teal, target 0 in gray. Numeric bins are fixed full-cohort quantiles, not equal-width density bins. Click a group for details.';
  $('#variable-table').innerHTML='<thead><tr><th>Group / bin</th><th>Records</th><th>Target 1</th><th>Target 0</th><th>Target rate</th><th>95% Wilson interval</th><th>Support</th></tr></thead><tbody>'+v.groups.map((g,i)=>`<tr data-bin="${i}" class="${g.n<support?'low-support ':''}${focused===i?'selected-row':''}"><td>${esc(g.label)}</td><td>${integer(g.n)}</td><td>${integer(g.positive)}</td><td>${integer(g.negative)}</td><td>${pct(g.rate)}</td><td>${g.n?pct(g.ci[0])+' – '+pct(g.ci[1]):'—'}</td><td>${g.n<support?'Small group':'—'}</td></tr>`).join('')+'</tbody>';
  const g=focused!=null?v.groups[focused]:null;$('#focused-group').hidden=!g;
  if(g)$('#focused-group').textContent=`${g.label}: ${integer(g.n)} records, ${integer(g.positive)} positive, rate ${pct(g.rate)}, interval ${pct(g.ci[0])} – ${pct(g.ci[1])}. ${g.n<support?'Small sample; avoid ranking this group as a reliable finding.':''}`;
  renderVariableList();
}
function renderRelationships(){
  const pair=relationship(data,Number($('#pair').value)||0,current),left=pair.leftVariable.bins.map(b=>b.label),right=pair.rightVariable.bins.map(b=>b.label);
  $('#pair-chart').innerHTML=heatMap(left,right,pair.cells,pairMode);
  const corr=data.correlations,method=$('#correlation-method').value,cells=corr[method].map(row=>row.map(value=>({value})));
  $('#correlation-chart').innerHTML=heatMap(corr.columns,corr.columns,cells,'rate',true);
  const pairs=[];corr.columns.forEach((a,i)=>corr.columns.forEach((b,j)=>{if(j>i&&corr[method][i][j]!=null)pairs.push({a,b,value:corr[method][i][j]});}));pairs.sort((a,b)=>Math.abs(b.value)-Math.abs(a.value));
  $('#correlation-pairs').innerHTML='<div class="correlation-pair-list">'+pairs.slice(0,5).map(p=>`<span>${esc(p.a)} × ${esc(p.b)}<br><b>${p.value.toFixed(3)}</b></span>`).join('')+'</div>';
}
function renderQuality(){
  const missing=Object.keys(data.variables).map(id=>({label:id,n:getVariable(id).missing,positive:0})).sort((a,b)=>b.n-a.n).slice(0,18);$('#missing-chart').innerHTML=barChart(missing,'count',{unlabeled:true});
  const q=$('#audit-search').value.toLowerCase(),table=$('#audit-table').value;const rows=data.source_profile.filter(r=>(!table||r.table===table)&&r.variable.toLowerCase().includes(q)).sort((a,b)=>b.missing_pct-a.missing_pct);
  $('#audit-grid').innerHTML='<thead><tr><th>Source / variable</th><th>Role</th><th>Type</th><th>Source rows</th><th>Missing</th><th>Missing %</th><th>Distinct</th><th>Unknown markers</th><th>365243 sentinel</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(r.variable)}<br><small>${esc(r.table)}</small></td><td>${esc(r.role)}</td><td>${esc(r.dtype)}</td><td>${integer(r.rows)}</td><td>${integer(r.missing)}</td><td>${r.missing_pct.toFixed(2)}%</td><td>${integer(r.unique_nonmissing)}</td><td>${integer(r.unknown_marker_count)}</td><td>${integer(r.sentinel_365243)}</td></tr>`).join('')+'</tbody>';
  renderPrevious();
}
function renderPrevious(){const previous=data.previous_analysis;$('#previous-context').hidden=!previous;if(!previous)return;
 const v=previous.distributions[$('#previous-variable').value];if(v)$('#previous-chart').innerHTML=barChart(v.bins.map(b=>({...b,positive:0})),'count',{unlabeled:true});
 const groups=previous.category_presence[$('#history-variable').value];if(groups)$('#history-chart').innerHTML=barChart(groups,'rate',{minN:support,baseline:data.positive/data.rows});
}
function renderMethod(){
  const repo=data.project==='bank'?'EDA':'Credit_EDA_Assignment';$('#repo-link').href='https://github.com/Ashik-Mohammed-S/'+repo;
  $('#method-body').innerHTML=`<h3>Source and analysis population</h3><p>${integer(data.meta.source_rows)} current-source rows; ${integer(data.rows)} analyzed target-labeled records. ${data.meta.previous_rows?integer(data.meta.previous_rows)+' previous applications are separately profiled and aggregated before the current-applicant join.':''} Unit: ${esc(data.meta.unit)}. Target: <code>${esc(data.meta.target)}</code>.</p><p>Identifiers, the target, and compound raw fields with normalized replacements are audited but excluded from explanatory charts. All other source variables and the documented derived fields are retained.</p><dl>${Object.entries(data.definitions).map(([key,value])=>`<dt>${esc(key.replaceAll('_',' '))}</dt><dd>${esc(value)}</dd>`).join('')}</dl><h3>Provenance and reproducibility</h3><p><a href="https://github.com/Ashik-Mohammed-S/${repo}/blob/main/dataset-sources.json" target="_blank" rel="noopener">Pinned sources, checksums and upstream terms</a> · <a href="https://github.com/Ashik-Mohammed-S/${repo}/blob/main/ANALYSIS.md" target="_blank" rel="noopener">Analysis notes</a>. This is a published historical snapshot, not a live data feed.</p>`;
}
function updateCohort(){current=cohort(data,selected);cache={};focused=null;renderKPIs();renderOverview();if(currentPage==='variables')renderVariable();if(currentPage==='relationships')renderRelationships();if(currentPage==='quality')renderQuality();}
async function loadDataset(id){const token=++request;$('#load-state').hidden=false;$('#workspace').hidden=true;$('#load-state').textContent='Loading '+(id==='bank'?'bank campaign':'credit application')+' analysis…';
  try{if(!datasets.has(id)){const response=await fetch(id+'.json.gz');if(!response.ok)throw Error('Dataset download failed');const bytes=new Uint8Array(await response.arrayBuffer());let text;if(bytes[0]===31&&bytes[1]===139){if(!('DecompressionStream'in window))throw Error('Use a current browser with gzip decompression support.');text=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}else{text=new TextDecoder().decode(bytes);}datasets.set(id,JSON.parse(text));}if(token!==request)return;data=datasets.get(id);selected=data.filters.map(()=>-1);currentVariable=data.featured_numeric[0];focused=null;
    $('#page-title').textContent=id==='bank'?'Campaign intelligence.':'Credit, in context.';$('#page-subtitle').textContent=id==='bank'?'Variable-level analysis of the bank telemarketing reference dataset.':'Applicant-level patterns, source quality and previous-loan context.';
    $('#overview-variable').innerHTML=data.featured_numeric.concat(data.featured_categorical).map(v=>`<option value="${esc(v)}">${esc(label(v))}</option>`).join('');
    $('#pair').innerHTML=data.pairs.map((p,i)=>`<option value="${i}">${esc(label(p.left)+' × '+label(p.right))}</option>`).join('');
    $('#audit-table').innerHTML='<option value="">All source tables</option>'+[...new Set(data.source_profile.map(p=>p.table))].map(t=>`<option>${esc(t)}</option>`).join('');
    if(data.previous_analysis){$('#previous-variable').innerHTML=Object.keys(data.previous_analysis.distributions).map(v=>`<option>${esc(v)}</option>`).join('');$('#history-variable').innerHTML=Object.keys(data.previous_analysis.category_presence).map(v=>`<option>${esc(v)}</option>`).join('');}
    $('#variable-search').value='';$('#audit-search').value='';renderFilters();renderMethod();updateCohort();renderVariableList();$('#load-state').hidden=true;$('#workspace').hidden=false;navigate(currentPage);
  }catch(error){$('#load-state').textContent='Could not load this analysis. '+error.message;}}

document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>navigate(b.dataset.page));
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>navigate(b.dataset.go));
$('#dataset').onchange=()=>loadDataset($('#dataset').value);
$('#filters').onchange=e=>{if(e.target.dataset.filter!=null){selected[Number(e.target.dataset.filter)]=Number(e.target.value);updateCohort();}};
$('#reset').onclick=()=>{selected=data.filters.map(()=>-1);renderFilters();updateCohort();};
$('#overview-variable').onchange=renderOverview;$('#variable-search').oninput=renderVariableList;
$('#variable-mode').onclick=e=>{const b=e.target.closest('[data-mode]');if(!b)return;variableMode=b.dataset.mode;$('#variable-mode').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));renderVariable();};
$('#support').oninput=e=>{support=Number(e.target.value);$('#support-value').textContent=support;renderVariable();};
$('#pair').onchange=renderRelationships;$('#correlation-method').onchange=renderRelationships;
$('#pair-mode').onclick=e=>{const b=e.target.closest('[data-mode]');if(!b)return;pairMode=b.dataset.mode;$('#pair-mode').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));renderRelationships();};
$('#audit-search').oninput=renderQuality;$('#audit-table').onchange=renderQuality;
$('#previous-variable').onchange=renderPrevious;$('#history-variable').onchange=renderPrevious;
document.addEventListener('click',e=>{const v=e.target.closest('[data-variable]');if(v){currentVariable=v.dataset.variable;focused=null;navigate('variables');}const bin=e.target.closest('[data-bin]');if(bin&&currentPage==='variables'){focused=Number(bin.dataset.bin);renderVariable();}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-bin]')){e.preventDefault();focused=Number(e.target.dataset.bin);renderVariable();}});
$('#export-cohort').onclick=()=>download(data.project+'-cohort.csv',[{records:current.n,positive:current.positive,target_rate:current.rate,ci95_low:current.ci[0],ci95_high:current.ci[1],filters:data.filters.map((f,i)=>f.id+'='+(selected[i]<0?'All':f.levels[selected[i]])).join('; '),unit:data.meta.unit}]);
$('#export-variable').onclick=()=>{const v=getVariable(currentVariable);download(data.project+'-'+v.id+'-cohort.csv',v.groups.map(g=>({variable:v.id,group:g.label,lower:g.lower,upper:g.upper,observations:g.n,positive:g.positive,negative:g.negative,target_rate:g.rate,ci95_low:g.ci[0],ci95_high:g.ci[1],small_group:g.n<support})));};
$('#export-profile').onclick=()=>download(data.project+'-full-source-profile.csv',data.source_profile);
async function start(){try{const response=await fetch('config.json');if(!response.ok)throw Error('Dashboard configuration unavailable');const config=await response.json();$('#dataset').innerHTML=config.datasets.map(d=>`<option value="${esc(d.id)}">${esc(d.title)}</option>`).join('');$('#dataset').value=config.default;await loadDataset(config.default);}catch(error){$('#load-state').textContent=error.message;}}
start();
