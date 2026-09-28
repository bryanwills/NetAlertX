// Chart.js instances, kept so a range switch destroys the old chart before
// building a new one on the same canvas (Chart.js throws otherwise).
var resourceHistoryChartInstances = {};

/**
 * Fetches Resource_History data for the given range ('hour'/'day'/'week'/'month')
 * and renders the four Performance-tab charts, or shows the disabled-state
 * message when no rows exist yet (collection off, or just enabled).
 */
function initResourceHistoryGraphs(range) {
  $.get('php/server/query_json.php', { file: `table_resource_history_${range}.json`, nocache: Date.now() }, function (res) {
    var rows = (res && res.data) ? res.data : [];

    if (rows.length === 0) {
      $('#resourceHistoryCharts').addClass('myhidden');
      $('#resourceHistoryDisabledMessage').removeClass('myhidden');
      return;
    }

    $('#resourceHistoryDisabledMessage').addClass('myhidden');
    $('#resourceHistoryCharts').removeClass('myhidden');

    var labels = [];
    var cpuData = [];
    var rssData = [];
    var ioReadData = [];
    var ioWriteData = [];
    var durationData = [];
    var tickFailed = [];

    function round2(n) {
      return n == null ? null : Math.round(n * 100) / 100;
    }

    rows.forEach(function (entry) {
      // hour/day rows carry resDateTime (raw); week/month rows carry bucket
      // (hourly rollup) instead - see const.py's sql_resource_history_* queries.
      var ts = entry.resDateTime || entry.bucket;
      labels.push(localizeTimestamp(ts).slice(0, 16));
      cpuData.push(round2(entry.resCpuPercent));
      rssData.push(round2(entry.resRssMb));
      // Bytes -> MB and ms -> s: raw units from the DB aren't a readable axis scale.
      ioReadData.push(entry.resIoReadBytes != null ? round2(entry.resIoReadBytes / (1024 * 1024)) : null);
      ioWriteData.push(entry.resIoWriteBytes != null ? round2(entry.resIoWriteBytes / (1024 * 1024)) : null);
      durationData.push(entry.resScanDurationMs != null ? round2(entry.resScanDurationMs / 1000) : null);
      tickFailed.push(entry.resTickFailed == 1);
    });

    renderResourceHistoryCharts(labels, cpuData, rssData, ioReadData, ioWriteData, durationData, tickFailed);
  }).fail(function () {
    console.error('Error fetching resource history data.');
  });
}

/**
 * Builds/replaces the four small-multiple Resource_History charts (CPU%,
 * memory usage MB, IO read+write MB, scan duration seconds) on the same time
 * axis. Rows written from the tick-failure `finally` path (resTickFailed = 1)
 * are rendered as visually distinct points rather than plain data, since
 * their numbers may reflect a truncated, crash-adjacent sample.
 */
function renderResourceHistoryCharts(labels, cpuData, rssData, ioReadData, ioWriteData, durationData, tickFailed) {
  var normalColor = "rgba(0, 166, 89, .8)";
  var failedColor = "#dd4b39";

  function pointColors(baseColor) {
    return tickFailed.map(function (failed) { return failed ? failedColor : baseColor; });
  }

  function destroyIfExists(key) {
    if (resourceHistoryChartInstances[key]) {
      resourceHistoryChartInstances[key].destroy();
    }
  }

  var commonScales = {
    yAxes: [{
      ticks: { beginAtZero: true, fontColor: '#A0A0A0' },
      gridLines: { color: "rgba(0, 0, 0, 0)" },
    }],
    xAxes: [{
      ticks: { fontColor: '#A0A0A0' },
      gridLines: { color: "rgba(0, 0, 0, 0)" },
    }],
  };

  destroyIfExists('cpu');
  resourceHistoryChartInstances.cpu = new Chart("ResourceCpuChart", {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: getString("Systeminfo_Performance_CPU"),
        data: cpuData,
        borderColor: normalColor,
        backgroundColor: "rgba(0, 166, 89, .2)",
        pointBackgroundColor: pointColors(normalColor),
        fill: true,
      }],
    },
    options: { legend: { display: true }, scales: commonScales, maintainAspectRatio: false, responsive: true },
  });

  destroyIfExists('rss');
  resourceHistoryChartInstances.rss = new Chart("ResourceRssChart", {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: getString("Systeminfo_Performance_Memory"),
        data: rssData,
        borderColor: "#3c8dbc",
        backgroundColor: "rgba(60, 141, 188, .2)",
        pointBackgroundColor: pointColors("#3c8dbc"),
        fill: true,
      }],
    },
    options: { legend: { display: true }, scales: commonScales, maintainAspectRatio: false, responsive: true },
  });

  destroyIfExists('io');
  resourceHistoryChartInstances.io = new Chart("ResourceIoChart", {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: getString("Systeminfo_Performance_IO_Read"),
          data: ioReadData,
          borderColor: "#00a65a",
          pointBackgroundColor: pointColors("#00a65a"),
          fill: false,
        },
        {
          label: getString("Systeminfo_Performance_IO_Write"),
          data: ioWriteData,
          borderColor: "#f39c12",
          pointBackgroundColor: pointColors("#f39c12"),
          fill: false,
        },
      ],
    },
    options: { legend: { display: true }, scales: commonScales, maintainAspectRatio: false, responsive: true },
  });

  destroyIfExists('duration');
  resourceHistoryChartInstances.duration = new Chart("ResourceDurationChart", {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: getString("Systeminfo_Performance_Duration"),
        data: durationData,
        borderColor: "#b2b6be",
        backgroundColor: "rgba(178, 182, 190, .2)",
        pointBackgroundColor: pointColors("#b2b6be"),
        fill: true,
      }],
    },
    options: { legend: { display: true }, scales: commonScales, maintainAspectRatio: false, responsive: true },
  });
}
