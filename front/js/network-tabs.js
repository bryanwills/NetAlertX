// network-tabs.js
// Tab management and tab content rendering functions

/**
 * Render network tabs from nodes
 * @param {Array} nodes - Array of network node objects
 */
function renderNetworkTabs(nodes) {
  let html = '';
  nodes.forEach((node, i) => {
    const iconClass = node.online == 1 ? "text-green" :
                      (node.node_alert == 1 ? "text-red" : "text-gray50");

    const portLabel = node.node_ports_count ? ` (${node.node_ports_count})` : '';
    const icon = atob(node.node_icon);
    const id = node.node_mac.replace(/:/g, '_');

    html += `
      <li class="networkNodeTabHeaders ${i === 0 ? 'active' : ''}">
        <a href="#${id}" data-mytabmac="${node.node_mac}" id="${id}_id" data-toggle="tab" title="${node.node_name}">
          <div class="icon ${iconClass}">${icon}</div>
          <span class="node-name">${node.node_name}</span>${portLabel}
        </a>
      </li>`;
  });

  $('.nav-tabs').html(html);

  // populate tabs
  renderNetworkTabContent(nodes);

  // init selected (first) tab
  initTab();

  // init selected node highlighting
  initSelectedNodeHighlighting()

  // Register events on tab change
  $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    initSelectedNodeHighlighting()
  });
}

/**
 * Render content for each network tab
 * @param {Array} nodes - Array of network node objects
 */
function renderNetworkTabContent(nodes) {
  $('.tab-content').empty();

  nodes.forEach((node, i) => {
    const id = node.node_mac.replace(/:/g, '_').toLowerCase();

    const badge = getStatusBadgeParts(
      node.online,
      node.node_alert,
      node.node_flapping,
      node.node_mac
    );

    const badgeHtml = `<a href="${badge.url}" class="badge ${badge.cssClass}">${badge.iconHtml} ${badge.status}</a>`;
    const parentId = node.parent_mac.replace(/:/g, '_');

    isRootNode = node.parent_mac == "";

    const paneHtml = `
              <div class="tab-pane box box-aqua box-body ${i === 0 ? 'active' : ''}" id="${id}">
                <h5><i class="fa fa-server"></i> ${getString('Network_Node')}</h5>

                <div class="mb-3 row">
                  <label class="col-sm-3 col-form-label fw-bold">${getString('DevDetail_Tab_Details')}</label>
                  <div class="col-sm-9">
                    <a href="./deviceDetails.php?mac=${node.node_mac}" target="_blank" class="anonymize">${node.node_name}</a>
                  </div>
                </div>

                <div class="mb-3 row">
                  <label class="col-sm-3 col-form-label fw-bold">MAC</label>
                  <div class="col-sm-9 anonymize">${node.node_mac}</div>
                </div>

                <div class="mb-3 row">
                  <label class="col-sm-3 col-form-label fw-bold">${getString('Device_TableHead_Type')}</label>
                  <div class="col-sm-9">${node.node_type}</div>
                </div>

                <div class="mb-3 row">
                  <label class="col-sm-3 col-form-label fw-bold">${getString('Device_TableHead_Status')}</label>
                  <div class="col-sm-9">${badgeHtml}</div>
                </div>

                <div class="mb-3 row">
                  <label class="col-sm-3 col-form-label fw-bold">${getString('Network_Parent')}</label>
                  <div class="col-sm-9">
                    ${isRootNode ? '' : `<a class="anonymize" href="#">`}
                      <span my-data-mac="${node.parent_mac}" data-mac="${node.parent_mac}" data-devIsNetworkNodeDynamic="1" onclick="handleNodeClick(this)">
                        ${isRootNode ? getString('Network_Root') : getDevDataByMac(node.parent_mac, "devName")}
                      </span>
                    ${isRootNode ? '' : `</a>`}
                  </div>
                </div>
                <hr/>
                <div class="box box-aqua box-body" id="connected">
                  <h5>
                    <i class="fa fa-sitemap fa-rotate-270"></i>
                    ${getString('Network_Connected')}
                  </h5>

                  <div id="leafs_${id}" class="table-responsive"></div>
                </div>
              </div>
            `;

    $('.tab-content').append(paneHtml);
    loadConnectedDevices(node.node_mac);
  });
}

/**
 * Initialize the active tab based on cache or query parameter
 */
function initTab()
{
  key = "activeNetworkTab"

  // default selection
  selectedTab = "Internet_id"

  // the #target from the url
  target = getQueryString('mac')

  // update cookie if target specified
  if(target != "")
  {
    setCache(key, target.replaceAll(":","_")+'_id') // _id is added so it doesn't conflict with AdminLTE tab behavior
  }

  // get the tab id from the cookie (already overridden by the target)
  if(!emptyArr.includes(getCache(key)))
  {
    selectedTab = getCache(key);
  }

  // Activate panel
  $('.nav-tabs a[id='+ selectedTab +']').tab('show');

  // When changed save new current tab
  $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    setCache(key, $(e.target).attr('id'))
  });

}

/**
 * Highlight the currently selected node in the tree
 */
function initSelectedNodeHighlighting()
{

  var currentNodeMac = $(".networkNodeTabHeaders.active a").data("mytabmac");

  // change highlighted node in the tree
  selNode = $("#networkTree .highlightedNode")[0]

  console.log(selNode)

  if(selNode)
  {
    $(selNode).attr('class',  $(selNode).attr('class').replace('highlightedNode'))
  }

  newSelNode = $("#networkTree div[data-mac='"+currentNodeMac+"']")[0]

  console.log(newSelNode)

  $(newSelNode).attr('class',  $(newSelNode).attr('class') + ' highlightedNode')
}

/**
 * Update a device's network assignment
 * @param {string} leafMac - MAC address of device to update
 * @param {string} action - 'assign' or 'unassign'
 */
function updateLeaf(leafMac, action) {
  console.log(leafMac); // child
  console.log(action);  // action

  const nodeMac = $(".networkNodeTabHeaders.active a").data("mytabmac") || "";

  if (action === "assign") {
    if (!nodeMac) {
      showMessage(getString("Network_Cant_Assign_No_Node_Selected"));
    } else if (leafMac.toLowerCase().includes("internet")) {
      showMessage(getString("Network_Cant_Assign"));
    } else {
      saveData("updateNetworkLeaf", leafMac, nodeMac);
      setTimeout(() => location.reload(), 500);
    }

  } else if (action === "unassign") {
    saveData("updateNetworkLeaf", leafMac, "");
    setTimeout(() => location.reload(), 500);

  } else {
    console.warn("Unknown action:", action);
  }
}

/**
 * Dynamically show/hide tab names based on available space
 * Hides tab names when tabs overflow, shows them again when space is available
 */
function checkTabsOverflow() {
  const $ul = $('.nav-tabs');
  const $lis = $ul.find('li');

  // First measure widths with current state
  let totalWidth = 0;
  $lis.each(function () {
    totalWidth += $(this).outerWidth(true);
  });

  const ulWidth = $ul.width();
  const isOverflowing = totalWidth > ulWidth;

  if (isOverflowing) {
    if (!$ul.hasClass('hide-node-names')) {
      $ul.addClass('hide-node-names');

      // Re-check: did hiding fix it?
      requestAnimationFrame(() => {
        let newTotal = 0;
        $lis.each(function () {
          newTotal += $(this).outerWidth(true);
        });

        if (newTotal > $ul.width()) {
          // Still overflowing — do nothing, keep class
        }
      });
    }
  } else {
    if ($ul.hasClass('hide-node-names')) {
      $ul.removeClass('hide-node-names');

      // Re-check: did un-hiding break it?
      requestAnimationFrame(() => {
        let newTotal = 0;
        $lis.each(function () {
          newTotal += $(this).outerWidth(true);
        });

        if (newTotal > $ul.width()) {
          // Oops, that broke it — re-hide
          $ul.addClass('hide-node-names');
        }
      });
    }
  }
}
