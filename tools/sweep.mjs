// Regression sweep: every HELIOS mission, every B-Team mission, endless mode, every cutscene, menu.
// Per mission: launch, run SWEEP_MS real time (player kept alive), record fps + draw calls + exceptions.
// Env: SWEEP_MS (default 3000), SWEEP_SHOTS=1 (screenshot per mission), SWEEP_ONLY="helios:3,bteam:0" (subset).
export default async function ({ ev, shot, sleep, log, fps, errors }) {
  const MS = +(process.env.SWEEP_MS || 3000);
  const SHOTS = process.env.SWEEP_SHOTS === '1';
  const ONLY = (process.env.SWEEP_ONLY || '').split(',').filter(Boolean);
  const want = (c, i) => !ONLY.length || ONLY.includes(c + ':' + i);
  const rows = [];
  // per-frame scene cost: renderer.info auto-resets per render() call (post-FX passes), so accumulate over a few frames
  await ev(`window.frameInfo = () => new Promise(res => { const r = renderer.info; r.autoReset = false; r.reset(); const f0 = r.render.frame; let n = 0;
    const step = () => { if (++n < 4) { requestAnimationFrame(step); return; } const frames = Math.max(1, r.render.frame - f0); const o = { calls: Math.round(r.render.calls / frames), tris: Math.round(r.render.triangles / frames), frames }; r.autoReset = true; res(o); };
    requestAnimationFrame(step); }), true`);
  await ev(`window.__keepAlive = setInterval(()=>{ try{ if(state==='playing'){ player.hp = player.maxHp||CFG.playerHP; } }catch(e){} }, 250), true`);
  const run = async (camp, i) => {
    const before = errors().exceptions.length + errors().consoleErrors.length;
    const setup = camp === 'helios' ? `activeCampaign=CAMPAIGN; campaignId='helios';` : `activeCampaign=BTEAM_CAMPAIGN; campaignId='bteam';`;
    let st;
    try {
      await ev(`${setup} launchMission(${i}); true`);
      await sleep(Math.max(600, MS - 1500));
      const f = await fps(1500);
      st = await ev(`frameInfo().then(fi=>({ id: activeCampaign[${i}].id, state, calls: fi.calls, tris: fi.tris,
        progs: renderer.info.programs ? renderer.info.programs.length : null, geos: renderer.info.memory.geometries, tex: renderer.info.memory.textures,
        enemies: enemies.length, boss: !!boss, weapon: player.weapon, gear: player.gearDown, onGround: player.onGround, lvl: GFX.level() }))`);
      st.fps = f.fps; st.p95 = f.p95;
      if (SHOTS) await shot(`sweep_${camp}_${String(i).padStart(2, '0')}_${st.id}`);
    } catch (e) { st = { err: String(e).slice(0, 300) }; }
    const after = errors().exceptions.length + errors().consoleErrors.length;
    st.camp = camp; st.i = i; st.newErrors = after - before;
    rows.push(st); log('mission', st);
  };
  const nH = await ev(`CAMPAIGN.length`), nB = await ev(`BTEAM_CAMPAIGN.length`);
  for (let i = 0; i < nH; i++) if (want('helios', i)) await run('helios', i);
  for (let i = 0; i < nB; i++) if (want('bteam', i)) await run('bteam', i);
  if (!ONLY.length || ONLY.includes('endless')) {
    try { await ev(`activeCampaign=CAMPAIGN; campaignId='helios'; startEndless(); true`); await sleep(MS); log('endless', await ev(`frameInfo().then(fi=>({state, enemies:enemies.length, calls:fi.calls, tris:fi.tris}))`)); if (SHOTS) await shot('sweep_endless'); }
    catch (e) { log('endless ERR', String(e)); }
  }
  if (!ONLY.length || ONLY.includes('cutscenes')) {
    const keys = await ev(`Object.keys(CUTSCENES).concat(Object.keys(BTEAM_CUTSCENES))`);
    for (const k of keys) {
      try { await ev(`showCutscene(${JSON.stringify(k)}, ()=>{}); true`); await sleep(350); }
      catch (e) { log('cutscene ERR', k, String(e)); }
    }
    if (SHOTS && keys.length) { await ev(`showCutscene(${JSON.stringify(keys[0])}, ()=>{}); true`); await sleep(1200); await shot('sweep_cutscene_' + keys[0]); }
    log('cutscenes', keys.length);
  }
  await ev(`clearInterval(window.__keepAlive); gotoMenu(); true`);
  await sleep(800);
  if (SHOTS) await shot('sweep_menu');
  const bad = rows.filter(r => r.err || r.newErrors);
  log('SWEEP', { missions: rows.length, withErrors: bad.length, minFps: Math.min(...rows.map(r => r.fps || 0)), maxCalls: Math.max(...rows.map(r => r.calls || 0)) });
}
