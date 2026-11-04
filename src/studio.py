"""Persisted local experiments, leakage-aware splits and trusted-artifact prediction."""
import hashlib
import csv
import io
import json
import math
import time
import uuid
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report,confusion_matrix
from sklearn.model_selection import train_test_split,GroupShuffleSplit
from src.train import prepare_xy,make_pipeline

MAX_ROWS=20000

def read_csv(content):
    if not isinstance(content,str) or not content.strip():raise ValueError('Choose a nonempty CSV file')
    if len(content.encode('utf-8'))>3*1024*1024:raise ValueError('CSV must be at most 3 MiB')
    header=next(csv.reader(io.StringIO(content)),[])
    if len(set(header))!=len(header):raise ValueError('CSV headers must be unique')
    frame=pd.read_csv(io.StringIO(content),nrows=MAX_ROWS+1,low_memory=False)
    if len(frame)>MAX_ROWS or frame.shape[1]>100:raise ValueError('Use at most 20,000 rows and 100 columns')
    if frame.columns.duplicated().any():raise ValueError('CSV headers must be unique')
    return frame

def preview(frame,label):
    X,y=prepare_xy(frame,label)
    if y.nunique()>30:raise ValueError('At most 30 classes are supported in the studio')
    return {'rows':len(frame),'valid_labeled_rows':len(y),'numeric_features':len(X.columns),'columns':list(frame.columns),
      'features':list(X.columns),'classes':{str(k):int(v) for k,v in y.value_counts().items()},
      'missing_values':int(X.isna().sum().sum()),'memory_bytes':int(frame.memory_usage(deep=True).sum())}

def split_rows(frame,label,strategy,column,seed,test_size):
    X,y=prepare_xy(frame,label)
    if y.nunique()>30:raise ValueError('At most 30 classes are supported in the studio')
    if set(y)&{'accuracy','macro avg','weighted avg','micro avg','samples avg'}:
        raise ValueError('Class names must not use reserved metric summary names')
    if not 0.1<=test_size<=0.5:raise ValueError('Test fraction must be between 0.1 and 0.5')
    if strategy=='stratified':
        n_test=math.ceil(len(y)*test_size)
        if min(n_test,len(y)-n_test)<y.nunique():raise ValueError('Too few rows per split to include every class')
        train,test=train_test_split(np.arange(len(X)),stratify=y,test_size=test_size,random_state=seed)
        detail={'method':'random-stratified','warning':'Related hosts or captures may cross this split.'}
    elif strategy=='group':
        if column not in frame.columns or column==label:raise ValueError('Choose a separate grouping column')
        groups=frame.loc[X.index,column]
        if groups.isna().any() or groups.astype(str).str.strip().eq('').any():raise ValueError('Every row needs a group identifier')
        groups=groups.astype(str)
        if groups.nunique()<2:raise ValueError('At least two distinct groups are required')
        train,test=next(GroupShuffleSplit(n_splits=1,test_size=test_size,random_state=seed).split(X,y,groups))
        overlap=set(groups.iloc[train])&set(groups.iloc[test]);assert not overlap
        detail={'method':'group-holdout','train_groups':int(groups.iloc[train].nunique()),'test_groups':int(groups.iloc[test].nunique()),'group_overlap':0}
        X=X.drop(columns=[column],errors='ignore')
    elif strategy=='temporal':
        if column not in frame.columns or column==label:raise ValueError('Choose a separate timestamp column')
        times=pd.to_datetime(frame.loc[X.index,column],utc=True,errors='coerce')
        if times.isna().any():raise ValueError('Every row must contain a valid timestamp')
        unique=times.drop_duplicates().sort_values()
        if len(unique)<2:raise ValueError('At least two distinct timestamps are required')
        count=max(1,min(len(unique)-1,math.ceil(len(unique)*test_size)))
        cutoff=unique.iloc[-count]
        train=np.flatnonzero((times<cutoff).to_numpy());test=np.flatnonzero((times>=cutoff).to_numpy())
        detail={'method':'temporal-holdout','cutoff':cutoff.isoformat(),'train_end':times.iloc[train].max().isoformat(),'test_start':times.iloc[test].min().isoformat()}
        X=X.drop(columns=[column],errors='ignore')
    else:raise ValueError('Unknown split strategy')
    if len(train)<5 or len(test)<2:raise ValueError('Split must contain at least 5 training rows and 2 test rows')
    if y.iloc[train].nunique()<2 or set(y.iloc[test])-set(y.iloc[train]):raise ValueError('Training must include at least two classes and cover all held-out classes; adjust the split')
    columns=X.iloc[train].columns[X.iloc[train].notna().any(axis=0)].tolist()
    if not columns:raise ValueError('No usable numeric training features remain')
    return X[columns],y,train,test,detail

def train(frame,model,strategy,column,seed,test_size,artifact_dir,dataset_hash,source,label='Label'):
    if model not in ['random-forest','logistic-regression']:raise ValueError('Unknown classifier')
    X,y,train_idx,test_idx,split=split_rows(frame,label,strategy,column,seed,test_size)
    pipeline=make_pipeline(X.columns,model,seed)
    if model=='random-forest':pipeline.set_params(classifier__n_jobs=1)
    started=time.perf_counter();pipeline.fit(X.iloc[train_idx],y.iloc[train_idx]);pred=pipeline.predict(X.iloc[test_idx])
    labels=sorted(y.unique().tolist())
    report=classification_report(y.iloc[test_idx],pred,labels=labels,output_dict=True,zero_division=0)
    matrix=confusion_matrix(y.iloc[test_idx],pred,labels=labels).tolist()
    identifier=str(uuid.uuid4());directory=Path(artifact_dir);directory.mkdir(parents=True,exist_ok=True)
    artifact=directory/(identifier+'.joblib')
    bundle={'pipeline':pipeline,'features':list(X.columns),'labels':labels,'format_version':1}
    joblib.dump(bundle,artifact)
    spec={'dataset':dataset_hash,'strategy':strategy,'column':column if strategy!='stratified' else '', 'seed':seed,'test_fraction':test_size,'label':label}
    compare_key=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:16]
    return {'id':identifier,'model':model,'source':source,'dataset_hash':dataset_hash,'comparison_key':compare_key,
      'rows':len(X),'train_rows':len(train_idx),'test_rows':len(test_idx),'features':list(X.columns),'labels':labels,
      'metrics':report,'confusion_matrix':matrix,'split':split,'seed':seed,'test_fraction':test_size,
      'seconds':round(time.perf_counter()-started,3),'macro_f1':report['macro avg']['f1-score'],
      'weighted_f1':report['weighted avg']['f1-score'],
      'boundary':'Held-out evaluation of the provided records. This is not proof of real-world intrusion detection quality.'}

def predict(frame,bundle):
    features=bundle['features']
    missing=[c for c in features if c not in frame.columns]
    if missing:raise ValueError('Missing model features: '+', '.join(missing))
    if not 1<=len(frame)<=1000:raise ValueError('Prediction accepts 1 to 1,000 rows')
    X=frame[features].apply(pd.to_numeric,errors='raise').replace([np.inf,-np.inf],np.nan)
    pipeline=bundle['pipeline'];labels=pipeline.predict(X)
    probabilities=pipeline.predict_proba(X);classes=list(pipeline.classes_)
    return {'rows':len(frame),'classes':classes,'predictions':[
      {'row':i+1,'label':str(label),'probabilities':{str(c):round(float(p),6) for c,p in zip(classes,probs)}} for i,(label,probs) in enumerate(zip(labels,probabilities))],
      'note':'Model probabilities are uncalibrated estimates, not confidence guarantees. No raw input rows are retained.'}
