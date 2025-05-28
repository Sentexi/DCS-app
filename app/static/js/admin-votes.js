document.addEventListener("DOMContentLoaded", function() {
  // Assume you have debate IDs as data attributes in your HTML
  document.querySelectorAll('[data-debate-id]').forEach(function(debateElem) {
    const debateId = debateElem.getAttribute('data-debate-id');
    // 1. Initial fetch (AJAX, only once)
    fetch(`/admin/debate/${debateId}/vote_stats`)
      .then(res => res.json())
      .then(data => updateProgressBar(debateId, data));
  });

  // 2. Setup WebSocket for live updates
  const socket = io();

  socket.on('vote_update', function(msg) {
    const debateId = msg.debate_id;
    const data = msg.vote_data;
    updateProgressBar(debateId, data);
  });

  function updateProgressBar(debateId, data) {
    const wrapper = document.querySelector(`[data-debate-id="${debateId}"] .vote-progress`);
    if (!wrapper) return;
    const { total_users, voted_users } = data;
    const pct = total_users ? Math.round((voted_users / total_users) * 100) : 0;
    wrapper.querySelector('.voted-count').textContent = voted_users;
    wrapper.querySelector('.total-count').textContent = total_users;
    wrapper.querySelector('.percent').textContent = pct;
    wrapper.querySelector('.progress-bar').style.width = pct + '%';
    wrapper.querySelector('.progress-bar').setAttribute('aria-valuenow', pct);
  }
});
