from __future__ import annotations


_FINAL_STYLE = r"""
/* Tianji v6.3 final polish: one small compatibility layer for density tokens. */
.tianji-console-v620{
  --v63-card-radius:18px;
  --v63-control-radius:13px;
  --v63-caption-size:11px;
  --v63-meta-size:12px;
}
.tianji-console-v620 .v510-platform-card,
.tianji-console-v620 .v510-deploy,
.tianji-console-v620 .v620-realtime-card{border-radius:var(--v63-card-radius)}
.tianji-console-v620 .v510-stage,
.tianji-console-v620 .v620-latency{border-radius:var(--v63-control-radius)}
.tianji-console-v620 .v630-health-summary small,
.tianji-console-v620 .v630-health-details>summary,
.tianji-console-v620 .v620-card-state,
.tianji-console-v620 .v620-realtime-head>span,
.tianji-console-v620 .v620-latency span,
.tianji-console-v620 .v620-latency em,
.tianji-console-v620 .v620-realtime-foot,
.tianji-console-v620 .v620-build,
.tianji-console-v620 .v620-fresh{font-size:var(--v63-caption-size)}
@media(max-width:520px){
  .tianji-console-v620 .v630-health-pill{font-size:11px}
  .tianji-console-v620 .v620-card-state{font-size:11px;min-height:22px}
  .tianji-console-v620 .v620-realtime-head>span{font-size:11px}
  .tianji-console-v620 .v620-latency span,
  .tianji-console-v620 .v620-latency em,
  .tianji-console-v620 .v620-realtime-foot{font-size:11px}
  .tianji-console-v620 .mobile-nav .nav-btn{font-size:11px!important}
  .tianji-console-v620 .v620-latency{padding:8px}
}
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from . import console_v3

    marker = "Tianji v6.3 final polish"
    if marker not in console_v3.V510_STYLE:
        console_v3.V510_STYLE += _FINAL_STYLE
    _INSTALLED = True
