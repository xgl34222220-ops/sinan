from __future__ import annotations

from html import escape


STYLE = r"""
:root{
  color-scheme:light;
  --bg:#f3f5fb;
  --bg2:#eef1f8;
  --surface:rgba(255,255,255,.86);
  --surface-solid:#ffffff;
  --surface-soft:rgba(246,248,253,.92);
  --text:#151824;
  --text-2:#34394a;
  --muted:#747b8e;
  --line:rgba(25,32,52,.08);
  --line-strong:rgba(25,32,52,.13);
  --primary:#6b5cff;
  --primary-2:#8a63ff;
  --primary-soft:#eeebff;
  --good:#12865e;
  --good-soft:#e8f8f1;
  --warn:#a96600;
  --warn-soft:#fff5df;
  --bad:#c43852;
  --bad-soft:#fff0f3;
  --shadow:0 20px 55px rgba(48,53,79,.10);
  --shadow-soft:0 10px 30px rgba(48,53,79,.07);
  --radius-xl:28px;
  --radius-lg:22px;
  --radius-md:17px;
  --safe-bottom:max(12px,env(safe-area-inset-bottom));
}
[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0f1118;
  --bg2:#151823;
  --surface:rgba(28,31,43,.84);
  --surface-solid:#1b1e29;
  --surface-soft:rgba(35,39,53,.9);
  --text:#f2f3f7;
  --text-2:#d9dce6;
  --muted:#989fb3;
  --line:rgba(255,255,255,.07);
  --line-strong:rgba(255,255,255,.12);
  --primary:#9588ff;
  --primary-2:#bc8cff;
  --primary-soft:#2b2850;
  --good:#56d6a1;
  --good-soft:#163b30;
  --warn:#f4bb63;
  --warn-soft:#3e311b;
  --bad:#ff8497;
  --bad-soft:#44232b;
  --shadow:0 22px 60px rgba(0,0,0,.30);
  --shadow-soft:0 12px 34px rgba(0,0,0,.22);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth}
body{
  margin:0;
  min-height:100vh;
  color:var(--text);
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI","Noto Sans SC",sans-serif;
  background:
    radial-gradient(circle at 10% -10%,color-mix(in srgb,var(--primary) 16%,transparent),transparent 34%),
    radial-gradient(circle at 105% 8%,color-mix(in srgb,var(--primary-2) 12%,transparent),transparent 32%),
    linear-gradient(180deg,var(--bg),var(--bg2));
}
button,input,select{font:inherit}
button{color:inherit}
a{color:inherit}
svg{display:block}
.shell{width:min(1180px,calc(100% - 28px));margin:0 auto;padding:18px 0 66px}
.appbar{
  position:sticky;top:0;z-index:40;
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  margin:0 -6px 18px;padding:12px 6px;
  background:linear-gradient(180deg,color-mix(in srgb,var(--bg) 94%,transparent) 72%,transparent);
  backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)
}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.brandmark{
  width:42px;height:42px;flex:0 0 42px;border-radius:15px;display:grid;place-items:center;
  color:#fff;background:linear-gradient(145deg,var(--primary),var(--primary-2));
  box-shadow:0 11px 26px color-mix(in srgb,var(--primary) 27%,transparent)
}
.brandmark svg{width:22px;height:22px}
.brandcopy{min-width:0}.brandcopy h1{font-size:18px;line-height:1.15;margin:0;font-weight:820;letter-spacing:-.02em}.brandcopy p{font-size:11px;color:var(--muted);margin:3px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.toolbar{display:flex;align-items:center;gap:8px}
.icon-btn,.btn,.nav-btn,.chip{border:0;cursor:pointer;transition:transform .18s ease,background .18s ease,border-color .18s ease,opacity .18s ease}
.icon-btn:active,.btn:active,.nav-btn:active,.chip:active{transform:scale(.97)}
.icon-btn{width:40px;height:40px;border-radius:14px;display:grid;place-items:center;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-soft);backdrop-filter:blur(14px)}
.icon-btn svg{width:19px;height:19px;color:var(--text-2)}
.status-pill{display:inline-flex;align-items:center;gap:8px;min-height:40px;padding:0 13px;border-radius:15px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-soft);font-size:12px;color:var(--muted);backdrop-filter:blur(14px)}
.status-dot{width:8px;height:8px;border-radius:99px;background:var(--good);box-shadow:0 0 0 5px color-mix(in srgb,var(--good) 14%,transparent)}
.hero{
  position:relative;overflow:hidden;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:end;
  padding:28px;border-radius:var(--radius-xl);border:1px solid var(--line);
  background:linear-gradient(145deg,color-mix(in srgb,var(--surface-solid) 91%,var(--primary-soft)),var(--surface));
  box-shadow:var(--shadow)
}
.hero:before{content:"";position:absolute;right:-90px;top:-120px;width:280px;height:280px;border-radius:50%;background:radial-gradient(circle,color-mix(in srgb,var(--primary) 20%,transparent),transparent 68%);pointer-events:none}
.hero-copy{position:relative;z-index:1}.eyebrow{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;color:var(--primary)}
.hero h2{font-size:clamp(28px,4.6vw,48px);line-height:1.08;letter-spacing:-.045em;margin:10px 0 12px;max-width:760px}.hero p{max-width:700px;color:var(--muted);font-size:14px;line-height:1.75;margin:0}
.hero-actions{position:relative;z-index:1;display:flex;gap:9px;flex-wrap:wrap;justify-content:flex-end}
.btn{min-height:43px;padding:0 16px;border-radius:15px;display:inline-flex;align-items:center;justify-content:center;gap:8px;text-decoration:none;font-size:13px;font-weight:760}
.btn svg{width:17px;height:17px}.btn.primary{color:#fff;background:linear-gradient(135deg,var(--primary),var(--primary-2));box-shadow:0 12px 26px color-mix(in srgb,var(--primary) 24%,transparent)}.btn.secondary{background:var(--surface-soft);border:1px solid var(--line);color:var(--text-2)}.btn.ghost{background:transparent;border:1px solid var(--line-strong);color:var(--text-2)}.btn:disabled{opacity:.55;cursor:not-allowed}
.section{margin-top:17px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:14px;margin:0 2px 11px}.section-head h2{font-size:19px;letter-spacing:-.025em;margin:0}.section-head p{font-size:12px;color:var(--muted);margin:4px 0 0}.section-meta{font-size:11px;color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.metric{padding:17px;border-radius:var(--radius-lg);background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-soft);backdrop-filter:blur(16px)}
.metric-top{display:flex;align-items:center;justify-content:space-between;gap:10px}.metric-icon{width:34px;height:34px;border-radius:12px;display:grid;place-items:center;background:var(--primary-soft);color:var(--primary)}.metric-icon svg{width:17px;height:17px}.metric-label{font-size:11px;color:var(--muted)}.metric-value{font-size:20px;font-weight:820;letter-spacing:-.025em;margin-top:10px;overflow-wrap:anywhere}.metric-foot{font-size:10px;color:var(--muted);margin-top:4px}
.lottery-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.lottery-card{overflow:hidden;border-radius:var(--radius-xl);background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow);backdrop-filter:blur(16px)}
.lottery-main{padding:22px}.lottery-title{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.lottery-title h3{font-size:22px;line-height:1.18;margin:0;letter-spacing:-.03em}.lottery-sub{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.55}.target-badge{flex:0 0 auto;padding:9px 11px;border-radius:15px;background:var(--surface-soft);border:1px solid var(--line);font-size:10px;color:var(--muted);text-align:right}.target-badge strong{display:block;color:var(--text);font-size:13px;margin-top:3px}
.numbers{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:6px;margin:18px 0}.number{aspect-ratio:1;border-radius:12px;display:grid;place-items:center;background:var(--surface-soft);border:1px solid var(--line);font-size:14px;font-weight:820;box-shadow:inset 0 1px 0 rgba(255,255,255,.32)}
.ai-strip{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-radius:15px;background:var(--surface-soft);border:1px solid var(--line)}.ai-strip-left{display:flex;align-items:center;gap:9px;min-width:0}.ai-orb{width:30px;height:30px;flex:0 0 30px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(145deg,var(--primary),var(--primary-2));color:#fff}.ai-orb svg{width:15px;height:15px}.ai-strip-title{font-size:12px;font-weight:760}.ai-strip-sub{font-size:10px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.state-badge{flex:0 0 auto;padding:6px 9px;border-radius:999px;font-size:10px;font-weight:760;background:var(--primary-soft);color:var(--primary)}.state-badge.good{background:var(--good-soft);color:var(--good)}.state-badge.warn{background:var(--warn-soft);color:var(--warn)}.state-badge.bad{background:var(--bad-soft);color:var(--bad)}
.forecasts{border-top:1px solid var(--line)}.forecast{padding:15px 22px;border-top:1px solid var(--line)}.forecast:first-child{border-top:0}.forecast-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.forecast-source{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:780}.source-dot{width:8px;height:8px;border-radius:50%;background:var(--primary)}.source-dot.native{background:var(--good)}.forecast-result{font-size:10px;font-weight:780;padding:5px 8px;border-radius:999px;background:var(--warn-soft);color:var(--warn)}.forecast-result.hit{background:var(--good-soft);color:var(--good)}.forecast-result.miss{background:var(--bad-soft);color:var(--bad)}.forecast-meta{font-size:11px;color:var(--muted);line-height:1.65;margin-top:7px}.ball-row{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}.mini-ball{min-width:25px;height:25px;padding:0 6px;border-radius:9px;display:grid;place-items:center;background:var(--surface-soft);border:1px solid var(--line);font-size:11px;font-weight:760}.empty{padding:24px;text-align:center;color:var(--muted);font-size:12px}
.disclaimer{margin-top:18px;padding:15px 18px;border-radius:18px;border:1px solid var(--line);background:var(--surface-soft);font-size:11px;color:var(--muted);line-height:1.7;text-align:center}
.layout{display:grid;grid-template-columns:226px minmax(0,1fr);gap:17px}.sidebar{position:sticky;top:76px;height:max-content;padding:10px;border-radius:22px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-soft);backdrop-filter:blur(18px)}.sidebar-label{font-size:10px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);padding:9px 11px 6px}.nav-btn{width:100%;min-height:45px;padding:0 12px;border-radius:14px;background:transparent;display:flex;align-items:center;gap:10px;text-align:left;color:var(--muted);font-size:13px;font-weight:720}.nav-btn svg{width:18px;height:18px}.nav-btn.active{color:var(--primary);background:var(--primary-soft)}.nav-btn .nav-tail{margin-left:auto;font-size:9px;color:var(--muted)}
.content{min-width:0}.panel{display:none}.panel.active{display:block}.panel-hero{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:13px}.panel-hero h2{font-size:27px;letter-spacing:-.04em;margin:0}.panel-hero p{font-size:12px;color:var(--muted);margin:5px 0 0;line-height:1.55}
.card{border-radius:var(--radius-xl);background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow);backdrop-filter:blur(18px)}.card-pad{padding:22px}.card + .card{margin-top:14px}.card-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:15px}.card-title h3{font-size:16px;margin:0}.card-title p{font-size:11px;color:var(--muted);margin:4px 0 0}
.overview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.overview-lottery{padding:19px}.overview-lottery .numbers{margin-bottom:12px}.overview-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:10px;color:var(--muted)}
.task-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.task-card{padding:16px;border-radius:18px;background:var(--surface-soft);border:1px solid var(--line)}.task-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.task-title{font-size:12px;font-weight:780}.task-body{font-size:11px;color:var(--muted);line-height:1.6;margin-top:7px}.task-time{font-size:10px;color:var(--muted);margin-top:7px}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.field{display:flex;flex-direction:column;gap:7px}.field.full{grid-column:1/-1}.field label{font-size:11px;color:var(--muted);font-weight:720}.input{width:100%;min-height:46px;padding:0 13px;border-radius:15px;border:1px solid var(--line);background:var(--surface-soft);color:var(--text);outline:none}.input:focus{border-color:color-mix(in srgb,var(--primary) 55%,var(--line));box-shadow:0 0 0 4px color-mix(in srgb,var(--primary) 11%,transparent);background:var(--surface-solid)}select.input{appearance:auto}.switch-row{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:15px;border-radius:17px;background:var(--surface-soft);border:1px solid var(--line)}.switch-copy strong{font-size:13px}.switch-copy div{font-size:10px;color:var(--muted);margin-top:3px}.switch{position:relative;width:48px;height:28px;flex:0 0 48px}.switch input{opacity:0;width:0;height:0}.slider{position:absolute;inset:0;border-radius:99px;background:#c9cedb;transition:.2s}.slider:before{content:"";position:absolute;width:22px;height:22px;left:3px;top:3px;border-radius:50%;background:#fff;box-shadow:0 3px 9px rgba(0,0,0,.18);transition:.2s}.switch input:checked+.slider{background:var(--primary)}.switch input:checked+.slider:before{transform:translateX(20px)}
.notice{padding:13px 14px;border-radius:15px;background:var(--primary-soft);border:1px solid color-mix(in srgb,var(--primary) 15%,var(--line));color:color-mix(in srgb,var(--primary) 72%,var(--text));font-size:11px;line-height:1.65}.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{min-height:34px;padding:0 11px;border-radius:999px;background:var(--surface-soft);border:1px solid var(--line);color:var(--muted);font-size:11px;font-weight:720}.chip:hover{border-color:color-mix(in srgb,var(--primary) 36%,var(--line));color:var(--primary)}
.result-box{min-height:78px;padding:15px;border-radius:17px;background:#141722;color:#e5e8f5;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;line-height:1.65;white-space:pre-wrap;word-break:break-word}.result-box.success{background:#11352a;color:#cef7e6}.result-box.error{background:#43212a;color:#ffdce2}
.archive-list{display:grid;gap:9px}.archive-item{display:grid;grid-template-columns:minmax(112px,.8fr) minmax(120px,1fr) minmax(150px,1.4fr) auto;gap:12px;align-items:center;padding:14px 15px;border-radius:17px;background:var(--surface-soft);border:1px solid var(--line)}.archive-title{font-size:12px;font-weight:780}.archive-sub{font-size:10px;color:var(--muted);margin-top:3px}.archive-picks{font-size:11px;color:var(--text-2)}
.details{border-radius:18px;background:var(--surface-soft);border:1px solid var(--line);overflow:hidden}.details summary{cursor:pointer;list-style:none;padding:14px 16px;font-size:12px;font-weight:760;display:flex;align-items:center;justify-content:space-between}.details summary::-webkit-details-marker{display:none}.details pre{margin:0;border-top:1px solid var(--line);padding:15px;max-height:360px;overflow:auto;background:#141722;color:#dfe4f4;font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
.mobile-nav{display:none}.toast{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));z-index:100;max-width:min(410px,calc(100% - 32px));padding:13px 15px;border-radius:15px;background:#171a25;color:#fff;box-shadow:0 18px 45px rgba(0,0,0,.28);font-size:12px;opacity:0;transform:translateY(10px);pointer-events:none;transition:.2s}.toast.show{opacity:1;transform:none}.toast.error{background:#762638}
.login-wrap{min-height:100vh;display:grid;place-items:center;padding:22px}.login-card{width:min(430px,100%);padding:26px;border-radius:30px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow);backdrop-filter:blur(22px)}.login-head{display:flex;align-items:center;gap:12px;margin-bottom:22px}.login-title h1{font-size:24px;letter-spacing:-.035em;margin:0}.login-title p{font-size:11px;color:var(--muted);margin:4px 0 0}.login-card .btn{width:100%;margin-top:12px}.login-foot{text-align:center;font-size:11px;color:var(--muted);margin-top:18px}.login-foot a{color:var(--primary);text-decoration:none}
.good{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}
@media(max-width:920px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.layout{grid-template-columns:190px minmax(0,1fr)}.numbers{grid-template-columns:repeat(5,minmax(0,1fr))}.archive-item{grid-template-columns:1fr 1fr}.archive-item>*:last-child{justify-self:end}}
@media(max-width:760px){.shell{width:min(100% - 18px,700px);padding-top:8px;padding-bottom:104px}.appbar{padding-top:9px}.status-pill.hide-mobile{display:none}.hero{grid-template-columns:1fr;padding:22px}.hero-actions{justify-content:flex-start}.lottery-grid{grid-template-columns:1fr}.layout{display:block}.sidebar{display:none}.content{width:100%}.mobile-nav{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;left:9px;right:9px;bottom:var(--safe-bottom);z-index:80;padding:6px;border-radius:22px;background:color-mix(in srgb,var(--surface-solid) 90%,transparent);border:1px solid var(--line);box-shadow:0 16px 44px rgba(28,32,52,.20);backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px)}.mobile-nav .nav-btn{min-height:54px;display:flex;flex-direction:column;justify-content:center;gap:3px;padding:0;font-size:9px;text-align:center}.mobile-nav .nav-btn svg{width:18px;height:18px}.mobile-nav .nav-tail{display:none}.panel-hero{align-items:flex-start;flex-direction:column}.overview-grid,.task-grid{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.archive-item{grid-template-columns:1fr auto}.archive-item .archive-picks{grid-column:1/-1}.toast{bottom:calc(84px + var(--safe-bottom))}}
@media(max-width:460px){.brandcopy p{display:none}.brandmark{width:39px;height:39px;flex-basis:39px}.toolbar{gap:6px}.icon-btn{width:38px;height:38px}.hero h2{font-size:29px}.hero p{font-size:12px}.metrics{gap:9px}.metric{padding:14px}.metric-value{font-size:17px}.lottery-main{padding:18px}.lottery-title h3{font-size:20px}.forecast{padding:14px 18px}.number{font-size:13px}.panel-hero h2{font-size:24px}.card-pad{padding:18px}.hero-actions{width:100%}.hero-actions .btn{flex:1}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
"""

ICONS = {
    "spark": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Z"/><path d="M18.5 13.5l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z"/><path d="M5 14l.9 2.8L9 18l-3.1 1.2L5 22l-.9-2.8L1 18l3.1-1.2L5 14Z"/></svg>',
    "sun": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"/></svg>',
    "refresh": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8 8 0 1 0-2.34 5.66"/><path d="M20 4v7h-7"/></svg>',
    "dashboard": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    "brain": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 4.5A3 3 0 0 0 6 7.4 3.2 3.2 0 0 0 4.5 13 3.1 3.1 0 0 0 7 18.1 3 3 0 0 0 12 20V4a3 3 0 0 0-2.5.5Z"/><path d="M14.5 4.5A3 3 0 0 1 18 7.4a3.2 3.2 0 0 1 1.5 5.6 3.1 3.1 0 0 1-2.5 5.1A3 3 0 0 1 12 20V4a3 3 0 0 1 2.5.5Z"/><path d="M8 10h4M12 14h4"/></svg>',
    "archive": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16v13H4z"/><path d="M3 3h18v4H3zM9 11h6"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-4"/></svg>',
    "server": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/></svg>',
    "database": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    "update": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7h-6V1"/><path d="M20 7a9 9 0 1 0 1 7"/></svg>',
    "logout": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9"/></svg>',
    "play": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m8 5 11 7-11 7V5Z"/></svg>',
    "key": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4"/><path d="m11 12 8-8M15 8l2 2M17 6l2 2"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"/></svg>',
}


def _icon(name: str) -> str:
    return ICONS[name]


def _document(title: str, body: str, script: str = "") -> str:
    template = """<!doctype html><html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f3f5fb"><title>__TITLE__</title><style>__STYLE__</style></head><body>__BODY__<div class="toast" id="toast"></div><script>__THEME_SCRIPT__</script><script>__SCRIPT__</script></body></html>"""
    theme_script = r"""
const root=document.documentElement;
const savedTheme=localStorage.getItem('tianji-theme');
const systemDark=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
root.dataset.theme=savedTheme||(systemDark?'dark':'light');
function toggleTheme(){root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';localStorage.setItem('tianji-theme',root.dataset.theme)}
"""
    return (
        template.replace("__TITLE__", escape(title))
        .replace("__STYLE__", STYLE)
        .replace("__BODY__", body)
        .replace("__THEME_SCRIPT__", theme_script)
        .replace("__SCRIPT__", script)
    )


def public_page() -> str:
    body = f"""
<div class="shell">
  <header class="appbar">
    <div class="brand"><div class="brandmark">{_icon('spark')}</div><div class="brandcopy"><h1>天机云端</h1><p>前向冻结 · 自动结算 · 本地兜底</p></div></div>
    <div class="toolbar"><div class="status-pill hide-mobile"><span class="status-dot" id="statusDot"></span><span id="statusText">连接中</span></div><button class="icon-btn" onclick="toggleTheme()" aria-label="切换主题">{_icon('sun')}</button><button class="icon-btn" id="refreshBtn" aria-label="刷新">{_icon('refresh')}</button></div>
  </header>
  <section class="hero"><div class="hero-copy"><div class="eyebrow">{_icon('spark')} Tianji Cloud</div><h2>云端持续运行，<br>手机始终保留本地能力。</h2><p>服务器负责同步开奖、冻结本机与 AI 前向结果并按目标期结算。服务器到期或断网后，Android 仍可使用本地历史、本机分析和手机直连 AI。</p></div><div class="hero-actions"><a class="btn primary" href="/admin">{_icon('dashboard')} 管理控制台</a><a class="btn secondary" href="/docs">{_icon('link')} API 文档</a></div></section>
  <section class="section"><div class="section-head"><div><h2>服务状态</h2><p>自动刷新，不需要手动盯守。</p></div><div class="section-meta" id="lastRefresh">—</div></div><div class="metrics" id="metrics"></div></section>
  <section class="section"><div class="section-head"><div><h2>实时预测</h2><p>每个彩种、每个目标期最多保留一条本机预测和一条 AI 预测。</p></div></div><div class="lottery-grid" id="lotteries"></div></section>
  <div class="disclaimer">随机开奖不可可靠预测。本服务只用于统计实验、首次冻结与目标期验证，不承诺盈利或必中。</div>
</div>
"""
    script = r"""
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=n=>n?new Date(n).toLocaleString('zh-CN',{hour12:false}):'—';
const ago=n=>{if(!n)return'—';const s=Math.max(0,Math.floor((Date.now()-n)/1000));if(s<60)return s+' 秒前';if(s<3600)return Math.floor(s/60)+' 分钟前';return Math.floor(s/3600)+' 小时前'};
const jobLabel=j=>{if(!j)return['等待调度','warn'];const map={queued:['排队中','warn'],running:['分析中','warn'],completed:['已冻结','good'],duplicate:['已冻结','good'],error:['调用失败','bad'],discarded:['封盘丢弃','bad'],skipped:['等待下期','warn']};return map[j.status]||[j.status||'未知','warn']};
const resultLabel=f=>f.top6_hit===true?['命中','hit']:f.top6_hit===false?['未中','miss']:['待开奖',''];
const ICONS={brain:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9.5 4.5A3 3 0 0 0 6 7.4 3.2 3.2 0 0 0 4.5 13 3.1 3.1 0 0 0 7 18.1 3 3 0 0 0 12 20V4a3 3 0 0 0-2.5.5Z"/><path d="M14.5 4.5A3 3 0 0 1 18 7.4a3.2 3.2 0 0 1 1.5 5.6 3.1 3.1 0 0 1-2.5 5.1A3 3 0 0 1 12 20V4a3 3 0 0 1 2.5.5Z"/></svg>`,server:`__SERVER__`,database:`__DATABASE__`,clock:`__CLOCK__`,update:`__UPDATE__`};
function renderLottery(x){const job=jobLabel(x.ai_job);const forecasts=(x.forecasts||[]).map(f=>{const r=resultLabel(f);return `<article class="forecast"><div class="forecast-head"><div class="forecast-source"><span class="source-dot ${f.source==='ai'?'':'native'}"></span>${f.source==='ai'?'云端 AI':'本机云端'} · 第 ${f.position+1} 名</div><span class="forecast-result ${r[1]}">${r[0]}</span></div><div class="ball-row">${f.top6.map(n=>`<span class="mini-ball">${n}</span>`).join('')}</div><div class="forecast-meta">模型 ${esc(f.model)} · 目标期 ${esc(f.target_period)}</div></article>`}).join('');return `<section class="lottery-card"><div class="lottery-main"><div class="lottery-title"><div><h3>${esc(x.name)}</h3><div class="lottery-sub">最新期 ${esc(x.latest_period||'等待同步')} · ${fmt(x.synced_at_epoch_ms)}</div></div><div class="target-badge">目标期<strong>${esc(x.next_period||'待同步')}</strong></div></div><div class="numbers">${(x.numbers||[]).map(n=>`<span class="number">${n}</span>`).join('')}</div><div class="ai-strip"><div class="ai-strip-left"><span class="ai-orb">${ICONS.brain}</span><div style="min-width:0"><div class="ai-strip-title">AI 任务</div><div class="ai-strip-sub">${esc((x.ai_job&&x.ai_job.model)||'等待配置')} · ${esc((x.ai_job&&x.ai_job.target_period)||x.next_period||'—')}</div></div></div><span class="state-badge ${job[1]}">${job[0]}</span></div></div><div class="forecasts">${forecasts||'<div class="empty">等待下一期前向档案</div>'}</div></section>`}
async function refresh(){try{const r=await fetch('/v1/public/overview',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();$('statusText').textContent=d.health.status==='ok'?'运行正常':'状态异常';$('statusDot').style.background=d.health.status==='ok'?'var(--good)':'var(--bad)';$('lastRefresh').textContent='刷新于 '+new Date().toLocaleTimeString('zh-CN',{hour12:false});$('metrics').innerHTML=`<div class="metric"><div class="metric-top"><span class="metric-label">服务</span><span class="metric-icon">${ICONS.server}</span></div><div class="metric-value ${d.health.status==='ok'?'good':'bad'}">${esc(d.health.status)}</div><div class="metric-foot">版本 ${esc(d.health.version)}</div></div><div class="metric"><div class="metric-top"><span class="metric-label">数据库</span><span class="metric-icon">${ICONS.database}</span></div><div class="metric-value ${d.health.database==='ok'?'good':'bad'}">${esc(d.health.database)}</div><div class="metric-foot">本地 SQLite 档案</div></div><div class="metric"><div class="metric-top"><span class="metric-label">后台任务</span><span class="metric-icon">${ICONS.clock}</span></div><div class="metric-value ${d.health.worker==='ok'?'good':'warn'}">${esc(d.health.worker)}</div><div class="metric-foot">${ago(d.health.last_worker_heartbeat_epoch_ms)}</div></div><div class="metric"><div class="metric-top"><span class="metric-label">云端 AI</span><span class="metric-icon">${ICONS.update}</span></div><div class="metric-value">${d.ai.configured?esc(d.ai.model):'未配置'}</div><div class="metric-foot">${d.ai.configured?'后台自动调度':'仍保留本机预测'}</div></div>`;$('lotteries').innerHTML=d.lotteries.map(renderLottery).join('')}catch(e){$('statusText').textContent='连接失败';$('statusDot').style.background='var(--bad)'}}
$('refreshBtn').onclick=refresh;refresh();setInterval(refresh,30000);
""".replace("__SERVER__", _icon("server")).replace("__DATABASE__", _icon("database")).replace("__CLOCK__", _icon("clock")).replace("__UPDATE__", _icon("update"))
    return _document("天机云端", body, script)


def login_page(configured: bool) -> str:
    message = "输入网页管理密码，模型、任务和档案都可直接在这里管理。" if configured else "服务器尚未设置网页管理密码，请先完成一次升级初始化。"
    disabled = "" if configured else "disabled"
    body = f"""
<div class="login-wrap"><main class="login-card"><div class="login-head"><div class="brandmark">{_icon('spark')}</div><div class="login-title"><h1>天机控制台</h1><p>安全登录到云端管理面板</p></div></div><p style="font-size:12px;color:var(--muted);line-height:1.7;margin:0 0 18px">{escape(message)}</p><form id="loginForm"><div class="field"><label>管理密码</label><input class="input" id="password" type="password" minlength="8" autocomplete="current-password" placeholder="输入管理密码" {disabled}></div><button class="btn primary" id="loginBtn" {disabled}>{_icon('shield')} 登录</button></form><div class="login-foot"><a href="/">返回公开状态页</a></div></main></div>
"""
    script = r"""
const toast=(m,e=false)=>{const t=document.getElementById('toast');t.textContent=m;t.className='toast show'+(e?' error':'');setTimeout(()=>t.className='toast',2600)};
document.getElementById('loginForm').addEventListener('submit',async e=>{e.preventDefault();const b=document.getElementById('loginBtn');b.disabled=true;try{const r=await fetch('/admin/api/login',{method:'POST',headers:{'Content-Type':'application/json','X-Tianji-Admin':'1'},body:JSON.stringify({password:document.getElementById('password').value})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'登录失败');location.href='/admin'}catch(err){toast(err.message,true);b.disabled=false}});
"""
    return _document("登录 · 天机控制台", body, script)


def admin_page() -> str:
    nav = f"""
<button class="nav-btn active" data-panel="overview">{_icon('dashboard')}<span>总览</span><span class="nav-tail">01</span></button>
<button class="nav-btn" data-panel="ai">{_icon('brain')}<span>AI 模型</span><span class="nav-tail">02</span></button>
<button class="nav-btn" data-panel="records">{_icon('archive')}<span>预测档案</span><span class="nav-tail">03</span></button>
<button class="nav-btn" data-panel="security">{_icon('shield')}<span>设置</span><span class="nav-tail">04</span></button>
"""
    body = f"""
<div class="shell admin-shell">
<header class="appbar"><div class="brand"><div class="brandmark">{_icon('spark')}</div><div class="brandcopy"><h1>天机控制台</h1><p>无需 SSH 的云端工作台</p></div></div><div class="toolbar"><div class="status-pill hide-mobile"><span class="status-dot" id="topDot"></span><span id="topStatus">读取中</span></div><button class="icon-btn" onclick="toggleTheme()" aria-label="切换主题">{_icon('sun')}</button><button class="icon-btn" id="logoutBtn" aria-label="退出">{_icon('logout')}</button></div></header>
<div class="layout"><aside class="sidebar"><div class="sidebar-label">Cloud Console</div>{nav}</aside><main class="content">
<section class="panel active" id="panel-overview"><div class="panel-hero"><div><h2>运行总览</h2><p>开奖同步、AI 调度、前向冻结和自动更新都在这里查看。</p></div><button class="btn primary" id="runBtn">{_icon('play')} 立即同步</button></div><div class="metrics" id="adminMetrics"></div><div class="section"><div class="section-head"><div><h2>彩种状态</h2><p>每个彩种独立同步和调度，不再互相阻塞。</p></div></div><div class="overview-grid" id="adminLotteries"></div></div><div class="card card-pad"><div class="card-title"><div><h3>任务状态</h3><p>使用可读状态代替整屏原始 JSON。</p></div></div><div class="task-grid" id="taskGrid"></div><details class="details" style="margin-top:12px"><summary><span>技术详情</span><span>展开</span></summary><pre id="runtimeLog">读取中…</pre></details></div></section>
<section class="panel" id="panel-ai"><div class="panel-hero"><div><h2>AI 模型</h2><p>修改接口、模型与密钥后立即生效，新模型从下一期开始使用。</p></div></div><div class="card card-pad"><div class="switch-row"><div class="switch-copy"><strong>启用云端 AI</strong><div>关闭后仍保留本机云端统计预测</div></div><label class="switch"><input id="aiEnabled" type="checkbox"><span class="slider"></span></label></div><div class="notice" style="margin:13px 0">API Key 只保存在服务器数据目录，不会完整回显。输入框留空会保留当前密钥。</div><div class="chips" style="margin-bottom:13px"><button class="chip" data-preset="deepseek-pro">DeepSeek V4 Pro</button><button class="chip" data-preset="deepseek-flash">DeepSeek V4 Flash</button><button class="chip" data-preset="deepseek-custom">DeepSeek 自定义</button><button class="chip" data-preset="openai">OpenAI Responses</button></div><div class="form-grid"><div class="field full"><label>接口地址</label><input class="input" id="aiEndpoint" inputmode="url" placeholder="https://api.example.com/v1/chat/completions"></div><div class="field"><label>模型名</label><input class="input" id="aiModel" list="modelList" placeholder="选择或输入模型"><datalist id="modelList"></datalist></div><div class="field"><label>超时时间</label><select class="input" id="aiTimeout"><option value="45">45 秒</option><option value="90">90 秒</option><option value="120">120 秒</option><option value="180">180 秒</option><option value="300">300 秒</option></select></div><div class="field full"><label>API Key</label><input class="input" id="aiKey" type="password" autocomplete="new-password" placeholder="留空保留当前密钥"></div></div><div class="section-meta" id="keyHint" style="margin-top:9px">当前密钥：读取中</div><div class="hero-actions" style="justify-content:flex-start;margin-top:16px"><button class="btn primary" id="saveAiBtn">保存并生效</button><button class="btn secondary" id="testAiBtn">真实调用测试</button><button class="btn secondary" id="modelsBtn">读取模型</button></div><div class="result-box" id="aiResult" style="margin-top:14px">等待操作</div></div></section>
<section class="panel" id="panel-records"><div class="panel-hero"><div><h2>预测档案</h2><p>查看首次冻结结果与目标期结算，旧结果不会被切换模型覆盖。</p></div></div><div class="card card-pad"><div class="archive-list" id="recordsList"></div></div></section>
<section class="panel" id="panel-security"><div class="panel-hero"><div><h2>设置</h2><p>管理网页登录密码并查看自动更新状态。</p></div></div><div class="card card-pad"><div class="card-title"><div><h3>管理密码</h3><p>只影响网页控制台，不修改服务器 root 密码。</p></div></div><div class="form-grid"><div class="field"><label>当前管理密码</label><input class="input" id="oldPassword" type="password" autocomplete="current-password"></div><div class="field"><label>新管理密码</label><input class="input" id="newPassword" type="password" minlength="8" autocomplete="new-password"></div></div><button class="btn primary" id="passwordBtn" style="margin-top:14px">更新管理密码</button></div><div class="card card-pad"><div class="card-title"><div><h3>自动更新</h3><p>每 5 分钟检查，更新前备份，失败自动回滚。</p></div></div><div class="task-card" id="updateCard">读取中…</div></div></section>
</main></div></div><nav class="mobile-nav">{nav}</nav>
"""
    script = r"""
const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));const fmt=n=>n?new Date(n).toLocaleString('zh-CN',{hour12:false}):'—';const ago=n=>{if(!n)return'—';const s=Math.max(0,Math.floor((Date.now()-n)/1000));if(s<60)return s+' 秒前';if(s<3600)return Math.floor(s/60)+' 分钟前';return Math.floor(s/3600)+' 小时前'};
const toast=(m,e=false)=>{const t=$('toast');t.textContent=m;t.className='toast show'+(e?' error':'');setTimeout(()=>t.className='toast',2800)};
async function api(path,options={}){const r=await fetch(path,{cache:'no-store',...options,headers:{'X-Tianji-Admin':'1',...(options.headers||{})}});if(r.status===401){location.href='/admin';throw new Error('登录已过期')}const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));return d}
function setPanel(name){document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id==='panel-'+name));document.querySelectorAll('.nav-btn').forEach(x=>x.classList.toggle('active',x.dataset.panel===name));window.scrollTo({top:0,behavior:'smooth'})}document.querySelectorAll('.nav-btn').forEach(x=>x.addEventListener('click',()=>setPanel(x.dataset.panel)));
const statusMap={queued:['排队中','warn'],running:['分析中','warn'],completed:['已冻结','good'],duplicate:['已冻结','good'],error:['失败','bad'],discarded:['封盘丢弃','bad'],skipped:['等待下期','warn']};
const jobView=j=>j?(statusMap[j.status]||[j.status||'未知','warn']):['等待调度','warn'];
function lotteryCard(x){const j=jobView(x.ai_job);return `<article class="card overview-lottery"><div class="lottery-title"><div><h3>${esc(x.name)}</h3><div class="lottery-sub">最新期 ${esc(x.latest_period||'等待同步')} · ${fmt(x.synced_at_epoch_ms)}</div></div><div class="target-badge">目标期<strong>${esc(x.next_period||'待同步')}</strong></div></div><div class="numbers">${(x.numbers||[]).map(n=>`<span class="number">${n}</span>`).join('')}</div><div class="overview-footer"><span>历史 ${x.draw_count} 期 · 档案 ${x.forecasts.length} 条</span><span class="state-badge ${j[1]}">AI ${j[0]}</span></div></article>`}
function taskCard(x){const j=jobView(x.ai_job);const msg=x.ai_job&&x.ai_job.message?x.ai_job.message:'后台会在合适的封盘窗口自动调度';return `<article class="task-card"><div class="task-head"><span class="task-title">${esc(x.name)} · AI</span><span class="state-badge ${j[1]}">${j[0]}</span></div><div class="task-body">${esc(msg)}</div><div class="task-time">目标期 ${esc((x.ai_job&&x.ai_job.target_period)||x.next_period||'—')} · ${ago(x.ai_job&&x.ai_job.updated_at)}</div></article>`}
function archiveItem(r){const label=r.top6_hit===true?['命中','good']:r.top6_hit===false?['未中','bad']:['待开奖','warn'];return `<article class="archive-item"><div><div class="archive-title">${esc(r.lottery_name)}</div><div class="archive-sub">目标期 ${esc(r.target_period)}</div></div><div><div class="archive-title">${r.source==='ai'?'云端 AI':'本机云端'} · 第 ${r.position+1} 名</div><div class="archive-sub">${esc(r.model)}</div></div><div class="archive-picks">六码 ${r.top6.join(' ')}</div><span class="state-badge ${label[1]}">${label[0]}</span></article>`}
function render(d){$('topStatus').textContent=d.health.worker==='ok'?'运行正常':'需要检查';$('topDot').style.background=d.health.worker==='ok'?'var(--good)':'var(--warn)';$('adminMetrics').innerHTML=`<div class="metric"><div class="metric-label">服务版本</div><div class="metric-value">${esc(d.health.version)}</div><div class="metric-foot">API ${esc(d.health.status)}</div></div><div class="metric"><div class="metric-label">数据库</div><div class="metric-value ${d.health.database==='ok'?'good':'bad'}">${esc(d.health.database)}</div><div class="metric-foot">前向档案正常</div></div><div class="metric"><div class="metric-label">后台任务</div><div class="metric-value ${d.health.worker==='ok'?'good':'warn'}">${esc(d.health.worker)}</div><div class="metric-foot">${ago(d.health.last_worker_heartbeat_epoch_ms)}</div></div><div class="metric"><div class="metric-label">当前模型</div><div class="metric-value">${d.ai.configured?esc(d.ai.model):'仅本机'}</div><div class="metric-foot">${d.ai.configured?'云端 AI 已配置':'未配置 Key'}</div></div>`;$('adminLotteries').innerHTML=d.lotteries.map(lotteryCard).join('');$('taskGrid').innerHTML=d.lotteries.map(taskCard).join('');$('runtimeLog').textContent=JSON.stringify({heartbeat:d.heartbeat,ai_errors:d.ai_errors},null,2);$('aiEnabled').checked=d.ai.enabled;$('aiEndpoint').value=d.ai.endpoint||'';$('aiModel').value=d.ai.model||'';$('aiTimeout').value=String(d.ai.timeout_seconds||120);$('keyHint').textContent='当前密钥：'+d.ai.api_key_hint;$('recordsList').innerHTML=d.records.length?d.records.map(archiveItem).join(''):'<div class="empty">暂无预测档案</div>';$('updateCard').innerHTML=`<div class="task-head"><span class="task-title">安全自动更新</span><span class="state-badge good">已支持</span></div><div class="task-body">VPS 每 5 分钟检查主分支；后端变化会先备份数据库、完成健康检查，失败自动回滚。</div><div class="task-time">App 单独更新不会重启云端服务</div>`}
async function load(){try{render(await api('/admin/api/state'))}catch(e){toast(e.message,true)}}
function payload(){return {enabled:$('aiEnabled').checked,endpoint:$('aiEndpoint').value.trim(),model:$('aiModel').value.trim(),api_key:$('aiKey').value||null,timeout_seconds:Number($('aiTimeout').value)}}
document.querySelectorAll('[data-preset]').forEach(b=>b.addEventListener('click',()=>{const p=b.dataset.preset;if(p==='deepseek-pro'){$('aiEndpoint').value='https://api.deepseek.com/chat/completions';$('aiModel').value='deepseek-v4-pro'}else if(p==='deepseek-flash'){$('aiEndpoint').value='https://api.deepseek.com/chat/completions';$('aiModel').value='deepseek-v4-flash'}else if(p==='deepseek-custom'){$('aiEndpoint').value='https://api.deepseek.com/chat/completions';$('aiModel').focus()}else if(p==='openai'){$('aiEndpoint').value='https://api.openai.com/v1/responses';$('aiModel').value=''}}));
$('saveAiBtn').onclick=async()=>{const b=$('saveAiBtn');b.disabled=true;try{await api('/admin/api/ai',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});$('aiKey').value='';toast('AI 配置已保存并立即生效');await load()}catch(e){toast(e.message,true)}finally{b.disabled=false}};
$('testAiBtn').onclick=async()=>{const b=$('testAiBtn');b.disabled=true;try{$('aiResult').className='result-box';$('aiResult').textContent='正在真实调用当前模型…';const d=await api('/admin/api/ai/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});$('aiResult').className='result-box success';$('aiResult').textContent=d.message+'\n耗时 '+d.latency_ms+' ms\n'+(d.models||[]).join('\n');toast('模型调用成功')}catch(e){$('aiResult').className='result-box error';$('aiResult').textContent=e.message;toast(e.message,true)}finally{b.disabled=false}};
$('modelsBtn').onclick=async()=>{const b=$('modelsBtn');b.disabled=true;try{$('aiResult').className='result-box';$('aiResult').textContent='正在读取模型列表…';const d=await api('/admin/api/ai/models',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});$('modelList').innerHTML=d.models.map(m=>`<option value="${esc(m)}"></option>`).join('');$('aiResult').className='result-box success';$('aiResult').textContent=d.message+'\n'+d.models.join('\n');toast('模型列表已读取')}catch(e){$('aiResult').className='result-box error';$('aiResult').textContent=e.message;toast(e.message,true)}finally{b.disabled=false}};
$('runBtn').onclick=async()=>{const b=$('runBtn');b.disabled=true;try{const d=await api('/admin/api/run',{method:'POST'});toast(d.message||'同步任务已开始');setTimeout(load,4500)}catch(e){toast(e.message,true)}finally{setTimeout(()=>b.disabled=false,2500)}};
$('passwordBtn').onclick=async()=>{try{await api('/admin/api/password',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:$('oldPassword').value,new_password:$('newPassword').value})});$('oldPassword').value='';$('newPassword').value='';toast('管理密码已更新')}catch(e){toast(e.message,true)}};
$('logoutBtn').onclick=async()=>{await api('/admin/api/logout',{method:'POST'}).catch(()=>{});location.href='/admin'};
load();setInterval(load,30000);
"""
    return _document("天机控制台", body, script)
