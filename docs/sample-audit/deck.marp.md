---
marp: true
theme: default
paginate: true
footer: 'Kenneth Buchanan · Consent Compliance Intelligence'
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap');

  :root {
    /* Light theme with brand accents */
    --bg:    #f6f4ee;          /* warm cream */
    --s:     #ffffff;          /* surface */
    --s2:    #faf8f2;           /* alt surface */
    --b:     #e7e3d8;          /* border */
    --b2:    #d8d2c2;          /* strong border */
    --t:     #14182b;          /* headline near-black */
    --body:  #1f2944;          /* body near-navy */
    --m:     #6b7794;          /* muted */
    --a:     #3d6abb;          /* brand blue accent */
    --navy:  #2b3954;          /* brand navy section markers */
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

### FORENSIC PRIVACY AUDIT · US · COMPLIANCE ASSESSMENT

<div style="position:absolute;top:44px;right:60px;background:rgba(255,255,255,0.06);border-radius:10px;padding:8px;line-height:0;"><img src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233d6abb' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/></svg>" style="height:44px;width:44px;border-radius:8px;object-fit:contain;display:block;" /></div>

# www.retailer.example

## Consent Compliance Report

<div style="position:absolute;bottom:50px;left:72px;right:72px;"><div style="border-top:1px solid #e7e3d8;padding-top:18px;display:flex;justify-content:space-between;align-items:center;"><div style="display:flex;align-items:center;gap:14px;"><div><div style="font-family:'Inter';font-weight:700;font-size:0.65em;color:#14182b;line-height:1.2;">Kenneth Buchanan</div><div style="font-family:'Inter';font-weight:400;font-size:0.46em;color:#4b5563;margin-top:3px;">Consent Compliance Intelligence</div></div></div><div style="display:flex;gap:36px;align-items:flex-start;"><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Date</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">November 05, 2026</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Methodology</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">Consent Enforcement</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Audit ID</div><div style="font-family:'Inter';font-weight:500;font-size:0.48em;color:#9ca3af;letter-spacing:0.02em;">9ae07da0-c77c-4112-9a56-d064dc255b25</div></div></div></div></div>

---

### AUDIT VERDICT

# Violations Confirmed

<p style="font-size:0.72em;color:#9ca3af;max-width:680px;line-height:1.6;margin-bottom:0;">Confirmed consent violations detected at https://www.retailer.example. The following vendors fired tracking technologies despite opted-out consent: Snapchat, Microsoft Clarity, Klaviyo, Pinterest, Meta, Microsoft / Bing, and 1 more.</p>

<div style="display:flex;gap:10px;margin-top:22px;"><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #ef4444;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Cookie Violations</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#ef4444;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">7</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">confirmed vendors</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #ef4444;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Pixel Endpoints</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#ef4444;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">8</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">post-denial firings</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #f59e0b;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">GCS State</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#f59e0b;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">G111</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">CMP integration failure</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Jurisdiction</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">US</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">simulated: Los Angeles, CA</div></div></div>

---

### SIGNAL ANALYSIS

# Findings at a Glance

<div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Cookie Violations</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#ef4444'>7 confirmed vendors</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Network Pixel Endpoints</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#ef4444'>8 post-denial endpoints</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Consent Mode (GCS)</div><div style="flex:3;color:#d1d5db;font-weight:400;"><code style='background:#faf8f2;color:#14182b;border:1px solid #e7e3d8;padding:2px 8px;border-radius:3px;font-size:0.9em;font-family:"SF Mono",Menlo,monospace;font-weight:600;'>G111</code>: CMP not updating Consent Mode on opt-out (integration failure)</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">sGTM</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#f59e0b'>www.retailer.example</strong> (consent bypass risk)</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">CMP Detected</div><div style="flex:3;color:#d1d5db;font-weight:400;">Shopify</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">GPC Signal Honored</div><div style="flex:3;color:#d1d5db;font-weight:400;">Tested: opt-out signal sent</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div></div>

---

### COOKIE EVIDENCE

# Confirmed Violations

<div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;"><div style="flex:1;min-width:160px;background:#ffffff;border-radius:10px;padding:16px;border-left:3px solid #ef4444;"><div style="font-family:'Inter';font-weight:600;font-size:0.82em;color:#14182b;margin-bottom:6px;">Snapchat</div><div style="color:#4b5563;font-size:0.62em;margin-bottom:10px;font-family:'Inter';">X-AB, _scid, _scid_r</div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH RISK</span></div><div style="flex:1;min-width:160px;background:#ffffff;border-radius:10px;padding:16px;border-left:3px solid #ef4444;"><div style="font-family:'Inter';font-weight:600;font-size:0.82em;color:#14182b;margin-bottom:6px;">Microsoft Clarity</div><div style="color:#4b5563;font-size:0.62em;margin-bottom:10px;font-family:'Inter';">CLID, _clck, SM</div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH RISK</span></div><div style="flex:1;min-width:160px;background:#ffffff;border-radius:10px;padding:16px;border-left:3px solid #ef4444;"><div style="font-family:'Inter';font-weight:600;font-size:0.82em;color:#14182b;margin-bottom:6px;">Meta</div><div style="color:#4b5563;font-size:0.62em;margin-bottom:10px;font-family:'Inter';">fr</div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH RISK</span></div><div style="flex:1;min-width:160px;background:#ffffff;border-radius:10px;padding:16px;border-left:3px solid #f59e0b;"><div style="font-family:'Inter';font-weight:600;font-size:0.82em;color:#14182b;margin-bottom:6px;">Klaviyo</div><div style="color:#4b5563;font-size:0.62em;margin-bottom:10px;font-family:'Inter';">__kla_id</div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#f59e0b12;color:#f59e0b;border:1px solid #f59e0b22;">MEDIUM RISK</span></div></div><p style="font-size:0.65em;color:#4b5563;margin-top:6px;">+3 additional vendors documented in full report</p>

<div style="margin-top:16px;background:#fbe8e2;border-radius:10px;padding:14px 18px;border-left:4px solid #ef4444;font-size:0.72em;color:#9ca3af;line-height:1.7;"><strong style="color:#ef4444;">CCPA exposure:</strong> these vendors received behavioral data after consent was denied. Each firing = potential $7,500 violation.</div>

---

### NETWORK EVIDENCE

# Post-Denial Pixel Endpoints

<p style="font-size:0.75em;color:#9ca3af;margin-bottom:4px;">Primary exhibit methodology used by plaintiff law firms (CIPA §631 · CCPA class actions)</p>
<div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Meta Pixel</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">connect.facebook.net/en_US/fbevents.js</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">advertising</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Meta Pixel</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">facebook.com/tr/</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">advertising</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Microsoft Clarity</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">clarity.ms/collect</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">session recording</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Pinterest Tag</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">ct.pinterest.com/user</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">advertising</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Pinterest Tag</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">ct.pinterest.com/v3</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">advertising</span></div></div></div>

---

### NETWORK EVIDENCE

# Pixel Endpoints (cont. 2)
<div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Snapchat Pixel</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">tr.snapchat.com/p</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">advertising</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Klaviyo</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">static.klaviyo.com/onsite/js</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#f59e0b12;color:#f59e0b;border:1px solid #f59e0b22;">advertising</span></div></div><div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:2;color:#d1d5db;font-weight:400;font-family:'Outfit';font-weight:600;">Klaviyo</div><div style="flex:3;color:#4b5563;font-family:'SF Mono',monospace;font-size:0.9em;">a.klaviyo.com</div><div style="flex:1.5;"><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#f59e0b12;color:#f59e0b;border:1px solid #f59e0b22;">advertising</span></div></div></div><p style="font-size:0.6em;color:#4b5563;margin-top:8px;">Continued (6 to 8 of 8)</p>

---

### NETWORK EVIDENCE

# Pixel Endpoints (cont. 3)
<div style="margin-top:12px;background:#ffffff;border-radius:8px;padding:12px 16px;border-left:3px solid #22c55e;"><div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#22c55e;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Observation: Expected ACM Behavior</div><div style="font-size:0.68em;color:#6b7280;line-height:1.6;"><div><strong style="color:#9ca3af;">Google Ads</strong> <span style="color:#4b5563;">(googleadservices.com/pagead/conversion)</span>: Consent Mode cookieless ping (GCS=G100, npa=1). No cookie ID transmitted. This is correct Advanced Consent Mode behavior.</div></div></div>

---

<!-- _class: compact -->

### RISK QUANTIFICATION

# Financial Exposure Estimate

<div style="display:flex;gap:8px;margin-top:14px;align-items:stretch;"><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">CCPA / CPRA</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">$7,500</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">per intentional violation · per consumer</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">CIPA §631</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">$5,000</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">per session · no actual damages required</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">FTC Act</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">$51,744</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">per day of ongoing violation</div></div></div><div style="display:flex;gap:8px;margin-top:8px;align-items:stretch;"><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #ef4444;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Conservative</div><div style="font-family:'Inter';font-weight:800;font-size:1.05em;color:#ef4444;line-height:1.15;margin-bottom:4px;letter-spacing:-0.01em;">$3.5M to $34.5M</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">50,000 CA opt-outs/mo<br>max $34.5B/yr</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #ef4444;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Mid-range</div><div style="font-family:'Inter';font-weight:800;font-size:1.05em;color:#ef4444;line-height:1.15;margin-bottom:4px;letter-spacing:-0.01em;">$17.2M to $172.5M</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">250,000 CA opt-outs/mo<br>max $172.5B/yr</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #ef4444;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">High-traffic</div><div style="font-family:'Inter';font-weight:800;font-size:1.05em;color:#ef4444;line-height:1.15;margin-bottom:4px;letter-spacing:-0.01em;">$69.0M to $690.0M</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">1,000,000 CA opt-outs/mo<br>max $690.0B/yr</div></div></div><div style="margin-top:8px;background:#ffffff;border-radius:8px;padding:8px 14px;border-left:3px solid #374151;"><div style="font-size:0.6em;color:#4b5563;line-height:1.5;">Realistic settlement range calibrated to precedent: Sephora $1.2M (2022) · Tractor Supply $1.35M (Sep 2025) · Disney $2.75M (Feb 2026)</div></div>

---

<!-- _class: compact -->

### GPC COMPLIANCE TEST

# GPC Compliance <span style="font-family:'Inter';font-weight:600;font-size:0.45em;letter-spacing:0.14em;text-transform:uppercase;padding:4px 12px;border-radius:4px;background:#ef444422;color:#ef4444;border:1px solid #ef444444;vertical-align:middle;margin-left:14px;">Ignored</span>

<p style="font-size:0.72em;color:#6b7794;margin:0 0 10px;line-height:1.5;">Sec-GPC: 1 header + navigator.globalPrivacyControl asserted on every request.</p><div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Sec-GPC: 1 header sent on all requests</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#22c55e'>YES</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">navigator.globalPrivacyControl = true</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#22c55e'>YES</strong></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Site honored GPC signal</div><div style="flex:3;color:#d1d5db;font-weight:400;"><strong style='color:#ef4444'>NO</strong>. 4 vendor pixels fired tracking after GPC was asserted</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Baseline pixel firings (post opt-out)</div><div style="flex:3;color:#d1d5db;font-weight:400;"><code>9</code></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Pixel firings under GPC</div><div style="flex:3;color:#d1d5db;font-weight:400;"><code style='color:#ef4444'>4</code></div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div></div><div style="margin-top:10px;background:#faf8f2;border-radius:6px;padding:10px 14px;border-left:3px solid #ef4444;"><div style="font-size:0.62em;color:#6b7794;line-height:1.5;">Under CCPA/CPRA, GPC is a legally binding opt-out signal. California's CPPA has stated GPC non-compliance is enforceable without prior notice.</div></div>




---

<!-- _class: compact -->

### ENFORCEMENT PATTERN MAP

# Current Enforcement Themes

<div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;padding-bottom:7px;border-bottom:2px solid #d8d2c2;font-size:0.56em;color:#6b7794;text-transform:uppercase;letter-spacing:0.12em;"><div>Theme</div><div>Severity</div><div>Evidence</div><div>Action</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Opt-out mechanism failure</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH</span></div><div style="color:#4b5563;line-height:1.45;">7 confirmed vendor finding(s); 9 pixel endpoint firing(s)</div><div style="color:#6b7280;line-height:1.45;">Re-test reject-all and GPC paths after each tag or CMP change.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">GPC / universal opt-out failure</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">CRITICAL</span></div><div style="color:#4b5563;line-height:1.45;">4 pixel endpoint(s) fired under GPC; baseline=9, gpc=4</div><div style="color:#6b7280;line-height:1.45;">Map Sec-GPC: 1 and navigator.globalPrivacyControl to the same denied state used by manual opt-out.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Vendor and third-party governance</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH</span></div><div style="color:#4b5563;line-height:1.45;">15 inventory row(s) likely require sale/sharing review</div><div style="color:#6b7280;line-height:1.45;">Confirm each ad-tech, analytics, and pixel vendor has purpose-limited contract terms and is classified in the tracking inventory.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Sensitive data / purpose limitation</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH</span></div><div style="color:#4b5563;line-height:1.45;">Sensitive context(s): minor_or_student; 15 likely sale/sharing row(s)</div><div style="color:#6b7280;line-height:1.45;">Block advertising and behavioral tracking on sensitive-context pages unless a specific consent and purpose basis exists.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Minor / student privacy</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">CRITICAL</span></div><div style="color:#4b5563;line-height:1.45;">Page context suggests children, students, or under-16 users</div><div style="color:#6b7280;line-height:1.45;">Verify under-16 sale/sharing controls, age-appropriate notice, and affirmative consent before targeted advertising.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Tracking technology inventory</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#6b728012;color:#6b7280;border:1px solid #6b728022;">INFO</span></div><div style="color:#4b5563;line-height:1.45;">18 inventory row(s) generated</div><div style="color:#6b7280;line-height:1.45;">Review and export this inventory quarterly and after every tag release.</div></div><p style="font-size:0.58em;color:#6b7280;margin-top:8px;">+1 additional theme(s) documented in the full report.</p>


---

<!-- _class: compact -->

### TRACKING TECHNOLOGY INVENTORY

# Vendors Requiring Review

<div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;padding-bottom:7px;border-bottom:2px solid #d8d2c2;font-size:0.56em;color:#6b7794;text-transform:uppercase;letter-spacing:0.12em;"><div>Vendor</div><div>Evidence</div><div>Sale / Sharing</div><div>GPC</div><div>Contract</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">DoubleClick/DV360</div><div style="color:#4b5563;">Pixel</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Google</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Google / DoubleClick</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Google Ads</div><div style="color:#4b5563;">Pixel</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Klaviyo</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Klaviyo</div><div style="color:#4b5563;">Pixel</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Meta</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Meta Pixel</div><div style="color:#4b5563;">Pixel</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><p style="font-size:0.58em;color:#6b7280;margin-top:8px;">+10 additional row(s) documented in the full report and JSON artifact.</p>


---

### CCPA · CPRA · CIPA · FTC ACT

# Applicable Legal Framework

<div style="margin-top:8px;">
<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CCPA/CPRA §1798.120: Right to opt out of sale and sharing</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CPRA sharing extension: Covers pixel-based data transfer to ad platforms</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">GPC mandate: `Sec-GPC: 1` is a legally binding opt-out signal</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">Fine exposure: Up to $7,500 per intentional violation per consumer</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CIPA: $5,000 statutory per-violation, no actual damages required</div></div>
</div>

---

### REMEDIATION ROADMAP

# Immediate Actions Required

<div style="display:flex;gap:12px;margin-top:10px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #ef4444;">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#ef4444;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Immediate</div>
    <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Disable <strong style='color:#14182b'>Snapchat</strong> tag in GTM until consent logic is verified</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Disable <strong style='color:#14182b'>Microsoft Clarity</strong> tag in GTM until consent logic is verified</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Disable <strong style='color:#14182b'>Klaviyo</strong> tag in GTM until consent logic is verified</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Audit sGTM container for consent signal passthrough enforcement</div></div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #3d6abb;"><div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#3d6abb;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Within 30 Days</div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Audit CMP integration against Consent Mode V2 requirements</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Verify GPC signal is mapped to CMP opt-out state</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Obtain written data processing agreements with all third-party vendors</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Fix Shopify → Consent Mode integration: opt-out must propagate denial signals (G100) to all Google tags</div></div></div>
</div>

---

### HOW WE AUDIT

# Forensic Methodology

<p style="font-size:0.75em;color:#6b7280;margin-bottom:12px;">Definitive (Consent Wiring Broken: tags fire regardless of CMP state). Independent forensic scan. No vendor access or cooperation required. Mirrors the approach used by the <strong style="color:#22c55e;">California Privacy Protection Agency</strong> in automated GPC compliance sweeps.</p>

<div style="margin-top:4px;">
<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Fresh browser context, zero prior cookies, consent denial pre-injected before page load</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Page reloaded post-denial to capture true opted-out network state</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">All network traffic captured and fingerprinted against 3,200+ vendor signatures</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Pixel endpoint detection: plaintiff law firm methodology (CIPA §631)</div></div><div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Regulatory findings cross-referenced against live enforcement database</div></div>
</div>

---

### PREPARED BY

# Kenneth Buchanan

<p style="font-size:0.72em;color:#6b7280;margin:-8px 0 0 0;">Independent forensic audit · <a href="https://kennethjbuchanan.com" style="color:#3d6abb;text-decoration:none;">kennethjbuchanan.com</a></p>

<div style="display:flex;gap:10px;margin-top:28px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Forensic Auditing</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">Post-denial traffic analysis<br>GPC signal testing<br>sGTM detection</div>
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
Audit 9ae07da0-c77c-4112-9a56-d064dc255b25 · 2026-11-05 · For compliance assessment purposes only. Consult legal counsel for enforcement risk analysis.
</div>