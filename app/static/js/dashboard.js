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

function createBadge(slot) {
  const span = document.createElement('span');
  span.classList.add('role-badge');
  if (slot.user_id == window.currentUserId) span.classList.add('me');
  span.setAttribute('role', 'listitem');
  span.setAttribute('aria-label', `${slot.role} – ${slot.name}`);

  const icon = document.createElement('i');
  icon.classList.add('bi');
  if (slot.role.startsWith('Judge')) icon.classList.add('bi-gavel');
  else if (slot.role.startsWith('Free')) icon.classList.add('bi-star');
  else if (['Gov', 'OG', 'CG'].includes(slot.role)) icon.classList.add('bi-megaphone');
  else icon.classList.add('bi-patch-question');
  span.appendChild(icon);

  span.appendChild(document.createTextNode(` ${slot.role}`));
  span.appendChild(document.createElement('br'));
  span.appendChild(document.createTextNode(slot.name));
  if (slot.user_id == window.currentUserId) {
    const em = document.createElement('em');
    em.textContent = ' (You)';
    span.appendChild(em);
  }
  return span;
}

function populateGraphic() {
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
      const roomStyle = (data.room_styles && data.room_styles[room]) || window.currentDebateStyle;

      cont.innerHTML = '';

      if (roomStyle === 'OPD') {
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

  const judgeBtn = document.getElementById('judgingButton');
  if (judgeBtn) {
    if (window.currentDebateId &&
        (window.assignmentsComplete === true || window.assignmentsComplete === 'true') &&
        (window.userIsJudgeChair === true || window.userIsJudgeChair === 'true')) {
      judgeBtn.style.display = 'inline-block';
    } else {
      judgeBtn.style.display = 'none';
    }
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

function updateCurrentDebate(data) {
  const titleEl = document.querySelector('.current-debate .card-title');
  if (!titleEl) return;

  const badge = titleEl.querySelector('span.badge');
  if (data) {
    titleEl.childNodes[0].nodeValue = data.title + ' ';
    if (badge) {
      badge.textContent = data.style;
    } else {
      const span = document.createElement('span');
      span.className = 'badge bg-info';
      span.textContent = data.style;
      titleEl.appendChild(span);
    }
  } else {
    titleEl.textContent = 'No debate right now';
    if (badge) badge.remove();
  }

  const progress = document.getElementById('voteProgress');
  const progressBar = document.querySelector('#voteProgress .progress-bar');
  const infoWrap = document.getElementById('voteInfo');
  if (progress) progress.style.display = data ? 'block' : 'none';
  if (infoWrap) infoWrap.style.display = data ? 'flex' : 'none';
  if (data && progressBar && infoWrap) {
    progressBar.style.width = data.vote_percent + '%';
    progressBar.setAttribute('aria-valuenow', data.vote_percent);
    progressBar.textContent = `${data.votes_cast}/${data.votes_total}`;
    const smalls = infoWrap.querySelectorAll('small.text-muted');
    if (smalls.length >= 2) {
      smalls[0].textContent = `${data.votes_cast}/${data.votes_total} have voted`;
      smalls[1].textContent = data.vote_percent + '%';
    }
  }

  const roleEl = document.querySelector('.current-debate .fw-bold.text-primary');
  if (roleEl) {
    if (data && data.user_role) {
      roleEl.textContent = `You are ${data.user_role}`;
      roleEl.style.display = 'block';
    } else {
      roleEl.style.display = 'none';
    }
  }

  const noDebateMsg = document.getElementById('noDebateMessage');
  if (noDebateMsg) {
    noDebateMsg.style.display = data ? 'none' : 'block';
  }

  window.currentDebateId = data ? data.id : null;
  window.votingOpen = data ? data.voting_open : false;
  window.assignmentsComplete = data ? data.assignment_complete : false;
  window.currentDebateStyle = data ? data.style : '';
  window.userHasSlot = data && data.user_role ? true : false;
  window.userIsJudgeChair = data && data.is_judge_chair ? true : false;

  const voteBox = document.getElementById('voteBoxContainer');
  if (voteBox) {
    if (window.currentDebateId && window.votingOpen) {
      voteBox.style.display = 'block';
      populateVoteBox();
    } else {
      voteBox.style.display = 'none';
    }
  }

  const graphicCont = document.getElementById('graphicContainer');
  if (graphicCont) {
    if (window.currentDebateId && window.assignmentsComplete && window.userHasSlot) {
      populateGraphic();
    } else {
      graphicCont.style.display = 'none';
    }
  }

  const judgeBtn = document.getElementById('judgingButton');
  if (judgeBtn) {
    if (window.currentDebateId && window.assignmentsComplete && window.userIsJudgeChair) {
      judgeBtn.style.display = 'inline-block';
      if (data && data.active) {
        judgeBtn.classList.remove('disabled');
        judgeBtn.removeAttribute('aria-disabled');
        judgeBtn.href = `/debate/${data.id}/judging`;
      } else {
        judgeBtn.classList.add('disabled');
        judgeBtn.setAttribute('aria-disabled', 'true');
        judgeBtn.removeAttribute('href');
      }
    } else {
      judgeBtn.style.display = 'none';
    }
  }
}

function buildDebateCards(cont, debates, badgeClass) {
  cont.innerHTML = '';
  if (!debates.length) {
    const div = document.createElement('div');
    div.className = 'text-center text-muted my-4';
    if (cont.id === 'active') div.textContent = 'No other active debates.';
    else if (cont.id === 'past') div.textContent = 'No past debates.';
    else div.textContent = 'No upcoming debates.';
    cont.appendChild(div);
    return;
  }
  debates.forEach(d => {
    const card = document.createElement('div');
    card.className = 'card debate-card mb-3';
    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h6');
    title.className = 'card-title';
    title.textContent = d.title;
    const span = document.createElement('span');
    span.className = 'badge ' + badgeClass;
    span.textContent = d.style;
    const link = document.createElement('a');
    link.href = `/debate/${d.id}`;
    link.className = 'stretched-link';
    body.append(title, span, link);
    card.appendChild(body);
    cont.appendChild(card);
  });
}

function updateDebateLists(data) {
  const activeCont = document.getElementById('active');
  const pastCont = document.getElementById('past');
  const upcomingCont = document.getElementById('upcoming');
  if (!activeCont || !pastCont || !upcomingCont) return;

  const activeDebates = data.active_debates.filter(d => d.active);
  const pastDebates = data.past_debates.filter(d => !d.active && d.assignment_complete);
  const upcomingDebates = data.upcoming_debates.filter(d => !d.active && !d.assignment_complete);

  buildDebateCards(activeCont, activeDebates, 'bg-info');
  buildDebateCards(pastCont, pastDebates, 'bg-secondary');
  buildDebateCards(upcomingCont, upcomingDebates, 'bg-warning text-dark');

  const openCount = (data.current_debate && data.current_debate.active ? 1 : 0) + activeDebates.length;
  if (openCount === 1) {
    if (data.current_debate && data.current_debate.active) {
      window.currentDebateId = data.current_debate.id;
    } else {
      window.currentDebateId = activeDebates[0].id;
    }
  } else {
    window.currentDebateId = null;
  }
}

function fetchDebateLists() {
  fetch('/dashboard/debates_json')
    .then(r => r.json())
    .then(data => {
      updateDebateLists(data);
      updateCurrentDebate(data.current_debate);
    });
}

socket.on('debate_list_update', () => {
  if (typeof fetchDebateLists === 'function') {
    fetchDebateLists();
  } else {
    location.reload();
  }
});
