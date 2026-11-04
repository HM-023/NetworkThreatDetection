import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from examples.make_synthetic_data import make_sample
from src.studio import read_csv,split_rows,train,predict
from webapp.app import Workspace
class StudioTests(unittest.TestCase):
    def test_group_split_is_disjoint_and_group_feature_removed(self):
        f=make_sample(180);f['Capture']=np.arange(180)//18
        X,y,a,b,detail=split_rows(f,'Label','group','Capture',42,.25)
        self.assertFalse(set(f.iloc[a]['Capture'])&set(f.iloc[b]['Capture']));self.assertNotIn('Capture',X.columns);self.assertEqual(detail['group_overlap'],0)
    def test_temporal_split_keeps_equal_timestamps_together(self):
        f=make_sample(180);f['Timestamp']=pd.date_range('2026-01-01',periods=60,freq='h').repeat(3).astype(str)
        X,y,a,b,detail=split_rows(f,'Label','temporal','Timestamp',42,.25)
        self.assertLess(f.iloc[a]['Timestamp'].max(),f.iloc[b]['Timestamp'].min());self.assertNotIn('Timestamp',X.columns)
    def test_unseen_holdout_class_is_rejected(self):
        f=make_sample(90);f['Capture']=['A']*60+['B']*30;f['Label']=['a']*30+['b']*30+['unseen']*30
        with self.assertRaises(ValueError):split_rows(f,'Label','group','Capture',42,.25)
    def test_train_and_predict_persisted_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            frame=make_sample(90);r=train(frame,'logistic-regression','stratified','',42,.25,d,'digest','synthetic')
            bundle=joblib.load(Path(d)/(r['id']+'.joblib'));p=predict(frame.drop(columns=['Label']).head(6),bundle)
            self.assertEqual(p['rows'],6);self.assertEqual(len(p['predictions']),6)
            self.assertEqual(sum(sum(row) for row in r['confusion_matrix']),r['test_rows'])
            with self.assertRaises(ValueError):predict(pd.DataFrame({'wrong':[1]}),bundle)
    def test_experiment_persists_and_delete_removes_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workspace(d);r=w.action({'action':'train','source':'synthetic','model':'logistic-regression'})
            self.assertEqual(Workspace(d).state()['experiments'][0]['id'],r['id'])
            self.assertNotIn('csv',r);self.assertEqual(r['source'],'synthetic')
            prediction=w.action({'action':'predict','id':r['id'],'csv':make_sample(2).drop(columns=['Label']).to_csv(index=False)})
            self.assertEqual(prediction['rows'],2)
            w.action({'action':'delete','id':r['id']});self.assertFalse((Path(d)/'models'/(r['id']+'.joblib')).exists())
    def test_limits_and_invalid_model_path(self):
        with self.assertRaises(ValueError):read_csv('')
        with self.assertRaises(ValueError):read_csv('x\n'+'1\n'*20001)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):Workspace(d).action({'action':'predict','id':'../../foreign.joblib','csv':'x\n1'})
    def test_duplicate_csv_headers_and_reserved_labels_are_rejected(self):
        with self.assertRaises(ValueError):read_csv('x,x,Label\n1,2,a\n')
        f=make_sample(90);f.loc[f['Label']=='normal','Label']='macro avg'
        with self.assertRaises(ValueError):split_rows(f,'Label','stratified','',42,.25)
    def test_comparison_key_changes_with_split_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            a=train(make_sample(90),'logistic-regression','stratified','',42,.25,d,'same','synthetic')
            b=train(make_sample(90),'random-forest','stratified','',42,.25,d,'same','synthetic')
            c=train(make_sample(90),'logistic-regression','stratified','',13,.25,d,'same','synthetic')
            self.assertEqual(a['comparison_key'],b['comparison_key']);self.assertNotEqual(a['comparison_key'],c['comparison_key'])
