document.addEventListener('DOMContentLoaded', () => {
  const histCtx = document.getElementById('histogramChart').getContext('2d');

  function createHistogram(data, min, max, bin) {
    const labels = [];
    const counts = [];
    for (let start = min; start < max; start += bin) {
      labels.push(`${start}-${start + bin}`);
      counts.push(0);
    }
    data.forEach(val => {
      const idx = Math.floor((val - min) / bin);
      if (idx >= 0 && idx < counts.length) counts[idx]++;
    });
    return { labels, counts };
  }

  const hist = createHistogram(window.histData || [], 25, 65, 3);
  new Chart(histCtx, {
    type: 'bar',
    data: {
      labels: hist.labels,
      datasets: [{
        label: 'Averaged OPD Scores',
        data: hist.counts,
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 }
        }
      }
    }
  });

  const medianCtx = document.getElementById('medianChart').getContext('2d');
  const datasets = (window.datasets || []).map(ds => ({
    label: ds.label,
    data: ds.data,
    spanGaps: true
  }));

  new Chart(medianCtx, {
    type: 'line',
    data: {
      labels: window.labels || [],
      datasets: datasets
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: { suggestedMin: 25, suggestedMax: 65 }
      }
    }
  });

  const judgeCtx = document.getElementById('judgeAverages').getContext('2d');
  new Chart(judgeCtx, {
    type: 'bar',
    data: {
      labels: window.judgeLabels || [],
      datasets: [{
        label: 'Average Score',
        data: window.judgeAverages || [],
        backgroundColor: 'rgba(153, 102, 255, 0.5)',
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
});
