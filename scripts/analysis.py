from scripts.analysis_common import *
from scripts.fetch_data import ensure_data
PROJECT='EDA'

def run(mode='full'):
    import matplotlib.pyplot as plt
    data=ensure_data(ROOT/'dataset')
    if PROJECT=='EDA':
        df=pd.read_csv(data/'bank_marketing_updated_v1.csv',skiprows=2)
        df=df.loc[df['response'].isin(['yes','no'])].copy();df['responded']=df['response'].map({'yes':1,'no':0})
        df['job']=df['jobedu'].str.split(',').str[0];df['education']=df['jobedu'].str.split(',').str[1]
        summaries=[]
        for c in ['job','education','marital','loan','housing','poutcome']:
            if c not in df:continue
            s=df.groupby(c,dropna=False)['responded'].agg(observations='size',positive='sum',response_rate='mean').reset_index();s.insert(0,'feature',c);s=s.rename(columns={c:'group'});summaries.append(s)
        summary=pd.concat(summaries,ignore_index=True)
        report={'objective':'Describe subscription response rates and campaign segments.','target':'response=yes','analysis_type':'target-conditioned descriptive EDA',
            'rows':len(df),'metrics':{'response_rate':df.responded.mean(),'positive_responses':int(df.responded.sum())},
            'interpretation':'Rates include group denominators. Duration is a post-contact diagnostic and is not used as a pre-contact decision predictor. Associations are not causal effects.'}
    else:
        cols=['SK_ID_CURR','TARGET','CODE_GENDER','NAME_INCOME_TYPE','NAME_EDUCATION_TYPE','NAME_CONTRACT_TYPE','AMT_INCOME_TOTAL','AMT_CREDIT','DAYS_BIRTH']
        df=pd.read_csv(data/'application_data.csv',usecols=cols)
        assert df.SK_ID_CURR.is_unique
        previous=pd.read_csv(data/'previous_application.csv',usecols=['SK_ID_CURR','NAME_CONTRACT_STATUS','AMT_CREDIT'])
        history=previous.groupby('SK_ID_CURR').agg(previous_applications=('SK_ID_CURR','size'),previous_credit=('AMT_CREDIT','mean'))
        df=df.merge(history,on='SK_ID_CURR',how='left',validate='one_to_one');df['previous_applications']=df.previous_applications.fillna(0)
        df['age_band']=pd.cut(-df.DAYS_BIRTH/365.25,bins=[0,25,35,45,55,65,120])
        summaries=[]
        for c in ['CODE_GENDER','NAME_INCOME_TYPE','NAME_EDUCATION_TYPE','NAME_CONTRACT_TYPE','age_band']:
            s=df.groupby(c,dropna=False,observed=True)['TARGET'].agg(observations='size',positive='sum',default_rate='mean').reset_index();s.insert(0,'feature',c);s=s.rename(columns={c:'group'});summaries.append(s)
        summary=pd.concat(summaries,ignore_index=True)
        report={'objective':'Describe repayment difficulty at the current-application level.','target':'TARGET=1','analysis_type':'target-conditioned credit-risk EDA',
            'rows':len(df),'previous_application_rows':len(previous),'metrics':{'default_rate':df.TARGET.mean(),'positive_applications':int(df.TARGET.sum())},
            'interpretation':'Previous loans are aggregated before a one-to-one join. Applicants with many previous loans do not receive extra weight in target rates. This is descriptive risk analysis, not a deployed credit-decision model.'}
    rate='response_rate' if PROJECT=='EDA' else 'default_rate'
    subset=summary.loc[summary.feature==summary.feature.iloc[0]].copy()
    fig,ax=plt.subplots(figsize=(10,4));ax.bar(subset.group.astype(str),subset[rate]);ax.set_ylabel(rate);ax.tick_params(axis='x',rotation=60);ax.set_title('Target rate by group; see CSV for denominators');fig.tight_layout();fig.savefig(output()/'overview.png',dpi=120);plt.close(fig)
    return finish(report,summary)
