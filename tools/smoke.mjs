// Smoke test: menu shot, one airborne mission, one runway mission, one escort mission; gear/weapon state + fps.
export default async function ({ ev, shot, sleep, log, fps }) {
  await shot('00_menu');
  const list = await ev(`CAMPAIGN.map((m,i)=>i+':'+m.id+':'+(m.start||'air')+':'+(m.spawns&&m.spawns.ally?'ally':''))`);
  log('missions', list);
  const pick = async (i, name) => {
    await ev(`launchMission(${i})`); await sleep(2500);
    const st = await ev(`({state, weapon:player.weapon, gearDown:player.gearDown, gearVis:player.obj.userData.gear.visible,
      allyGear: ally? ally.obj.userData.gear.visible : null, onGround:player.onGround, y:Math.round(player.obj.position.y)})`);
    log(name, st);
    await shot(name);
    log(name + '_fps', await fps(2500));
  };
  await pick(1, '01_m1');
  const esc = await ev(`CAMPAIGN.findIndex(m=>m.spawns&&m.spawns.ally)`);
  await pick(esc, '02_escort');
  const gnd = await ev(`CAMPAIGN.findIndex(m=>m.objectives.some(o=>o.kind==='destroyGround') && m.start!=='runway')`);
  await pick(gnd, '03_ground');
  const rw = await ev(`CAMPAIGN.findIndex(m=>m.start==='runway')`);
  await pick(rw, '04_runway');
  await ev(`gotoMenu()`);
}
