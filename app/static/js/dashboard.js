const socket = io();

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
