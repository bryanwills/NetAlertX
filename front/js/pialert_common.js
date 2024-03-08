/* -----------------------------------------------------------------------------
*  Pi.Alert
*  Open Source Network Guard / WIFI & LAN intrusion detector 
*
*  pialert_common.js - Front module. Common Javascript functions
*-------------------------------------------------------------------------------
#  Puche 2021 / 2022+ jokob             jokob@duck.com                GNU GPLv3
----------------------------------------------------------------------------- */

// -----------------------------------------------------------------------------
var timerRefreshData = ''
var modalCallbackFunction = '';
var emptyArr            = ['undefined', "", undefined, null, 'null'];
var UI_LANG = "English";
var settingsJSON = {}


// urlParams = new Proxy(new URLSearchParams(window.location.search), {
//   get: (searchParams, prop) => searchParams.get(prop.toString()),
// });


// -----------------------------------------------------------------------------
// Simple session cache withe expiration managed via cookies
// -----------------------------------------------------------------------------
function getCache(key, noCookie = false)
{
  // check cache
  if(sessionStorage.getItem(key))
  {
    // check if not expired
    if(noCookie || getCookie(key + '_session_expiry') != "")
    {
      return sessionStorage.getItem(key);
    }
  }

  return "";  
}

// -----------------------------------------------------------------------------
function setCache(key, data, expirationMinutes='')
{
  sessionStorage.setItem(key, data);  

  // create cookie if expiration set to handle refresh of data
  if (expirationMinutes != '') 
  {
    setCookie (key + '_session_expiry', 'OK', expirationMinutes='')
  }
}


// -----------------------------------------------------------------------------
function setCookie (cookie, value, expirationMinutes='') {
  // Calc expiration date
  var expires = '';
  if (typeof expirationMinutes === 'number') {
    expires = ';expires=' + new Date(Date.now() + expirationMinutes *60*1000).toUTCString();
  } 

  // Save Cookie
  document.cookie = cookie + "=" + value + expires;
}

// -----------------------------------------------------------------------------
function getCookie (cookie) {
  // Array of cookies
  var allCookies = document.cookie.split(';');

  // For each cookie
  for (var i = 0; i < allCookies.length; i++) {
    var currentCookie = allCookies[i].trim();

    // If the current cookie is the correct cookie
    if (currentCookie.indexOf (cookie +'=') == 0) {
      // Return value
      return currentCookie.substring (cookie.length+1);
    }
  }

  // Return empty (not found)
  return "";
}


// -----------------------------------------------------------------------------
function deleteCookie (cookie) {
  document.cookie = cookie + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC';
}

// -----------------------------------------------------------------------------
function deleteAllCookies() {
  // Array of cookies
  var allCookies = document.cookie.split(";");

  // For each cookie
  for (var i = 0; i < allCookies.length; i++) {
    var cookie = allCookies[i].trim();
    var eqPos = cookie.indexOf("=");
    var name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC";
    }
}




// -----------------------------------------------------------------------------
// Get settings from the .json file generated by the python backend
// -----------------------------------------------------------------------------
function cacheSettings()
{
  
  $.get('api/table_settings.json?nocache=' + Date.now(), function(res) { 
    
    settingsJSON = res;
        
    data = settingsJSON["data"];       

    data.forEach((set) => {      
      setCache(`pia_set_${set.Code_Name}`, set.Value) 
    });        
  })
}

// Get a setting value by key
function getSetting (key) {

  // handle initial load to make sure everything is set-up and cached
  handleFirstLoad()
 
  result = getCache(`pia_set_${key}`, true);

  if (result == "")
  {
    console.log(`Setting with key "${key}" not found`)
  }

  return result;
}

// -----------------------------------------------------------------------------
// Get language string
// -----------------------------------------------------------------------------
function cacheStrings()
{

  // handle core strings and translations
  var allLanguages = ["en_us", "es_es", "de_de"]; // needs to be same as in lang.php

  allLanguages.forEach(function (language_code) {
    $.get(`php/templates/language/${language_code}.json?nocache=${Date.now()}`, function (res) {
      // Iterate over each language
      Object.entries(res).forEach(([key, value]) => {
        // Store translations for each key-value pair
        setCache(`pia_lang_${key}_${language_code}`, value)
      });
    });
  });

  
  // handle strings and translations from plugins
  $.get(`api/table_plugins_language_strings.json?nocache=${Date.now()}`, function(res) {    
        
    data = res["data"];       

    data.forEach((langString) => {      
      setCache(`pia_lang_${langString.String_Key}_${langString.Language_Code}`, langString.String_Value) 
    });        
  })
  
}

// Get translated language string
function getString (key) {

  // handle initial laod to make sure everything is set-up and cached
  handleFirstLoad()
 
  UI_LANG = getSetting("UI_LANG");

  lang_code = 'en_us';

  switch(UI_LANG)
  {
    case 'English': 
      lang_code = 'en_us';
      break;
    case 'Spanish': 
      lang_code = 'es_es';
      break;
    case 'German': 
      lang_code = 'de_de';
      break;
  }
  result = getCache(`pia_lang_${key}_${lang_code}`, true);


  if(isEmpty(result))
  {    
    result = getCache(`pia_lang_${key}_en_us`, true);
  }

  return result;
}

// -----------------------------------------------------------------------------
// Modal dialog handling
// -----------------------------------------------------------------------------
function showModalOK (title, message, callbackFunction) {
  showModalOk (title, message, callbackFunction)
}
function showModalOk (title, message, callbackFunction) {
  // set captions
  $('#modal-ok-title').html   (title);
  $('#modal-ok-message').html (message); 
  
  if(callbackFunction!= null)
  {   
    $("#modal-ok-OK").click(function()
    { 
      callbackFunction()      
    });
  }

  // Show modal
  $('#modal-ok').modal('show');
}

// -----------------------------------------------------------------------------
function showModalDefault (title, message, btnCancel, btnOK, callbackFunction) {
  // set captions
  $('#modal-default-title').html   (title);
  $('#modal-default-message').html (message);
  $('#modal-default-cancel').html  (btnCancel);
  $('#modal-default-OK').html      (btnOK);
  modalCallbackFunction =          callbackFunction;

  // Show modal
  $('#modal-default').modal('show');
}

// -----------------------------------------------------------------------------

function showModalDefaultStrParam (title, message, btnCancel, btnOK, callbackFunction, param='') {
  // set captions
  $('#modal-str-title').html   (title);
  $('#modal-str-message').html (message);
  $('#modal-str-cancel').html  (btnCancel);
  $('#modal-str-OK').html      (btnOK);
  $("#modal-str-OK").off("click"); //remove existing handlers
  $('#modal-str-OK').on('click', function (){ 
    $('#modal-str').modal('hide');
    callbackFunction(param)
  })

  // Show modal
  $('#modal-str').modal('show');
}

// -----------------------------------------------------------------------------
function showModalWarning (title, message, btnCancel=getString('Gen_Cancel'), btnOK=getString('Gen_Okay'), callbackFunction=null) {
  // set captions
  $('#modal-warning-title').html   (title);
  $('#modal-warning-message').html (message);
  $('#modal-warning-cancel').html  (btnCancel);
  $('#modal-warning-OK').html      (btnOK);

  if ( callbackFunction != null)
  {
    modalCallbackFunction =          callbackFunction;
  }

  // Show modal
  $('#modal-warning').modal('show');
}

// -----------------------------------------------------------------------------
function modalDefaultOK () {
  // Hide modal
  $('#modal-default').modal('hide');

  // timer to execute function
  window.setTimeout( function() {
    window[modalCallbackFunction]();
  }, 100);
}

// -----------------------------------------------------------------------------
function modalWarningOK () {
  // Hide modal
  $('#modal-warning').modal('hide');

  // timer to execute function
  window.setTimeout( function() {
    window[modalCallbackFunction]();
  }, 100);
}

// -----------------------------------------------------------------------------
function showMessage (textMessage="") {
  if (textMessage.toLowerCase().includes("error")  ) {
    // show error
    alert (textMessage);
  } else {
    // show temporal notification
    $("#alert-message").html (textMessage);
    $("#notification").fadeIn(1, function () {
      window.setTimeout( function() {
        $("#notification").fadeOut(500)
      }, 3000);
    } );
  }
}


// -----------------------------------------------------------------------------
// String utilities
// -----------------------------------------------------------------------------
function jsonSyntaxHighlight(json) {
  if (typeof json != 'string') {
       json = JSON.stringify(json, undefined, 2);
  }
  json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
      var cls = 'number';
      if (/^"/.test(match)) {
          if (/:$/.test(match)) {
              cls = 'key';
          } else {
              cls = 'string';
          }
      } else if (/true|false/.test(match)) {
          cls = 'boolean';
      } else if (/null/.test(match)) {
          cls = 'null';
      }
      return '<span class="' + cls + '">' + match + '</span>';
  });
}


// -----------------------------------------------------------------------------
// General utilities
// -----------------------------------------------------------------------------

// check if JSON object
function isJsonObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}


// remove unnecessary lines from the result
function sanitize(data)
{
  return data.replace(/(\r\n|\n|\r)/gm,"").replace(/[^\x00-\x7F]/g, "")
}


// -----------------------------------------------------------------------------
// Check and handle locked database
function handle_locked_DB(data)
{
  if(data.includes('database is locked'))
  {
    // console.log(data)    
    showSpinner()

    setTimeout(function() {
      location.reload(); 
    }, 5000);
  }
}

// -----------------------------------------------------------------------------
function numberArrayFromString(data)
{  
  data = JSON.parse(sanitize(data));
  return data.replace(/\[|\]/g, '').split(',').map(Number);
}

// -----------------------------------------------------------------------------
function setParameter (parameter, value) {
  // Retry
  $.get('php/server/parameters.php?action=set&parameter=' + parameter +
    '&value='+ value,
  function(data) {
    if (data != "OK") {
      // Retry
      sleep (200);
      $.get('php/server/parameters.php?action=set&parameter=' + parameter +
        '&value='+ value,
        function(data) {
          if (data != "OK") {
          // alert (data);
          } else {
          // alert ("OK. Second attempt");
          };
      } );
    };
  } );
}


// -----------------------------------------------------------------------------  
function saveData(functionName, id, value) {
  $.ajax({
    method: "GET",
    url: "php/server/devices.php",
    data: { action: functionName, id: id, value:value  },
    success: function(data) {      
        
        if(sanitize(data) == 'OK')
        {
          showMessage("Saved")
          // Remove navigation prompt "Are you sure you want to leave..."
          window.onbeforeunload = null;
        } else
        {
          showMessage("ERROR")
        }        

      }
  });

}


// -----------------------------------------------------------------------------
// create a link to the device
function createDeviceLink(input)
{
  if(checkMacOrInternet(input))
  {
    return `<span class="anonymizeMac"><a href="/deviceDetails.php?mac=${input}" target="_blank">${getNameByMacAddress(input)}</a><span>`
  }

  return input;
}


// -----------------------------------------------------------------------------
// remove an item from an array
function removeItemFromArray(arr, value) {
  var index = arr.indexOf(value);
  if (index > -1) {
    arr.splice(index, 1);
  }
  return arr;
}

// -----------------------------------------------------------------------------
function sleep(milliseconds) {
  const date = Date.now();
  let currentDate = null;
  do {
    currentDate = Date.now();
  } while (currentDate - date < milliseconds);
}

// --------------------------------------------------------- 
somethingChanged = false;
function settingsChanged()
{
  somethingChanged = true;
  // Enable navigation prompt ... "Are you sure you want to leave..."
  window.onbeforeunload = function() {  
    return true;
  };
}

// -----------------------------------------------------------------------------
// Get Anchor from URL
function getUrlAnchor(defaultValue){

  target = defaultValue

  var url = window.location.href;
  if (url.includes("#")) {

    // default selection
    selectedTab = defaultValue

    // the #target from the url
    target = window.location.hash.substr(1) 

    // get only the part between #...?
    if(target.includes('?'))
    {
      target = target.split('?')[0]
    }
  
    return target
  
  }

}

// -----------------------------------------------------------------------------
// get query string from URL
function getQueryString(key){
  params = new Proxy(new URLSearchParams(window.location.search), {
    get: (searchParams, prop) => searchParams.get(prop),
  });

  tmp = params[key] 

  if(emptyArr.includes(tmp))
  {
    var queryParams = {};
    fullUrl = window.location.toString();

    // console.log(fullUrl);

    if (fullUrl.includes('?')) {
      var queryString = fullUrl.split('?')[1];
  
      // Split the query string into individual parameters
      var paramsArray = queryString.split('&');
  
      // Loop through the parameters array
      paramsArray.forEach(function(param) {
          // Split each parameter into key and value
          var keyValue = param.split('=');
          var keyTmp = decodeURIComponent(keyValue[0]);
          var value = decodeURIComponent(keyValue[1] || '');
  
          // Store key-value pair in the queryParams object
          queryParams[keyTmp] = value;
      });
    }

    // console.log(queryParams);

    tmp = queryParams[key]
  }

  result = emptyArr.includes(tmp) ? "" : tmp;

  return result
}  
// -----------------------------------------------------------------------------
function translateHTMLcodes (text) {
  if (text == null || emptyArr.includes(text)) {
    return null;
  } else if (typeof text === 'string' || text instanceof String)
  {
    var text2 = text.replace(new RegExp(' ', 'g'), "&nbsp");
    text2 = text2.replace(new RegExp('<', 'g'), "&lt");
    return text2;
  }

  return "";
}


// -----------------------------------------------------------------------------
function stopTimerRefreshData () {
  try {
    clearTimeout (timerRefreshData); 
  } catch (e) {}
}


// -----------------------------------------------------------------------------
function newTimerRefreshData (refeshFunction) {
  timerRefreshData = setTimeout (function() {
    refeshFunction();
  }, 60000);
}


// -----------------------------------------------------------------------------
function debugTimer () {
  $('#pageTitle').html (new Date().getSeconds());
}


// -----------------------------------------------------------------------------
// Open url in new tab
function openInNewTab (url) {
  window.open(url, "_blank");
}

// ----------------------------------------------------------------------------- 
// Navigate to URL if the current URL is not in the provided list of URLs
function openUrl(urls) {
  var currentUrl = window.location.href;
  var mainUrl = currentUrl.match(/^.*?(?=#|\?|$)/)[0]; // Extract main URL

  var isMatch = false;

  $.each(urls,function(index, obj){

    // remove . for comaprison if in the string, e.g.: ./devices.php
    arrayUrl = obj.replace('.','')

    // check if we are on a url contained in the array
    if(mainUrl.includes(arrayUrl))
    {
      isMatch = true;
    }
  });

  // if we are not, redirect
  if (isMatch == false) {
    window.location.href = urls[0]; // Redirect to the first URL in the list if not found
  }
}


// -----------------------------------------------------------------------------
function navigateToDeviceWithIp (ip) {

  $.get('api/table_devices.json', function(res) {    
        
    devices = res["data"];

    mac = ""
    
    $.each(devices, function(index, obj) {
      
      if(obj.dev_LastIP.trim() == ip.trim())
      {
        mac = obj.dev_MAC;

        window.open(window.location.origin +'/deviceDetails.php?mac=' + mac , "_blank");
      }
    });
    
  });
}

// -----------------------------------------------------------------------------
function getNameByMacAddress(macAddress) {
  return getDeviceDataByMacAddress(macAddress, "dev_Name")
}

// -----------------------------------------------------------------------------
// Check if MAC or Internet
function checkMacOrInternet(inputStr) {
  // Regular expression pattern for matching a MAC address
  const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;

  if (inputStr.toLowerCase() === 'internet') {
      return true;
  } else if (macPattern.test(inputStr)) {
      return true;
  } else {
      return false;
  }
}


// -----------------------------------------------------------------------------
// A function used to make the IP address orderable
function isValidIPv6(ipAddress) {
  // Regular expression for IPv6 validation
  const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}$|^([0-9a-fA-F]{1,4}:){1,7}:|^([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}$|^([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}$|^([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}$|^([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}$|^([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}$|^[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})$/;

  return ipv6Regex.test(ipAddress);
}

function formatIPlong(ipAddress) {
  if (ipAddress.includes(':') && isValidIPv6(ipAddress)) {
    const parts = ipAddress.split(':');

    return parts.reduce((acc, part, index) => {
      if (part === '') {
        const remainingGroups = 8 - parts.length + 1;
        return acc << (16 * remainingGroups);
      }

      const hexValue = parseInt(part, 16);
      return acc | (hexValue << (112 - index * 16));
    }, 0);
  } else {
    // Handle IPv4 address
    const parts = ipAddress.split('.');

    if (parts.length !== 4) {
      console.log("⚠ Invalid IPv4 address: " + ipAddress);
      return -1; // or any other default value indicating an error
    }

    return (parseInt(parts[0]) << 24) |
           (parseInt(parts[1]) << 16) |
           (parseInt(parts[2]) << 8) |
           parseInt(parts[3]);
  }
}

// -----------------------------------------------------------------------------
// Check if MAC is a random one
function isRandomMAC(mac)
{
  isRandom = false;

  isRandom = ["2", "6", "A", "E", "a", "e"].includes(mac[1]); 

  // if detected as random, make sure it doesn't start with a prefix which teh suer doesn't want to mark as random
  if(isRandom)
  {
    $.each(createArray(getSetting("UI_NOT_RANDOM_MAC")), function(index, prefix) {

      if(mac.startsWith(prefix))
      {
        isRandom = false;     
      }    
      
    });
    
  }

  return isRandom;
}

  // ---------------------------------------------------------  
  // Generate an array object from a string representation of an array
  function createArray(input) {
    // Empty array
    if (input === '[]') {
      return [];
    }

    // Regex patterns
    const patternBrackets = /(^\s*\[)|(\]\s*$)/g;
    const patternQuotes = /(^\s*')|('\s*$)/g;
    const replacement = '';

    // Remove brackets
    const noBrackets = input.replace(patternBrackets, replacement);

    const options = [];

    // Create array
    const optionsTmp = noBrackets.split(',');

    // Handle only one item in array
    if (optionsTmp.length === 0) {
      return [noBrackets.replace(patternQuotes, replacement)];
    }

    // Remove quotes
    optionsTmp.forEach(item => {
      options.push(item.replace(patternQuotes, replacement).trim());
    });

    return options;
  }

// -----------------------------------------------------------------------------
// A function to get a device property using the mac address as key and DB column nakme as parameter
//  for the value to be returned
function getDeviceDataByMacAddress(macAddress, dbColumn) {

  const sessionDataKey = 'devicesListAll_JSON';  
  const sessionData = sessionStorage.getItem(sessionDataKey);

  if (!sessionData) {
      console.log(`Session variable "${sessionDataKey}" not found.`);
      return "Unknown";
  }

  const devices = JSON.parse(sessionData);

  for (const device of devices) {
      if (device["dev_MAC"].toLowerCase() === macAddress.toLowerCase()) {

          return device[dbColumn];
      }
  }

  return "Unknown"; // Return a default value if MAC address is not found
}

// -----------------------------------------------------------------------------

function initDeviceListAll_JSON()
{ 

  $.get('api/table_devices.json', function(data) {    
    
    // console.log(data)

    devicesListAll_JSON = data["data"]

    setCache('devicesListAll_JSON', JSON.stringify(devicesListAll_JSON))
  });

}

var devicesListAll_JSON      = [];   // this will contain a list off all devices 

// -----------------------------------------------------------------------------
function isEmpty(value)
{
  return emptyArr.includes(value)
}


// -----------------------------------------------------------------------------
// Generate a GUID
function getGuid() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

// -----------------------------------------------------------------------------
// UI 
// -----------------------------------------------------------------------------
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
//  Loading Spinner overlay
// -----------------------------------------------------------------------------
function showSpinner(stringKey='Loading')
{
  if($("#loadingSpinner").length)
  {    
    $("#loadingSpinner").show();
  }
  else{    
    html =  `
    <!-- spinner -->
    <div id="loadingSpinner" style="display: block">
      <div class="pa_semitransparent-panel"></div>
      <div class="panel panel-default pa_spinner">
        <table>
          <td width="130px" align="middle">${getString(stringKey)}</td>
          <td><i class="ion ion-ios-loop-strong fa-spin fa-2x fa-fw"></td>
        </table>
      </div>
    </div>
    `

    $(".wrapper").append(html)
  }
}
// -----------------------------------------------------------------------------
function hideSpinner()
{
  $("#loadingSpinner").hide()
}


// --------------------------------------------------------
// Calls a backend function to add a front-end event to an execution queue
function updateApi()
{

  // value has to be in format event|param. e.g. run|ARPSCAN
  action = `update_api|devices,appevents`

  $.ajax({
    method: "POST",
    url: "php/server/util.php",
    data: { function: "addToExecutionQueue", action: action  },
    success: function(data, textStatus) {
        console.log(data)
    }
  })
}

// ----------------------------------------------------------------------------- 
// handling smooth scrolling
// ----------------------------------------------------------------------------- 
function setupSmoothScrolling() {
  // Function to scroll to the element
  function scrollToElement(id) {
      $('html, body').animate({
          scrollTop: $("#" + id).offset().top - 50
      }, 1000);
  }

  // Scroll to the element when clicking on anchor links
  $('a[href*="#"]').on('click', function(event) {
      var href = $(this).attr('href');
      if (href !=='#' && href && href.includes('#') && !$(this).is('[data-toggle="collapse"]')) {
          var id = href.substring(href.indexOf("#") + 1); // Get the ID from the href attribute
          if ($("#" + id).length > 0) {
              event.preventDefault(); // Prevent default anchor behavior
              scrollToElement(id); // Scroll to the element
          }
      }
  });

  // Check if there's an ID in the URL and scroll to it
  var url = window.location.href;
  if (url.includes("#")) {
      var idFromURL = url.substring(url.indexOf("#") + 1);
      if ($("#" + idFromURL).length > 0) {
          scrollToElement(idFromURL);
      }
  }
}



// -----------------------------------------------------------------------------
// initialize
// -----------------------------------------------------------------------------
// Define a unique key for storing the flag in sessionStorage
var sessionStorageKey = "myScriptExecuted_pialert_common";

function resetInitializedFlag()
{
  // Set the flag in sessionStorage to indicate that the code and cahce needs to be reloaded
  sessionStorage.setItem(sessionStorageKey, "false");
}

// check if cache needs to be refreshed because of setting changes 
$.get('api/app_state.json?nocache=' + Date.now(), function(appState) {   

  console.log(appState["settingsImported"]*1000)
  
  importedMiliseconds = parseInt((appState["settingsImported"]*1000));

  lastReloaded = parseInt(sessionStorage.getItem(sessionStorageKey + '_time'));

  if(importedMiliseconds > lastReloaded)
  {
    resetInitializedFlag()
    location.reload();
  }

});

// Display spinner and reload page if not yet initialized
function handleFirstLoad()
{
  if(!pialert_common_init)
  {
    setTimeout(function() {
      
      location.reload(); 
    }, 100);
  }
}

// Check if the code has been executed before by checking sessionStorage
var pialert_common_init = sessionStorage.getItem(sessionStorageKey) === "true";

// Define a function that will execute the code only once
function executeOnce() {
  if (!pialert_common_init) {

    showSpinner()

    // Your initialization code here
    cacheSettings();
    cacheStrings();
    initDeviceListAll_JSON();

    // Set the flag in sessionStorage to indicate that the code has been executed and save time when last time the page for initialized
    sessionStorage.setItem(sessionStorageKey, "true");    
    const millisecondsNow = Date.now();
    sessionStorage.setItem(sessionStorageKey + '_time', millisecondsNow);

    console.log("init pialert_common.js");
  }
}

// Call the function to execute the code
executeOnce();






