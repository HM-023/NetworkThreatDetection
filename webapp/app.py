"""Local ML experiment dashboard. Never accepts uploaded model artifacts."""
import hashlib
import uuid
import joblib
from webapp.runtime import Store,integer,now,serve
from src.studio import read_csv,preview,train,predict
from examples.make_synthetic_data import make_sample

class Workspace:
    def __init__(self,directory):self.store=Store(directory)
    def state(self):
        return {'kind':'ml','title':'Network Threat Studio','subtitle':'Inspect a dataset, compare classifiers and inspect predictions from your own saved experiments.','category':'APPLIED MACHINE LEARNING','experiments':self.store.all('experiment')}
    def dataset(self,body):
        source=body.get('source','synthetic')
        if source not in ['synthetic','uploaded']:raise ValueError('Unknown data source')
        csv=make_sample(300).to_csv(index=False) if source=='synthetic' else body.get('csv','')
        frame=read_csv(csv);return frame,hashlib.sha256(csv.encode()).hexdigest(),source
    def action(self,body):
        action=body.get('action')
        if action in ['preview','train']:
            frame,digest,source=self.dataset(body);label=body.get('label','Label')
            if not isinstance(label,str) or not label or len(label)>100:raise ValueError('Invalid label column')
            if action=='preview':return {**preview(frame,label),'source':source,'dataset_hash':digest}
            seed=integer(body.get('seed',42),'Seed',0,2147483647)
            try:fraction=float(body.get('test_fraction',0.25))
            except (TypeError,ValueError):raise ValueError('Invalid test fraction') from None
            result=train(frame,body.get('model','random-forest'),body.get('strategy','stratified'),body.get('column',''),seed,fraction,
                         self.store.directory/'models',digest,source,label)
            result['created']=now()
            try:self.store.save('experiment',result)
            except Exception:
                (self.store.directory/'models'/(result['id']+'.joblib')).unlink(missing_ok=True);raise
            return result
        if action=='predict':
            identifier=body.get('id','')
            try:identifier=str(uuid.UUID(identifier))
            except (ValueError,TypeError,AttributeError):raise ValueError('Invalid experiment ID') from None
            self.store.get('experiment',identifier)
            # Only artifacts generated in this workspace can be selected. No model upload or arbitrary path input.
            path=self.store.directory/'models'/(identifier+'.joblib')
            if not path.is_file():raise ValueError('The local model artifact is unavailable; train again')
            bundle=joblib.load(path)
            return predict(read_csv(body.get('csv','')),bundle)
        if action=='delete':
            old=self.store.get('experiment',body.get('id'))
            self.store.delete('experiment',old['id'])
            (self.store.directory/'models'/(old['id']+'.joblib')).unlink(missing_ok=True)
            return {'ok':True}
        raise ValueError('Unknown action')

if __name__=='__main__':serve(Workspace,8101)
