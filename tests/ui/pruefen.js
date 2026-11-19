// Sichtpruefung fuer jedes Text-Element: vollstaendig im sichtbaren Bereich (bzw. scrollbar erreichbar) und nicht ueberdeckt.
// Rueckgabe: Liste von Befunden. Aufruf im Browser: (opts)=>{...}
(opts) => {
  opts = opts || {};
  const out = [], vw = document.documentElement.clientWidth, vh = innerHeight;
  const fixe = [...document.querySelectorAll('body *')].filter(e => { const s = getComputedStyle(e); return (s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none' && s.visibility !== 'hidden' && e.getBoundingClientRect().height > 0; });
  const sichtbar = el => { const s = getComputedStyle(el); if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) return false; if (el.closest('[hidden],[inert],dialog:not([open]),.sr-only,[aria-hidden=true]')) return false; const d = el.closest('details'); if (d && !d.open && !el.closest('summary')) return false; for (let p = el; p; p = p.parentElement) if (parseFloat(getComputedStyle(p).opacity) === 0) return false; const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1; };
  const offen = document.querySelector('dialog[open]');
  const texte = [...document.querySelectorAll('h1,h2,h3,h4,p,li,button,a,label,dt,dd,span,small,b,strong,figcaption,summary,input,select')].filter(el => {
    if (!sichtbar(el)) return false; if (offen && !offen.contains(el)) return false;
    const t = (el.value !== undefined && el.tagName === 'INPUT' ? el.placeholder || el.value : [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')).trim();
    return t.length > 0 || el.tagName === 'INPUT';
  });
  const label = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : '') + ' "' + (el.textContent || el.placeholder || '').trim().replace(/\s+/g, ' ').slice(0, 30) + '"';
  for (const el of texte) {
    const r = el.getBoundingClientRect();
    // horizontal abgeschnitten (gilt immer), Scrollcontainer: Element muss in seinem Container liegen oder per Scroll erreichbar sein
    if (r.left < -1 || r.right > vw + 1) {
      let sc = el.parentElement; while (sc && !(getComputedStyle(sc).overflowX === 'auto' || getComputedStyle(sc).overflowX === 'scroll')) sc = sc.parentElement;
      if (!sc) out.push('ragt seitlich heraus: ' + label(el) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
      continue;
    }
    // Text in sich abgeschnitten (Ueberlauf versteckt)
    const s = getComputedStyle(el);
    if ((s.overflow === 'hidden' || s.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1 && !el.matches('.konto-menue-mail')) out.push('Text abgeschnitten: ' + label(el));
    // nur Elemente im Viewport auf Ueberdeckung pruefen
    if (r.bottom <= 0 || r.top >= vh) continue;
    if (opts.bereich === 'oben' && r.top > vh / 2) continue;
    if (opts.bereich === 'unten' && r.bottom < vh / 2) continue;
    const punkte = [[r.left + 2, r.top + 2], [r.right - 2, r.top + 2], [r.left + 2, r.bottom - 2], [r.right - 2, r.bottom - 2], [(r.left + r.right) / 2, (r.top + r.bottom) / 2]]
      .filter(([x, y]) => x >= 0 && x < vw && y >= 0 && y < vh);
    for (const [x, y] of punkte) {
      const oben = document.elementFromPoint(x, y);
      if (!oben || oben === el || el.contains(oben) || oben.contains(el)) continue;
      // Ueberdeckt durch ein festes/klebendes Element oder anderes Element
      let fix = fixe.find(f => f.contains(oben));
      // oben gescrollt zaehlen nur Leisten am oberen Rand, ganz unten nur Leisten am unteren Rand (Weiterscrollen ist normal)
      if (fix) { const fr = fix.getBoundingClientRect(); if ((opts.bereich === 'oben' && fr.top > vh / 2) || (opts.bereich === 'unten' && fr.bottom < vh / 2)) continue; }
      if (fix && !fix.contains(el)) { out.push('ueberdeckt von ' + label(fix) + ': ' + label(el)); break; }
      if (!fix && !opts.nurFixe) {
        // nur echte Ueberdeckung: zwischen dem obersten Element und dem gemeinsamen Vorfahren liegt etwas Deckendes
        let deckt = false;
        for (let q = oben; q && !q.contains(el); q = q.parentElement) { const st = getComputedStyle(q); const bg = st.backgroundColor.match(/rgba?\(([^)]+)\)/); const al = bg ? (bg[1].split(',')[3] === undefined ? 1 : parseFloat(bg[1].split(',')[3])) : 0;
          const textTrifft = q === oben && [...q.childNodes].some(n => { if (n.nodeType !== 3 || !n.textContent.trim()) return false; const rg = document.createRange(); rg.selectNodeContents(n); const fs = parseFloat(getComputedStyle(q).fontSize);
            /* Glyphenhoehe ~ 0,72 der Schriftgroesse, mittig in der Inhaltsbox */
            return [...rg.getClientRects()].some(b => { const m = (b.top + b.bottom) / 2, hh = fs * 0.36; return x >= b.left && x <= b.right && y >= m - hh && y <= m + hh; }); });
          if (al > 0.5 || /^(IMG|SVG|CANVAS|VIDEO)$/i.test(q.tagName) || textTrifft) { deckt = true; break; } }
        if (deckt) { out.push('ueberlagert von ' + label(oben) + ': ' + label(el)); break; }
      }
    }
  }
  if (document.documentElement.scrollWidth > vw + 1) out.push('horizontales Scrollen: ' + (document.documentElement.scrollWidth - vw) + ' px');
  return [...new Set(out)];
}
