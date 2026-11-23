# Execute after the fixed label-blind profile and overlays are reviewed.
from spectral_lab.comparison import run
spectral_receipt=run(root,output)
from spectral_lab.audit_saved import audit
spectral_audit=audit(root,output)
