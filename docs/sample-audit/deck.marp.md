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

### FORENSIC PRIVACY AUDIT · US · CONFIDENTIAL

<div style="position:absolute;top:44px;right:60px;background:rgba(255,255,255,0.92);border-radius:10px;padding:10px;line-height:0;"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABLAAAAJ2CAIAAAG3JdydAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAA4ZpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMTExIDc5LjE1ODMyNSwgMjAxNS8wOS8xMC0wMToxMDoyMCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDpkYzRjNGI3NC1mYzNjLTRjY2YtYWQ4OS1kOTcyYzc2Y2ZmODEiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6QTY3RjJFODgwNDI2MTFFNkFGNkFBN0QxMDg2OEFCN0IiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6QTY3RjJFODcwNDI2MTFFNkFGNkFBN0QxMDg2OEFCN0IiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTUgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpkNGQ5NjNmMy01MDg5LTQ4OTctOWQ1Yy0wNjcwM2NlMTIyZTUiIHN0UmVmOmRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDpiYjQ2MjBlYi00YzkwLTExNzktYmI3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b5I/b8783Jn9n6sZe2FevFJZUfnHEJ+rYEHe3FnZdhwIIbxhVTW1Z36rGMiWE8eP27h6RWJi4hCfsbOru+zMuebWAX20o2Bh3twc/QMhhLfl4cNH99rbExIS0lJTRo0c+daeN/b6bWm7H/tiXHra0FsLQggAwXH3CQCEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACEEACe96cA7N37V5R1HsBxhssMd0YkkjRIFNFE82QaURZS3rLa6tRu/YVtW2dPa1bmJWvL1o28SyGJCl7wgpcKGIKZYfHU2W6AMGon5vt6/dA5HZ7Rvp/neXozt+eJjI2NmQIAnhECgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACgBACIIRGAIAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQAoAQQvYYSgxfvHLVHCBj+UYAs87xru6Oru50Ov3jv1aUlT67/gljASGELHe279K+Lw+PjY39/kmh4YAQQjbrPd+378CRyX46mkwaEQghZKdUOv3We7t+/ywQEELIfl2new8c++qWm5UUFZkVCCFkm12f7u+/fmM6W8YryowLhBCyyj93fPTDyMg0N55XNdfEQAghe7z9we7R0Rl8/qVuQY2hQcZ8oR7+dM8FZ1TBcbFo1NxACCEb7Pp0//RfEQWEELLKyTNnp/npmF9as3K50YEQwqyXSqfbj3Zk8MDFD9xveiCEMOu99d6uDB5VVlJsdCCEMOud7Dmb2bVjXGsbhBCyQfuRTF4UjZeX5eY6hUEIYZbr7D6d2QO3tD5ueiCEMOsd6jiRwaNam1cbHQghzHojo6MZPKpqTrym+h7TAyGEWe/Asa9n+pCCgvwN65qNDoQQssGZcxdm+pBXtjxjbiCEEKjXX9hsCHBnufsEzA55ubl/fW6jOYAQQvYYSgxPc8uqOXHvC4IQQrYZTCSms9n6x9bMu8etd0EIIevkRm7xJn11VeXTLWsNCoQQslNJcdFkP5o/r/rJtQ8bEQgh/OkMJhJdp3p6zl9MDE/1Dl9pcdGS+rrG+gem2KYw9ts7y99bNXf1imUVZaUTbj8wONTde673fN/AUGLqP7b2vpqGhbXlpSX2F9xSJLNr3kNouk73HDzemdn5sqhuwdqHmib80XhNC2OxSCQyxcM7u08f/qor41O1qXHxisbF9iAIIWRiNJl8f+9n0/945xTy8/Oebnm0Ml4+ze17L1z8/MCRO3WGxqIFW1ofLyostE9BCGFaUun0Ox/uzexaoFNrrK97uGnZZD9NJlN797f3X7txNxaVl5v74qb10YIC+xeEEKbyafuhc32X7u65F4msXNpQX7ugMBZNplIXLl3pOtVz5dr1P2B1vpUIQghTPRH8x/adIaz05c1tsWjUHgchhJ9dvnptz74vwlnv2lVNi2oX2O8IoRDCTSdOnTl4vDO0VdfNr2lZ/ZC9jxBC6Dq6uo92fhPm2muqq1qbH3EMECy3YYKbNwUMtoLj+i73/+fgUYcBQgiB+n5wSAbGfxXo7j3nYEAIIUTb9/zbEG628OwFQyBMrjVK0N5+f7chjGtrWXNvlTs9IYQQmJM9Z0eTSXN4deuG/Lw8c0AIITjtRzoM4fUXNhsCQggh+ujz9sAnEIlEXnt+kyMBfFiGQF3qvxr4BFQQhJBwfbz/y8An4BVREEKC1ne5P+Tlv7hxvWMAhJBwnTkX9BfmljfUFxXGHAYghIRr/6Fj4Z7wuZGVy5Y4BkAICVrIF5p/ZcszDgAQQoJ2/uLlYNceLy/L88V5EEICd/jrrmDXvvmpFgcACCGh++77gTAXXpCfH4lEHAAghBCo9Y+59S4IIcEbGRkNdu1z58QdACCEhO5s38VAz/NcZzoIIdy8vui1MBfeWF9n74MQQk7/9RthLvyBBffZ+yCEkDM4lAhz4fHyMnsfhBAAhBAAhBAAhBAAhBAAITQCAIQQyGaDiYQhgBBCuHrO9xkCCCGEq+tUryGAEEJOaXFxmAtPDA/b+yCEkDMnXh7s2keTSQcACCGhqww4hJ+1H3IAgBASunlVc4Nd+8UrVx0AIIR4RlgR8vI7urodAyCEEK6jnd8YAgghBG3Pvi8MAYSQoBUVxkJe/uWr1waGXGUGhJCALa67P/AJvLv7E4cBCCHhWrpooSG8uX2nIYAQEqj8/DxDSKfT/9r1sTmAEBKoSCRiCEOJ4W1eIwUhJEwPLvbq6E2DQ4m33t9lDiCEBKepscEQfpRMpt7YtmN01GVIEUII6qDP9dLor7z9we7jJ06aA0IIAZk/r9oQfunYiZNvbt+ZSqWMggBFxsbGTIHQJJMpb49NqKb6ntbm1eaAZ4SQ5XyJYjJ9l6+8sW2HOSCEkP2W+ezoJMpKig0BIYTst+rBRkOYUFvLWkNACCEIRYWFhvB7xUXGghBCGLa0thjCbyxfssgQEEIIRSwadbm131i51NUGEEIIyaYnHzOE/6uMlxsCQghhmVPhf/0/27jOrwUIIYRnS+vjhjCutLjIC8UIIYQoXl6Wl+tEyNna9qQhIIQQqJc2tfltwLXIEUIIV0FBfkVZacgT8PowQgihe3b9E8GufUl9nQMAIQRyHlnxYJgLX920zN5HCIGchoW1AX5qZmvbOrseIQR+8urWDUGtt2pOvLy0xH5HCIGfRCKRh0N6nXDDumY7HYQQfqWxvi4WjYaw0r9saLW7QQhhAi9vzv6vFS5vqHe7JRBCmNTzzzyVxasrjEVXLltiL4MQwqRKi4uasvfOfK6kA0IIt7ZiaUNWfqLytec32bkghDAtW9vW5WbXNwtf3tzmFhMghDADf3tuYzZ1PZAPxIIQwp30+gubs2AVG9Y1++48TCgyNjZmCnBLb2zbMaufC6ogCCHcrr+/++GdPV+iBQXVcytLSooKY9FUMvXtwOCFS1dSqdSd/c9+aVPb+J9v94EQwh2wbdcng4nE7fwJlfHyNSubxv859Wb912+0H+m48d33t3V6RyI+IwpCCHfY1ydPH/7qxEwfFS8ve+rR1RlczOXajW8/+e+B4R9GZvrAhoW1wd5YCoQQ7rp3du5NDP8wnS0fXbWivnb+7f+NJ06dOXi8czpbxqLRFze25ub6KBwIIdxNqXR6z74vrl6/MeFP6xbUNK9acTdq1HW6d/wp6YRvJVbGK9pa1hTk59s7IITwh/puYHBkdLQwFi0tLv4j/97E8PDAUCJaUFBRVmovgBACwIx5FwEAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQQAIQRACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFACAFgcv8ToL27f2r6QPA4bgKE8BwggigoiuAjPhWRqt219Xo3O3f/6P1yN3O3Ozu2W9tqFavVqtVqrQ8gDyLPEB7zeHF7c7PX7bbaCoR8X692GFohIR8y8+UtSb6hXC5nBQAAgADyN6MAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAAQQgAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAAAAQQgAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAAAAQQgAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAgCA0AQAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAACAolFqAgBYN5lMZnY+MTOXmJmfz7+dSyTS6Uz+/zc1Npw/02sfAAQhABSJpeWVp0Mjz54PLywt//xHzi8smgsAQQgAm1gul8sX4IPvnyYWl97oE1dWV60HgCAEgM1ndj5x896D8clpUwAgCAEgKB149eaducTCWzgel5TYEwBBCACFLpPJXL9zf2B49C1eZk11lWEBEIQAULgSi0ufX/vqTZ8f+Dq2NsTMC4AgBIBCNDkz+1n/V6l0eo0uv7Wl2cgACEIAKCwzc/MXr95IplJrdxU1VZXN8UZTAyAIAaBQrCaTH1++thYPEP2RQ10d1gZAEAJAofjy9jdPn4+swxVtbajf3bbD4AAIQgDYeLPziY8uX8tkMutwXeFw+He9J2wOgCAEgI339f2HD58MrNvVnek5FomUmR0AQQgAGymXy1241D8zN79u19hz5GDrtibLAyAIAWAjpdLp//7LpdVkct2usffo4Y5drZYHQBACwEZKplL5GlzTE0v8yPnTvU3xBssDIAgBYCPlcrk/f3Zl3WowWl7+r++f9bxBAAQhAGy8yze+XlpeWZ/r6tq9653uAzYHQBACwMZ7NjQyMja+DldUWRH98Gxf/q3NARCEAFAQ7jz4fq2vIhwOn+t7pzneaG0ABCEAFIrHg0PLK2v7YNHjh/bv72g3NQCCEAAKy8DQ6BpdcigUeqf7QGf7TiMDIAgBoOBkstmJ6Zm3frHR8vL3eo/H62MWBkAQAkCBSiwsvt0L3NfRfuzAvnA4ZFsABCEAFLRUOv3bLyQUCnW27zyyv7OszPEUAEEIAJtEeSTyqz83Xh87vG9vS1PcjAAIQgB4A6lUemFpaWl5ZXF5eWVldTWZSqZe/ZvJZPP//O1HRsrKIpFIeaSsMhqtrIjWVFXV1lSVlb6dI1dtdVU4HM5ms6/1wTXV7Tta2tu2V1VU/Lqry1/RwtLy0l9v8cpqcjWZv8XpZDqVy+byf5r/j9KSkvzXk3+/LK+0JN+rkUhZRTRaXVlRVVmR/1P3HAAEIQCbQ755xiYmxyam8m+XV1bX6Fqi5ZFtW+Nt27e1NMVL/lpTbyReHxufmv7h/XyE5bMzn17VVZWxmpr6utr6uppQ6M2eEJjPvJGx8Rfjk+NTM/nwW7t58zd8a0N9c7xxe/PW/Nfs/gbArxbK5XJWAOC3yGZzo+MTTwaH8i20sYeVWG3N3va29h3b1+FJffnoHRwefTo0MjufKITvQj4Rd7ftaG9tKfHrRAAEIQBrKplKPXwy8Ojp4Ft5dZY10hCr62xv27Xj7TTS/MLi48GhgaHR1WSywL874XC4Y2froa49FdGo+yoAghCAt2P05cStew8Si0ub8YuP18f27NzR2tL8Oq8ok85kXk5MDb14OfRiLJ3ObN5vWf7GHjvYtbttx5s+AhYAQQgArzwfHfvq7reF/5uxX3MgDIXKSktT6XTRHxBLSkqOHujs2r1LGQIgCAH4ZYnFpStf3Z6ZmzdFMamIRs/0HN3aUG8KAAQhAD9hYHj0y9v3XvOsDGxSBzv3HD3QZQcAQQgA/+v+oyd3H35vh+Bo3dZ8pudo+M3P2wGAIASgeDx6Onjz3gM7BNOObU3vnTzu6YUAghCAwJmYmrnYf8MDRPEgUgBBCECAZDKZjy5fK5BTq1MIwuHwub6e5niDKQCCoNQEAIH1bGjk2tff2IEfhEKhQ10dh7s6PHAUQBACUOQuXr3+cnLaDuTFamt+13uiqrLCFACCEIAit5pM/vHi5WQyZQr27Wk/fmifXwkCCEIAAmFmbv7CpX5PIA+4fAH2Hju8p22HKQAEIQBBMTYx9Wn/DTsEPAXfPXFk144WUwAgCAECZHxqWg0G3OF9e7v37bUDAIIQIFgSC4ufXLluh8CK18fOn+kNh8OmAEAQAgRLJpO5cKnfDsEUCoU+ePdkk/MKAiAIAYLp8o2vU+m0HQKoIVb3z+/1eRFRAAQhQEA9Hhh6MT5phwA62Lnn6IEuOwAgCAECKpVK37z3wA4BdOpY956dzioBgCAECLC7Dx9ls1k7BM3Zk8fbWprtAMAv8mpjAEVrNZl89Oy5HYKm9+ghNQiAIAQIuu+eDBghaPa2t3XsarMDAIIQIOieDo0YIVAqK6InjxyyAwCCECDoxqeml1dW7RAofce7jQCAIARgi1NNBE28IdYcb7QDAIIQgC0vJ6eNEChdu3cZAQBBCMArs3PzRgiOUCjklUUBEIQAvLKwuJRx+sEgqa+rDYcd0wEQhABs2eLlZIImVlttBAAEIQCvrKwKwmCJlJUZAQBBCMAr2WzOCMH6jud8xwEQhAAQSMlkyggACEIAXgmFbBAsi8vLRgBAEALwSmlpqRECZWpmLudRowAIQgDyouXlRgiUbDY7NjFpBwAEIQBbqiqjRgiap89HjACAIARgS3kkUlJSYodAeT46trC4ZAcABCEAW+rraowQNLfuPzQCAIIQgC2NsTojBM3I2PjA8KgdABCEAIEPwvqYEQLo2tffLCx54CgAghAg2Fqa4kYIoFwud+Hz/lQqbQoABCFAcEXKyuJ+SRhIyVTqvz75PP/WFAAIQoDgatu+zQgBbcJk6j8vfDqfWDAFAIIQIKB2t203QmBls9k/ffrFk+fDpgBAEAIEUXkk0tK01Q5Bdv32vY8u9+fj0BQACEKAwNnf0W6EgJuamfv3P37kdBQA/KRQLpezAkAR+/NnV2bnE3agPBL58OypmuoqUwAgCAGCYmh07IuvbtuBH1RWRM+fOVVdWWEKAAQhQCBcuNQ/PTtnB/5PtDxyrq+nvq7WFACCUBACFLnxqelPrly3Az/+ISAU6t6391BXhykABCEAxaz/1l0vK8I/UlNVefqdow2xOlMACEIAilA6nfmPCxczmYwp+BmN9bG+4921XngGQBACUGQGhkf7b921A6+juqqyp/tgS1PcFACCEIAi4YGjvPEPCqHQ7rYd3fv2VlZErQFQfJyYHiBA+o53R8vL7cDry+VyT58PLy2vmAJAEAKwuYVCoX86e8oOvJEj+zvjDTE7AAhCADa9mqrK904etwOvqTne4LwUAIIQgOLR2tJ8ZH+nHfhFFdHyc309dgAQhAAUlUNdHV27d9mBn/sRIRz6l9+dDof9qAAgCAEoOu90H9i5fZsd+Ec+ON1bEfUSRACCEIAidabnWOu2Jjvwk/eNrQ31dgAQhAAUs/d6T7S1NNuBv3Xq2GG/PQYICCemB2DL1Vt3Bodf2IG83qOHOna12QFAEAIQILe//e7B42d2CLjTJ47uam2xA4AgBCBwHj0bvPnNAzsE1rm+npamuB0ABCEAATUxNfOXK1/aIXA/DYRCfzh3pq6m2hQAghCAQFtZTf7p4uVkKmWKgCiPRP7t/HuRsjJTAAhCANiSPzR8cuX6xPSMKYpeU2PD+TO9dgAQhADw/zx4/Oz2t9/ZoYgdPdB1sHOPHQAEIQD8hLnEwoXPr2ayWVMUmZKSkj/8/nRNdZUpAAShIATg53x27eaL8Qk7FI3meMMHpz1MFABBCMDrGXk5cenLm3YoAs4tAYAgBOCNZbPZj7+4Nj07b4pNqqmx4YPTJ0OhkCkAEIQA/BrDY+OXr9+yw+YSDofff7cnH4SmAEAQAvCb5A8cl67fGn3pWYWbQ2f7zp4jB+0AgCAE4K1JLC59fPnaajJpioJVX1f74dlTJSUlpgBAEALw9g0Mj/bfumuHQlNZEf3wbF/+rSkAEIQArK07Dx59+/1TOxSCsrLSD97tbYjVmgIAQQjA+rlx5/7jwSE7bJRoeeRcX099nRQEQBACsEH8tnD9VVdWvn/6ZHVlhSkAEIQAbLyhFy/7b93NZDKF8yWVlpbE62NbG+rjDbG6mpqKaPkvfkr+ELmwtDyXSMzOL0xOz0xOz6bS6YLaeVdry6lj3SXhsLscAIIQgMKymkxdvXlnbGJyvY9toVBTY31rS3PrtuY1emGV+YXFwZEXg8OjicWl9R+2pqqy78SRfN+6jwEgCAEodHOJhRt37k9Mz6zR5UfKyna3bd+zszVWW7MhNzCbzY2Ojz8ZHH4xPrl2B9Z8B/YcObRta6N7FACCEIDNJ53JPHo6+PDJwG88gWEkUrazZdve9raCfQ2VxOLS4PDo4MiL+YXF33I5ZaWlne07D3Tuzkev+w8AghCA4rGwtDw6Nv5yanp6dm5peeXvP6C0pKSmuqqupjpeH2uKN+Tf2bw3NpPNTk3PTs7M5m/sbGJhYXHp7w/BlRXRxlhdU7xxe1O8uqrSPQQAQQgAAMCa8LpkAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAAEEIAACAIAQAAEAQAgAAIAgBAAAQhAAAAAhCAAAABCEAAIAgNAEAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAAAAQQgAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAAAAQQgAAIAgBAAAQBACAAAgCAEAABCEAAAACEIAAAAEIQAAAIIQAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAgCAEAABAEAIAACAIAQAAEIQAAAAIQgAAAAQhAAAAghAAAABBCAAAIAgBAAAQhAAAAAhCAAAABCEAAACCEAAAgKLxP0lYWpUaipKdAAAAAElFTkSuQmCC" style="height:58px;width:58px;border-radius:8px;object-fit:contain;display:block;" /></div>

# www.apple.com

## Consent Compliance Report

<div style="position:absolute;bottom:50px;left:72px;right:72px;"><div style="border-top:1px solid #e7e3d8;padding-top:18px;display:flex;justify-content:space-between;align-items:center;"><div style="display:flex;align-items:center;gap:14px;"><div><div style="font-family:'Inter';font-weight:700;font-size:0.65em;color:#14182b;line-height:1.2;">Kenneth Buchanan</div><div style="font-family:'Inter';font-weight:400;font-size:0.46em;color:#4b5563;margin-top:3px;">Consent Compliance Intelligence</div></div></div><div style="display:flex;gap:36px;align-items:flex-start;"><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Date</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">June 04, 2026</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Methodology</div><div style="font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;">Baseline Scan</div></div><div><div style="color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Audit ID</div><div style="font-family:'Inter';font-weight:500;font-size:0.48em;color:#9ca3af;letter-spacing:0.02em;">8efa1638-b8a6-4ce7-ba13-a7e48cc8d02d</div></div></div></div></div>

---

### AUDIT VERDICT

# Enforcement Not Verified

<p style="font-size:0.72em;color:#9ca3af;max-width:680px;line-height:1.6;margin-bottom:0;">No confirmed consent violations were detected at https://www.apple.com under the Inconclusive (CMP not recognised, injection unverified) methodology.</p>

<div style="display:flex;gap:10px;margin-top:22px;"><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #22c55e;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Cookie Violations</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#22c55e;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">0</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">none detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #22c55e;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Pixel Endpoints</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#22c55e;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">0</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">none detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">GCS State</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">N/A</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">not detected</div></div><div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;padding:12px 14px;border-top:3px solid #3d6abb;"><div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;">Jurisdiction</div><div style="font-family:'Inter';font-weight:800;font-size:1.7em;color:#3d6abb;line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">US</div><div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">simulated: Los Angeles, CA</div></div></div>

---

### SIGNAL ANALYSIS

# Findings at a Glance

<div style="margin-top:14px;"><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Cookie Violations</div><div style="flex:3;color:#d1d5db;font-weight:400;">None detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Network Pixel Endpoints</div><div style="flex:3;color:#d1d5db;font-weight:400;">None detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Consent Mode (GCS)</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">Server-Side GTM</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">CMP Detected</div><div style="flex:3;color:#d1d5db;font-weight:400;">Not detected</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div></div><div style="display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="flex:2.5;color:#6b7280;font-weight:200;">GPC Signal Honored</div><div style="flex:3;color:#d1d5db;font-weight:400;">Tested: opt-out signal sent</div><div style="flex:0 0 28px;text-align:center;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div></div></div>

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

<!-- _class: compact -->

### ENFORCEMENT PATTERN MAP

# Current Enforcement Themes

<div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;padding-bottom:7px;border-bottom:2px solid #d8d2c2;font-size:0.56em;color:#6b7794;text-transform:uppercase;letter-spacing:0.12em;"><div>Theme</div><div>Severity</div><div>Evidence</div><div>Action</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Vendor and third-party governance</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH</span></div><div style="color:#4b5563;line-height:1.45;">2 inventory row(s) likely require sale/sharing review</div><div style="color:#6b7280;line-height:1.45;">Confirm each ad-tech, analytics, and pixel vendor has purpose-limited contract terms and is classified in the tracking inventory.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Sensitive data / purpose limitation</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">HIGH</span></div><div style="color:#4b5563;line-height:1.45;">Sensitive context(s): video_or_streaming; 2 likely sale/sharing row(s)</div><div style="color:#6b7280;line-height:1.45;">Block advertising and behavioral tracking on sensitive-context pages unless a specific consent and purpose basis exists.</div></div><div style="display:grid;grid-template-columns:1.5fr 0.8fr 2fr 2fr;gap:14px;align-items:start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.66em;"><div style="color:#14182b;font-weight:600;">Tracking technology inventory</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#6b728012;color:#6b7280;border:1px solid #6b728022;">INFO</span></div><div style="color:#4b5563;line-height:1.45;">2 inventory row(s) generated</div><div style="color:#6b7280;line-height:1.45;">Review and export this inventory quarterly and after every tag release.</div></div>


---

<!-- _class: compact -->

### TRACKING TECHNOLOGY INVENTORY

# Vendors Requiring Review

<div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;padding-bottom:7px;border-bottom:2px solid #d8d2c2;font-size:0.56em;color:#6b7794;text-transform:uppercase;letter-spacing:0.12em;"><div>Vendor</div><div>Evidence</div><div>Sale / Sharing</div><div>GPC</div><div>Contract</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Adobe Analytics</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div><div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1fr;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #e7e3d8;font-size:0.65em;"><div style="color:#14182b;font-weight:600;">Adobe Target</div><div style="color:#4b5563;">Cookie</div><div><span style="font-family:'Inter';font-weight:600;font-size:0.55em;letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;border-radius:4px;background:#ef444412;color:#ef4444;border:1px solid #ef444422;">LIKELY</span></div><div style="color:#6b7280;">Not observed</div><div style="color:#6b7280;">Needed</div></div>


---

### CCPA · CPRA · CIPA · FTC ACT

# Applicable Legal Framework

<div style="margin-top:8px;">
<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CCPA/CPRA §1798.120: Right to opt out of sale and sharing</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CPRA sharing extension: Covers pixel-based data transfer to ad platforms</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">GPC mandate: `Sec-GPC: 1` is a legally binding opt-out signal</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">Fine exposure: Up to $7,500 per intentional violation per consumer</div></div><div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #e7e3d8;font-size:0.75em;"><div style="color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;">—</div><div style="color:#9ca3af;font-weight:200;line-height:1.6;">CIPA: $5,000 statutory per-violation, no actual damages required</div></div>
</div>

---

### REMEDIATION ROADMAP

# Maintaining Compliance

<div style="display:flex;gap:12px;margin-top:10px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #22c55e;">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:#22c55e;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;">Ongoing</div>
    <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #e7e3d8;font-size:0.73em;"><div style="flex:0 0 20px;margin-top:2px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div><div style="color:#9ca3af;font-weight:200;line-height:1.5;">Consent Mode enforcement could not be assessed in this scan. Re-audit from a region or CMP that surfaces Google Consent Mode, or verify the consent state manually.</div></div>
  </div>
  
</div>

---

### HOW WE AUDIT

# Forensic Methodology

<p style="font-size:0.75em;color:#6b7280;margin-bottom:12px;">Inconclusive (CMP not recognised, injection unverified). Independent forensic scan. No vendor access or cooperation required. Mirrors the approach used by the <strong style="color:#22c55e;">California Privacy Protection Agency</strong> in automated GPC compliance sweeps.</p>

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
Audit 8efa1638-b8a6-4ce7-ba13-a7e48cc8d02d · 2026-06-04 · For compliance assessment purposes only. Consult legal counsel for enforcement risk analysis.
</div>