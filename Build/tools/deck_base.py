"""Builds the workshop slide deck (one self-contained HTML file).
Usage: python build_deck.py <output_dir>   -> writes Maestro_Case_Workshop_Deck.html (offline copy) and _artifact_index.html (for publishing)."""
import base64
import html
import os
import sys

OUT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = "data:image/jpeg;base64," + base64.b64encode(open(os.path.join(HERE, "speaker.jpg"), "rb").read()).decode()
TITLE = "Mastering UiPath Maestro Case Management"
esc = html.escape

# ------------------------------------------------------------------ styling
CSS = r"""
/* Layout concept: a fixed 16:9 stage scaled to the screen. Dark charcoal ground, one ribbon line that runs through the deck, coloured squares as section markers. */
:root{
  --bg:#182026; --bg2:#1F2B33; --bg3:#2A3945; --ink:#FFFFFF; --ink2:#C4CED6; --ink3:#8696A3; --line:#33444F; --page:#0A0F13; --silo:rgba(31,43,51,.75); --rsec:#16363D; --rfr:#2C1B2C; --rdn:#3A1F1D; --failbg:#4A1E1B; --corner:#3B4955;
  --orange:#FA4616; --teal:#0BA2B3; --blue:#1E6482; --magenta:#8B288A; --coral:#FA7678; --ok:#3CCB8E;
  --font:Arial,"Helvetica Neue",Helvetica,sans-serif; --mono:Consolas,"Courier New",monospace; color-scheme:dark;
}
*{box-sizing:border-box}
html,body{height:100%;margin:0;background:var(--page);color:var(--ink);font-family:var(--font);overflow:hidden}
#deck{position:fixed;inset:0;overflow:hidden;background:var(--page)}
#stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform-origin:center center;background:var(--bg);overflow:hidden}
.slide{position:absolute;inset:0;padding:96px 120px 120px;opacity:0;visibility:hidden;transform:translateX(60px);transition:opacity .55s ease,transform .55s cubic-bezier(.2,.7,.2,1),visibility 0s .55s}
.slide.active{opacity:1;visibility:visible;transform:none;transition:opacity .55s ease,transform .55s cubic-bezier(.2,.7,.2,1),visibility 0s}
.slide.past{transform:translateX(-60px)}
.eyebrow{font:700 26px/1 var(--font);letter-spacing:.16em;text-transform:uppercase;color:var(--orange);margin:0 0 26px}
h1{font:700 104px/1.04 var(--font);letter-spacing:-.025em;margin:0}
h2{font:700 72px/1.08 var(--font);letter-spacing:-.02em;margin:0 0 18px;text-wrap:balance}
h3{font:700 40px/1.15 var(--font);margin:0 0 10px}
p{margin:0}
.lead{font:400 38px/1.4 var(--font);color:var(--ink2);max-width:1250px}
.small{font:400 28px/1.45 var(--font);color:var(--ink2)}
.mono{font-family:var(--mono)}
.o{color:var(--orange)}.t{color:var(--teal)}.m{color:#D57AD4}.c{color:var(--coral)}.g{color:var(--ok)}
/* entrance and step animations */
.a{opacity:0;transform:translateY(28px)}
.slide.active .a{animation:rise .75s cubic-bezier(.2,.7,.2,1) forwards;animation-delay:calc(var(--d,0) * 1ms)}
@keyframes rise{to{opacity:1;transform:none}}
.st{opacity:0;transform:translateY(22px);transition:opacity .55s ease,transform .55s cubic-bezier(.2,.7,.2,1);pointer-events:none}
.st.on{opacity:1;transform:none}
.dim{opacity:.35}
/* ribbon + squares */
.deco{position:absolute;left:0;right:0;bottom:0;height:330px;pointer-events:none}
.ribbon{fill:none;stroke-width:34;stroke-linecap:round;stroke-dasharray:3600;stroke-dashoffset:3600}
.slide.active .ribbon{animation:draw 2.6s .2s cubic-bezier(.4,.1,.2,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.sq{opacity:0;transform:scale(.6);transform-origin:center}
.slide.active .sq{animation:pop .6s cubic-bezier(.2,.9,.3,1.3) forwards;animation-delay:calc(var(--d,0) * 1ms)}
@keyframes pop{to{opacity:1;transform:none}}
.corner{position:absolute;right:-120px;top:-60px;width:760px;opacity:.9}
.corner path{fill:none;stroke:var(--corner);stroke-width:44;stroke-linecap:round}
/* layout helpers */
.row{display:flex;gap:40px}.col{display:flex;flex-direction:column}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:36px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:28px}
.card{background:var(--bg2);border-radius:26px;padding:40px 40px 44px;border-top:8px solid var(--line);min-width:0}
.card h3{margin-bottom:14px}.card p{font:400 30px/1.4 var(--font);color:var(--ink2)}
.card.t{border-top-color:var(--teal)}.card.o{border-top-color:var(--orange)}.card.m{border-top-color:var(--magenta)}.card.c{border-top-color:var(--coral)}.card.b{border-top-color:#4B8FAE}
.card.t,.card.o,.card.m,.card.c{color:inherit}
.big{font:700 120px/1 var(--font);letter-spacing:-.03em}
.chip{display:inline-block;font:700 24px/1 var(--font);padding:12px 18px;border-radius:999px;background:var(--bg3);color:var(--ink2)}
.chip.o{background:var(--orange);color:#fff}.chip.t{background:var(--teal);color:#06242A}
.tag{font:700 22px/1 var(--font);letter-spacing:.1em;text-transform:uppercase;color:var(--ink3)}
.slide.divider{padding:0;background:var(--bg)}
.divider .num{position:absolute;left:120px;top:150px;font:700 300px/1 var(--font);color:var(--bg3);letter-spacing:-.05em}
.divider .txt{position:absolute;left:120px;top:490px;max-width:1300px}
.photo{width:620px;height:620px;border-radius:34px;object-fit:cover;display:block;box-shadow:0 30px 80px rgba(0,0,0,.5)}
.tl{font:400 34px/1.2 var(--font)}
.tlrow{display:grid;grid-template-columns:150px 1fr 150px;gap:28px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.tl .tm{font:700 34px/1 var(--mono);color:var(--teal)}
.tl .mn{color:var(--ink3);text-align:right;font-size:28px}
.ct{font:700 140px/1 var(--font);letter-spacing:-.03em}
table.cmp{width:100%;border-collapse:separate;border-spacing:0;font-size:30px;line-height:1.3}
.cmp th{font:700 24px/1 var(--font);letter-spacing:.12em;text-transform:uppercase;color:var(--ink3);text-align:left;padding:0 22px 18px}
.cmp td{padding:17px 22px;border-top:1px solid var(--line);color:var(--ink2);vertical-align:top}
.cmp td:first-child{color:var(--ink);font-weight:700;width:210px}
.cmp td.hl{background:rgba(250,70,22,.12);color:var(--ink)}
.cmp th.hl{color:var(--orange)}
.codeblk{background:#0E161B;border:2px solid var(--line);border-radius:20px;padding:30px 36px;font:500 32px/1.5 var(--mono);color:#E8EEF2}
.codeblk b{color:var(--orange)}
/* diagram text */
svg text{font-family:var(--font)}
.nd rect{fill:var(--bg2);stroke:#5A6C79;stroke-width:3}.nd text{fill:#fff;font-weight:700;font-size:23px}.nd .s{fill:var(--ink3);font-size:17px;font-weight:400}
.nd.sec rect{fill:#0F3B42;stroke:var(--teal)}.nd.fr rect{fill:#3B1B3B;stroke:#B04BAF}.nd.dn rect{fill:#4A1E1B;stroke:var(--coral)}
.road{stroke:#8DA0AD;stroke-width:3.5;fill:none}.det{stroke:var(--teal);stroke-width:3.5;fill:none}.ret{stroke:var(--teal);stroke-width:3.5;fill:none;stroke-dasharray:9 8}.den{stroke:var(--coral);stroke-width:3.5;fill:none}
.lbl{fill:var(--ink3);font-size:17px;font-weight:700;letter-spacing:.12em}
.tok circle{stroke:#fff;stroke-width:3}.tok text{fill:#06141A;font-weight:700;font-size:20px}.tok{opacity:0}
.nm{font:700 17px var(--font);fill:#fff}
.glow{animation:pulse 1.1s ease-in-out infinite}
@keyframes pulse{50%{filter:drop-shadow(0 0 14px rgba(11,162,179,.95))}}
.dr{stroke-dasharray:1200;stroke-dashoffset:1200;transition:stroke-dashoffset 1.1s ease}.dr.on{stroke-dashoffset:0}
.bx{opacity:0;transition:opacity .5s ease}.bx.on{opacity:1}
.mark{font:700 48px/1 var(--font)}
.lock{display:inline-grid;place-items:center;width:84px;height:84px;border-radius:22px;background:var(--bg3);margin-bottom:20px}
.ok{color:var(--ok)}.bad{color:var(--coral)}
.q{font:400 40px/1.3 var(--font);margin-bottom:26px;display:flex;gap:28px;align-items:baseline}
.q b{font:700 40px var(--mono);color:var(--orange)}.q i{font-style:normal;color:var(--ok);font-weight:700;margin-left:12px}
.tick{display:flex;gap:26px;align-items:center;font:400 38px/1.3 var(--font);margin-bottom:22px}
.tick span{display:inline-grid;place-items:center;width:52px;height:52px;border-radius:50%;background:var(--ok);color:#06241A;font:700 32px/1 var(--font);flex:none}
.step{display:flex;gap:30px;align-items:flex-start;margin-bottom:26px}
.step b{flex:none;display:inline-grid;place-items:center;width:64px;height:64px;border-radius:50%;background:var(--orange);font:700 34px/1 var(--font);color:#fff}
.step div{font:400 36px/1.35 var(--font);color:var(--ink2);padding-top:8px}.step div strong{color:var(--ink)}
/* chrome */
#hud{position:fixed;left:0;right:0;bottom:0;height:5px;background:rgba(255,255,255,.08);z-index:20}
#bar{height:100%;width:0;background:var(--orange);transition:width .45s ease}
#ctr{position:fixed;right:22px;bottom:16px;font:700 15px var(--mono);color:#7F8E99;z-index:21;letter-spacing:.08em;user-select:none}
.navb{position:fixed;bottom:12px;z-index:21;width:44px;height:44px;border-radius:50%;border:1px solid #3A4A56;background:rgba(24,32,38,.82);color:#C4CED6;font:700 20px var(--font);cursor:pointer}
#prev{left:18px}#next{left:70px}
.navb:hover{border-color:var(--orange);color:#fff}
.navb:focus-visible,#ov button:focus-visible{outline:3px solid var(--orange);outline-offset:2px}
#hint{position:fixed;left:50%;bottom:70px;transform:translateX(-50%);z-index:22;background:rgba(10,15,19,.9);border:1px solid #33444F;border-radius:999px;padding:12px 22px;font:400 16px var(--font);color:#C4CED6;transition:opacity .8s;white-space:nowrap}
#notes{position:fixed;left:0;right:0;bottom:0;z-index:30;background:rgba(10,15,19,.97);border-top:3px solid var(--orange);padding:22px 36px 30px;font:400 20px/1.5 var(--font);color:#E4EAEE;max-height:42vh;overflow:auto;transform:translateY(105%);transition:transform .35s ease}
#notes.open{transform:none}
#notes h4{margin:0 0 8px;font:700 14px var(--font);letter-spacing:.16em;text-transform:uppercase;color:var(--orange)}
#ov{position:fixed;inset:0;z-index:40;background:rgba(10,15,19,.96);padding:40px;overflow:auto;display:none}
#ov.open{display:block}
#ov h4{margin:0 0 20px;font:700 16px var(--font);letter-spacing:.16em;text-transform:uppercase;color:var(--orange)}
#ov .ovg{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
#ov button{display:flex;gap:12px;align-items:baseline;text-align:left;padding:16px;border-radius:14px;border:1px solid #33444F;background:#1B262D;color:#fff;font:400 17px/1.3 var(--font);cursor:pointer}
#ov button b{font:700 14px var(--mono);color:var(--orange)}
#ov button.cur{border-color:var(--orange)}
@media (prefers-reduced-motion:reduce){.a,.sq{opacity:1;transform:none;animation:none!important}.ribbon{stroke-dashoffset:0;animation:none!important}.slide,.st,.dr,.bx{transition:none}.glow{animation:none}}
"""

# ------------------------------------------------------------------ small building blocks
RIBBON_D = "M-20 210 C60 70 180 330 240 210 S420 70 480 210 S660 330 720 210 S900 70 960 210 S1140 330 1200 210 S1380 70 1440 210 S1620 330 1680 210 S1860 70 1940 210"


def deco(sq=True, colors=("#0BA2B3", "#8B288A", "#FA4616", "#1E6482")):
    squares = ""
    if sq:
        pos = [(360, 90, colors[0]), (840, 150, colors[1]), (1320, 60, colors[2]), (1680, 120, colors[3])]
        for i, (x, y, c) in enumerate(pos):
            squares += f'<rect class="sq" style="--d:{500 + i * 160}" x="{x}" y="{y}" width="200" height="200" fill="{c}"/>'
    return (f'<svg class="deco" viewBox="0 0 1920 330" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="rg" x1="0" x2="1"><stop offset="0" stop-color="#0BA2B3"/>'
            f'<stop offset=".35" stop-color="#1E6482"/><stop offset=".6" stop-color="#FA4616"/><stop offset=".85" stop-color="#8B288A"/><stop offset="1" stop-color="#FA7678"/></linearGradient></defs>'
            f'{squares}<path class="ribbon" d="{RIBBON_D}" stroke="url(#rg)"/></svg>')


CORNER = '<svg class="corner" viewBox="0 0 760 420" aria-hidden="true"><path d="M20 20 C20 140 60 220 160 215 C260 210 330 170 420 200 C520 235 450 330 560 340 C650 348 700 330 760 350"/></svg>'


def S(n):
    return f'st" data-s="{n}'


def slide(sid, title, inner, steps=0, notes="", cls=""):
    return (f'<section class="slide {cls}" id="{sid}" data-steps="{steps}" data-title="{esc(title)}" data-notes="{esc(notes)}">{inner}</section>')


def head(eyebrow, title, d=0):
    return f'<p class="eyebrow a" style="--d:{d}">{esc(eyebrow)}</p><h2 class="a" style="--d:{d + 80}">{title}</h2>'


def tok_def(cls, letter, color):
    return f'<g class="tok {cls}"><circle r="19" fill="{color}"/><text text-anchor="middle" y="7">{letter}</text></g>'


