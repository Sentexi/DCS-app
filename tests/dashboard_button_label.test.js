const fs = require('fs');
const vm = require('vm');

class ClassList {
  constructor() { this.set = new Set(); }
  add(...cls) { cls.forEach(c => this.set.add(c)); }
  remove(...cls) { cls.forEach(c => this.set.delete(c)); }
}

function createButton() {
  return {
    id: 'joinLaterBtn',
    disabled: true,
    textContent: 'Join Debate',
    style: { display: 'none' },
    classList: new ClassList(),
    addEventListener: () => {}
  };
}

global.document = { addEventListener: () => {}, getElementById: () => null };
global.window = {};
global.io = () => ({ on: () => {} });
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ assignments: [] }) });

const code = fs.readFileSync('app/static/js/dashboard.js', 'utf8');
vm.runInThisContext(code);

async function runScenario(preferJudging, expected) {
  const btn = createButton();
  global.document = {
    getElementById: id => id === 'joinLaterBtn' ? btn : null,
    addEventListener: () => {}
  };
  global.window = {
    currentDebateId: 1,
    assignmentsComplete: true,
    userHasSlot: false,
    userJudgeSkill: 'Wing',
    currentDebateStyle: 'OPD',
    preferJudging: preferJudging
  };
  global.fetch = () => Promise.resolve({
    json: () => Promise.resolve({
      assignments: [
        { role: 'Free-1', room: 1 },
        { role: 'Judge-Wing', room: 1 }
      ]
    })
  });
  updateJoinLaterAvailability();
  await new Promise(r => setTimeout(r, 0));
  const text = btn.textContent.trim();
  if (text !== expected) {
    throw new Error(`expected "${expected}", got "${text}"`);
  }
}

(async () => {
  try {
    await runScenario(true, 'Join as Judge');
    await runScenario(false, 'Join Debate');
    console.log('ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
