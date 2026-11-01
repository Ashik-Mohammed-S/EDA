"""Full variable profiles and additive cohort cubes. No sampling or applicant expansion."""
from pathlib import Path
import json,gzip,hashlib,math
import numpy as np
import pandas as pd

MISSING='(Missing / not applicable)'
UNKNOWN={'unknown','xna','xap','not specified'}

def clean_json(value):
    if isinstance(value,dict):return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean_json(v) for v in value]
    if isinstance(value,(np.integer,np.floating)):value=value.item()
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def wilson(positive,n,z=1.959963984540054):
    if not n:return (None,None)
    p=positive/n;denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return center-half,center+half

def raw_profile(df,table):
    rows=[]
    for col in df:
        s=df[col];numeric=pd.api.types.is_numeric_dtype(s)
        r={'table':table,'variable':col,'dtype':str(s.dtype),'rows':len(s),'missing':int(s.isna().sum()),'missing_pct':100*s.isna().mean(),'unique_nonmissing':int(s.nunique()),'role':'identifier' if col in ['SK_ID_CURR','SK_ID_PREV','customerid'] else 'target' if col in ['TARGET','response'] else 'variable',
           'unknown_marker_count':sum(int(count) for value,count in s.value_counts(dropna=True).items() if str(value).lower() in UNKNOWN) if not numeric else 0}
        if numeric:
            desc=s.describe(percentiles=[.01,.25,.5,.75,.99]).to_dict()
            r.update({str(k):v for k,v in desc.items()})
            r['sentinel_365243']=int((s==365243).sum()) if col.startswith('DAYS_') else 0
        rows.append(r)
    return pd.DataFrame(rows)

def labels(s):return s.astype('str').fillna(MISSING)
def cut(s,bins,names):return pd.cut(s,bins,labels=names,include_lowest=True,right=False).astype('str').fillna(MISSING)
def duration_to_seconds(series):
    parts=series.str.extract(r'^\s*([0-9.]+)\s*(sec|min)\s*$')
    return pd.to_numeric(parts[0],errors='coerce')*parts[1].map({'sec':1.,'min':60.})

def load_bank(root):
    from scripts.fetch_data import ensure_data
    data=ensure_data(root/'dataset');raw=pd.read_csv(data/'bank_marketing_updated_v1.csv',skiprows=2)
    profiles=raw_profile(raw,'bank_source');valid=raw.response.isin(['yes','no'])
    df=raw.loc[valid].copy();df['target']=df.response.map({'yes':1,'no':0}).astype('int8')
    df['job']=df.jobedu.str.split(',',n=1).str[0];df['education']=df.jobedu.str.split(',',n=1).str[1]
    df['duration_seconds']=duration_to_seconds(df.duration)
    if df.duration_seconds.isna().any():raise ValueError('Unparsed bank duration')
    df['source_month']=df.month.str.split(',').str[0]
    df['prior_contact']=np.where(df.pdays.eq(-1),'Not previously contacted','Previously contacted')
    df['pdays_since_contact']=df.pdays.mask(df.pdays.eq(-1))
    df['age_band']=cut(df.age,[0,30,40,50,60,200],['Under 30','30–39','40–49','50–59','60+'])
    filters=['age_band','housing','contact','source_month']
    notes={'duration_seconds':'Mixed sec/min source values normalized to seconds. Post-contact diagnostic, not an available pre-contact predictor.',
        'pdays':'-1 denotes not previously contacted, not an ordinary elapsed-day value.',
        'pdays_since_contact':'-1 removed only in this derived elapsed-days field; structural missing means no previous contact.',
        'salary':'Supplied source salary; no independent validation of salary or its relationship to occupation.',
        'age':'Missing ages are retained as a visible group. Outliers are flagged, not removed.',
        'source_month':'Month labels as supplied in the modified source; not a longitudinal causal study.'}
    pairs=[('job','education'),('housing','loan'),('age','balance'),('campaign','poutcome'),('duration_seconds','contact')]
    return df,profiles,filters,notes,pairs,{'source_rows':len(raw),'analyzed_rows':len(df),'excluded_missing_target':int((~valid).sum()),'source_columns':len(raw.columns),'unit':'one bank source record','target':'response = yes','positive_label':'Subscribed','negative_label':'Did not subscribe',
        'source_files':['bank_marketing_updated_v1.csv'],'quality_notes':['30 records without a yes/no target are excluded; age/month missingness is retained.','No outliers or unknown categories are dropped or imputed.','Duration is post-contact; all associations are descriptive.'],'previous_rows':0},['age','salary','balance','duration_seconds','campaign','pdays_since_contact'],['job','education','marital','housing','loan','poutcome']

def load_credit(root):
    from scripts.fetch_data import ensure_data
    data=ensure_data(root/'dataset');raw=pd.read_csv(data/'application_data.csv')
    sample=pd.read_csv(data/'previous_application.csv',nrows=1000)
    categories={c:'category' for c in sample if not pd.api.types.is_numeric_dtype(sample[c])}
    previous=pd.read_csv(data/'previous_application.csv',dtype=categories)
    profiles=pd.concat([raw_profile(raw,'current_application_source'),raw_profile(previous,'previous_application_source')],ignore_index=True)
    if not raw.SK_ID_CURR.is_unique:raise ValueError('Current application ID must be unique')
    if not raw.TARGET.isin([0,1]).all():raise ValueError('Unexpected credit target')
    df=raw.copy();df['target']=df.TARGET.astype('int8')
    previous_distribution={};previous_presence={}
    target_lookup=raw[['SK_ID_CURR','TARGET']]
    for col in previous:
        if col in ['SK_ID_CURR','SK_ID_PREV']:continue
        codes,bins,kind,values=encode(previous[col])
        counts=np.bincount(codes,minlength=len(bins)).astype(int)
        previous_distribution[col]={'kind':kind,'bins':[{**b,'n':int(count)} for b,count in zip(bins,counts)]}
        if not pd.api.types.is_numeric_dtype(previous[col]):
            grouped_values=previous[col].astype('str').fillna(MISSING)
            top=grouped_values.value_counts().index[:29]
            grouped_values=grouped_values.where(grouped_values.isin(top),'(Other categories)')
            unique=pd.DataFrame({'SK_ID_CURR':previous.SK_ID_CURR,'group':grouped_values}).drop_duplicates()
            linked=unique.merge(target_lookup,on='SK_ID_CURR',how='inner',validate='many_to_one')
            presence=linked.groupby('group',dropna=False).TARGET.agg(n='size',positive='sum').reset_index()
            previous_presence[col]=[]
            for row in presence.itertuples():
                previous_presence[col].append({'label':str(row.group),'n':int(row.n),'positive':int(row.positive),'negative':int(row.n-row.positive),'rate':row.positive/row.n,'ci':wilson(row.positive,row.n)})
    df['age_years']=-df.DAYS_BIRTH/365.25
    df['employment_years']=-df.DAYS_EMPLOYED.mask(df.DAYS_EMPLOYED.eq(365243)|df.DAYS_EMPLOYED.gt(0))/365.25
    # Keep original raw distributions in the source profile; sentinel-aware analytical fields below.
    df['DAYS_EMPLOYED']=df.DAYS_EMPLOYED.mask(df.DAYS_EMPLOYED.eq(365243))
    df['credit_income_ratio']=df.AMT_CREDIT/df.AMT_INCOME_TOTAL.where(df.AMT_INCOME_TOTAL>0)
    df['annuity_income_ratio']=df.AMT_ANNUITY/df.AMT_INCOME_TOTAL.where(df.AMT_INCOME_TOTAL>0)
    grouped=previous.groupby('SK_ID_CURR')
    history=grouped.agg(previous_applications=('SK_ID_PREV','size'),previous_credit_mean=('AMT_CREDIT','mean'),previous_credit_sum=('AMT_CREDIT','sum'),previous_annuity_mean=('AMT_ANNUITY','mean'),previous_decision_days_mean=('DAYS_DECISION','mean'))
    status=pd.crosstab(previous.SK_ID_CURR,previous.NAME_CONTRACT_STATUS)
    for name in ['Approved','Refused','Canceled','Unused offer']:
        history['previous_'+name.lower().replace(' ','_')+'_count']=status.get(name,pd.Series(0,index=status.index))
    df=df.merge(history,on='SK_ID_CURR',how='left',validate='one_to_one')
    count_cols=['previous_applications']+[c for c in history if c.endswith('_count')]
    for col in count_cols:df[col]=df[col].fillna(0)
    df['previous_approval_share']=df.previous_approved_count/df.previous_applications.where(df.previous_applications>0)
    df['previous_refusal_share']=df.previous_refused_count/df.previous_applications.where(df.previous_applications>0)
    df['previous_history']=np.select([df.previous_applications.eq(0),df.previous_approved_count.eq(df.previous_applications),df.previous_refused_count.eq(df.previous_applications)],['No previous history','Approved only','Refused only'],default='Mixed / other')
    df['age_band']=cut(df.age_years,[0,30,40,50,60,200],['Under 30','30–39','40–49','50–59','60+'])
    filters=['age_band','CODE_GENDER','NAME_CONTRACT_TYPE','NAME_INCOME_TYPE']
    notes={'DAYS_EMPLOYED':'365243 sentinel excluded only in analytical employment fields, counted in source audit; applicants retained.',
        'employment_years':'Negative source employment days converted to years; sentinel and positive day values become missing, not fictitious long tenure.',
        'age_years':'-DAYS_BIRTH / 365.25, a derived age approximation.',
        'credit_income_ratio':'Source credit / positive source income; zero denominators become missing.',
        'annuity_income_ratio':'Source annuity / positive source income; no unverified monthly/annual period assumption.',
        'CODE_GENDER':'Source XNA remains visible; no reassignment to the majority gender.',
        'previous_approval_share':'Approved count / all previous applications; no-history applicants have missing share rather than zero.',
        'previous_credit_sum':'Sum over linked previous applications; not a measure of current outstanding debt.'}
    for col in df:
        if col.startswith('previous_'):notes.setdefault(col,'Previous applications aggregated per SK_ID_CURR before a validated one-to-one join. Current target rates weight each applicant once.')
    pairs=[('NAME_EDUCATION_TYPE','NAME_FAMILY_STATUS'),('AMT_INCOME_TOTAL','AMT_CREDIT'),('age_years','employment_years'),('NAME_CONTRACT_TYPE','previous_history'),('OCCUPATION_TYPE','NAME_INCOME_TYPE')]
    meta={'source_rows':len(raw),'analyzed_rows':len(df),'excluded_missing_target':0,'source_columns':len(raw.columns),'unit':'one current application / applicant record','target':'TARGET = 1','positive_label':'Payment difficulty','negative_label':'Other target',
        'source_files':['application_data.csv','previous_application.csv'],'previous_rows':len(previous),'previous_unique_ids':int(previous.SK_ID_CURR.nunique()),'current_with_history':int(df.previous_applications.gt(0).sum()),
        'quality_notes':['All 307,511 current records are retained; previous applications are not expanded into target-rate rows.','All 122 current and 37 previous source columns are profiled, including fields with high missingness.','Unknown categories are retained; employment sentinel 365243 is explicitly reported.','Observed associations are not causal effects or lending/eligibility recommendations.']}
    meta['_previous_analysis']={'distributions':previous_distribution,'category_presence':previous_presence,'scope':'Full previous source records for univariate distributions. Target rates use unique current applicants with at least one previous application in that category. Category groups can overlap; do not sum them or apply current-cohort filters.'}
    return df,profiles,filters,notes,pairs,meta,['age_years','employment_years','AMT_INCOME_TOTAL','AMT_CREDIT','AMT_ANNUITY','credit_income_ratio'],['CODE_GENDER','NAME_INCOME_TYPE','NAME_EDUCATION_TYPE','OCCUPATION_TYPE','NAME_CONTRACT_TYPE','previous_history']

def encode(s):
    numeric=pd.api.types.is_numeric_dtype(s)
    if numeric:
        s=pd.to_numeric(s,errors='coerce').replace([np.inf,-np.inf],np.nan)
        unique=np.sort(s.dropna().unique())
    if numeric and len(unique)>12:
        edges=np.unique(np.quantile(s.dropna(),np.linspace(0,1,13)))
        if len(edges)<2:edges=np.array([float(s.min()),float(s.max())+1])
        codes=np.searchsorted(edges[1:-1],s.fillna(edges[0]).to_numpy(),side='right')
        bins=[{'label':f'{edges[i]:.4g} – {edges[i+1]:.4g}','lower':float(edges[i]),'upper':float(edges[i+1]),'upper_inclusive':i==len(edges)-2} for i in range(len(edges)-1)]
        kind='numeric'
    else:
        values=s.astype('str').fillna(MISSING)
        if numeric:levels=[str(x) for x in unique]
        else:levels=values.loc[values.ne(MISSING)].value_counts().index[:29].tolist()
        if numeric:
            # Numeric flags/discrete counts retain numeric order.
            mapping={float(x):i for i,x in enumerate(unique)}
            codes=s.map(mapping).fillna(len(levels)).to_numpy(dtype=int)
        else:
            if values.loc[values.ne(MISSING)].nunique()>len(levels):levels+=['(Other categories)']
            mapping={x:i for i,x in enumerate(levels)}
            codes=values.map(mapping).fillna(mapping.get('(Other categories)',len(levels))).to_numpy(dtype=int)
        bins=[{'label':str(x)} for x in levels];kind='discrete numeric' if numeric else 'categorical'
    missing=s.isna().to_numpy();codes=np.asarray(codes,dtype=np.int32)
    codes[missing]=len(bins);bins.append({'label':MISSING,'missing':True})
    return codes,bins,kind,s

def association(counts,positives):
    counts=np.asarray(counts,float);positives=np.asarray(positives,float)
    obs=np.column_stack([counts-positives,positives]);obs=obs[counts>0]
    if len(obs)<2 or obs.sum()==0:return None
    expected=np.outer(obs.sum(axis=1),obs.sum(axis=0))/obs.sum()
    valid=expected>0
    return float(np.sqrt(np.sum(((obs-expected)**2)[valid]/expected[valid])/obs.sum()))

def build(root,project):
    root=Path(root);out=root/'results';out.mkdir(exist_ok=True);dest=root/'dashboard';dest.mkdir(exist_ok=True)
    loaded=load_bank(root) if project=='bank' else load_credit(root)
    df,profiles,filter_names,notes,pair_names,meta,numeric_featured,categorical_featured=loaded
    previous_analysis=meta.pop('_previous_analysis',None)
    y=df.target.to_numpy(dtype=np.int32);n=len(df);positive=int(y.sum())
    excluded={'target','TARGET','response','SK_ID_CURR','SK_ID_PREV','customerid','duration','jobedu'}
    fields=[c for c in df if c not in excluded]
    filter_levels=[sorted(labels(df[c]).unique().tolist()) for c in filter_names]
    filter_codes=np.column_stack([labels(df[c]).map({x:i for i,x in enumerate(levels)}).to_numpy(dtype=int) for c,levels in zip(filter_names,filter_levels)])
    strata,sid=np.unique(filter_codes,axis=0,return_inverse=True);ns=len(strata)
    cohort_n=np.bincount(sid,minlength=ns).astype(int);cohort_p=np.bincount(sid,weights=y,minlength=ns).astype(int)
    variables={};encoded={};segments=[];numeric_summary=[];associations=[]
    for col in fields:
        codes,bins,kind,s=encode(df[col]);encoded[col]=(codes,len(bins));nb=len(bins)
        counts=np.bincount(sid*nb+codes,minlength=ns*nb).reshape(ns,nb).astype(int)
        positives=np.bincount(sid*nb+codes,weights=y,minlength=ns*nb).reshape(ns,nb).astype(int)
        full_n=counts.sum(axis=0);full_p=positives.sum(axis=0)
        profile={'nonmissing':int(s.notna().sum()),'missing':int(s.isna().sum()),'unique':int(s.nunique()),'unknown_markers':int(s.astype('str').str.lower().isin(UNKNOWN).sum()) if not pd.api.types.is_numeric_dtype(s) else 0}
        stats=None
        if pd.api.types.is_numeric_dtype(s):
            values=s.to_numpy(dtype=float,na_value=np.nan);finite=np.isfinite(values)
            q=s.quantile([.25,.5,.75]).to_numpy();iqr=q[2]-q[0]
            outliers=finite&((values<q[0]-1.5*iqr)|(values>q[2]+1.5*iqr)) if len(q) and np.isfinite(iqr) and iqr>0 else np.zeros(n,dtype=bool)
            stats=np.column_stack([np.bincount(sid,weights=finite,minlength=ns),np.bincount(sid,weights=np.nan_to_num(values),minlength=ns),np.bincount(sid,weights=np.nan_to_num(values)**2,minlength=ns),np.bincount(sid,weights=outliers,minlength=ns)]).tolist()
            profile.update(mean=s.mean(),std=s.std(),minimum=s.min(),q1=q[0],median=q[1],q3=q[2],maximum=s.max(),iqr_outliers=int(outliers.sum()))
            for value in [0,1]:
                part=s.loc[df.target.eq(value)]
                numeric_summary.append({'variable':col,'target':value,**part.describe(percentiles=[.01,.25,.5,.75,.99]).to_dict()})
            corr=s.corr(df.target) if s.nunique()>1 else None
        else:corr=None
        v={'id':col,'label':col.replace('_',' ').title() if project=='bank' else col,'kind':kind,'note':notes.get(col,''),'bins':bins,'counts':counts.tolist(),'positives':positives.tolist(),'stats':stats,'profile':profile}
        variables[col]=v
        associations.append({'variable':col,'binned_cramers_v':association(full_n,full_p),'point_biserial_r':corr,'missing_fraction':profile['missing']/n})
        for b,obs,pos in zip(bins,full_n,full_p):
            low,high=wilson(int(pos),int(obs))
            segments.append({'variable':col,'group':b['label'],'observations':int(obs),'positive':int(pos),'negative':int(obs-pos),'target_rate':pos/obs if obs else None,'ci95_low':low,'ci95_high':high,'lift_vs_overall':pos/obs/(positive/n) if obs else None})
    pairs=[]
    for left,right in pair_names:
        x,nx=encoded[left];z,nz=encoded[right];index=(sid*nx+x)*nz+z
        cnt=np.bincount(index,minlength=ns*nx*nz).reshape(ns,nx,nz).astype(int)
        pos=np.bincount(index,weights=y,minlength=ns*nx*nz).reshape(ns,nx,nz).astype(int)
        where=np.nonzero(cnt)
        sparse=[[int(a),int(b),int(c),int(cnt[a,b,c]),int(pos[a,b,c])] for a,b,c in zip(*where)]
        pairs.append({'left':left,'right':right,'rows':sparse})
    # Keep all-variable univariate/target analysis, but limit expensive pairwise
    # correlations to explicitly documented continuous, domain-relevant fields.
    correlation_candidates=numeric_featured+(['AMT_GOODS_PRICE','AMT_ANNUITY','EXT_SOURCE_1','EXT_SOURCE_2','EXT_SOURCE_3','REGION_POPULATION_RELATIVE','previous_applications','previous_credit_mean','previous_approval_share','CNT_CHILDREN','CNT_FAM_MEMBERS'] if project=='credit' else ['previous','pdays','day'])
    numeric=list(dict.fromkeys(c for c in correlation_candidates if c in df and pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique()>1))
    corr_frame=df[numeric].replace([np.inf,-np.inf],np.nan)
    correlations={method:corr_frame.corr(method=method).round(6).to_numpy().tolist() for method in ['pearson','spearman']}
    for method in correlations:pd.DataFrame(correlations[method],index=numeric,columns=numeric).to_csv(out/f'correlation_{method}.csv')
    associations=pd.DataFrame(associations).sort_values('binned_cramers_v',ascending=False)
    profiles.to_csv(out/'all_source_variable_profiles.csv',index=False)
    pd.DataFrame(segments).to_csv(out/'target_summary.csv',index=False)
    pd.DataFrame(numeric_summary).to_csv(out/'numeric_by_target.csv',index=False)
    associations.to_csv(out/'variable_associations.csv',index=False)
    if previous_analysis:
        pd.DataFrame([{'variable':col,**b} for col,v in previous_analysis['distributions'].items() for b in v['bins']]).to_csv(out/'previous_univariate.csv',index=False)
        pd.DataFrame([{'variable':col,'group':g['label'],'current_applicants':g['n'],'positive':g['positive'],'target_rate':g['rate'],'ci95_low':g['ci'][0],'ci95_high':g['ci'][1]} for col,groups in previous_analysis['category_presence'].items() for g in groups]).to_csv(out/'previous_category_presence.csv',index=False)
    package={'schema_version':1,'project':project,'title':'Bank campaign' if project=='bank' else 'Credit applications','meta':meta,'rows':n,'positive':positive,'source_profile':profiles.to_dict('records'),
        'filters':[{'id':c,'levels':level} for c,level in zip(filter_names,filter_levels)],'strata':strata.tolist(),'cohort_n':cohort_n.tolist(),'cohort_positive':cohort_p.tolist(),
        'variables':variables,'pairs':pairs,'correlations':{'columns':numeric,**correlations},'associations':associations.to_dict('records'),'featured_numeric':numeric_featured,'featured_categorical':categorical_featured,
        'previous_analysis':previous_analysis,'definitions':{'rates':'Positive count / all target-labeled records in the group. Wilson 95% intervals are descriptive binomial intervals, not causal uncertainty or multiple-comparison-adjusted significance.',
            'numeric_bins':'Fixed full-cohort quantile boundaries (up to 12 bins); missing values have a separate bin. Boundaries do not change with filters.',
            'other_categories':'Categorical variables with >29 levels retain the 29 most frequent source levels and an explicit Other group. No records are discarded.',
            'correlations':'Pairwise complete-case Pearson/Spearman coefficients for the full analyzed cohort. They do not recompute under dashboard filters.',
            'privacy':'Aggregate strata, counts and statistics only; no customer/applicant IDs or individual records in the dashboard artifact.'}}
    package=clean_json(package)
    # Invariants guard every variable and pair, including missing bins and empty strata.
    for col,v in variables.items():
        if not np.array_equal(np.array(v['counts']).sum(axis=1),cohort_n):raise AssertionError('Variable count conservation: '+col)
        if not np.array_equal(np.array(v['positives']).sum(axis=1),cohort_p):raise AssertionError('Positive count conservation: '+col)
    for p in pairs:
        if sum(r[3] for r in p['rows'])!=n or sum(r[4] for r in p['rows'])!=positive:raise AssertionError('Pair conservation')
    raw=json.dumps(package,separators=(',',':'),allow_nan=False).encode()
    path=dest/(project+'.json.gz');path.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    manifest={'schema_version':1,'project':project,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'uncompressed_bytes':len(raw),'compressed_bytes':path.stat().st_size,'rows':n,'positive':positive,'variables':len(variables),'source_profile_columns':len(profiles),'strata':ns,'unit':meta['unit']}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    fixture_selections=[[-1]*len(filters) for filters in [filter_names]]
    fixture_selections+=[[int(x) for x in strata[0]], [int(x) for x in strata[-1]], [999]+[-1]*(len(filter_names)-1)]
    for j,level in enumerate(filter_levels):
        chosen=[-1]*len(filter_names);chosen[j]=0;fixture_selections.append(chosen)
    fixtures=[]
    for selected in fixture_selections:
        mask=np.ones(n,dtype=bool)
        for j,value in enumerate(selected):
            if value>=0:mask&=filter_codes[:,j]==value
        fixtures.append({'selected':selected,'n':int(mask.sum()),'positive':int(y[mask].sum()),'numeric':{c:{'count':int(df.loc[mask,c].notna().sum()),'mean':df.loc[mask,c].mean()} for c in numeric_featured[:2]}})
    (dest/'check-fixtures.json').write_text(json.dumps(clean_json(fixtures),indent=2,allow_nan=False),encoding='utf-8')
    report={'objective':'Comprehensive descriptive variable analysis, quality audit and target-conditioned associations.','analysis_type':'full-variable EDA with additive dashboard cohorts','target':meta['target'],'rows':n,'previous_application_rows':meta['previous_rows'],'metrics':{'target_rate':positive/n,'positive_records':positive,'analyzed_variables':len(variables),'profiled_source_columns':len(profiles)},'data_quality':meta,'dashboard':manifest,'interpretation':'No sample reduction, target imputation or indiscriminate outlier removal. Group denominators and missing categories retained; descriptive associations are not causal or predictive validation.'}
    report['metrics']['response_rate' if project=='bank' else 'default_rate']=positive/n
    report['metrics']['positive_responses' if project=='bank' else 'positive_applications']=positive
    (out/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    plot_report(package,out)
    from scripts.eda_findings import write_findings
    write_findings(root,project)
    return report

def plot_report(p,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    numeric=p['featured_numeric'];categorical=p['featured_categorical']
    for fields,name,rate in [(numeric,'numeric_distributions',False),(categorical,'categorical_target_rates',True)]:
        fig,axes=plt.subplots(2,3,figsize=(16,9))
        for ax,col in zip(axes.flat,fields):
            v=p['variables'][col];n=np.array(v['counts']).sum(axis=0);yes=np.array(v['positives']).sum(axis=0)
            order=np.argsort(-n)[:10] if rate else np.arange(len(n))
            x=np.arange(len(order));text=[v['bins'][i]['label'][:22] for i in order]
            if rate:
                values=np.divide(yes[order],n[order],out=np.zeros(len(order)),where=n[order]>0)
                intervals=[wilson(int(yes[i]),int(n[i])) for i in order]
                lower=np.array([lo if lo is not None else 0 for lo,hi in intervals]);upper=np.array([hi if hi is not None else 0 for lo,hi in intervals])
                ax.bar(x,values,color='#25857d',yerr=np.maximum(0,np.vstack([values-lower,upper-values])),capsize=2);ax.set_ylabel('Target rate / 95% Wilson')
            else:
                ax.bar(x,n[order]-yes[order],color='#cbd9de',label='Target 0');ax.bar(x,yes[order],bottom=n[order]-yes[order],color='#25857d',label='Target 1');ax.set_ylabel('Records')
            ax.set_xticks(x,text,rotation=65,ha='right',fontsize=7);ax.set_title(col,fontsize=10)
        fig.suptitle(p['title']+' — '+name.replace('_',' '),fontsize=16);fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=120);plt.close(fig)
    raw=pd.DataFrame(p['source_profile']);top=raw.sort_values('missing_pct',ascending=False).head(20)
    fig,ax=plt.subplots(figsize=(11,7));ax.barh((top.table+' · '+top.variable).str[-60:],top.missing_pct,color='#d59365');ax.invert_yaxis();ax.set_xlabel('Raw source missing %');fig.tight_layout();fig.savefig(out/'missingness.png',dpi=120);plt.close(fig)
    fields=[c for c in numeric+categorical if c in p['correlations']['columns']][:12]
    if len(fields)>1:
        indices=[p['correlations']['columns'].index(c) for c in fields];matrix=np.array(p['correlations']['spearman'],dtype=float)[np.ix_(indices,indices)]
        fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(matrix,cmap='RdBu_r',vmin=-1,vmax=1);ax.set_xticks(range(len(fields)),fields,rotation=70,ha='right',fontsize=8);ax.set_yticks(range(len(fields)),fields,fontsize=8);fig.colorbar(im,ax=ax,label='Spearman (pairwise complete)');fig.tight_layout();fig.savefig(out/'correlations.png',dpi=120);plt.close(fig)
    # Legacy runner entry image now points at a multi-variable view, not one bar plot.
    (out/'overview.png').write_bytes((out/'numeric_distributions.png').read_bytes())

if __name__=='__main__':
    import argparse,sys
    parser=argparse.ArgumentParser();parser.add_argument('--project',choices=['bank','credit'],required=True);parser.add_argument('--root',required=True);args=parser.parse_args()
    root=Path(args.root).resolve();sys.path.insert(0,str(root));print(json.dumps(build(root,args.project),indent=2))
