"""The celebration pop-up's markup: confetti, a headline, the real result as cards.

Design rules (from the research behind this feature):
* Quiet by default, expressive when earned: no PR = a calm card; a PR = confetti and
  a GIF; a milestone (plate crossed, first PR, first workout, 2+ PRs) = bigger.
* Vary the media so it stays fun (never the same one twice in a row).
* Always show the real result (lift, weight, how much it went up). Motion is
  decoration, never the only message.
* Respect `prefers-reduced-motion`: no confetti, no pop-in.
"""
import html
import random

CONFETTI = ["#B044E1", "#FFC857", "#4FD1C5", "#F54946", "#6C8CFF", "#FFFFFF"]

HEADLINES = {
    "pr": ["New PR!", "You just got stronger", "Personal best!", "That one moved the bar"],
    "big": ["MILESTONE!", "Big moment", "Look at you go"],
    "none": ["Solid session", "Work done", "Another one logged"],
}

CSS = """
<style>
.bs-wrap{text-align:center;color:inherit;font-family:inherit}
.bs-stage{position:relative;height:230px;overflow:hidden;border-radius:18px;display:flex;align-items:center;
  justify-content:center;background:radial-gradient(ellipse at 50% 100%,rgba(176,68,225,.35),rgba(176,68,225,0) 70%)}
.bs-emoji{position:absolute;font-size:110px;line-height:1;animation:bs-pop .6s cubic-bezier(.2,1.6,.4,1) both}
.bs-media{position:absolute;inset:8px;background-position:center;background-repeat:no-repeat;background-size:contain;
  animation:bs-pop .6s cubic-bezier(.2,1.6,.4,1) both}
@keyframes bs-pop{from{transform:scale(.3);opacity:0}to{transform:scale(1);opacity:1}}
.bs-fire{margin-bottom:44px;font-family:'Material Symbols Rounded';font-size:120px;line-height:1;font-variation-settings:'FILL' 1;color:transparent;
  background:linear-gradient(180deg,#ffd1ef 0%,#ec4899 40%,#8b5cf6 100%);-webkit-background-clip:text;background-clip:text;
  filter:drop-shadow(0 0 22px rgba(236,72,153,.5));animation:bs-ignite .7s cubic-bezier(.2,1.5,.4,1) both,bs-flick 2.6s ease-in-out .8s infinite}
.bs-wk{position:absolute;bottom:12px;left:0;right:0;display:flex;justify-content:center;gap:12px}
.bs-wd{display:flex;flex-direction:column;align-items:center;font-size:.66rem;opacity:.7}
.bs-wd i{font-style:normal;font-family:'Material Symbols Rounded';font-size:22px;line-height:1;font-variation-settings:'FILL' 0,'wght' 300}
.bs-wd.on i{font-variation-settings:'FILL' 1;color:transparent;background:linear-gradient(180deg,#ffd1ef,#ec4899 40%,#8b5cf6);
  -webkit-background-clip:text;background-clip:text}
.bs-wd.now{opacity:1}.bs-wd.now b{font-weight:800}
.bs-wd.now.on i{animation:bs-catch .6s ease-out 1s both}
@keyframes bs-ignite{0%{transform:scale(.2) translateY(30px);opacity:0}100%{transform:none;opacity:1}}
@keyframes bs-flick{0%,100%{transform:scale(1) rotate(-1.5deg)}50%{transform:scale(1.06) rotate(1.5deg)}}
@keyframes bs-catch{0%{transform:scale(.3);opacity:0}70%{transform:scale(1.35)}100%{transform:none;opacity:1}}
.bs-purple{filter:hue-rotate(250deg) saturate(1.15) drop-shadow(0 0 24px rgba(168,85,247,.45))}
.bs-credit{font-size:.7rem;opacity:.5;margin-top:.25rem}
.bs-credit a{color:inherit}
.bs-conf{position:absolute;top:-14px;width:9px;height:14px;opacity:0;border-radius:2px;
  animation:bs-fall var(--d) var(--delay) linear 2 forwards}
@keyframes bs-fall{0%{transform:translate3d(0,-10px,0) rotate(0);opacity:1}
  100%{transform:translate3d(var(--x),260px,0) rotate(var(--r));opacity:.9}}
.bs-title{margin:.5rem 0 .1rem;font-size:2rem;font-weight:800;letter-spacing:-.02em;animation:bs-rise .5s .3s both}
.bs-title.big{background:linear-gradient(90deg,var(--gold),#db2777,var(--purple));-webkit-background-clip:text;
  background-clip:text;color:transparent}
.bs-sub{opacity:.75;margin-bottom:.8rem;animation:bs-rise .5s .45s both}
.bs-cards{display:grid;gap:.6rem;text-align:left}
.bs-card{background:none;border:none;border-top:1px solid var(--bs-c-line);border-radius:0;padding:.9rem 0;animation:bs-rise .5s both}
.bs-top{display:flex;justify-content:space-between;align-items:center;gap:.5rem;font-weight:600}
.bs-up{background:var(--bs-c-upbg);color:var(--bs-c-up);border-radius:999px;padding:.1rem .6rem;font-size:.85rem;font-weight:700;white-space:nowrap}
.bs-big{font-size:1.6rem;font-weight:800;color:var(--gold);line-height:1.2}
.bs-note{opacity:.7;font-size:.85rem}
.bs-chip{display:inline-block;margin:.2rem .3rem 0 0;background:rgba(176,68,225,.2);border-radius:999px;padding:.15rem .7rem;font-size:.85rem}
@keyframes bs-rise{from{transform:translateY(12px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){
  .bs-media,.bs-title,.bs-sub,.bs-card{animation:none !important}.bs-conf{display:none}
}
</style>
"""


def confetti(n=36, seed=None):
    rnd = random.Random(seed)
    bits = []
    for _ in range(n):
        bits.append(
            f'<i class="bs-conf" style="left:{rnd.uniform(2, 98):.1f}%;background:{rnd.choice(CONFETTI)};'
            f'--d:{rnd.uniform(2.2, 3.6):.2f}s;--delay:{rnd.uniform(0, 1.6):.2f}s;'
            f'--x:{rnd.uniform(-60, 60):.0f}px;--r:{rnd.choice([-1, 1]) * rnd.uniform(240, 720):.0f}deg"></i>'
        )
    return "".join(bits)


def headline(tier):
    return random.choice(HEADLINES[tier])


# Noto animated fire (Google, CC BY 4.0; credited on the You page, About), recoloured to the app's purple.
FIRE = "https://fonts.gstatic.com/s/e/notoemoji/latest/1f525/512.webp"


def render(tier, title, subline, cards, chips, seed=None):
    """tier: none|pr|big. cards: [{title, big, badge, note}]. One purple flame, the same every time."""
    stage_confetti = confetti(44 if tier == "big" else 26, seed) if tier in ("pr", "big") else ""
    card_html = "".join(
        f'<div class="bs-card" style="animation-delay:{0.55 + i * 0.12:.2f}s">'
        f'<div class="bs-top"><span>{html.escape(c["title"])}</span>'
        + (f'<span class="bs-up">{html.escape(c["badge"])}</span>' if c.get("badge") else "")
        + f'</div><div class="bs-big">{html.escape(c["big"])}</div>'
        + (f'<div class="bs-note">{html.escape(c["note"])}</div>' if c.get("note") else "")
        + "</div>"
        for i, c in enumerate(cards)
    )
    chip_html = "".join(f'<span class="bs-chip">{html.escape(c)}</span>' for c in chips)
    import ui  # light and dark get their own celebration colours (gold on white was unreadable)

    theme = (".bs-wrap{--gold:#FFC857;--purple:#C084FC;--bs-c-line:rgba(255,255,255,.16);--bs-c-up:#4FD1C5;--bs-c-upbg:rgba(79,209,197,.16)}"
             if ui.is_dark() else
             ".bs-wrap{--gold:#B45309;--purple:#7C3AED;--bs-c-line:rgba(27,23,64,.12);--bs-c-up:#0F766E;--bs-c-upbg:rgba(15,118,110,.12)}")
    return (
        CSS + f"<style>{theme}</style>"
        + f'<div class="bs-wrap"><div class="bs-stage">{stage_confetti}'
        f'<div class="bs-media bs-purple" style="background-image:url(\'{FIRE}\')" aria-hidden="true"></div></div>'
        f'<div class="bs-title {"big" if tier == "big" else ""}">{html.escape(title)}</div>'
        f'<div class="bs-sub">{html.escape(subline)}</div>'
        + (f'<div style="margin-bottom:.6rem">{chip_html}</div>' if chip_html else "")
        + f'<div class="bs-cards">{card_html}</div></div>'
    )
