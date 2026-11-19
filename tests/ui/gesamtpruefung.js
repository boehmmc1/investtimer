// Gesamtpruefung je Ansicht: Klickflaechen, Kontrast, verwaiste Einzelworte in Ueberschriften, Begriffe in sichtbaren Texten.
(opts) => {
  const out = [], vw = document.documentElement.clientWidth;
  const sichtbar = el => { const s = getComputedStyle(el); if (s.display === 'none' || s.visibility === 'hidden') return false; if (el.closest('[hidden],[inert],dialog:not([open]),.sr-only')) return false; const d = el.closest('details'); if (d && !d.open && !el.closest('summary')) return false; for (let p = el; p; p = p.parentElement) if (parseFloat(getComputedStyle(p).opacity) === 0) return false; const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1; };
  const offen = document.querySelector('dialog[open]');
  const imBereich = el => !offen || offen.contains(el);
  const label = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : '') + ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 28) + '"';
  // Klickflaechen 44 px (Ausnahme: Links im Fliesstext)
  for (const el of document.querySelectorAll('button, a[href], select, input:not([type=hidden]), summary, [role=button], [role=menuitem]')) {
    if (!sichtbar(el) || !imBereich(el) || el.closest('[aria-hidden=true]')) continue; if (el.matches('.verlauf-band-knopf')) continue; /* Zusatzziel im Diagramm, Alternative: Chip-Leiste */
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    const imText = el.tagName === 'A' && s.display === 'inline' && el.parentElement && /^(P|LI|SPAN|SMALL|DD)$/.test(el.parentElement.tagName);
    if (imText) continue;
    if (el.matches('input[type=range],input[type=radio],input[type=checkbox]')) continue;
    if (r.height < 43.5 || r.width < 43.5) out.push('Klickflaeche ' + Math.round(r.width) + 'x' + Math.round(r.height) + ': ' + label(el));
  }
  // Kontrast (WCAG AA)
  const rgb = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(',').map(x => parseFloat(x)); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
  const lum = c => { const f = x => { x /= 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const hintergrund = el => { for (let p = el; p; p = p.parentElement) { const s = getComputedStyle(p); if (s.backgroundImage && s.backgroundImage !== 'none' && !/gradient/.test(s.backgroundImage)) return null; const c = rgb(s.backgroundColor); if (c && c.a > 0.9) return c; } return rgb(getComputedStyle(document.body).backgroundColor); };
  for (const el of document.querySelectorAll('body *')) {
    if (!sichtbar(el) || !imBereich(el)) continue;
    const eigen = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!eigen) continue;
    const s = getComputedStyle(el), c = rgb(s.color), h = hintergrund(el);
    if (!c || !h || el.closest('.film-karte,.film-mini,svg')) continue;
    if (el.matches(':disabled') || el.closest(':disabled')) continue;
    const a = lum(c), b = lum(h), k = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const gross = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && parseInt(s.fontWeight) >= 700);
    if (k < (gross ? 3 : 4.5) - 0.02) out.push('Kontrast ' + k.toFixed(2) + ': ' + label(el));
  }
  // Ueberschriften: einzelnes Wort allein in der letzten Zeile
  for (const h of document.querySelectorAll('h1,h2,h3,h4')) {
    if (!sichtbar(h) || !imBereich(h)) continue;
    const t = h.textContent.trim(); if (t.split(/\s+/).length < 3) continue;
    const rg = document.createRange(); rg.selectNodeContents(h);
    const zeilen = {}; for (const r of rg.getClientRects()) { const y = Math.round(r.top); zeilen[y] = (zeilen[y] || 0) + r.width; }
    const ys = Object.keys(zeilen).map(Number).sort((a, b) => a - b);
    if (ys.length < 2) continue;
    // letzte Zeile: Woerter zaehlen ueber Range je Wort
    const woerter = []; const tw = document.createTreeWalker(h, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) { const re = /\S+/g; let m; while ((m = re.exec(n.textContent))) { const r2 = document.createRange(); r2.setStart(n, m.index); r2.setEnd(n, m.index + m[0].length); const rr = r2.getClientRects()[0]; if (rr) woerter.push(Math.round(rr.top)); } }
    const letzte = Math.max(...woerter); if (woerter.filter(y => Math.abs(y - letzte) < 3).length === 1) out.push('Einzelwort in letzter Zeile: ' + label(h));
  }
  // Begriffe in sichtbaren Texten
  const text = (offen || document.body).innerText;
  const regeln = [[/\bfolgt\b/i, 'folgt'], [/demnächst/i, 'demnächst'], [/Entwurf/i, 'Entwurf'], [/Beispiel(?!:)/, 'Beispiel'], [/TODO/, 'TODO'], [/von 14\b|of 14\b/, 'von 14'],
    [/Anteil an der Berechnung|Share of the calculation/, 'Anteil an der Berechnung'], [/\d+\s?%/, 'Prozentzahl'], [/\bVIX\b|VVIX|\bMOVE\b|Put\/Call/, 'Fachkuerzel'], [/S&P/, 'S&P'],
    [/undefined|NaN|\[object|\{[a-z]+\}/, 'Platzhalter'], [/Lorem|ipsum/i, 'Blindtext']];
  for (const [re, name] of regeln) { const m = text.match(re); if (m && !(opts.erlaubt || []).includes(name)) out.push('Begriff „' + name + '“: …' + text.slice(Math.max(0, m.index - 30), m.index + 30).replace(/\s+/g, ' ') + '…'); }
  const ds = (text.match(/Datenstand|Data as of/g) || []).length;
  if (ds > (opts.datenstandMax ?? 2)) out.push('„Datenstand“ ' + ds + '× sichtbar');
  return [...new Set(out)];
}
