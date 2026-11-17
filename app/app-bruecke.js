/* InvestTimer-App (Capacitor): verbindet die Website mit den nativen Funktionen.
   - Relative Aufrufe (/api, /data) gehen an https://investtimer.net
   - Push-Mitteilungen ueber Apple (APNs) statt Web-Push
   - Premium-Kauf ueber Apple In-App-Kauf (RevenueCat), gleiche Nutzer-ID wie im Web */
(function () {
  const cfg = window.INVESTTIMER_APP || {};
  const basis = (cfg.api || "https://investtimer.net").replace(/\/$/, "");
  const echt = window.fetch.bind(window);
  window.fetch = (url, opt) => {
    if (typeof url === "string" && /^\/(api|data)\//.test(url)) url = basis + url;
    return echt(url, opt);
  };
  const C = () => window.Capacitor;
  const plugin = n => C() && C().Plugins && C().Plugins[n];
  if (!C() || !C().isNativePlatform || !C().isNativePlatform()) return;
  document.documentElement.classList.add("ist-app");

  function nutzer() {
    const s = window.InvestTimer && window.InvestTimer.session;
    try { return s && JSON.parse(atob(s.access_token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub; } catch { return null; }
  }

  // --- Push (APNs) ---
  const P = () => plugin("PushNotifications");
  const push = {
    async status() {
      const p = await P().checkPermissions();
      if (p.receive === "denied") return "blockiert";
      return p.receive === "granted" && localStorage.getItem("investtimer-apns") ? "aktiv" : "aus";
    },
    async einschalten() {
      let p = await P().checkPermissions();
      if (p.receive !== "granted") p = await P().requestPermissions();
      if (p.receive !== "granted") return null;
      return new Promise((ok, fehler) => {
        let h1, h2;
        const fertig = () => { h1 && h1.remove(); h2 && h2.remove(); };
        Promise.resolve(P().addListener("registration", t => { fertig(); localStorage.setItem("investtimer-apns", t.value); ok(t.value); })).then(h => h1 = h);
        Promise.resolve(P().addListener("registrationError", e => { fertig(); fehler(e); })).then(h => h2 = h);
        P().register();
      });
    },
    async aus() { const t = localStorage.getItem("investtimer-apns"); localStorage.removeItem("investtimer-apns"); return t; }
  };
  if (P()) P().addListener("pushNotificationActionPerformed", () => window.InvestTimer && window.InvestTimer.loadLive && window.InvestTimer.loadLive(true));

  // --- Kauf (RevenueCat / Apple) ---
  const RC = () => plugin("Purchases");
  let rcNutzer = null;
  async function rc() {
    const uid = nutzer();
    if (!uid) throw "login";
    if (!cfg.revenuecatApple || !RC()) throw "zahlung_inaktiv";
    if (!rcNutzer) await RC().configure({ apiKey: cfg.revenuecatApple, appUserID: uid });
    else if (rcNutzer !== uid) await RC().logIn({ appUserID: uid });
    rcNutzer = uid;
    return RC();
  }
  async function kaufen(tarif) {
    const p = await rc();
    const angebote = await p.getOfferings();
    const paket = angebote && angebote.current && angebote.current.availablePackages
      .find(x => x.packageType === (tarif === "jaehrlich" ? "ANNUAL" : "MONTHLY"));
    if (!paket) throw "zahlung_inaktiv";
    try { await p.purchasePackage({ aPackage: paket }); }
    catch (e) { if (e && (e.userCancelled || String(e.code) === "1")) throw "abbruch"; throw e; }
  }
  async function wiederherstellen() { await (await rc()).restorePurchases(); }
  async function abmelden() { if (rcNutzer && RC()) { try { await RC().logOut(); } catch {} } rcNutzer = null; await push.aus(); }

  // Apple-Abos verwalten: Systemseite der Apple-ID oeffnen
  async function verwaltenApple() { try { await (await rc()).showManageSubscriptions(); } catch { location.href = "https://apps.apple.com/account/subscriptions"; } }

  window.InvestTimerApp = { push, kaufen, wiederherstellen, abmelden, verwaltenApple, kaufBereit: !!(cfg.revenuecatApple && RC()), plattform: C().getPlatform() };
})();
