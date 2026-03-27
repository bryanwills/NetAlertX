<?php
  //------------------------------------------------------------------------------
  // check if authenticated
  require_once  $_SERVER['DOCUMENT_ROOT'] . '/php/templates/security.php';
?>

<!-- Main content ---------------------------------------------------------- -->
<section class="content">
  <div class="plugin-filters hidden" >
    <div class="input-group col-sm-12">
      <label class="col-sm-3"><?= lang('Plugins_Filters_Mac');?></label>
      <input class="col-sm-3" id="txtMacFilter" type="text" value="--" readonly>
    </div>
  </div>
  <div class="nav-tabs-custom plugin-content" style="margin-bottom: 0px;">

    <ul id="tabs-location" class="nav nav-tabs col-sm-2 ">
      <!-- PLACEHOLDER -->
    </ul>
    <div id="tabs-content-location-wrap" class="tab-content col-sm-10">
      <div id="tabs-content-location" class="tab-content col-sm-12">
        <!-- PLACEHOLDER -->
      </div>
    </div>

</section>

<script>

// Global variable to track the last MAC we initialized with
let lastMac = null;
let keepUpdating = true;

function initMacFilter() {
  // Parse the MAC parameter from the URL (e.g., ?mac=00:11:22:33:44:55)
  const urlParams = new URLSearchParams(window.location.search);
  const mac = urlParams.get('mac');

  // Set the MAC in the input field
  if(mac)
  {
    $("#txtMacFilter").val(mac);
  }
  else
  {
    $("#txtMacFilter").val("--");
  }

  return mac;
}

// -----------------------------------------------
// INIT with polling for panel element visibility
// -----------------------------------------------

// -----------------------------------------------------------------------------
// Initializes the fields if the MAC in the URL is different or not yet set
function initFields() {

  // Only proceed if .plugin-content is visible
  if (!$('.plugin-content:visible').length) {
    return; // exit early if nothing is visible
  }

  // Get current value from the readonly text field
  const currentVal = initMacFilter();

  // If a MAC exists in the URL and it's either:
  //  - the first time running (field shows default "--"), or
  //  - different from what's already displayed
  if (currentVal != "--" && currentVal !== lastMac) {

    // Update the lastMac so we don't reload unnecessarily
    lastMac = currentVal;

    // Trigger data loading based on new MAC
    getData();
  } else if((currentVal === "--" || currentVal == null  ) && keepUpdating)
  {
    $("#txtMacFilter").val("--"); // need to set this as filters are using this later on
    keepUpdating = false; // stop updates
    getData();
  }
}

// -----------------------------------------------------------------------------
// Get form control according to the column definition from config.json > database_column_definitions
function getFormControl(dbColumnDef, value, index) {

  result = ''

  // Check if mapped_to_column_data exists and has a value to override the supplied value which is most likely `undefined`
  if (dbColumnDef.mapped_to_column_data && dbColumnDef.mapped_to_column_data.value) {
    value = dbColumnDef.mapped_to_column_data.value;
  }


  result = processColumnValue(dbColumnDef, value, index, dbColumnDef.type)

  return result;
}

// -----------------------------------------------------------------------------
// Process column value
function processColumnValue(dbColumnDef, value, index, type) {
  if (type.includes('.')) {
  const typeParts = type.split('.');

  // recursion
  for (const typePart of typeParts) {
    value = processColumnValue(dbColumnDef, value, index, typePart)
  }

  } else{
  // pick form control based on the supplied type
  switch(type)
  {
    case 'label':
      value = `<span>${value}<span>`;
      break;
    case 'none':
      value = `${value}`;
      break;
    case 'textarea_readonly':
      value = `<textarea cols="70" rows="3" wrap="off" readonly style="white-space: pre-wrap;">
          ${value.replace(/^b'(.*)'$/gm, '$1').replace(/\\n/g, '\n').replace(/\\r/g, '\r')}
          </textarea>`;
      break;
    case 'textbox_save':

      value = value == 'null' ? '' : value; // hide 'null' values

      id = `${dbColumnDef.column}_${index}`

      value =  `<span class="form-group">
              <div class="input-group">
                <input class="form-control" type="text" value="${value}" id="${id}" data-my-column="${dbColumnDef.column}"  data-my-index="${index}" name="${dbColumnDef.column}">
                <span class="input-group-addon"><i class="fa fa-save pointer" onclick="genericSaveData('${id}');"></i></span>
              </div>
            <span>`;
      break;
    case 'url':
      value = `<span><a href="${value}" target="_blank">${value}</a><span>`;
      break;
    case 'url_http_https':

      value = `<span>
            <a href="http://${value}" target="_blank">
              <i class="fa fa-lock-open "></i>
            </a>
            /
            <a href="https://${value}" target="_blank">
              <i class="fa fa-lock "></i>
            </a>
          <span>`;
      break;
    case 'device_name_mac':
      value = `<div class="text-center"> ${value}
                <br/>
                (${createDeviceLink(value)})
              </div>`;
      break;
    case 'device_mac':
      value = `<span class="anonymizeMac"><a href="/deviceDetails.php?mac=${value}" target="_blank">${value}</a><span>`;
      break;
    case 'device_ip':
      value = `<span class="anonymizeIp"><a href="#" onclick="navigateToDeviceWithIp('${value}')" >${value}</a><span>`;
      break;
    case 'threshold':

      valueTmp = ''

      $.each(dbColumnDef.options, function(index, obj) {
        if(Number(value) < Number(obj.maximum) && valueTmp == '')
        {
          valueTmp = `<div class="thresholdFormControl" style="background-color:${obj.hexColor}">${value}</div>`
          // return;
        }
      });

      value = valueTmp;

      break;
    case 'replace':
      $.each(dbColumnDef.options, function(index, obj) {
        if(value == obj.equals)
        {
          value = `<span title="${value}">${obj.replacement}</span>`
        }
      });
      break;
    case 'regex':

      for (const option of dbColumnDef.options) {
        if (option.type === type) {

          const regexPattern = new RegExp(option.param);
          const match = value.match(regexPattern);
          if (match) {
            // Return the first match
            value =  match[0];

          }
        }
      }
      break;
    case 'eval':

      for (const option of dbColumnDef.options) {
        if (option.type === type) {
          // console.log(option.param)
          value =  eval(option.param);
        }
      }
      break;

    default:
      value = value + `<div style='text-align:center' title="${getString("Plugins_no_control")}"><i class='fa-solid fa-circle-question'></i></div>` ;
  }
  }

  // Default behavior if no match is found
  return value;
}



// -----------------------------------------------------------------------------
// Update the corresponding DB column and entry
function genericSaveData (id) {
  columnName  = $(`#${id}`).attr('data-my-column')
  index  = $(`#${id}`).attr('data-my-index')
  columnValue = $(`#${id}`).val()

  console.log(columnName)
  console.log(index)
  console.log(columnValue)

  const apiBase = getApiBase();
  const apiToken = getSetting("API_TOKEN");
  const url = `${apiBase}/dbquery/update`;

  $.ajax({
    url,
    method: "POST",
    headers: { "Authorization": `Bearer ${apiToken}` },
    data: JSON.stringify({
      dbtable: "Plugins_Objects",
      columnName: "index",
      id: index,
      columns: "userData",
      values: columnValue
    }),
    contentType: "application/json",
    success: function(response) {
      if(response.success)
      {
        showMessage('<?= lang('Gen_DataUpdatedUITakesTime');?>')
        // Remove navigation prompt "Are you sure you want to leave..."
        window.onbeforeunload = null;
      } else
      {
        showMessage('<?= lang('Gen_LockedDB');?>')
      }
    },
    error: function(xhr, status, error) {
      console.error("Error saving data:", status, error);
      showMessage('<?= lang('Gen_LockedDB');?>');
    }
  });
}


// -----------------------------------------------------------------------------
pluginDefinitions = []

async function getData() {
  try {
    showSpinner();
    console.log("Plugins getData called");

    const plugins = await fetchJson('plugins.json');
    pluginDefinitions = plugins.data;

    generateTabs();
  } catch (err) {
    console.error("Failed to load data", err);
  }
}

async function fetchJson(filename) {
  const response = await fetch(`php/server/query_json.php?file=${filename}`);
  if (!response.ok) throw new Error(`Failed to load ${filename}`);
  return await response.json();
}

// GraphQL helper — fires a paginated plugin table query and calls back with
// the DataTables-compatible response plus the raw GraphQL result object.
function postPluginGraphQL(gqlField, prefix, foreignKey, dtRequest, callback) {
  const apiToken = getSetting("API_TOKEN");
  const apiBase  = getApiBase();
  const page   = Math.floor(dtRequest.start / dtRequest.length) + 1;
  const limit  = dtRequest.length;
  const search = dtRequest.search?.value || null;

  let sort = [];
  if (dtRequest.order?.length > 0) {
    const order = dtRequest.order[0];
    sort.push({ field: dtRequest.columns[order.column].data, order: order.dir });
  }

  const query = `
    query PluginData($options: PluginQueryOptionsInput) {
      ${gqlField}(options: $options) {
        count
        dbCount
        entries {
          index plugin objectPrimaryId objectSecondaryId
          dateTimeCreated dateTimeChanged
          watchedValue1 watchedValue2 watchedValue3 watchedValue4
          status extra userData foreignKey
          syncHubNodeName helpVal1 helpVal2 helpVal3 helpVal4 objectGuid
        }
      }
    }
  `;

  $.ajax({
    method: "POST",
    url: `${apiBase}/graphql`,
    headers: { "Authorization": `Bearer ${apiToken}`, "Content-Type": "application/json" },
    data: JSON.stringify({
      query,
      variables: { options: { page, limit, search, sort, plugin: prefix, foreignKey } }
    }),
    success: function(response) {
      if (response.errors) {
        console.error("[plugins] GraphQL errors:", response.errors);
        callback({ data: [], recordsTotal: 0, recordsFiltered: 0 });
        return;
      }
      const result = response.data[gqlField];
      callback({ data: result.entries, recordsTotal: result.dbCount, recordsFiltered: result.count }, result);
    },
    error: function() {
      callback({ data: [], recordsTotal: 0, recordsFiltered: 0 });
    }
  });
}

// Fetch the lightweight plugins_stats.json (~1KB) and populate all badge
// and sub-tab counts instantly — no GraphQL, no 250MB file loads.
async function prefetchPluginBadges() {
  try {
    const stats = await fetchJson('table_plugins_stats.json');
    // Build lookup: { ARPSCAN: { objects: 42, events: 3, history: 100 }, ... }
    const counts = {};
    for (const row of stats.data) {
      const p = row.tableName;  // 'objects' | 'events' | 'history'
      const plugin = row.plugin;
      if (!counts[plugin]) counts[plugin] = { objects: 0, events: 0, history: 0 };
      counts[plugin][p] = row.cnt;
    }
    for (const [prefix, c] of Object.entries(counts)) {
      $(`#badge_${prefix}`).text(c.objects);
      $(`#objCount_${prefix}`).text(c.objects);
      $(`#evtCount_${prefix}`).text(c.events);
      $(`#histCount_${prefix}`).text(c.history);
    }
    // Set 0 for plugins with no rows in any table
    pluginDefinitions.filter(p => p.show_ui).forEach(p => {
      const prefix = p.unique_prefix;
      if (!counts[prefix]) {
        $(`#badge_${prefix}`).text(0);
        $(`#objCount_${prefix}`).text(0);
        $(`#evtCount_${prefix}`).text(0);
        $(`#histCount_${prefix}`).text(0);
      }
    });
  } catch (err) {
    console.error('[plugins] badge prefetch failed:', err);
  }
}

function generateTabs() {

  // Reset the tabs by clearing previous headers and content
  resetTabs();

  // Sort pluginDefinitions by unique_prefix alphabetically
  pluginDefinitions.sort((a, b) => a.unique_prefix.localeCompare(b.unique_prefix));

  let assignActive = true;

  // Iterate over the sorted pluginDefinitions to create tab headers and content
  pluginDefinitions.forEach(pluginObj => {
    if (pluginObj.show_ui) {
      createTabContent(pluginObj, assignActive);
      createTabHeader(pluginObj, assignActive);
      assignActive = false;
    }
  });

  // Now that ALL DOM elements exist (both <a> headers and tab panes),
  // wire up DataTable initialization: immediate for the active tab,
  // deferred via shown.bs.tab for the rest.
  let firstVisible = true;
  pluginDefinitions.forEach(pluginObj => {
    if (pluginObj.show_ui) {
      const prefix = pluginObj.unique_prefix;
      const colDefinitions = getColumnDefinitions(pluginObj);
      if (firstVisible) {
        initializeDataTables(prefix, colDefinitions, pluginObj);
        firstVisible = false;
      } else {
        $(`a[href="#${prefix}"]`).one('shown.bs.tab', function() {
          initializeDataTables(prefix, colDefinitions, pluginObj);
        });
      }
    }
  });

  // Auto-select tab from ?tab= URL param or cache (scoped to plugin nav only)
  initializeTabsShared({
    cacheKey:      'activePluginsTab',
    urlParamName:  'tab',
    idSuffix:      '_id',
    tabContainer:  '#tabs-location'
  });

  // Pre-fetch badge counts for every plugin in a single batched GraphQL call.
  prefetchPluginBadges();

  hideSpinner()
}

function resetTabs() {
  // Clear any existing tab headers and content from the DOM
  $('#tabs-location').empty();
  $('#tabs-content-location').empty();
}

// ---------------------------------------------------------------
// left headers
function createTabHeader(pluginObj, assignActive) {
  const prefix = pluginObj.unique_prefix; // Get the unique prefix for the plugin

  // Determine the active class for the first tab
  const activeClass = assignActive ? "active" : "";

  // Append the tab header to the tabs location
  $('#tabs-location').append(`
    <li class="left-nav ${activeClass} ">
      <a class="col-sm-12 textOverflow" href="#${prefix}" data-plugin-prefix="${prefix}" id="${prefix}_id" data-toggle="tab">
        ${getString(`${prefix}_icon`)} ${getString(`${prefix}_display_name`)}

      </a>
      <div class="pluginBadgeWrap"><span title="" class="badge pluginBadge" id="badge_${prefix}">…</span></div>
    </li>
  `);

}

// ---------------------------------------------------------------
// Content of selected plugin (header)
function createTabContent(pluginObj, assignActive) {
  const prefix = pluginObj.unique_prefix; // Get the unique prefix for the plugin
  const colDefinitions = getColumnDefinitions(pluginObj); // Get column definitions for DataTables

  // Append the content structure for the plugin's tab to the content location
  $('#tabs-content-location').append(`
    <div id="${prefix}" class="tab-pane ${assignActive ? 'active' : ''}">
      ${generateTabNavigation(prefix)} <!-- Create tab navigation -->
      <div class="tab-content">
        ${generateDataTable(prefix, 'Objects', colDefinitions)}
        ${generateDataTable(prefix, 'Events', colDefinitions)}
        ${generateDataTable(prefix, 'History', colDefinitions)}
      </div>
      <div class='plugins-description'>
        ${getString(`${prefix}_description`)} <!-- Display the plugin description -->
        <span><a href="https://github.com/netalertx/NetAlertX/tree/main/front/plugins/${pluginObj.code_name}" target="_blank">${getString('Gen_ReadDocs')}</a></span> <!-- Link to documentation -->
      </div>
    </div>
  `);

  // DataTable init is handled by generateTabs() after all DOM elements exist.
}

function getColumnDefinitions(pluginObj) {
  // Filter and return only the columns that are set to show in the UI
  return pluginObj["database_column_definitions"].filter(colDef => colDef.show);
}

function generateTabNavigation(prefix) {
  // Create navigation tabs for Objects, Unprocessed Events, and History
  return `
    <div class="nav-tabs-custom" style="margin-bottom: 0px">
      <ul class="nav nav-tabs">
        <li class="active">
          <a href="#objectsTarget_${prefix}" data-toggle="tab"><i class="fa fa-cube"></i> ${getString('Plugins_Objects')} (<span id="objCount_${prefix}">…</span>)</a>
        </li>
        <li>
          <a href="#eventsTarget_${prefix}" data-toggle="tab"><i class="fa fa-bolt"></i> ${getString('Plugins_Unprocessed_Events')} (<span id="evtCount_${prefix}">…</span>)</a>
        </li>
        <li>
          <a href="#historyTarget_${prefix}" data-toggle="tab"><i class="fa fa-clock"></i> ${getString('Plugins_History')} (<span id="histCount_${prefix}">…</span>)</a>
        </li>
      </ul>
    </div>
  `;
}

function generateDataTable(prefix, tableType, colDefinitions) {
  // Generate HTML for a DataTable and associated buttons for a given table type
  const headersHtml = colDefinitions.map(colDef => `<th class="${colDef.css_classes}">${getString(`${prefix}_${colDef.column}_name`)}</th>`).join('');

  return `
    <div id="${tableType.toLowerCase()}Target_${prefix}" class="tab-pane ${tableType == "Objects" ? "active":""}">
      <table id="${tableType.toLowerCase()}Table_${prefix}" class="display table table-striped table-stretched" data-my-dbtable="Plugins_${tableType}">
        <thead><tr>${headersHtml}</tr></thead>
      </table>
      <div class="plugin-obj-purge">
        <button class="btn btn-primary" onclick="purgeAll('${prefix}', 'Plugins_${tableType}' )"><?= lang('Plugins_DeleteAll');?></button>
        ${tableType !== 'Events' ? `<button class="btn btn-primary" onclick="deleteListed('${prefix}', 'Plugins_${tableType}' )"><?= lang('Plugins_Obj_DeleteListed');?></button>` : ''}
      </div>
    </div>
  `;
}

function initializeDataTables(prefix, colDefinitions, pluginObj) {
  const mac        = $("#txtMacFilter").val();
  const foreignKey = (mac && mac !== "--") ? mac : null;

  const tableConfigs = [
    { tableId: `objectsTable_${prefix}`, gqlField: 'pluginsObjects', countId: `objCount_${prefix}`, badgeId: `badge_${prefix}` },
    { tableId: `eventsTable_${prefix}`,  gqlField: 'pluginsEvents',  countId: `evtCount_${prefix}`, badgeId: null },
    { tableId: `historyTable_${prefix}`, gqlField: 'pluginsHistory', countId: `histCount_${prefix}`, badgeId: null },
  ];

  function buildDT(tableId, gqlField, countId, badgeId) {
    if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
      return; // already initialized
    }
    $(`#${tableId}`).DataTable({
      processing: true,
      serverSide: true,
      paging:     true,
      searching:  true,
      ordering:   false,
      pageLength: 25,
      lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
      createdRow: function(row, data) {
        $(row).attr('data-my-index', data.index);
      },
      ajax: function(dtRequest, callback) {
        postPluginGraphQL(gqlField, prefix, foreignKey, dtRequest, function(dtResponse, result) {
          if (result) {
            $(`#${countId}`).text(result.count);
            if (badgeId) $(`#${badgeId}`).text(result.dbCount);
          }
          callback(dtResponse);
        });
      },
      columns: colDefinitions.map(colDef => ({
        data:      colDef.column,
        title:     getString(`${prefix}_${colDef.column}_name`),
        className: colDef.css_classes || '',
        createdCell: function(td, cellData, rowData) {
          $(td).html(getFormControl(colDef, cellData, rowData.index));
        }
      }))
    });
  }

  // Initialize the Objects table immediately (it is the active/visible sub-tab).
  // Defer Events and History tables until their sub-tab is first shown.
  const [objCfg, evtCfg, histCfg] = tableConfigs;
  buildDT(objCfg.tableId, objCfg.gqlField, objCfg.countId, objCfg.badgeId);

  $(`a[href="#eventsTarget_${prefix}"]`).one('shown.bs.tab', function() {
    buildDT(evtCfg.tableId, evtCfg.gqlField, evtCfg.countId, evtCfg.badgeId);
  });

  $(`a[href="#historyTarget_${prefix}"]`).one('shown.bs.tab', function() {
    buildDT(histCfg.tableId, histCfg.gqlField, histCfg.countId, histCfg.badgeId);
  });
}

// --------------------------------------------------------
// Filter method that determines if an entry should be shown
function shouldBeShown(entry, pluginObj)
{
  if (pluginObj.hasOwnProperty('data_filters')) {

    let dataFilters = pluginObj.data_filters;

    // Loop through 'data_filters' array and appply filters on individual plugin entries
    for (let i = 0; i < dataFilters.length; i++) {

      compare_field_id = dataFilters[i].compare_field_id;
      compare_column = dataFilters[i].compare_column;
      compare_operator = dataFilters[i].compare_operator;
      compare_js_template = dataFilters[i].compare_js_template;
      compare_use_quotes = dataFilters[i].compare_use_quotes;
      compare_field_id_value = $(`#${compare_field_id}`).val();

      // console.log(compare_field_id_value);
      // console.log(compare_field_id);


      // apply filter if the filter field has a valid value
      if(compare_field_id_value != undefined && compare_field_id_value != '--')
      {
        // valid value
        // resolve the left and right part of the comparison
        let left = compare_js_template.replace('{value}', `${compare_field_id_value}`)
        let right = compare_js_template.replace('{value}', `${entry[compare_column]}`)

        // include wrapper quotes if specified
        compare_use_quotes ? quotes = '"' : quotes = ''

        result =  eval(
                quotes +  `${eval(left)}` + quotes +
                        ` ${compare_operator} ` +
                quotes +  `${eval(right)}` + quotes
              );

        return result;
      }
    }
  }
  return true;
}

// --------------------------------------------------------
// Data cleanup/purge functionality
plugPrefix = ''
dbTable  = ''

// --------------------------------------------------------
function purgeAll(callback) {
  plugPrefix = arguments[0];  // plugin prefix
  dbTable  = arguments[1];  // DB table

  // Ask for confirmation
  showModalWarning(`${getString('Gen_Purge')} ${plugPrefix} ${dbTable}`, `${getString('Gen_AreYouSure')}`,
    `${getString('Gen_Cancel')}`, `${getString('Gen_Okay')}`, "purgeAllExecute");
}

// --------------------------------------------------------
function purgeAllExecute() {
  const apiBase = getApiBase();
  const apiToken = getSetting("API_TOKEN");
  const url = `${apiBase}/dbquery/delete`;

  $.ajax({
    method: "POST",
    url: url,
    headers: { "Authorization": `Bearer ${apiToken}` },
    data: JSON.stringify({
      dbtable: dbTable,
      columnName: 'Plugin',
      id: [plugPrefix]
    }),
    contentType: "application/json",
    success: function(response, textStatus) {
      showModalOk('Result', response.success ? "Deleted successfully" : (response.error || "Unknown error"));
    },
    error: function(xhr, status, error) {
      console.error("Error deleting:", status, error);
      showModalOk('Result', "Error: " + (xhr.responseJSON?.error || error));
    }
  });
}

// --------------------------------------------------------
function deleteListed(plugPrefixArg, dbTableArg) {
  plugPrefix = plugPrefixArg;
  dbTable = dbTableArg;

  // Collect selected IDs
  idArr = $(`#${plugPrefix} table[data-my-dbtable="${dbTable}"] tr[data-my-index]`)
    .map(function() {
      return $(this).attr("data-my-index");
    }).get();

  if (idArr.length === 0) {
    showModalOk('Nothing to delete', 'No items are selected for deletion.');
    return;
  }

  // Ask for confirmation
  showModalWarning(`${getString('Gen_Purge')} ${plugPrefix} ${dbTable}`, `${getString('Gen_AreYouSure')} (${idArr.length})`,
    `${getString('Gen_Cancel')}`, `${getString('Gen_Okay')}`,  () => deleteListedExecute(idArr));
}

// --------------------------------------------------------
function deleteListedExecute(idArr) {
  const apiBase = getApiBase();
  const apiToken = getSetting("API_TOKEN");
  const url = `${apiBase}/dbquery/delete`;

  console.log(idArr);


  $.ajax({
    method: "POST",
    url: url,
    headers: { "Authorization": `Bearer ${apiToken}` },
    data: JSON.stringify({
      dbtable: dbTable,
      columnName: 'Index',
      id: idArr
    }),
    contentType: "application/json",
    success: function(response, textStatus) {
      updateApi("plugins_objects")
      showModalOk('Result', response.success ? "Deleted successfully" : (response.error || "Unknown error"));
    },
    error: function(xhr, status, error) {
      console.error("Error deleting:", status, error);
      showModalOk('Result', "Error: " + (xhr.responseJSON?.error || error));
    }
  });
}


// -----------------------------------------------------------------------------
// Main sequence

// -----------------------------------------------------------------------------
// Recurring function to monitor the URL and reinitialize if needed
function updater() {
  initFields();

  // Run updater again after delay
  setTimeout(updater, 200);
}

// if visible, load immediately, if not start updater
if (!$('.plugin-content:visible').length) {
  updater();
}
else
{
  initFields();
}

</script>
