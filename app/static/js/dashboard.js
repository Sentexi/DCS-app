const socket = io();

function populateTopics() {
  const debateId = window.currentDebateId;
  if (!debateId) return;
  fetch(`/debate/${debateId}/topics_json`)
    .then(r => r.json())
    .then(data => {
      const menu = document.getElementById('voteDropdownMenu');
      if (!menu) return;
      menu.innerHTML = '';
      data.topics.forEach(t => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.classList.add('dropdown-item');
        a.href = '#';
        a.dataset.topicId = t.id;
        a.textContent = t.text;
        li.appendChild(a);
        menu.appendChild(li);
      });
    });
}

function populateAssignments() {
  const debateId = window.currentDebateId;
  if (!debateId) return Promise.resolve();
  return fetch(`/debate/${debateId}/assignments_json`)
    .then(r => r.json())
    .then(data => {
      const menu = document.getElementById('speakerDropdownMenu');
      if (!menu) return;
      menu.innerHTML = '';
      data.assignments.forEach(a => {
        const li = document.createElement('li');
        li.classList.add('dropdown-item-text');
        li.textContent = `${a.role} - ${a.username} (Room ${a.room})`;
        menu.appendChild(li);
      });
      const divider = document.createElement('li');
      divider.innerHTML = '<hr class="dropdown-divider">';
      menu.appendChild(divider);
      const linkLi = document.createElement('li');
      const link = document.createElement('a');
      link.classList.add('dropdown-item');
      link.href = window.graphicUrl;
      link.textContent = 'Open Graphic';
      linkLi.appendChild(link);
      menu.appendChild(linkLi);
    });
}

function castVote(topicId) {
  const debateId = window.currentDebateId;
  fetch(`/debate/${debateId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ topic_id: topicId })
  }).then(() => {
    const dropdown = bootstrap.Dropdown.getOrCreateInstance(document.getElementById('voteDropdown'));
    dropdown.hide();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.currentDebateId && (window.votingOpen === true || window.votingOpen === "true")) {
    populateTopics();
  } else {
    const cont = document.getElementById('voteDropdownContainer');
    if (cont) cont.style.display = 'none';
  }
  if (window.currentDebateId && (window.assignmentsComplete === true || window.assignmentsComplete === "true")) {
    populateAssignments();
  }

  const voteMenu = document.getElementById('voteDropdownMenu');
  if (voteMenu) {
    voteMenu.addEventListener('click', e => {
      const target = e.target.closest('[data-topic-id]');
      if (!target) return;
      e.preventDefault();
      castVote(target.dataset.topicId);
    });
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
  const cont = document.getElementById('voteDropdownContainer');
  if (!cont) return;
  if (data.voting_open) {
    cont.style.display = 'block';
    populateTopics();
  } else {
    cont.style.display = 'none';
  }
});

socket.on('assignments_ready', data => {
  if (data.debate_id !== window.currentDebateId) return;
  populateAssignments().then(() => {
    const dd = bootstrap.Dropdown.getOrCreateInstance(document.getElementById('speakerDropdown'));
    dd.show();
  });
});
