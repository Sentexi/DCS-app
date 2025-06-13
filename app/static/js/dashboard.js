const socket = io();

function populateVoteBox() {
  const debateId = window.currentDebateId;
  if (!debateId) return;
  Promise.all([
    fetch(`/debate/${debateId}/topics_json`).then(r => r.json()),
    fetch(`/debate/${debateId}/vote_status_json`).then(r => r.json())
  ]).then(([topics, status]) => {
    const cont = document.getElementById('voteBoxContainer');
    if (!cont) return;
    cont.innerHTML = '';
    const list = document.createElement('ul');
    topics.topics.forEach(t => {
      const li = document.createElement('li');
      li.textContent = t.text + ' ';
      if (status.user_votes.includes(t.id)) {
        const strong = document.createElement('strong');
        strong.textContent = '\u2014 You voted';
        li.appendChild(strong);
      } else if (status.votes_left > 0) {
        const btn = document.createElement('button');
        btn.classList.add('btn', 'btn-primary', 'btn-sm');
        btn.dataset.topicId = t.id;
        btn.textContent = 'Vote';
        li.appendChild(btn);
      }
      list.appendChild(li);
    });
    const p = document.createElement('p');
    p.classList.add('mt-2');
    p.textContent = `You have ${status.votes_left} vote${status.votes_left == 1 ? '' : 's'} left for this debate.`;
    cont.appendChild(list);
    cont.appendChild(p);
    cont.style.display = 'block';

    list.querySelectorAll('button[data-topic-id]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        castVote(btn.dataset.topicId);
      });
    });
  });
}

function castVote(topicId) {
  const debateId = window.currentDebateId;
  fetch(`/debate/${debateId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ topic_id: topicId })
  }).then(() => populateVoteBox());
}

<<<<<<< aiv06p-codex/implement-populategraphic-function-and-update-ui
function createBadge(slot) {
  const span = document.createElement('span');
  span.classList.add('role-badge');
  if (slot.user_id == window.currentUserId) span.classList.add('me');
  span.setAttribute('role', 'listitem');
  span.setAttribute('aria-label', `${slot.role} – ${slot.username}`);

  const icon = document.createElement('i');
  icon.classList.add('bi');
  if (slot.role.startsWith('Judge')) icon.classList.add('bi-gavel');
  else if (slot.role.startsWith('Free')) icon.classList.add('bi-star');
  else if (['Gov', 'OG', 'CG'].includes(slot.role)) icon.classList.add('bi-megaphone');
  else icon.classList.add('bi-patch-question');
  span.appendChild(icon);

  span.appendChild(document.createTextNode(` ${slot.role}`));
  span.appendChild(document.createElement('br'));
  span.appendChild(document.createTextNode(slot.username));
  if (slot.user_id == window.currentUserId) {
    const em = document.createElement('em');
    em.textContent = ' (You)';
    span.appendChild(em);
  }
  return span;
}

function populateGraphic() {
=======
function showGraphic() {
  if (!(window.hasSlot === true || window.hasSlot === 'true')) return;
>>>>>>> dynamic_dashboard
  const debateId = window.currentDebateId;
  const cont = document.getElementById('graphicContainer');
  if (!debateId || !cont) return;

  fetch(`/debate/${debateId}/assignments_json`)
    .then(r => r.json())
    .then(data => {
      const mySlot = data.assignments.find(a => a.user_id == window.currentUserId);
      if (!mySlot) return;
      const room = mySlot.room;
      const slots = data.assignments.filter(a => a.room == room);

      cont.innerHTML = '';

      if (window.currentDebateStyle === 'OPD') {
        const diagram = document.createElement('div');
        diagram.className = 'diagram-opd';

        const gov = document.createElement('div');
        gov.className = 'bench gov-bench';
        const gt = document.createElement('h5');
        gt.className = 'bench-title';
        gt.textContent = 'Government';
        gov.appendChild(gt);
        slots.filter(s => s.role === 'Gov').forEach(s => gov.appendChild(createBadge(s)));

        const free = document.createElement('div');
        free.className = 'free-area';
        const ft = document.createElement('h6');
        ft.textContent = 'Free Speakers';
        free.appendChild(ft);
        const freeSlots = slots.filter(s => s.role.startsWith('Free'));
        if (freeSlots.length) {
          freeSlots.forEach(s => free.appendChild(createBadge(s)));
        } else {
          const ph = document.createElement('span');
          ph.className = 'placeholder';
          ph.textContent = 'No Free Speaker';
          free.appendChild(ph);
        }

        const opp = document.createElement('div');
        opp.className = 'bench opp-bench';
        const ot = document.createElement('h5');
        ot.className = 'bench-title';
        ot.textContent = 'Opposition';
        opp.appendChild(ot);
        slots.filter(s => s.role === 'Opp').forEach(s => opp.appendChild(createBadge(s)));

        diagram.append(gov, free, opp);
        cont.appendChild(diagram);

        const judges = document.createElement('div');
        judges.className = 'judges-row mt-3';
        const judgeSlots = slots.filter(s => s.role.startsWith('Judge'));
        if (judgeSlots.length) {
          judgeSlots.forEach(s => judges.appendChild(createBadge(s)));
        } else {
          const ph = document.createElement('span');
          ph.className = 'placeholder';
          ph.textContent = 'No Judges Assigned';
          judges.appendChild(ph);
        }
        cont.appendChild(judges);
      } else {
        const diagram = document.createElement('div');
        diagram.className = 'diagram-bp';
        ['OG', 'OO', 'CG', 'CO'].forEach(team => {
          const card = document.createElement('div');
          card.className = 'bp-team-card mb-3 mb-md-0';
          const title = document.createElement('h6');
          title.className = 'bp-title';
          title.textContent = team;
          card.appendChild(title);
          const ts = slots.filter(s => s.role === team);
          if (ts.length) {
            ts.forEach(s => card.appendChild(createBadge(s)));
          } else {
            const ph = document.createElement('span');
            ph.className = 'placeholder';
            ph.textContent = 'Empty';
            card.appendChild(ph);
          }
          diagram.appendChild(card);
        });
        cont.appendChild(diagram);

        const judges = document.createElement('div');
        judges.className = 'judges-row mt-3';
        slots.filter(s => s.role.startsWith('Judge'))
          .forEach(s => judges.appendChild(createBadge(s)));
        cont.appendChild(judges);
      }

      cont.style.display = 'block';
    });
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.currentDebateId && (window.votingOpen === true || window.votingOpen === 'true')) {
    populateVoteBox();
  } else {
    const cont = document.getElementById('voteBoxContainer');
    if (cont) cont.style.display = 'none';
  }
  if (window.currentDebateId &&
      (window.assignmentsComplete === true || window.assignmentsComplete === 'true') &&
      (window.userHasSlot === true || window.userHasSlot === 'true')) {
    populateGraphic();
  }
});

socket.on('vote_update', data => {
  const currentDebateId = window.currentDebateId;
  if (!currentDebateId || data.debate_id !== currentDebateId) return;

  const votedUsers = data.vote_data.voted_users;
  const totalUsers = data.vote_data.total_users;
  const percent = totalUsers > 0 ? Math.round((votedUsers / totalUsers) * 100) : 0;

  const progressBar = document.querySelector('.progress-bar');
  if (progressBar) {
    progressBar.style.width = percent + '%';
    progressBar.setAttribute('aria-valuenow', percent);
    progressBar.textContent = `${votedUsers}/${totalUsers}`;
  }

  document.querySelectorAll('.text-muted').forEach(el => {
    if (el.textContent.includes('have voted')) {
      el.textContent = `${votedUsers}/${totalUsers} have voted`;
    } else if (el.textContent.includes('%')) {
      el.textContent = percent + '%';
    }
  });
});

socket.on('debate_status', data => {
  if (data.debate_id !== window.currentDebateId) return;
  const cont = document.getElementById('voteBoxContainer');
  if (!cont) return;
  if (data.voting_open) {
    cont.style.display = 'block';
    populateVoteBox();
  } else {
    cont.style.display = 'none';
  }
});

socket.on('assignments_ready', data => {
  if (data.debate_id !== window.currentDebateId) return;
  if (window.userHasSlot === true || window.userHasSlot === 'true') {
    populateGraphic();
  }
});
