<?php
require 'php/templates/header.php';
?>

<script>
  showSpinner();
</script>

<div class="content-wrapper changeHistoryPage spinnerTarget" id="changeHistoryPage">

  <section class="content-header">
    <h1>
      <?= lang('Navigation_ChangeHistory'); ?>
      <small><?= lang('device_history_col_changes'); ?></small>
    </h1>
  </section>

  <section class="content">
    <div class="row">
      <div class="col-xs-12">
        <div class="box">

          <!-- Filter bar -->
          <div class="box-header with-border" style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
            <select id="filterChangedBy" class="form-control" style="width:200px;"
                    onchange="loadChangeHistory()">
              <option value=""><?= lang('device_history_col_source'); ?> - All</option>
            </select>
            <select id="filterChangedColumn" class="form-control" style="width:200px;"
                    onchange="loadChangeHistory()">
              <option value=""><?= lang('device_history_col_changes'); ?> - All</option>
            </select>
          </div>

          <!-- DataTable -->
          <div class="box-body">
            <table id="changeHistoryTable" class="table table-bordered table-striped">
              <thead>
                <tr>
                  <th><?= lang('device_history_col_time'); ?></th>
                  <th><?= lang('device_history_col_source'); ?></th>
                  <th>Device</th>
                  <th><?= lang('device_history_col_changes'); ?></th>
                </tr>
              </thead>
              <tbody id="changeHistoryBody">
                <tr><td colspan="4" class="text-center">
                  <i class="fa fa-spinner fa-spin"></i>
                </td></tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div class="box-footer" style="display:flex; justify-content:space-between; align-items:center;">
            <span id="changeHistoryInfo" class="text-muted"></span>
            <div>
              <button class="btn btn-default btn-sm" id="btnPrev" onclick="changePage(-1)" disabled>
                <i class="fa fa-chevron-left"></i>
              </button>
              <span id="pageLabel" style="margin:0 8px;">1</span>
              <button class="btn btn-default btn-sm" id="btnNext" onclick="changePage(1)" disabled>
                <i class="fa fa-chevron-right"></i>
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  </section>
</div>

<script>
var _chPage   = 0;
var _chLimit  = 50;
var _chTotal  = 0;

function loadChangeHistory() {
  var changedBy     = document.getElementById('filterChangedBy').value;
  var changedColumn = document.getElementById('filterChangedColumn').value;

  var query = `
    query($changedColumn: String, $changedBy: String, $limit: Int, $offset: Int) {
      allDeviceHistoryGrouped(
        changedColumn: $changedColumn
        changedBy: $changedBy
        limit: $limit
        offset: $offset
      ) {
        count
        history {
          devGUID
          timestamp
          changedBy
          changes { changedColumn oldValue newValue }
        }
      }
    }
  `;

  var variables = {
    changedBy:     changedBy     || null,
    changedColumn: changedColumn || null,
    limit:         _chLimit,
    offset:        _chPage * _chLimit
  };

  $.ajax({
    url:    '/server/graphql',
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + getSetting('API_TOKEN') },
    data:    JSON.stringify({ query: query, variables: variables }),
    success: function(resp) {
      if (!resp.data || !resp.data.allDeviceHistoryGrouped) return;
      var result = resp.data.allDeviceHistoryGrouped;
      _chTotal = result.count;
      renderTable(result.history);
      updatePagination();
    }
  });
}

function renderTable(groups) {
  var tbody = document.getElementById('changeHistoryBody');
  if (!groups || groups.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted"><?= lang('device_history_empty_state'); ?></td></tr>';
    return;
  }
  var html = '';
  groups.forEach(function(g) {
    var sourceIcon = g.changedBy === 'user:api' || g.changedBy === 'USER'
      ? '<i class="fa fa-user" title="' + g.changedBy + '"></i>'
      : '<i class="fa fa-cog"  title="' + g.changedBy + '"></i>';
    var changesHtml = g.changes.map(function(c) {
      return '<div><code>' + escHtml(c.changedColumn) + '</code>: '
        + '<span class="text-danger">' + escHtml(c.oldValue || '∅') + '</span>'
        + ' → '
        + '<span class="text-success">' + escHtml(c.newValue || '∅') + '</span>'
        + '</div>';
    }).join('');
    html += '<tr>'
      + '<td style="white-space:nowrap">' + escHtml(g.timestamp) + '</td>'
      + '<td>' + sourceIcon + ' ' + escHtml(g.changedBy) + '</td>'
      + '<td><a href="deviceDetails.php?mac=" data-guid="' + escHtml(g.devGUID) + '">' + escHtml(g.devGUID) + '</a></td>'
      + '<td>' + changesHtml + '</td>'
      + '</tr>';
  });
  tbody.innerHTML = html;
}

function updatePagination() {
  var totalPages = Math.max(1, Math.ceil(_chTotal / _chLimit));
  document.getElementById('pageLabel').textContent = (_chPage + 1) + ' / ' + totalPages;
  document.getElementById('changeHistoryInfo').textContent =
    _chTotal + ' <?= lang('device_history_col_changes'); ?>';
  document.getElementById('btnPrev').disabled = _chPage <= 0;
  document.getElementById('btnNext').disabled = (_chPage + 1) >= totalPages;
}

function changePage(delta) {
  _chPage = Math.max(0, _chPage + delta);
  loadChangeHistory();
}

function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function populateFilters() {
  var query = `
    query {
      allDeviceHistoryGrouped(limit: 1) {
        history { changedBy changes { changedColumn } }
      }
    }
  `;
  // Fetch distinct filter values from the filter-values endpoint
  $.ajax({
    url:    '/server/devices/history/filters',
    method: 'GET',
    headers: { 'Authorization': 'Bearer ' + getSetting('API_TOKEN') },
    success: function(resp) {
      if (!resp.data) return;
      var byEl  = document.getElementById('filterChangedBy');
      var colEl = document.getElementById('filterChangedColumn');
      (resp.data.changedBy || []).forEach(function(v) {
        byEl.add(new Option(v, v));
      });
      (resp.data.changedColumn || []).forEach(function(v) {
        colEl.add(new Option(v, v));
      });
    }
  });
}

$(document).ready(function() {
  populateFilters();
  loadChangeHistory();
  hideSpinner();
});
</script>

<?php require 'php/templates/footer.php'; ?>
