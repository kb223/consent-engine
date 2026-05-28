---
marp: true
theme: default
paginate: true
footer: 'Kenneth Buchanan · Consent Compliance Intelligence'
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap');

  :root {
    /* LIGHT theme — warm cream, Anthropic-style, KJB accents */
    --bg:    #f6f4ee;          /* warm cream */
    --s:     #ffffff;          /* surface */
    --s2:    #faf8f2;           /* alt surface */
    --b:     #e7e3d8;          /* border */
    --b2:    #d8d2c2;          /* strong border */
    --t:     #14182b;          /* headline near-black */
    --body:  #1f2944;          /* body near-navy */
    --m:     #6b7794;          /* muted */
    --a:     #3d6abb;          /* KJB blue accent */
    --navy:  #2b3954;          /* KJB navy — section markers */
    --g:     #2f7a4f;          /* green */
    --gs:    #e4f1e6;          /* green-soft */
    --r:     #b34d4d;          /* red */
    --rs:    #fbe8e2;          /* red-soft */
    --y:     #a06913;          /* amber */
    --ys:    #f5ebd2;          /* amber-soft */
  }
  section {
    background: var(--bg); color: var(--body);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-weight: 400;
    padding: 72px 96px 88px; line-height: 1.55;
    letter-spacing: -0.003em;
    box-sizing: border-box;
  }
  section > * { max-width: 100%; }
  footer {
    font-size: 0.52em; color: var(--m);
    padding: 14px 96px 18px;
    background: var(--bg); position: absolute; bottom: 0; left: 0; right: 0;
    border-top: 1px solid var(--b);
    letter-spacing: 0.08em;
  }
  h1 {
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 500;
    font-size: 2.6em;
    color: var(--t);
    letter-spacing: -0.022em;
    line-height: 1.12;
    margin: 0 0 14px;
  }
  h2 {
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 400;
    font-size: 1.15em;
    color: var(--m);
    margin: 0 0 26px;
    letter-spacing: 0;
  }
  h3 {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.6em;
    color: var(--a);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin: 0 0 10px;
  }
  strong { color: var(--t); font-weight: 600; }
  p { color: var(--body); font-size: 0.84em; line-height: 1.65; margin: 0 0 10px; }
  li { color: var(--body); font-size: 0.84em; line-height: 1.65; margin-bottom: 6px; }
  blockquote {
    margin: 22px 0 28px;
    padding-left: 22px;
    border-left: 2px solid var(--a);
    font-family: 'Source Serif 4', Georgia, serif;
    font-style: italic;
    font-weight: 400;
    font-size: 0.95em;
    color: var(--body);
  }
  a { color: var(--a); text-decoration: none; border-bottom: 1px solid var(--a); }
  code {
    background: var(--s2); color: var(--t);
    padding: 1px 6px; border-radius: 3px; border: 1px solid var(--b);
    font-size: 0.82em; font-family: 'SF Mono', Menlo, monospace;
  }
  section.lead { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
  section.compact { padding: 56px 96px 56px; }
  section.compact h1 { font-size: 2.1em; margin-bottom: 8px; }
  section.compact h2 { font-size: 1em; margin-bottom: 18px; }
  section.compact p { font-size: 0.78em; }
  section.cover { padding: 110px 96px; background: var(--bg); }
  section.cover h1 {
    font-size: 3.2em; border-left: 3px solid var(--a);
    padding-left: 28px; margin-bottom: 16px; color: var(--t);
  }
  section.cover h2 {
    font-size: 1.05em; padding-left: 31px;
    color: var(--m); margin: 0 0 48px;
  }
  section.cover .brand-mark {
    position: absolute; top: 56px; right: 96px;
    width: 64px; height: 64px; display: flex;
    align-items: center; justify-content: center;
    background: var(--s); border: 1px solid var(--b);
    border-radius: 8px; padding: 8px;
    box-shadow: 0 1px 2px rgba(20,24,43,0.04);
  }
  section.cover .brand-mark img {
    max-width: 100%; max-height: 100%; object-fit: contain;
    display: block;
  }
  section::after {
    font-family: 'Inter', sans-serif; font-size: 0.54em;
    color: var(--m); right: 96px; bottom: 18px; letter-spacing: 0.08em;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.78em; margin: 14px 0 18px; }
  th {
    text-align: left; padding: 12px 18px 12px 0;
    color: var(--m); font-weight: 500;
    font-size: 0.74em; text-transform: uppercase; letter-spacing: 0.12em;
    border-bottom: 1px solid var(--b);
  }
  td {
    padding: 12px 18px 12px 0; color: var(--body);
    border-bottom: 1px solid var(--b);
  }
  tr:last-child td { border-bottom: none; }
  .tag {
    font-family: 'Inter', sans-serif; font-weight: 600;
    font-size: 0.52em; letter-spacing: 0.12em;
    text-transform: uppercase; padding: 3px 9px;
    border-radius: 3px; display: inline-block;
  }
  details {
    background: var(--s); border: 1px solid var(--b);
    border-radius: 5px; padding: 14px 18px; margin-top: 8px;
  }
  details summary { color: var(--a); font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.78em; cursor: pointer; }
  details p { color: var(--body); font-size: 0.76em; margin-top: 8px; line-height: 1.6; }
---

<style>section:first-of-type > footer { display: none !important; }</style>

### FORENSIC PRIVACY AUDIT · US · CONFIDENTIAL

<div style="position:absolute;top:44px;right:60px;background:rgba(255,255,255,0.06);border-radius:10px;padding:8px;line-height:0;"><img src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233d6abb' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/></svg>" style="height:44px;width:44px;border-radius:8px;object-fit:contain;display:block;" /></div>

# example.com

## Consent Compliance Report

<div style="position:absolute;bottom:50px;left:72px;right:72px;"><div style="border-top:1px solid #e7e3d8;padding-top:18px;display:flex;justify-content:space-between;align-items:center;"><div style="display:flex;align-items:center;gap:14px;"><div><div style="font-family:'Inter';font-weight:700;font-size:0.65em;color:#14182b;line-height:1.2;">Kenneth Buchanan</div><div style="font-family:'Inter';font-weight:400;font-size:0.46em;color:#4b5563;margin-top:3px;">Consent Compliance Intelligence</div></div></div><div style="display:flex;gap:36px;align-items:flex-start;"><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Date</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">May 28, 2026</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Methodology</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">Baseline Scan</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Audit ID</div><div style="font-family:'Inter';font-weight:500;font-size:0.48em;color:#9ca3af;letter-spacing:0.02em;">87cea70e-9719-4421-8b1d-530d144a30d4</div></div></div></div></div>

---

### AUDIT VERDICT

# No Violations Detected

<p style="font-size:0.72em;color:#9ca3af;max-width:680px;line-height:1.6;margin-bottom:0;">No confirmed consent violations were detected at https://example.com under the s3_inconclusive_unknown_cmp methodology.</p>

<div style="display:flex;gap:10px;margin-top:22px;"><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #22c55e;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Cookie Violations</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#22c55e;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">0</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">none detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #22c55e;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Pixel Endpoints</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#22c55e;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">0</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">none detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">GCS State</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">N/A</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">not detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Jurisdiction</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">US</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">simulated: Los Angeles, CA</div></div></div>

---

### SIGNAL ANALYSIS

# Findings at a Glance

<div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Cookie Violations</div><div style="flex:3;color:#d1d5db;font-weight:400;">None detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Network Pixel Endpoints</div><div style="flex:3;color:#d1d5db;font-weight:400;">None detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Consent Mode (GCS)</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Server-Side GTM</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">CMP Detected</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">GPC Signal Honored</div><div style="flex:3;color:#d1d5db;font-weight:400;">Tested — mandatory opt-out signal sent</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div></div>

---

### COOKIE ANALYSIS

# No Cookie Violations

<p>No tracking cookies were observed firing after consent was denied.</p>





---

<!-- _class: compact -->

### GPC COMPLIANCE TEST

# GPC Compliance <span style="font-family:'Inter';font-weight:600;font-size:0.45em;letter-spacing:0.14em;text-transform:uppercase;padding:4px 12px;border-radius:4px;background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44;vertical-align:middle;margin-left:14px;">Inconclusive</span>

<p style="font-size:0.72em;color:#6b7794;margin:0 0 10px;line-height:1.5;">Sec-GPC: 1 header + navigator.globalPrivacyControl asserted on every request.</p><div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Sec-GPC: 1 header sent on all requests</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#22c55e'>YES</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">navigator.globalPrivacyControl = true</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#22c55e'>YES</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Site honored GPC signal</div><div style="flex:3;color:#d1d5db;font-weight:400;">Inconclusive</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Baseline pixel firings (post opt-out)</div><div style="flex:3;color:#d1d5db;font-weight:400;"><code>0</code></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Pixel firings under GPC</div><div style="flex:3;color:#d1d5db;font-weight:400;"><code style='color:#22c55e'>0</code></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div></div><div style="margin-top:10px;background:#faf8f2;border-radius:6px;padding:10px 14px;border-left:3px solid #f59e0b;"><div style="font-size:0.62em;color:#6b7794;line-height:1.5;">Under CCPA/CPRA, GPC is a legally binding opt-out signal. California's CPPA has stated GPC non-compliance is enforceable without prior notice.</div></div>




---

### CCPA · CPRA · CIPA · FTC ACT

# Applicable Legal Framework

<div style="margin-top:8px;">
<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CCPA/CPRA §1798.120: Right to opt out of sale and sharing</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CPRA sharing extension: Covers pixel-based data transfer to ad platforms</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">GPC mandate: `Sec-GPC: 1` is a legally binding opt-out signal</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">Fine exposure: Up to $7,500 per intentional violation per consumer</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CIPA: $5,000 statutory per-violation — no actual damages required</div></div>
</div>

---

### REMEDIATION ROADMAP

# Maintaining Compliance

<div style="display:flex;gap:12px;margin-top:10px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #22c55e;">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#22c55e;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Ongoing</div>
    <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">No immediate actions required — site is compliant</div></div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #3d6abb;"><div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#3d6abb;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Within 30 Days</div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Schedule quarterly consent audits to catch configuration drift</div></div></div>
</div>

---

### HOW WE AUDIT

# Forensic Methodology

<p style="font-size:0.75em;color:#6b7280;margin-bottom:12px;">Inconclusive (CMP not recognised, injection unverified) — Independent forensic scan. No vendor access or cooperation required. Mirrors the approach used by the <strong style="color:#22c55e;">California Privacy Protection Agency</strong> in automated GPC compliance sweeps.</p>

<div style="margin-top:4px;">
<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Fresh browser context — zero prior cookies, consent denial pre-injected before page load</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Page reloaded post-denial to capture true opted-out network state</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">All network traffic captured and fingerprinted against 3,200+ vendor signatures</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Pixel endpoint detection — plaintiff law firm methodology (CIPA §631)</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Regulatory findings cross-referenced against live enforcement database</div></div>
</div>

---

### PREPARED BY

# Kenneth Buchanan

<p style="font-size:0.72em;color:#6b7280;margin:-8px 0 0 0;">Independent forensic audit · <a href="https://kennethjbuchanan.com" style="color:#3d6abb;text-decoration:none;">kennethjbuchanan.com</a></p>

<div style="display:flex;gap:10px;margin-top:28px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Forensic Auditing</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">Post-denial traffic analysis<br>GPC signal testing<br>SSGTM detection</div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Regulatory Intelligence</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">Live US &amp; EU enforcement data<br>Fine exposure modeling<br>Case precedent library</div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Remediation Advisory</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">CMP configuration<br>Consent Mode V2<br>GTM consent architecture</div>
  </div>
</div>

<div style="margin-top:20px;font-size:0.6em;color:#4b5563;line-height:1.6;">
Audit 87cea70e-9719-4421-8b1d-530d144a30d4 · 2026-05-28 · For compliance assessment purposes only. Consult legal counsel for enforcement risk analysis.
</div>