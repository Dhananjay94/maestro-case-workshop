"""Builds the Motor Claims Case workshop site (a landing page plus six documents) from Participant_Build_Guide.md.
Usage: python build_site.py <guide.md> <output_dir>"""
import html
import os
import re
import sys

import markdown

SRC, OUT = sys.argv[1], sys.argv[2]
md_all = open(SRC, encoding="utf-8").read()
SITE = "Motor Claims Case Workshop"

# ---------------------------------------------------------------- split the guide into its numbered sections
parts = re.split(r"\n(?=## )", md_all)
sections = {}
for p in parts:
    m = re.match(r"## (\d+)\. ", p)
    if m:
        sections[int(m.group(1))] = p
    elif p.startswith("## Contents"):
        pass
assert set(range(1, 13)).issubset(sections), sorted(sections)


def body(sec_no):
    txt = sections[sec_no]
    return txt.split("\n", 1)[1].strip("\n").rstrip("-").rstrip() + "\n"


def lift_bold_headings(txt, labels, level):
    for lab in labels:
        txt = re.sub(r"(?m)^\*\*" + re.escape(lab) + r"[^*\n]*\*\*\s*$", lambda m: "#" * level + " " + m.group(0).strip().strip("*").strip(), txt)
    return txt


# ---------------------------------------------------------------- document definitions
DOCS = [
    dict(slug="01-scenario", short="Business scenario", title="The business scenario", who="Everyone", time="10 min read",
         lead="Why this process exists, who is in it, and the three customers you will test with.", secs=[1]),
    dict(slug="02-setup", short="Import and set up", title="Import and set up", who="Participants", time="30 min to do",
         lead="Import one file, run Setup once, and open your solution. Nothing to install.", secs=[3]),
    dict(slug="03-building-blocks", short="Building blocks", title="What is already built for you", who="Participants", time="10 min read",
         lead="Every worker the case can call: what goes in, what comes out, and where it is used.", secs=[2]),
    dict(slug="04-business-rules", short="Business rules", title="The business rules", who="Participants", time="15 min with the exercise",
         lead="Seventeen rules from the business. Turn each into something the case does.", secs=[4]),
    dict(slug="05-build-guide", short="Build guide", title="Build it, step by step", who="Participants", time="3 to 5 hours, in parts",
         lead="Five ideas first, then the build: happy path, then each exception, then the extras. Each step says why.", secs=[5, 6]),
    dict(slug="06-reference", short="Quick reference", title="Quick reference", who="Everyone", time="Look-up",
         lead="Variables, every rule on one page, claim statuses, the test matrix, troubleshooting and a glossary.", secs=[7, 8, 9, 10, 11, 12]),
]

# extra content for the setup page (from the participant setup checklist)
SETUP_EXTRA = """
## Ready check

Tick these off as you go. Your ticks stay in this browser.

<ul class="checks">
<li><label><input type="checkbox" data-key="rc1"> I imported <code>MotorClaimsWorkshop_Setup.uis</code> and can see <strong>SetupWorkshop</strong> in Studio Web</label></li>
<li><label><input type="checkbox" data-key="rc2"> I ran it with <code>InstallWorkshop</code> and it ended with <strong>Done</strong></label></li>
<li><label><input type="checkbox" data-key="rc3"> I wrote down my Intake App address from the last line</label></li>
<li><label><input type="checkbox" data-key="rc4"> <strong>MotorInsuranceClaimManagement</strong> is in my Studio Web, and <code>MyClaimsCase</code> shows one trigger circle</label></li>
<li><label><input type="checkbox" data-key="rc5"> I created a Gmail and a Data Fabric connection</label></li>
<li><label><input type="checkbox" data-key="rc6"> I ran <code>RegisterClaim</code> for Rahul and can Debug a case with his claim</label></li>
</ul>

## If something goes wrong

| What you see | What to do |
|---|---|
| The screen looks stuck | Run Setup again with **Action** = `Status`. It prints how far Setup got and says FINISHED or NOT FINISHED |
| Setup says the name cannot be used | Run Setup with **DeploymentName** set to a new name, for example `ClaimsSolutionNew`, and use that name later |
| It says `FAILED` | Read the line after FAILED. Fix what it names, or send the whole text to the facilitator |
| Debug cannot find an app or worker | Delete the solution **MotorInsuranceClaimManagement** in Studio Web and run Setup again |
| You want to start over | Delete the solution in Studio Web, then **Uninstall** the deployment in Orchestrator > Solutions > Deployments (never delete the folder by hand), then run Setup again |

> **Stuck?** Send the facilitator the full text of any error. Setup is safe to run again.
"""

# ---------------------------------------------------------------- CSS and JS shared by every page
FONTS = "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
CSS = r"""
/* Layout concept: a case folder. A rail of numbered documents on the left (the true reading order), one calm column of text on the right. */
:root{
  --bg:#F4F7F9; --surface:#FFFFFF; --surface-2:#EAF0F4; --ink:#13212B; --ink-2:#4C5F6E; --line:#D5DDE4; --line-2:#B9C5CF;
  --accent:#0A6C85; --accent-ink:#FFFFFF; --accent-soft:#D9EEF3;
  --why:#2557C4; --why-bg:#E4ECFB; --check:#17794A; --check-bg:#DFF2E7; --stuck:#9A5B00; --stuck-bg:#FBEED2; --trap:#B0281F; --trap-bg:#FBE4E1;
  --code-bg:#0F1C26; --code-ink:#E4EDF3; --code-line:#233646; --shadow:0 1px 2px rgba(19,33,43,.06),0 6px 18px rgba(19,33,43,.06);
  --f-display:"Bricolage Grotesque","Segoe UI",system-ui,sans-serif; --f-body:"IBM Plex Sans","Segoe UI",system-ui,sans-serif; --f-mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0D151B; --surface:#131E27; --surface-2:#1A2833; --ink:#E5EDF3; --ink-2:#9DB0BE; --line:#26384A; --line-2:#385068;
  --accent:#55B8D1; --accent-ink:#06222B; --accent-soft:#12323C;
  --why:#8DB0FF; --why-bg:#18274A; --check:#6BD39B; --check-bg:#12301F; --stuck:#F0B25C; --stuck-bg:#3A2A0B; --trap:#FF9A90; --trap-bg:#40181A;
  --code-bg:#0A1218; --code-ink:#DCE8F0; --code-line:#1E2F3D; --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 18px rgba(0,0,0,.35); color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0D151B; --surface:#131E27; --surface-2:#1A2833; --ink:#E5EDF3; --ink-2:#9DB0BE; --line:#26384A; --line-2:#385068;
  --accent:#55B8D1; --accent-ink:#06222B; --accent-soft:#12323C;
  --why:#8DB0FF; --why-bg:#18274A; --check:#6BD39B; --check-bg:#12301F; --stuck:#F0B25C; --stuck-bg:#3A2A0B; --trap:#FF9A90; --trap-bg:#40181A;
  --code-bg:#0A1218; --code-ink:#DCE8F0; --code-line:#1E2F3D; --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 18px rgba(0,0,0,.35); color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--f-body);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-underline-offset:3px}
a:focus-visible,button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:var(--surface);padding:8px 12px;z-index:50}
.topbar{position:sticky;top:env(safe-area-inset-top,0px);z-index:30;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.topbar-in{max-width:1240px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:14px}
.brand{font:700 17px/1 var(--f-display);color:var(--ink);text-decoration:none;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
.brand i{display:inline-block;width:12px;height:12px;border-radius:3px;background:var(--accent);transform:rotate(45deg)}
.spacer{flex:1}
.btn{font:500 14px/1 var(--f-body);color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:9px 12px;cursor:pointer}
.btn:hover{border-color:var(--line-2)}
.menu-btn{display:none}
.shell{max-width:1240px;margin:0 auto;padding:28px 20px 80px;display:grid;grid-template-columns:268px minmax(0,1fr);gap:44px}
.rail{position:sticky;top:76px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;padding-right:6px}
.rail h2{font:600 12px/1 var(--f-body);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2);margin:0 0 10px}
.docs{list-style:none;margin:0 0 26px;padding:0;display:flex;flex-direction:column;gap:2px}
.docs a{display:flex;gap:10px;align-items:baseline;padding:8px 10px;border-radius:8px;color:var(--ink);text-decoration:none;font-weight:500;font-size:15px}
.docs a b{font:500 12px var(--f-mono);color:var(--ink-2);min-width:18px}
.docs a:hover{background:var(--surface-2)}
.docs a[aria-current="page"]{background:var(--accent-soft);color:var(--ink)}
.docs a[aria-current="page"] b{color:var(--accent)}
.toc{list-style:none;margin:0;padding:0;border-left:2px solid var(--line)}
.toc a{display:block;padding:5px 12px;margin-left:-2px;border-left:2px solid transparent;color:var(--ink-2);text-decoration:none;font-size:14px;line-height:1.4}
.toc a:hover{color:var(--ink)}
.toc a.on{color:var(--ink);border-left-color:var(--accent);font-weight:500}
.toc .l3 a{padding-left:24px;font-size:13px}
main{min-width:0}
.eyebrow{font:600 12px/1 var(--f-body);letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin:0 0 12px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.eyebrow span+span::before{content:"";display:inline-block;width:4px;height:4px;border-radius:50%;background:var(--line-2);margin-right:10px;vertical-align:middle}
h1{font:700 clamp(30px,4.4vw,46px)/1.08 var(--f-display);letter-spacing:-.02em;margin:0 0 14px;text-wrap:balance}
.lead{font-size:18px;line-height:1.55;color:var(--ink-2);max-width:60ch;margin:0 0 30px}
.content{max-width:820px}
.content h2{font:650 clamp(23px,2.6vw,29px)/1.2 var(--f-display);letter-spacing:-.015em;margin:48px 0 14px;padding-top:6px;text-wrap:balance}
.content h3{font:650 21px/1.28 var(--f-display);letter-spacing:-.01em;margin:38px 0 10px;text-wrap:balance;display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.content h4{font:650 17.5px/1.3 var(--f-display);margin:30px 0 8px;padding:8px 12px;background:var(--surface-2);border-radius:8px;border-left:3px solid var(--accent)}
.content h2 a.anchor,.content h3 a.anchor{color:var(--line-2);text-decoration:none;font-weight:400;margin-left:8px;opacity:0}
.content h2:hover a.anchor,.content h3:hover a.anchor{opacity:1}
.chip{font:500 12px/1 var(--f-mono);background:var(--accent-soft);color:var(--accent);padding:5px 8px;border-radius:999px;white-space:nowrap}
.content p{margin:0 0 14px;max-width:70ch}
.content ul,.content ol{margin:0 0 16px;padding-left:22px;max-width:70ch}
.content li{margin:4px 0}
.content hr{border:0;border-top:1px solid var(--line);margin:36px 0}
code{font:500 .88em var(--f-mono);background:var(--surface-2);padding:.12em .38em;border-radius:5px;overflow-wrap:anywhere}
pre{position:relative;margin:0 0 18px;background:var(--code-bg);color:var(--code-ink);border:1px solid var(--code-line);border-radius:10px;padding:16px 18px;overflow-x:auto;font:400 13.5px/1.6 var(--f-mono)}
pre code{background:none;padding:0;font:inherit;overflow-wrap:normal;color:inherit}
.copy{position:absolute;top:8px;right:8px;font:500 12px var(--f-body);color:var(--code-ink);background:rgba(255,255,255,.08);border:1px solid var(--code-line);border-radius:6px;padding:5px 9px;cursor:pointer}
.copy:hover{background:rgba(255,255,255,.16)}
.tablewrap{overflow-x:auto;margin:0 0 20px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14.5px;line-height:1.5}
th{font:600 12.5px/1.3 var(--f-body);letter-spacing:.04em;text-transform:uppercase;color:var(--ink-2);background:var(--surface-2);text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:10px 14px;border-top:1px solid var(--line);vertical-align:top;min-width:96px}
tr:first-child td{border-top:0}
td code{white-space:normal;font-size:.8em;overflow-wrap:break-word}
blockquote{margin:0 0 18px;padding:13px 16px;background:var(--surface-2);border-radius:10px;border-left:4px solid var(--line-2);max-width:78ch}
blockquote p{margin:0 0 8px}blockquote p:last-child{margin:0}
blockquote.why{background:var(--why-bg);border-left-color:var(--why)}blockquote.why>p:first-child>strong:first-child{color:var(--why)}
blockquote.check{background:var(--check-bg);border-left-color:var(--check)}blockquote.check>p:first-child>strong:first-child{color:var(--check)}
blockquote.stuck{background:var(--stuck-bg);border-left-color:var(--stuck)}blockquote.stuck>p:first-child>strong:first-child{color:var(--stuck)}
blockquote.trap{background:var(--trap-bg);border-left-color:var(--trap)}blockquote.trap>p:first-child>strong:first-child{color:var(--trap)}
.checks{list-style:none;padding:0!important;display:grid;gap:8px;margin:0 0 20px}
.checks li{margin:0}
.checks label{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;background:var(--surface);border:1px solid var(--line);border-radius:10px;cursor:pointer}
.checks input{margin-top:4px;width:18px;height:18px;accent-color:var(--accent)}
.checks input:checked+*{opacity:.6}
.pager{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:56px;max-width:820px}
.pager a{display:block;padding:16px 18px;background:var(--surface);border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--ink);box-shadow:var(--shadow)}
.pager a:hover{border-color:var(--accent)}
.pager small{display:block;font:600 11.5px/1 var(--f-body);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2);margin-bottom:8px}
.pager .next{text-align:right;grid-column:2}
.figure{margin:8px 0 28px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px;overflow-x:auto}
.figure svg{display:block;min-width:720px;width:100%;height:auto}
.figure figcaption{font-size:13.5px;color:var(--ink-2);padding:10px 8px 2px}
.n rect{fill:var(--surface);stroke:var(--line-2);stroke-width:1.5}.n text{fill:var(--ink);font:600 15px var(--f-body)}.n .s{fill:var(--ink-2);font:400 12px var(--f-body)}
.n.sec rect{fill:var(--accent-soft);stroke:var(--accent)}.n.end rect{fill:var(--trap-bg);stroke:var(--trap)}.n.end text{fill:var(--ink)}
.b circle{fill:var(--accent);stroke:var(--surface);stroke-width:2}.b text{fill:var(--accent-ink);font:700 12px var(--f-body)}.b.r circle{fill:var(--trap)}.b.r text{fill:#fff}
.legend{list-style:none;margin:6px 8px 4px;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:6px 24px;font-size:14px;color:var(--ink-2)}.legend li{display:flex;gap:10px;align-items:baseline}.legend b{display:inline-grid;place-items:center;min-width:22px;height:22px;border-radius:50%;background:var(--accent);color:var(--accent-ink);font:700 12px var(--f-body)}.legend .r b{background:var(--trap);color:#fff}
.road{stroke:var(--ink-2);stroke-width:2;fill:none}.det{stroke:var(--accent);stroke-width:2;fill:none}.ret{stroke:var(--accent);stroke-width:2;fill:none;stroke-dasharray:6 5}.den{stroke:var(--trap);stroke-width:2;fill:none}
.lbl{fill:var(--ink-2);font:500 12px var(--f-body)}.lbl.a{fill:var(--accent)}.lbl.r{fill:var(--trap)}
.hero{display:grid;gap:26px;padding:8px 0 10px}
.facts{display:flex;gap:10px 28px;flex-wrap:wrap;margin:0 0 6px;padding:0;list-style:none}
.facts li{display:flex;flex-direction:column;gap:2px}.facts b{font:700 28px/1 var(--f-display);letter-spacing:-.02em}.facts span{font-size:13px;color:var(--ink-2)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px;margin:12px 0 8px}
.card{display:flex;flex-direction:column;gap:8px;padding:18px;background:var(--surface);border:1px solid var(--line);border-radius:14px;text-decoration:none;color:var(--ink);box-shadow:var(--shadow);min-width:0}
.card:hover{border-color:var(--accent)}
.card .no{font:500 12px var(--f-mono);color:var(--accent)}
.card h3{font:650 20px/1.2 var(--f-display);margin:0;letter-spacing:-.01em}
.card p{margin:0;color:var(--ink-2);font-size:15px;line-height:1.5}
.card .meta{margin-top:auto;padding-top:6px;font-size:13px;color:var(--ink-2);display:flex;gap:8px;flex-wrap:wrap}
.card .meta span{background:var(--surface-2);padding:4px 8px;border-radius:999px}
.sec-t{font:650 24px/1.2 var(--f-display);letter-spacing:-.015em;margin:44px 0 12px}
.path{width:100%;max-width:820px}
@media (max-width:920px){
  .shell{grid-template-columns:minmax(0,1fr);gap:20px;padding-top:18px}
  .rail{position:static;max-height:none;display:none}
  .rail.open{display:block;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px}
  .menu-btn{display:inline-block}
  .pager{grid-template-columns:1fr}.pager .next{grid-column:1}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

JS = r"""
(function(){
  function get(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function set(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  var root=document.documentElement,t=get('mc-theme'); if(t==='dark'||t==='light'){root.setAttribute('data-theme',t)}
  var tb=document.getElementById('theme');
  if(tb){tb.addEventListener('click',function(){var cur=root.getAttribute('data-theme');if(!cur){cur=(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light'}
    var nx=cur==='dark'?'light':'dark';root.setAttribute('data-theme',nx);set('mc-theme',nx);tb.textContent=nx==='dark'?'Light mode':'Dark mode'});
    var c=root.getAttribute('data-theme')||((window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light');tb.textContent=c==='dark'?'Light mode':'Dark mode'}
  var mb=document.getElementById('menu'),rail=document.getElementById('rail');
  if(mb&&rail){mb.addEventListener('click',function(){var o=rail.classList.toggle('open');mb.setAttribute('aria-expanded',o?'true':'false')})}
  document.querySelectorAll('pre').forEach(function(pre){
    if(pre.classList.contains('nocopy'))return;
    var b=document.createElement('button');b.className='copy';b.type='button';b.textContent='Copy';
    b.addEventListener('click',function(){
      var txt=pre.innerText.replace(/\sCopy$/,'');
      function done(ok){b.textContent=ok?'Copied':'Select and copy';setTimeout(function(){b.textContent='Copy'},1600)}
      try{navigator.clipboard.writeText(txt).then(function(){done(true)},function(){sel();done(false)})}catch(e){sel();done(false)}
      function sel(){var r=document.createRange();r.selectNodeContents(pre.querySelector('code')||pre);var s=getSelection();s.removeAllRanges();s.addRange(r)}
    });pre.appendChild(b)});
  document.querySelectorAll('input[data-key]').forEach(function(i){
    var k='mc-chk-'+location.pathname+'-'+i.getAttribute('data-key');i.checked=get(k)==='1';
    i.addEventListener('change',function(){set(k,i.checked?'1':'0')})});
  var links=[].slice.call(document.querySelectorAll('.toc a'));
  if(links.length&&'IntersectionObserver' in window){
    var map={};links.forEach(function(a){map[a.getAttribute('href').slice(1)]=a});
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){links.forEach(function(a){a.classList.remove('on')});var a=map[e.target.id];if(a)a.classList.add('on')}})},{rootMargin:'-80px 0px -70% 0px'});
    document.querySelectorAll('.content h2[id],.content h3[id]').forEach(function(h){io.observe(h)})}
})();
"""


# ---------------------------------------------------------------- markdown to html
SPLIT_CALLOUTS = False  # the Setup page writes each box as its own quote; the converter merges neighbours, so split them again


def callouts(h):
    def repl(m):
        inner = m.group(1)
        if SPLIT_CALLOUTS:
            parts = re.split(r"(?=<p><strong>(?:Check|Why|Stuck|If )[^<]*</strong>)", inner)
            parts = [x for x in parts if x.strip()]
            if len(parts) > 1:
                return "".join(repl2(x) for x in parts)
        return repl2(inner)

    def repl2(inner):
        first = re.match(r"\s*<p><strong>([^<]*)</strong>", inner)
        kind = ""
        if first:
            t = first.group(1).lower()
            if t.startswith("why"):
                kind = "why"
            elif t.startswith("check"):
                kind = "check"
            elif t.startswith("stuck") or (SPLIT_CALLOUTS and t.startswith("if ")):
                kind = "stuck"
            elif t.startswith(("two traps", "do not rename", "not used")):
                kind = "trap" if not t.startswith("not used") else "stuck"
        return f'<blockquote class="{kind}">{inner}</blockquote>' if kind else f"<blockquote>{inner}</blockquote>"
    return re.sub(r"<blockquote>(.*?)</blockquote>", repl, h, flags=re.S)


def tables(h):
    return re.sub(r"(<table>.*?</table>)", r'<div class="tablewrap">\1</div>', h, flags=re.S)


def chips(h):
    return re.sub(r"(<h[23][^>]*>)(.*?)\((\d+ min)\)(.*?)(</h[23]>)", lambda m: f'{m.group(1)}{m.group(2).rstrip()}{m.group(4)} <span class="chip">{m.group(3)}</span>{m.group(5)}', h)


def render(md_text):
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"], extension_configs={"toc": {"permalink": "#", "permalink_class": "anchor", "toc_depth": "2-3"}})
    h = md.convert(md_text)
    h = chips(tables(callouts(h)))
    toc_items = []
    for m in re.finditer(r'<h([23]) id="([^"]+)">(.*?)</h\1>', h, flags=re.S):
        txt = re.sub(r"<[^>]+>", "", m.group(3)).replace("#", "").strip()
        txt = re.sub(r"\s*\d+ min$", "", txt)
        toc_items.append((int(m.group(1)), m.group(2), txt))
    return h, toc_items


# ---------------------------------------------------------------- diagrams
def journey_svg():
    def node(cx, cy, w, label, sub="", cls=""):
        x, y = cx - w / 2, cy - 34
        s = f'<g class="n {cls}"><rect x="{x}" y="{y}" width="{w}" height="68" rx="12"/><text x="{cx}" y="{cy - 3}" text-anchor="middle">{label}</text>'
        if sub:
            s += f'<text class="s" x="{cx}" y="{cy + 17}" text-anchor="middle">{sub}</text>'
        return s + "</g>"

    def badge(x, y, n, cls="b"):
        return f'<g class="{cls}"><circle cx="{x}" cy="{y}" r="11"/><text x="{x}" y="{y + 4.5}" text-anchor="middle">{n}</text></g>'

    main = [(95, "Intake", "documents, policy"), (275, "Assessment", "fraud score, damage"), (455, "Review", "adjuster decides"), (635, "Settlement", "calculate, approve, pay"), (815, "Closure", "packet, notify")]
    svg = ['<svg viewBox="0 0 910 372" role="img" aria-label="Claim journey: five main stages with three exception stages below" xmlns="http://www.w3.org/2000/svg">',
           '<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>']
    svg.append('<text class="lbl" x="20" y="22">THE MAIN ROAD</text>')
    for i in range(4):
        svg.append(f'<path class="road" d="M{main[i][0] + 76} 70 H{main[i + 1][0] - 76}" marker-end="url(#ah)"/>')
    for cx, lab, sub in main:
        svg.append(node(cx, 70, 150, lab, sub))
    svg.append('<text class="lbl" x="20" y="232">EXCEPTIONS</text>')
    svg.append(node(185, 300, 190, "Pending Customer", "waits for the customer", "sec"))
    svg.append(node(430, 300, 190, "Fraud Investigation", "a person decides", "sec"))
    svg.append(node(735, 300, 190, "Denied", "ends the case", "end"))
    # forward detours
    svg.append('<path class="det" d="M70 104 L130 266" marker-end="url(#ah)"/>' + badge(100, 185, 1))
    svg.append('<path class="det" d="M470 104 L255 266" marker-end="url(#ah)"/>' + badge(392, 150, 2))
    svg.append('<path class="det" d="M255 104 L385 266" marker-end="url(#ah)"/>' + badge(290, 140, 3))
    # returns (dashed)
    svg.append('<path class="ret" d="M160 266 L118 104" marker-end="url(#ah)"/>' + badge(140, 200, 4))
    svg.append('<path class="ret" d="M440 266 L300 104" marker-end="url(#ah)"/>' + badge(372, 200, 5))
    # to denied (red)
    svg.append('<path class="den" d="M528 300 H636" marker-end="url(#ah)"/>' + badge(582, 300, 6, "b r"))
    svg.append('<path class="den" d="M650 104 L705 266" marker-end="url(#ah)"/>' + badge(678, 185, 7, "b r"))
    svg.append('<text class="lbl r" x="905" y="352" text-anchor="end">also into Denied: invalid policy (Intake), adjuster rejects (Review)</text>')
    svg.append("</svg>")
    return "".join(svg)


JOURNEY_LEGEND = ('<ol class="legend"><li><b>1</b> Intake to Pending Customer: documents missing</li><li><b>2</b> Review to Pending Customer: the adjuster asks for information</li>'
                  '<li><b>3</b> Assessment to Fraud Investigation: high fraud risk</li><li><b>4</b> Pending Customer back to where it came from, once the customer replies</li>'
                  '<li><b>5</b> Fraud Investigation back to Assessment: cleared</li><li class="r"><b>6</b> Fraud Investigation to Denied: fraud confirmed</li>'
                  '<li class="r"><b>7</b> Settlement to Denied: the senior approver rejects</li></ol>')


def detour_svg():
    return ('<svg viewBox="0 0 760 210" role="img" aria-label="A detour has two matching halves" xmlns="http://www.w3.org/2000/svg">'
            '<defs><marker id="ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>'
            '<g class="n"><rect x="20" y="30" width="300" height="150" rx="14"/><text x="170" y="62" text-anchor="middle">ORIGIN stage</text>'
            '<text class="s" x="170" y="96" text-anchor="middle">Exit rule (the first half)</text><text class="s" x="170" y="118" text-anchor="middle">after the deciding task, if the condition is true,</text>'
            '<text class="s" x="170" y="138" text-anchor="middle">leave and go to the target</text><text class="s" x="170" y="160" text-anchor="middle">Marks stage complete: off</text></g>'
            '<g class="n sec"><rect x="440" y="30" width="300" height="150" rx="14"/><text x="590" y="62" text-anchor="middle">TARGET stage</text>'
            '<text class="s" x="590" y="96" text-anchor="middle">Entry rule (the second half)</text><text class="s" x="590" y="118" text-anchor="middle">type: Selected stage exited</text>'
            '<text class="s" x="590" y="138" text-anchor="middle">stage: the origin. The same condition.</text><text class="s" x="590" y="160" text-anchor="middle">Interrupting: on</text></g>'
            '<path class="det" d="M322 105 H436" marker-end="url(#ah2)"/><text class="lbl a" x="380" y="96" text-anchor="middle">same</text><text class="lbl a" x="380" y="126" text-anchor="middle">condition</text>'
            '</svg>')


# ---------------------------------------------------------------- page assembly
def head(title, desc):
    return (f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{html.escape(title)}</title>'
            f'<meta name="description" content="{html.escape(desc)}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="{FONTS}"><style>{CSS}</style>')


def topbar(home=False):
    return (f'<a class="skip" href="#main">Skip to content</a><header class="topbar"><div class="topbar-in"><a class="brand" href="index.html"><i></i>{SITE}</a><span class="spacer"></span>'
            '<button class="btn menu-btn" id="menu" type="button" aria-expanded="false" aria-controls="rail">Contents</button><button class="btn" id="theme" type="button">Dark mode</button></div></header>')


def rail(cur, toc):
    docs = "".join(f'<li><a href="{d["slug"]}.html"{" aria-current=\"page\"" if d["slug"] == cur else ""}><b>{i + 1}</b>{html.escape(d["short"])}</a></li>' for i, d in enumerate(DOCS))
    t = ""
    if toc:
        t = '<h2>On this page</h2><ul class="toc">' + "".join(f'<li class="l{lvl}"><a href="#{id_}">{html.escape(txt)}</a></li>' for lvl, id_, txt in toc) + "</ul>"
    home = '<li><a href="index.html"><b>0</b>Overview</a></li>'
    return f'<nav class="rail" id="rail" aria-label="Documents"><h2>Documents</h2><ul class="docs">{home}{docs}</ul>{t}</nav>'


def pager(idx):
    prev = DOCS[idx - 1] if idx > 0 else None
    nxt = DOCS[idx + 1] if idx < len(DOCS) - 1 else None
    a = ""
    if prev:
        a += f'<a class="prev" href="{prev["slug"]}.html"><small>Previous</small>{html.escape(prev["title"])}</a>'
    else:
        a += '<a class="prev" href="index.html"><small>Back to</small>Overview</a>'
    if nxt:
        a += f'<a class="next" href="{nxt["slug"]}.html"><small>Next</small>{html.escape(nxt["title"])}</a>'
    return f'<div class="pager">{a}</div>'


NL = chr(10)
LIST_RE = re.compile(r"\s*(- |\d+\. )")
NUM_HEAD_RE = re.compile(r"^(#{2,5}) \d+\.\d+ ")


def prep(txt):
    """Make the guide's Markdown safe for a strict converter: blank line before lists, tables and quotes; plain section numbers dropped."""
    out, fence, prev = [], False, ""
    for line in txt.split(NL):
        if line.strip().startswith("```"):
            fence = not fence
            out.append(line)
            prev = line
            continue
        if not fence:
            is_list = bool(LIST_RE.match(line))
            prev_list = bool(LIST_RE.match(prev)) or prev.startswith("   ")
            if prev.strip() and ((is_list and not prev_list and not prev.lstrip().startswith(("|", ">", "#"))) or (line.startswith("|") and not prev.startswith("|")) or (line.startswith(">") and not prev.startswith(">"))):
                out.append("")
            m = NUM_HEAD_RE.match(line)
            if m:
                line = m.group(1) + " " + line[m.end():]
        out.append(line)
        prev = line
    return NL.join(out)


def normalise_levels(txt):
    levels = [len(m.group(1)) for m in re.finditer(r"(?m)^(#{2,6}) ", re.sub(r"```.*?```", "", txt, flags=re.S))]
    if levels and min(levels) >= 3:
        shift = min(levels) - 2
        txt = re.sub(r"(?m)^(#{3,6}) ", lambda m: "#" * (len(m.group(1)) - shift) + " ", txt)
    return txt


def doc_markdown(d):
    out = []
    for n in d["secs"]:
        t = body(n)
        if n == 1:
            t = lift_bold_headings(t, ["The people", "The three customers you will test with", "The journey of a claim"], 2)
            t = re.sub(r"```" + NL + r" Customer registers claim.*?```", "<!--JOURNEY-->", t, flags=re.S)
        if n == 2:
            t = lift_bold_headings(t, ["Agents", "Functions", "API workflows", "Human task screens", "Connectors"], 4)
        if n == 5:
            t = re.sub(r"```" + NL + r" ORIGIN stage.*?```", "<!--DETOUR-->", t, flags=re.S)
            t = lift_bold_headings(t, ["5. The detour pattern"], 3)
            t = "### Five ideas you need before you start" + NL + NL + t
        t = normalise_levels(prep(t))
        if n in (7, 8, 9, 10, 11, 12):
            title = re.sub(r"^## \d+\. ", "", sections[n].split(NL, 1)[0])
            t = "## " + title + NL + NL + t
        if n == 3:
            t += NL + prep(SETUP_EXTRA)
        out.append(t)
    return (NL + NL).join(out)


def build_doc(i, d):
    txt = doc_markdown(d)
    h, toc = render(txt)
    h = h.replace("<!--JOURNEY-->", f'<figure class="figure">{journey_svg()}<figcaption>Solid arrows leave a stage early (a detour). Dashed arrows return to where the claim came from. Red arrows end in a denial.</figcaption>{JOURNEY_LEGEND}</figure>')
    h = h.replace("<!--DETOUR-->", f'<figure class="figure">{detour_svg()}</figure>')
    h = h.replace("<p><!--JOURNEY--></p>", "").replace("<p><!--DETOUR--></p>", "")
    eyebrow = f'<p class="eyebrow"><span>Document {i + 1} of {len(DOCS)}</span><span>{html.escape(d["who"])}</span><span>{html.escape(d["time"])}</span></p>'
    main = f'<main id="main">{eyebrow}<h1>{html.escape(d["title"])}</h1><p class="lead">{html.escape(d["lead"])}</p><div class="content">{h}</div>{pager(i)}</main>'
    page = (f'<!doctype html><html lang="en"><head>{head(d["title"] + " | " + SITE, d["lead"])}</head><body>{topbar()}'
            f'<div class="shell">{rail(d["slug"], toc)}{main}</div><script>{JS}</script></body></html>')
    return page


def build_index():
    setup_card = ('<a class="card" href="Setup_Guide.html"><span class="no">Setup guide</span><h3>Get ready and run Rahul&#8217;s claim</h3>'
                  '<p>Run Setup, configure your Gmail and Data Fabric connections, and run a finished claim end to end.</p>'
                  '<div class="meta"><span>Everyone</span><span>25 min</span></div></a>')
    cards = setup_card + "".join(
        f'<a class="card" href="{d["slug"]}.html"><span class="no">Document {i + 1}</span><h3>{html.escape(d["short"])}</h3><p>{html.escape(d["lead"])}</p>'
        f'<div class="meta"><span>{html.escape(d["who"])}</span><span>{html.escape(d["time"])}</span></div></a>' for i, d in enumerate(DOCS))
    path = [
        ("MyClaimsCase (empty)", "Case settings", "10 min"), ("1_HappyPath", "Five stages in a line", "90 min"), ("2_PendingCustomer", "Missing documents, event wait", "45 min"),
        ("3_Denied", "Three ways to a no", "35 min"), ("4_FraudInvestigation", "Cleared or confirmed", "30 min"), ("5_Complete", "Record updates, emails, SLAs", "80 min")]
    rows = "".join(f"<tr><td><code>{a}</code></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in path)
    body_html = (f'<a class="skip" href="#main">Skip to content</a><header class="topbar"><div class="topbar-in"><a class="brand" href="index.html"><i></i>{SITE}</a><span class="spacer"></span>'
                 '<button class="btn" id="theme" type="button">Dark mode</button></div></header>'
                 f'<div class="shell" style="grid-template-columns:minmax(0,1fr)"><main id="main"><div class="hero"><div><p class="eyebrow"><span>Maestro Case</span><span>Half-day workshop</span></p>'
                 '<h1>Build a motor insurance claims case, end to end</h1>'
                 '<p class="lead">A claim goes from a customer registering it to a payment or a denial. AI agents read the documents, code checks the rules, people decide only when they must. You build the conductor; the workers are ready.</p>'
                 '<ul class="facts"><li><b>8</b><span>stages</span></li><li><b>24</b><span>tasks</span></li><li><b>17</b><span>business rules</span></li><li><b>3</b><span>test customers</span></li><li><b>6</b><span>example cases to jump in from</span></li></ul></div>'
                 f'<figure class="figure">{journey_svg()}<figcaption>The case you will build. Solid arrows leave a stage early (a detour). Dashed arrows return to where the claim came from. Red arrows end in a denial.</figcaption>{JOURNEY_LEGEND}</figure></div>'
                 '<h2 class="sec-t">Start here</h2>'
                 f'<div class="cards">{cards}</div>'
                 '<h2 class="sec-t">The build path</h2><p class="lead" style="margin-bottom:14px">You build in <b>MyClaimsCase</b>. Each step has a finished example case in the same solution to compare with. If you fall behind, open it and carry on.</p>'
                 f'<div class="path"><div class="tablewrap"><table><thead><tr><th>Example case</th><th>You add</th><th>First time</th></tr></thead><tbody>{rows}</tbody></table></div></div>'
                 '<p style="color:var(--ink-2);font-size:14px;max-width:70ch">Times are estimates for a first build. A half-day session covers the happy path, Pending Customer and Denied. The rest is for a faster pace or homework.</p>'
                 f'</main></div><script>{JS}</script>')
    frag = f'<title>{SITE}</title><meta name="description" content="Build a motor insurance claims case in UiPath Maestro: scenario, setup, building blocks, business rules, a step-by-step build guide and a quick reference."><link rel="stylesheet" href="{FONTS}"><style>{CSS}</style>'
    return frag, body_html


def build_setup_page():
    """The standalone Setup guide (WorkshopKit/Setup_Guide.md) as one page in the same look."""
    md_path = os.path.join(os.path.dirname(os.path.abspath(SRC)), "Setup_Guide.md")
    if not os.path.exists(md_path):
        return None
    global SPLIT_CALLOUTS
    SPLIT_CALLOUTS = True
    raw = open(md_path, encoding="utf-8").read()
    first, rest = raw.split(NL, 1)
    title = first.lstrip("# ").strip()
    h, toc = render(normalise_levels(prep(rest)))
    toc = [t for t in toc if t[0] <= 3]
    lead = "Run Setup once, configure your Gmail and Data Fabric connections, and run Rahul's claim end to end. Building and deploying come later in the workshop."
    nav = '<nav class="rail" id="rail" aria-label="On this page"><h2>On this page</h2><ul class="toc">' + "".join(
        f'<li class="l{lvl}"><a href="#{id_}">{html.escape(txt)}</a></li>' for lvl, id_, txt in toc) + "</ul></nav>"
    eyebrow = '<p class="eyebrow"><span>Setup guide</span><span>Everyone</span><span>About 25 minutes</span></p>'
    main = f'<main id="main">{eyebrow}<h1>{html.escape(title)}</h1><p class="lead">{html.escape(lead)}</p><div class="content">{h}</div></main>'
    top = topbar()
    return (f'<!doctype html><html lang="en"><head>{head(title + " | " + SITE, lead)}</head><body>{top}'
            f'<div class="shell">{nav}{main}</div><script>{JS}</script></body></html>')



os.makedirs(OUT, exist_ok=True)
for i, d in enumerate(DOCS):
    open(os.path.join(OUT, d["slug"] + ".html"), "w", encoding="utf-8").write(build_doc(i, d))
hd, bd = build_index()
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(hd + bd)
sp = build_setup_page()
if sp:
    open(os.path.join(OUT, "Setup_Guide.html"), "w", encoding="utf-8").write(sp)
print("built", [d["slug"] + ".html" for d in DOCS], "+ index.html" + (" + Setup_Guide.html" if sp else ""))
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, "KB")
