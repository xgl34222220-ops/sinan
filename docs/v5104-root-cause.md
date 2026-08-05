# v5.10.4 root cause

The v5.10.3 target-period guard was only enabled when the model response contained a successfully parsed structured forecast payload. Some providers returned a visible prediction answer but omitted or malformed the hidden `tianji_forecast` block. In that case `prediction == null`, so the visible heading was not reconciled even though the user request was an explicit prediction.

v5.10.4 enables reconciliation from the resolved request intent (`wantsPrediction`) instead of structured-payload parse success.
