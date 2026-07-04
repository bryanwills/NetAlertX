<!--
#---------------------------------------------------------------------------------#
#  NetAlertX                                                                       #
#  Open Source Network Guard / WIFI & LAN intrusion detector                      #
#                                                                                 #
#  deviceDetails.php - Front module. Device management page                       #
#---------------------------------------------------------------------------------#
#    Puche      2021        pi.alert.application@gmail.com   GNU GPLv3            #
#    jokob-sk   2022        jokob.sk@gmail.com               GNU GPLv3            #
#    leiweibau  2022        https://github.com/leiweibau     GNU GPLv3            #
#    cvc90      2023        https://github.com/cvc90         GNU GPLv3            #
#---------------------------------------------------------------------------------#
-->

<?php
  require 'php/templates/header.php';
?>

<script>
  showSpinner();
</script>

<!-- Page ------------------------------------------------------------------ -->
  <div class="content-wrapper" id="deviceDetailsPage">

    <?php require 'php/templates/skel_device_details.php'; ?>

<!-- Content header--------------------------------------------------------- -->
    <section class="content-header">

      <h1 id="pageTitle">
        &nbsp<small>Quering device info...</small>
      </h1>

      <div id="devicePageInfoPlc" class="card-body bg-light">
          <div class="small-box panel  rounded">
              <div class="inner text-center">

              </div>
          </div>
      </div>

      <!-- period selector -->
      <span class="breadcrumb" style="top: 0px;">
        <select class="form-control" id="period" onchange="javascript: periodChanged();">
          <option value="1 day"><?= lang('DevDetail_Periodselect_today');?></option>
          <option value="7 days"><?= lang('DevDetail_Periodselect_LastWeek');?></option>
          <option value="1 month" selected><?= lang('DevDetail_Periodselect_LastMonth');?></option>
          <option value="1 year"><?= lang('DevDetail_Periodselect_LastYear');?></option>
          <option value="100 years"><?= lang('DevDetail_Periodselect_All');?></option>
        </select>
      </span>
    </section>

<!-- Main content ---------------------------------------------------------- -->
    <section class="content">

      <div id="TopSmallBoxes"></div>

<!-- tab control------------------------------------------------------------ -->
      <div class="row">
        <div class="col-lg-12 col-sm-12 col-xs-12">
        <!-- <div class="box-transparent"> -->
          <div id="navDevice" class="nav-tabs-custom">
            <ul class="nav nav-tabs" style="font-size:16px;">
              <li>
                <a id="tabDetails"  href="#panDetails"  data-toggle="tab">
                  <i class="fa fa-info-circle"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Details');?>
                    </span>
                </a>
                </li>
                <li>
                <a id="tabTools"    href="#panTools"    data-toggle="tab">
                  <i class="fa fa-screwdriver-wrench"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Tools');?>
                    </span>
                </a>
                </li>
              <li>
                <a id="tabSessions" href="#panSessions" data-toggle="tab">
                  <i class="fa fa-list-ol"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Sessions');?>
                    </span>
                </a>
                </li>
              <li>
                <a id="tabPresence" href="#panPresence" data-toggle="tab">
                  <i class="fa fa-calendar"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Presence');?>
                    </span>
                </a>
                </li>
              <li>
                <a id="tabEvents"   href="#panEvents"   data-toggle="tab">
                  <i class="fa fa-bolt"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Events');?>
                    </span>
                </a>
                </li>
              <li>
                <a id="tabPlugins"  href="#panPlugins"  data-toggle="tab">
                  <i class="fa fa-plug"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('DevDetail_Tab_Plugins');?>
                    </span>
                </a>
                </li>
              <li>
                <a id="tabHistory" href="#panHistory" data-toggle="tab">
                  <i class="fa fa-clock-rotate-left"></i>
                    <span class="dev-detail-tab-name">
                      <?= lang('device_history_tab_title');?>
                    </span>
                </a>
                </li>

              <div class="btn-group pull-right">
                <button type="button" class="btn btn-default"  style="padding: 10px; min-width: 30px;"
                  id="btnPrevious" onclick="recordSwitch('prev')"> <i class="fa fa-chevron-left"></i> </button>

                <div class="btn pa-btn-records"  style="padding: 10px; min-width: 30px; margin-left: 1px;"
                  id="txtRecord"     > 0 / 0 </div>

                <button type="button" class="btn btn-default"  style="padding: 10px; min-width: 30px; margin-left: 1px;"
                  id="btnNext"     onclick="recordSwitch('next')"> <i class="fa fa-chevron-right"></i> </button>
              </div>
            </ul>

            <div class="tab-content spinnerTarget" >
              <div class="tab-pane fade" id="panDetails">
                <?php
                  require 'deviceDetailsEdit.php';
                ?>
              </div>
              <div class="tab-pane fade" id="panSessions">
              <?php
                  require 'deviceDetailsSessions.php';
                ?>
              </div>
              <div class="tab-pane fade" id="panTools">
                <?php
                  require 'deviceDetailsTools.php';
                ?>
              </div>
              <div class="tab-pane fade" id="panPresence">
                <?php
                  // Include the other page
                  include 'deviceDetailsPresence.php';
                ?>
              </div>
              <div class="tab-pane fade " id="panEvents">
              <?php
                  // Include the other page
                  include 'deviceDetailsEvents.php';
                ?>
              </div>
              <div class="tab-pane fade table-responsive" id="panPlugins">
                <?php
                  // Include the other page
                  include 'pluginsCore.php';
                ?>
              </div>

              <div class="tab-pane fade" id="panHistory">
                <?php require 'php/templates/skel_device_details_tab_history.php'; ?>
                <!-- Filter bar -->
                <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:12px;">
                  <select id="histFilterBy" class="form-control" style="width:180px;"
                          onchange="loadHistoryData()">
                    <option value=""><?= lang('device_history_col_source');?> — All</option>
                  </select>
                  <select id="histFilterCol" class="form-control" style="width:180px;"
                          onchange="loadHistoryData()">
                    <option value=""><?= lang('device_history_col_changes');?> — All</option>
                  </select>
                </div>
                <!-- Table -->
                <table class="table table-bordered table-striped table-hover">
                  <thead>
                    <tr>
                      <th><?= lang('device_history_col_time');?></th>
                      <th><?= lang('device_history_col_source');?></th>
                      <th><?= lang('device_history_col_changes');?></th>
                    </tr>
                  </thead>
                  <tbody id="historyTableBody">
                    <tr><td colspan="3" class="text-center"><i class="fa fa-spinner fa-spin"></i></td></tr>
                  </tbody>
                </table>
                <!-- Pagination -->
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                  <span id="histInfo" class="text-muted" style="font-size:12px;"></span>
                  <div>
                    <button class="btn btn-default btn-xs" id="histBtnPrev" onclick="histChangePage(-1)" disabled>
                      <i class="fa fa-chevron-left"></i>
                    </button>
                    <span id="histPageLabel" style="margin:0 6px;font-size:12px;">1</span>
                    <button class="btn btn-default btn-xs" id="histBtnNext" onclick="histChangePage(1)" disabled>
                      <i class="fa fa-chevron-right"></i>
                    </button>
                  </div>
                </div>
              </div>
            <!-- /.tab-content -->
          </div>
          <!-- /.nav-tabs-custom -->

          <!-- </div> -->
        </div>
        <!-- /.col -->
      </div>
      <!-- /.row -->

    </section>
    <!-- /.content -->
  </div>
  <!-- /.content-wrapper -->


<!-- ----------------------------------------------------------------------- -->
<?php
  require 'php/templates/footer.php';
?>


  <!-- ----------------------------------------------------------------------- -->

<!-- Dark-Mode Patch -->
<?php
switch ($UI_THEME) {
  case "Dark":
    echo '<link rel="stylesheet" href="css/dark-patch-cal.css">';
    break;
  case "System":
    echo '<link rel="stylesheet" href="css/system-dark-patch-cal.css">';
    break;

}
?>

<!-- page script ----------------------------------------------------------- -->
<script >

  // ------------------------------------------------------------

  mac                     = getMac()  // can also be rowID!! not only mac
  var devicesList         = [];   // this will contain a list the database row IDs of the devices ordered by the position displayed in the UI

  var pos                 = -1;
  var parPeriod           = 'Front_Details_Period';

  var tab                 = 'tabDetails'
  var selectedTab         = 'tabDetails';
  var emptyArr            = ['undefined', "", undefined, null];

// -----------------------------------------------------------------------------
function main () {

  // Initialize MAC
  var urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has ('mac') == true) {
    mac = urlParams.get ('mac');
    setCache("naxDeviceDetailsMac", mac); // set cookie
  } else {
    $('#pageTitle').html ('Device not found');
  }

  key ="activeDevicesTab"

  // Activate panel
  if(!emptyArr.includes(getCache(key)))
  {
    selectedTab = getCache(key);
  }

  tab = selectedTab;

  period = '1 day';
  sessionsRows = 50;
  eventsRows = 50;
  // $('#chkHideConnectionEvents')[0].checked = eval(eventsHide == 'true');

  // Initialize components with parameters


  // Init tabs once DOM ready
  $( document ).ready(function() {
    initializeTabs();
  });

}


// -----------------------------------------------------------------------------
function periodChanged () {
  loadSessionsData();
  loadPresenceData();
  loadEventsData();
}


// -----------------------------------------------------------------------------
// Left (prev) < > (next) Right toggles at the top right of device details to
// cycle between devices
function recordSwitch(direction) {

  if(somethingChanged)
  {
    showModalDefaultStrParam ('Unsaved changes', 'Do you want to discard your changes?',
      '<?= lang('Gen_Cancel');?>', '<?= lang('Gen_Okay');?>', performSwitch, direction);
  } else
  {
    showSpinner();
    performSwitch(direction)
  }
}


// ----------------------------------------
// Handle previous/next arrows/chevrons
function updateChevrons(currentMac) {
  const devicesList = getDevicesList();

  pos = devicesList.findIndex(item => item.devMac === currentMac);

  if (pos === -1) {
    console.warn('Device not found in cache. Re-caching devices...', currentMac);

    showSpinner();

    cacheDevices(true).then(() => {
      hideSpinner();

      // Retry after re-caching
      const refreshedList = getDevicesList();
      pos = refreshedList.findIndex(item => item.devMac === currentMac);

      if (pos === -1) {
        console.warn('Device not found in device list after re-cache — hiding navigation controls:', currentMac);
        $('#txtRecord').hide();
        $('#btnPrevious').hide();
        $('#btnNext').hide();
        return;
      }

      console.log('Device found after re-cache:', refreshedList[pos]);
      // Proceed with using `refreshedList[pos]`
    }).catch((err) => {
      hideSpinner();
      console.error('Failed to cache devices:', err);
    });

    return;
  }

  // Update the record number display
  $('#txtRecord').html((pos + 1) + ' / ' + devicesList.length);

  // Enable/disable previous button
  if (pos <= 0) {
    $('#btnPrevious').attr('disabled', '');
    $('#btnPrevious').addClass('text-gray50');
  } else {
    $('#btnPrevious').removeAttr('disabled');
    $('#btnPrevious').removeClass('text-gray50');
  }

  // Enable/disable next button
  if (pos >= devicesList.length - 1) {
    $('#btnNext').attr('disabled', '');
    $('#btnNext').addClass('text-gray50');
  } else {
    $('#btnNext').removeAttr('disabled');
    $('#btnNext').removeClass('text-gray50');
  }
}

// -----------------------------------------------------------------------------

function performSwitch(direction)
{
  somethingChanged = false;

  devicesList = getDevicesList()

  // Update the global position in the devices list variable 'pos'
  if (direction === "next") {
    console.log("direction:" + direction);

    if (pos < devicesList.length) {
      pos++;
    }
  } else if (direction === "prev") {
    if (pos > 0) {
      pos--;
    }
  }

  // Get the new MAC address from devicesList
  mac = devicesList[pos].devMac.toString();

  setCache("naxDeviceDetailsMac", mac);

  // Update the query string with the new MAC and refresh the page
  const baseUrl = window.location.href.split('?')[0];
  window.location.href = `${baseUrl}?mac=${encodeURIComponent(mac)}`;

}

// -----------------------------------------------------------------------------
// Activate save & restore on any value change
$(document).on('input', 'input:text', function() {
  settingsChanged();
});

// -----------------------------------------------------------------------------

function initializeTabs () {
  initializeTabsShared({
    cacheKey:    'activeDevicesTab',
    defaultTab:  'tabDetails'
  });
}


//------------------------------------------------------------------------------
//  Render the small boxes on top
async function renderSmallBoxes() {

    try {
        // Show loading dialog
        showSpinner();

        // Get data from the server
        const apiToken = getSetting("API_TOKEN");

        const apiBaseUrl = getApiBase();
        // Ensure period is a string, not an element
        let periodValue = period;
        if (typeof period === 'object' && period !== null && 'value' in period) {
          periodValue = period.value;
        }
        const url = `${apiBaseUrl}/device/${getMac()}?period=${encodeURIComponent(periodValue)}`;

        const response = await fetch(url, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${apiToken}`,
            "Content-Type": "application/json"
          }
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(`Error fetching device data: ${response.status} ${text}`);
        }

        const deviceData = await response.json();

        // Derive status card appearance from shared getStatusBadgeParts —
        // ensures icon, color, label and lang key are always in sync with the rest of the UI.
        const statusBadge = badgeFromDevice(deviceData);
        const statusText = statusBadge.label;

        // Prepare custom data
        const customData = [
            {
                "onclickEvent": "$('#tabDetails').trigger('click')",
                "color": statusBadge.cssClass,
                "headerId": "deviceStatus",
                "headerStyle": "margin-left: 0em",
                "labelLang": "DevDetail_Shortcut_CurrentStatus",
                "iconId": "deviceStatusIcon",
                "iconHtml": statusBadge.iconHtml,
                "dataValue": statusText
            },
            {
                "onclickEvent": "$('#tabSessions').trigger('click');",
                "color": "bg-green",
                "headerId": "deviceSessions",
                "headerStyle": "",
                "labelLang": "DevDetail_Shortcut_Sessions",
                "iconId": "",
                "iconClass": "fa fa-plug",
                "dataValue": deviceData.devSessions
            },
            {
                "onclickEvent": "$('#tabPresence').trigger('click')",
                "color": "bg-yellow",
                "headerId": "deviceEvents",
                "headerStyle": "margin-left: 0em",
                "labelLang": "DevDetail_Shortcut_Presence",
                "iconId": "deviceEventsIcon",
                "iconClass": "fa fa-calendar",
                "dataValue": `${deviceData.devPresenceHours ?? 0}h`
            },
            {
                "onclickEvent": "$('#tabEvents').trigger('click');",
                "color": "bg-red",
                "headerId": "deviceDownAlerts",
                "headerStyle": "",
                "labelLang": "DevDetail_Shortcut_DownAlerts",
                "iconId": "",
                "iconClass": "fa fa-warning",
                "dataValue": deviceData.devDownAlerts
            }
        ];

        // Send data to render small boxes
        const cardResponse = await fetch('php/components/device_cards.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ items: customData })
        });

        if (!cardResponse.ok) {
            throw new Error(`Error rendering small boxes: ${cardResponse.statusText}`);
        }

        const html = await cardResponse.text();

        $('#TopSmallBoxes').html(html);

    } catch (error) {
        console.error('Error in renderSmallBoxes:', error);
    } finally {
        // Hide loading dialog
        // hideSpinner();
    }
}

// ----------------------------------------
// Write device name/owner into page title DOM. Pure DOM side-effect, no data fetching.
function applyDevicePageTitle(mac, name, owner) {
  let pageTitleText;

  if (mac === "new") {
      pageTitleText = getString("Gen_create_new_device");
      $('#pageTitle').html(
          `<i title="${pageTitleText}" class="fa fa-square-plus"></i> ` + pageTitleText
      );
      $('#devicePageInfoPlc .inner').html(
          `<i class="fa fa-circle-info"></i> ` + getString("Gen_create_new_device_info")
      );
      $('#devicePageInfoPlc').show();
  } else if (!owner || (name && name.toString().includes(owner))) {
      pageTitleText = encodeSpecialChars(name ?? getString("DevDetail_EveandAl_NewDevice"));
      $('#pageTitle').html(pageTitleText);
      $('#devicePageInfoPlc').hide();
  } else {
      pageTitleText = `${encodeSpecialChars(name ?? getString("DevDetail_EveandAl_NewDevice"))} (${encodeSpecialChars(owner)})`;
      $('#pageTitle').html(pageTitleText);
      $('#devicePageInfoPlc').hide();
  }

  // Prepend to the <title> tag
  $('title').html(pageTitleText + ' - ' + $('title').html());
}

// ----------------------------------------
// Resolve device name/owner for the page title.
// Stage 1: localStorage cache (synchronous, fast path).
// Stage 2: one forced re-cache from table_devices.json.
// Stage 3: REST API fallback so a direct-link visit never loops.
async function updateDevicePageName(mac) {
  let name  = getDevDataByMac(mac, "devName");
  let owner = getDevDataByMac(mac, "devOwner");

  // Stage 2: one re-cache attempt
  if (mac !== 'new' && name === null) {
    console.warn("Device not in cache, attempting re-cache:", mac);
    showSpinner();
    try {
      await cacheDevices(true);
    } catch (err) {
      console.error("Re-cache failed:", err);
    } finally {
      hideSpinner();
    }
    name  = getDevDataByMac(mac, "devName");
    owner = getDevDataByMac(mac, "devOwner");
  }

  // Stage 3: REST fallback — same endpoint renderSmallBoxes uses, always DB-direct
  if (mac !== 'new' && name === null) {
    console.warn("Device not found in cache after re-cache, falling back to REST API:", mac);
    try {
      const { apiBase, authHeader } = getAuthContext();
      const res = await fetch(`${apiBase}/device/${encodeURIComponent(mac)}`, {
        headers: authHeader
      });
      if (res.ok) {
        const data = await res.json();
        name  = data.devName  ?? null;
        owner = data.devOwner ?? null;
      } else {
        console.error("REST fallback for device name returned:", res.status);
      }
    } catch (err) {
      console.error("REST fallback error:", err);
    }
  }

  applyDevicePageTitle(mac, name, owner);
}


//-----------------------------------------------------------------------------------
window.onload = function() {
  // Always trigger app-init bootstrap
  if (typeof executeOnce === 'function') {
    executeOnce();
  }

  mac = getMac();

  // Wait for app initialization (cache populated) before using cached data
  callAfterAppInitialized(async () => {
    updateDevicePageName(mac);
    updateChevrons(mac);
    await renderSmallBoxes();
    main();
    hideDeviceDetailsSkeleton();
  });

// -----------------------------------------------------------------------------
function hideDeviceDetailsSkeleton() {
  $('#device-details-skeleton').fadeOut(0, function() { $(this).remove(); });
}

// Fallback: remove main skeleton and all tab pane skeletons if init stalls
setTimeout(function() {
  hideDeviceDetailsSkeleton();
  if (typeof hideDetailsTabSkeleton  === 'function') hideDetailsTabSkeleton();
  if (typeof hideSessionsTabSkeleton === 'function') hideSessionsTabSkeleton();
  if (typeof hidePresenceTabSkeleton === 'function') hidePresenceTabSkeleton();
  if (typeof hideEventsTabSkeleton   === 'function') hideEventsTabSkeleton();
  $('#skel-tab-history').hide();
}, 15000);
}

// ---------------------------------------------------------------------------
// Change Log tab — device-scoped history
// ---------------------------------------------------------------------------

var _histPage   = 0;
var _histLimit  = 50;
var _histTotal  = 0;
var _histLoaded = false;

function loadHistoryData() {
  var devGuid = getDevDataByMac(mac, 'devGUID');
  // Devices without a GUID (created before GUIDs were introduced) cannot be
  // queried — show a clear message instead of spinning indefinitely.
  if (devGuid === null || devGuid === undefined || devGuid === '') {
    _renderHistoryTable([]);
    return;
  }

  var changedBy     = (document.getElementById('histFilterBy')  || {}).value || null;
  var changedColumn = (document.getElementById('histFilterCol') || {}).value || null;

  var query = [
    'query($devGuid:String!,$changedBy:String,$changedColumn:String,$limit:Int,$offset:Int){',
    '  deviceHistoryGrouped(devGuid:$devGuid,changedBy:$changedBy,changedColumn:$changedColumn,limit:$limit,offset:$offset){',
    '    count history{timestamp changedBy changes{changedColumn oldValue newValue}}',
    '  }',
    '}'
  ].join('');

  var variables = {
    devGuid:       devGuid,
    changedBy:     changedBy     || null,
    changedColumn: changedColumn || null,
    limit:         _histLimit,
    offset:        _histPage * _histLimit
  };

  $.ajax({
    url:         getApiBase() + '/graphql',
    method:      'POST',
    contentType: 'application/json',
    headers:     { 'Authorization': 'Bearer ' + getSetting('API_TOKEN') },
    data:        JSON.stringify({ query: query, variables: variables }),
    success: function(resp) {
      if (!resp.data || !resp.data.deviceHistoryGrouped) return;
      var result = resp.data.deviceHistoryGrouped;
      _histTotal = result.count;
      _renderHistoryTable(result.history);
      _updateHistoryPagination();

      // Populate filter dropdowns once on first load
      if (!_histLoaded) {
        _histLoaded = true;
        _populateHistoryFilters(devGuid);
      }
    }
  });
}

function _populateHistoryFilters(devGuid) {
  $.ajax({
    url:     getApiBase() + '/devices/history/filters?devGuid=' + encodeURIComponent(devGuid),
    method:  'GET',
    headers: { 'Authorization': 'Bearer ' + getSetting('API_TOKEN') },
    success: function(resp) {
      if (!resp.data) return;
      var byEl  = document.getElementById('histFilterBy');
      var colEl = document.getElementById('histFilterCol');
      (resp.data.changedBy    || []).forEach(function(v) { byEl.add(new Option(v, v)); });
      (resp.data.changedColumn || []).forEach(function(v) { colEl.add(new Option(v, v)); });
    }
  });
}

function _renderHistoryTable(groups) {
  var tbody = document.getElementById('historyTableBody');
  if (!tbody) return;
  // Always hide the loading skeleton once we have a result (even empty)
  $('#skel-tab-history').fadeOut(0, function() { $(this).hide(); });
  if (!groups || groups.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted"><?= lang('device_history_empty_state');?></td></tr>';
    return;
  }
  var html = '';
  groups.forEach(function(g) {
    var iconHtml = (g.changedBy === 'user:api' || g.changedBy === 'USER')
      ? '<i class="fa fa-user" title="' + _histEsc(g.changedBy) + '"></i>'
      : '<i class="fa fa-cog"  title="' + _histEsc(g.changedBy) + '"></i>';
    var changesHtml = g.changes.map(function(c) {
      return '<div><code>' + _histEsc(c.changedColumn) + '</code>: '
        + '<span class="text-danger">'  + _histEsc(c.oldValue || '\u2205') + '</span>'
        + ' \u2192 '
        + '<span class="text-success">' + _histEsc(c.newValue || '\u2205') + '</span>'
        + '</div>';
    }).join('');
    html += '<tr>'
      + '<td style="white-space:nowrap;font-size:12px;">' + _histEsc(g.timestamp) + '</td>'
      + '<td>' + iconHtml + ' ' + _histEsc(g.changedBy) + '</td>'
      + '<td>' + changesHtml + '</td>'
      + '</tr>';
  });
  tbody.innerHTML = html;
}

function _updateHistoryPagination() {
  var totalPages = Math.max(1, Math.ceil(_histTotal / _histLimit));
  var lbl = document.getElementById('histPageLabel');
  var info = document.getElementById('histInfo');
  var prev = document.getElementById('histBtnPrev');
  var next = document.getElementById('histBtnNext');
  if (lbl)  lbl.textContent  = (_histPage + 1) + ' / ' + totalPages;
  if (info) info.textContent = _histTotal + ' <?= lang('device_history_col_changes');?>';
  if (prev) prev.disabled    = _histPage <= 0;
  if (next) next.disabled    = (_histPage + 1) >= totalPages;
}

function histChangePage(delta) {
  _histPage = Math.max(0, _histPage + delta);
  loadHistoryData();
}

function _histEsc(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Load history when the tab becomes visible
$(document).on('shown.bs.tab', 'a[id="tabHistory"]', function() {
  _histPage  = 0;
  loadHistoryData();
});

</script>


