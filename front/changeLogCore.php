<script>
  showSpinner();
</script>
  <?php require 'php/templates/skel_change_log.php'; ?>
  <section class="content">    
    <div class="row">
      <div class="col-xs-12">
        <div class="box">

          <!-- Filter bar -->
          <div class="box-header " style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
            <select id="filterChangedBy" class="form-control" style="width:200px;">
              <option value=""><?= lang('device_history_col_source'); ?> - All</option>
            </select>
            <select id="filterChangedColumn" class="form-control" style="width:200px;">
              <option value=""><?= lang('device_history_col_dropdown'); ?> - All</option>
            </select>
          </div>

          <!-- DataTable -->
          <div class="box-body">
            <table id="changeHistoryTable" class="table table-bordered table-striped">
              <thead>
                <tr>
                  <th><?= lang('device_history_col_time'); ?></th>
                  <th><?= lang('device_history_col_source'); ?></th>
                  <th><?= lang('gen_device'); ?></th>                  
                  <th><?= lang('device_history_table_title_changes'); ?></th>
                </tr>
              </thead>
              <tbody id="changeHistoryBody">
                <tr><td colspan="4" class="text-center">
                  <i class="fa fa-spinner fa-spin"></i>
                </td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>


<script>

let historyTable;
const urlMac = getMacFromUrl();

function initializeHistoryTable() {

    historyTable = $('#changeHistoryTable').DataTable({

        processing: true,
        serverSide: true,
        paging: true,
        searching: true,
        ordering: true,
        info: true,
        autoWidth: false,

        pageLength: getSetting("UI_DEFAULT_PAGE_SIZE"),
        lengthMenu: getLengthMenu(getSetting("UI_DEFAULT_PAGE_SIZE")),

        ajax: function (dtRequest, callback) {

            const limit = parseInt(dtRequest.length, 10) || 50;
            const start = parseInt(dtRequest.start, 10) || 0;
            const page = Math.floor(start / limit) + 1;
            const search = dtRequest.search?.value || null;
            const order = dtRequest.order?.[0];

            devGUID = null;

            if(urlMac)
            {
                devGUID = getDevDataByMac(urlMac,"devGUID") 
            }

            const columns = [
                "timestamp",
                "changedBy",
                "devGUID",
                null // changes column (not sortable)
            ];

            const sort = [];

            if (order) {
                const field = columns[order.column];
                if (field) {
                    sort.push({
                        field: field,
                        order: order.dir
                    });
                }
            }

            const query = `
                query(
                    $devGUID:String,
                    $changedColumn:String,
                    $changedBy:String,
                    $options:PageQueryOptionsInput
                ){
                    deviceHistoryGrouped(
                        devGUID:$devGUID
                        changedColumn:$changedColumn
                        changedBy:$changedBy
                        options:$options
                    ){
                        count
                        history{
                            devGUID
                            timestamp
                            changedBy
                            changes{
                                changedColumn
                                oldValue
                                newValue
                            }
                        }
                    }
                }
            `;
            
            console.log(query)

            $.ajax({
                url: "/server/graphql",
                method: "POST",
                contentType: "application/json",
                headers: {
                    Authorization: "Bearer " + getSetting("API_TOKEN")
                },

                data: JSON.stringify({
                    query,
                    variables: {
                        changedBy: $('#filterChangedBy').val() || null,
                        changedColumn: $('#filterChangedColumn').val() || null,
                        devGUID: devGUID,
                        options: {
                            page: page,
                            limit: limit,
                            sort: sort,
                            search: search
                        }
                    }
                }),

                success: function (resp) { 
                    const result = resp?.data?.deviceHistoryGrouped;

                    callback({
                        data: result?.history || [],
                        recordsTotal: result?.count || 0,
                        recordsFiltered: result?.count || 0
                    });

                    hideSpinner();
                    hideChangeLogSkeleton();
                },

                error: function () {
                    callback({
                        data: [],
                        recordsTotal: 0,
                        recordsFiltered: 0
                    });
                }
            });
        },

        columns: [
            { data: "timestamp" },
            { data: "changedBy" },
            { data: "devGUID" },
            { data: "changes" }
        ],

        columnDefs: [
            {
                targets: 0,
                render: function (data) {
                    return localizeTimestamp(data);
                }
            },
            {
                targets: 1,
                render: function (data) {
                   
                    return `${escHtml(data)}`;
                }
            },
            {
                targets: 2,
                render: function (data) {
                    return `<a href="deviceDetails.php?mac=${getDevDataByGuid(escHtml(data), "devMac")}" data-guid="${escHtml(data)}">${getDevDataByGuid(escHtml(data), "devName")} (${escHtml(data)}) </a>`;
                }
            },
            {
                targets: 3,
                orderable: false,
                searchable: false,
                render: function (changes) {

                    if (!Array.isArray(changes)) return "";

                    return changes.map(c =>
                        `<div>
                            <code>${escHtml(c.changedColumn)}</code>:
                            <span class="text-danger">${escHtml(c.oldValue || "∅")}</span>
                            →
                            <span class="text-success">${escHtml(c.newValue || "∅")}</span>
                        </div>`
                    ).join("");
                }
            }
        ],

        language: {
            processing: '<i class="fa fa-spinner fa-spin"></i>',
            emptyTable: "<?= lang('device_history_empty_state'); ?>"
        }
    });
}

function bindHistoryFilters() {

    $('#filterChangedBy, #filterChangedColumn').on('change', function () {
        if (historyTable) {            
            showSpinner();
            historyTable.ajax.reload(null, true); // reset paging
        }
    });
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

   url = '/server/devices/history/filters';

   if(urlMac)
   {
        url = `${url}?devGUID=${getDevDataByMac(urlMac,"devGUID")}`; 
   } 

  // Fetch distinct filter values from the filter-values endpoint
  $.ajax({
    url:    url,
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

      // trigger initial load AFTER filters are ready
      $('#changeHistoryTable').DataTable().ajax.reload();
    }
  });
}

function getMacFromUrl() {
    return new URLSearchParams(window.location.search).get('mac');
}

$(document).ready(function () {
    callAfterAppInitialized(initChangeLog);
});

function initChangeLog(){
    populateFilters();
    initializeHistoryTable();
    bindHistoryFilters();
}

function hideChangeLogSkeleton() {
  $('#change-log-skeleton').fadeOut(0, function() { $(this).hide(); });
}

function showChangeLogSkeleton() {
  var $skel = $('#change-log-skeleton');
  $skel.stop(true, true).fadeIn(0);
}

</script>