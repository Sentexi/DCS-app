document.addEventListener("DOMContentLoaded", function() {
  function refreshVoteProgress() {
    document.querySelectorAll('.vote-progress').forEach(async function(wrapper) {
      // Find the closest ancestor with data-debate-id
      const parent = wrapper.closest('[data-debate-id]');
      if (!parent) return;
      const debateId = parent.getAttribute('data-debate-id');
      if (!debateId) return;
      try {
        const res = await fetch(`/admin/debate/${debateId}/vote_stats`);
        if (!res.ok) return;
        const data = await res.json();
        const { total_users, voted_users } = data;
        const pct = total_users ? Math.round((voted_users / total_users) * 100) : 0;
        wrapper.querySelector('.voted-count').textContent = voted_users;
        wrapper.querySelector('.total-count').textContent = total_users;
        wrapper.querySelector('.percent').textContent = pct;
        wrapper.querySelector('.progress-bar').style.width = pct + '%';
        wrapper.querySelector('.progress-bar').setAttribute('aria-valuenow', pct);
      } catch (e) {
        // You can add error handling here
      }
    });
  }
  refreshVoteProgress();
  setInterval(refreshVoteProgress, 10000);
});
