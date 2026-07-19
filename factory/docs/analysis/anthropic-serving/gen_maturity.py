from html import escape
def xe(s): return escape(str(s),quote=True)
W,H=1820,470
stages=[("AI & ML","Turn data into decisions","#1E5BB0"),
        ("Deep Learning","Neural networks for complex tasks","#2E8B57"),
        ("Gen AI","Create new content","#E08A1E"),
        ("AI Agents","Autonomous tasks · tools · memory · planning","#C0392B"),
        ("Agentic AI","Automate entire processes with autonomous agents","#5B21B6")]
p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">',f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']
p.append('<defs><marker id="ar" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0L7,3L0,6Z" fill="#444"/></marker></defs>')
bw,bh,gap,x0,y=300,210,55,40,90
for i,(t,s,c) in enumerate(stages):
    x=x0+i*(bw+gap)
    p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="14" fill="{c}"/>')
    p.append(f'<text x="{x+bw/2}" y="{y+78}" font-size="30" font-weight="bold" fill="#fff" text-anchor="middle">{xe(t)}</text>')
    # wrap subtitle
    words=s.split(); lines=[];cur=""
    for w_ in words:
        if len(cur)+len(w_)>26: lines.append(cur); cur=w_
        else: cur=(cur+" "+w_).strip()
    lines.append(cur)
    yy=y+120
    for ln in lines:
        p.append(f'<text x="{x+bw/2}" y="{yy}" font-size="16" fill="#fff" text-anchor="middle" opacity="0.95">{xe(ln)}</text>'); yy+=22
    if i<len(stages)-1:
        ax=x+bw; p.append(f'<line x1="{ax+6}" y1="{y+bh/2}" x2="{ax+gap-6}" y2="{y+bh/2}" stroke="#444" stroke-width="3" marker-end="url(#ar)"/>')
# bottom autonomy arrow
ay=y+bh+60
p.append(f'<line x1="{x0}" y1="{ay}" x2="{x0+4*(bw+gap)+bw}" y2="{ay}" stroke="#6B7280" stroke-width="4" marker-end="url(#ar)"/>')
p.append(f'<text x="{W/2}" y="{ay-14}" font-size="20" font-weight="bold" fill="#374151" text-anchor="middle">Increasing autonomy  ·  from assisting humans  →  to automating whole processes</text>')
p.append("</svg>")
open("maturity.svg","w").write("\n".join(p))
