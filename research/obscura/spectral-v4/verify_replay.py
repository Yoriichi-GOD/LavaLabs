# Run only as the final cell of the fresh saved private notebook.
import json,hashlib
import numpy as np
import pandas as pd
expected='ae6287bd5aee9269d6d5eb6ffe8e77f7b60db3714c7b275e59154474a2a2055a'
receipt=json.loads((output/'spectral_receipt.json').read_text())
refit=json.loads((output/'refit_receipt.json').read_text())
audit=json.loads((output/'independent_spectral_audit.json').read_text())
if not receipt['gate']['passed'] or not audit['passed']:raise ValueError('Replayed gate/audit failed')
if abs(receipt['development']['scores']['F']['mcrmse']-.9194996153136487)>1e-12:raise ValueError('Development replay mismatch')
if abs(receipt['environment_stress']['scores']['F']['mcrmse']-.9462006522193394)>1e-12:raise ValueError('Environment replay mismatch')
if refit['candidate_sha256']!=expected or hashlib.sha256((output/'submission_spectral.csv').read_bytes()).hexdigest()!=expected:
    raise ValueError('Final candidate identity mismatch')
csv=pd.read_csv(output/'submission_spectral.csv',dtype={'sample_id':str})
template=pd.read_csv(root/'sample_submission.csv',dtype={'sample_id':str})
if list(csv.columns)!=list(template.columns) or not csv.sample_id.equals(template.sample_id) or len(csv)!=1221 or not np.isfinite(csv.iloc[:,1:].to_numpy()).all():
    raise ValueError('Final CSV independent contract mismatch')
old=pd.read_csv(output/'private_control_replay.csv',dtype={'sample_id':str})
if not np.array_equal(csv.iloc[:,1:5].to_numpy(),old.iloc[:,1:5].to_numpy()):raise ValueError('Protected exported targets changed')
replay={'schema':1,'expected_results_matched':True,'candidate_sha256':expected,'rows':len(csv),
        'protected_exported_targets_equal':True,'development_mcrmse':receipt['development']['scores']['F']['mcrmse'],
        'environment_mcrmse':receipt['environment_stress']['scores']['F']['mcrmse'],
        'note':'Fresh process established by the saved Save and Run All version, not by this in-process assertion alone.',
        'no_scored_submission_in_notebook':True}
(output/'replay_verification.json').write_text(json.dumps(replay,sort_keys=True,indent=2))
print('SPECTRAL_REPLAY_BEGIN');print(json.dumps(replay,sort_keys=True));print('SPECTRAL_REPLAY_END',flush=True)
