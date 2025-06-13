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

function showGraphic() {
  if (!(window.hasSlot === true || window.hasSlot === 'true')) return;
  const debateId = window.currentDebateId;
  const cont = document.getElementById('graphicContainer');
  if (!debateId || !cont) return;
  cont.innerHTML = `<iframe src="/debate/${debateId}/graphic"></iframe>`;
  cont.style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.currentDebateId && (window.votingOpen === true || window.votingOpen === 'true')) {
    populateVoteBox();
  } else {
    const cont = document.getElementById('voteBoxContainer');
    if (cont) cont.style.display = 'none';
  }
  if (window.currentDebateId && (window.assignmentsComplete === true || window.assignmentsComplete === 'true')) {
    showGraphic();
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
  showGraphic();
});
