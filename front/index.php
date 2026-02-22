<!-- NetAlertX CSS -->
<link rel="stylesheet" href="css/app.css">

<?php

require_once $_SERVER['DOCUMENT_ROOT'].'/php/server/db.php';
require_once $_SERVER['DOCUMENT_ROOT'].'/php/templates/language/lang.php';
require_once $_SERVER['DOCUMENT_ROOT'].'/php/templates/security.php';

// if (session_status() === PHP_SESSION_NONE) {
//     session_start();
// }

session_start();

const COOKIE_NAME = 'NetAlertX_SaveLogin';
const DEFAULT_REDIRECT = '/devices.php';

/* =====================================================
   Helper Functions
===================================================== */

function safe_redirect(string $path): void {
    header("Location: {$path}", true, 302);
    exit;
}

function validate_local_path(?string $encoded): string {
    if (!$encoded) return DEFAULT_REDIRECT;

    $decoded = base64_decode($encoded, true);
    if ($decoded === false) {
        return DEFAULT_REDIRECT;
    }

    // strict local path check (allow safe query strings + fragments)
    // Using ~ as the delimiter instead of #
    if (!preg_match('~^(?!//)(?!.*://)/[a-zA-Z0-9_\-./?=&:%#]*$~', $decoded)) {
        return DEFAULT_REDIRECT;
    }

    return $decoded;
}

function append_hash(string $url): string {
    if (!empty($_POST['url_hash'])) {
        return $url . preg_replace('/[^#a-zA-Z0-9_\-]/', '', $_POST['url_hash']);
    }
    return $url;
}

function is_authenticated(): bool {
    return isset($_SESSION['login']) && $_SESSION['login'] === 1;
}

function login_user(): void {
    $_SESSION['login'] = 1;
    session_regenerate_id(true);
}

function is_https_request(): bool {

    // Direct HTTPS detection
    if (!empty($_SERVER['HTTPS']) && strtolower($_SERVER['HTTPS']) !== 'off') {
        return true;
    }

    // Standard port check
    if (!empty($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == 443) {
        return true;
    }

    // Trusted proxy headers (only valid if behind a trusted reverse proxy)
    if (!empty($_SERVER['HTTP_X_FORWARDED_PROTO']) &&
        strtolower($_SERVER['HTTP_X_FORWARDED_PROTO']) === 'https') {
        return true;
    }

    if (!empty($_SERVER['HTTP_X_FORWARDED_SSL']) &&
        strtolower($_SERVER['HTTP_X_FORWARDED_SSL']) === 'on') {
        return true;
    }

    return false;
}

function call_api(string $endpoint, array $data = []): ?array {
    /*
    Call NetAlertX API endpoint (for login page endpoints that don't require auth).

    Returns: JSON response as array, or null on failure
    */
    try {
        // Determine API host (assume localhost on same port as frontend)
        $api_host = $_SERVER['HTTP_HOST'] ?? 'localhost';
        $api_scheme = is_https_request() ? 'https' : 'http';
        $api_url = $api_scheme . '://' . $api_host;

        $url = $api_url . $endpoint;

        $ch = curl_init($url);
        if (!$ch) return null;

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 5,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Accept: application/json'
            ]
        ]);

        if (!empty($data)) {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }

        $response = curl_exec($ch);
        $httpcode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpcode !== 200 || !$response) {
            return null;
        }

        return json_decode($response, true);
    } catch (Exception $e) {
        return null;
    }
}


function logout_user(): void {
    $_SESSION = [];
    session_destroy();

    setcookie(COOKIE_NAME,'',[
        'expires'=>time()-3600,
        'path'=>'/',
        'secure'=>is_https_request(),
        'httponly'=>true,
        'samesite'=>'Strict'
    ]);
}

/* =====================================================
   Redirect Handling
===================================================== */

$redirectTo = validate_local_path($_GET['next'] ?? null);

/* =====================================================
   Web Protection Disabled
===================================================== */

if ($nax_WebProtection !== 'true') {
    if (!is_authenticated()) {
        login_user();
    }
    safe_redirect(append_hash($redirectTo));
}

/* =====================================================
   Login Attempt
===================================================== */

if (!empty($_POST['loginpassword'])) {

    $incomingHash = hash('sha256', $_POST['loginpassword']);

    if (hash_equals($nax_Password, $incomingHash)) {

        login_user();

        // Handle "Remember Me" if checked
        if (!empty($_POST['PWRemember'])) {
            // Generate random token (64-byte hex = 128 chars, use 64 chars)
            $token = bin2hex(random_bytes(32));

            // Call API to save token hash to Parameters table
            $save_response = call_api('/auth/remember-me/save', [
                'token' => $token
            ]);

            // If API call successful, set persistent cookie
            if ($save_response && isset($save_response['success']) && $save_response['success']) {
                setcookie(COOKIE_NAME, $token, [
                    'expires' => time() + 604800,
                    'path' => '/',
                    'secure' => is_https_request(),
                    'httponly' => true,
                    'samesite' => 'Strict'
                ]);
            }
        }

        safe_redirect(append_hash($redirectTo));
    }
}

/* =====================================================
   Remember Me Validation
===================================================== */

if (!is_authenticated() && !empty($_COOKIE[COOKIE_NAME])) {

    // Call API to validate token against stored hash
    $validate_response = call_api('/auth/validate-remember', [
        'token' => $_COOKIE[COOKIE_NAME]
    ]);

    // If API returns valid token, authenticate and redirect
    if ($validate_response && isset($validate_response['valid']) && $validate_response['valid'] === true) {
        login_user();
        safe_redirect(append_hash($redirectTo));
    }
}

/* =====================================================
   Already Logged In
===================================================== */

if (is_authenticated()) {
    safe_redirect(append_hash($redirectTo));
}

/* =====================================================
   Login UI Variables
===================================================== */

$login_headline = lang('Login_Toggle_Info_headline');
$login_info     = lang('Login_Info');
$login_mode     = 'info';
$login_display_mode = 'display:none;';
$login_icon     = 'fa-info';

if ($nax_Password === '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92') {
    $login_info = lang('Login_Default_PWD');
    $login_mode = 'danger';
    $login_display_mode = 'display:block;';
    $login_headline = lang('Login_Toggle_Alert_headline');
    $login_icon = 'fa-ban';
}
?>

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>NetAlert X | Log in</title>
  <!-- Tell the browser to be responsive to screen width -->
  <meta content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" name="viewport">
  <!-- Bootstrap 3.3.7 -->
  <link rel="stylesheet" href="lib/bootstrap/bootstrap.min.css">
  <!-- Ionicons -->
  <link rel="stylesheet" href="lib/Ionicons/ionicons.min.css">
  <!-- Theme style -->
  <link rel="stylesheet" href="lib/AdminLTE/dist/css/AdminLTE.min.css">
  <!-- iCheck -->
  <link rel="stylesheet" href="lib/iCheck/square/blue.css">
  <!-- Font Awesome -->
  <link rel="stylesheet" href="lib/font-awesome/all.min.css">

  <!-- Favicon -->
  <link id="favicon" rel="icon" type="image/x-icon" href="img/NetAlertX_logo.png">
  <link rel="stylesheet" href="/css/offline-font.css">
</head>
<body class="hold-transition login-page col-sm-12 col-sx-12">
<div class="login-box login-custom">
  <div class="login-logo">
    <a href="/index2.php">Net<b>Alert</b><sup>x</sup></a>
  </div>
  <!-- /.login-logo -->
  <div class="login-box-body">
    <p class="login-box-msg"><?= lang('Login_Box');?></p>
      <form action="index.php<?php
      echo !empty($_GET['next'])
          ? '?next=' . htmlspecialchars($_GET['next'], ENT_QUOTES, 'UTF-8')
          : '';
      ?>" method="post">
      <div class="form-group has-feedback">
        <input type="hidden" name="url_hash" id="url_hash">
        <input type="password" class="form-control" placeholder="<?= lang('Login_Psw-box');?>" name="loginpassword">
        <span class="glyphicon glyphicon-lock form-control-feedback"></span>
      </div>
      <div class="row">
        <div class="col-xs-8">
          <div class="checkbox icheck">
            <label>
              <input type="checkbox" name="PWRemember">
                <div style="margin-left: 10px; display: inline-block; vertical-align: top;">
                  <?= lang('Login_Remember');?><br><span style="font-size: smaller"><?= lang('Login_Remember_small');?></span>
                </div>
            </label>
          </div>
        </div>
        <!-- /.col -->
        <div class="col-xs-4" style="padding-top: 10px;">
          <button type="submit" class="btn btn-primary btn-block btn-flat"><?= lang('Login_Submit');?></button>
        </div>
        <!-- /.col -->
      </div>
    </form>

    <div style="padding-top: 10px;">
      <button class="btn btn-xs btn-primary btn-block btn-flat" onclick="Passwordhinfo()"><?= lang('Login_Toggle_Info');?></button>
    </div>

  </div>
  <!-- /.login-box-body -->

  <div id="myDIV" class="box-body" style="margin-top: 50px; <?php echo $login_display_mode;?>">
      <div class="alert alert-<?php echo $login_mode;?> alert-dismissible">
          <button type="button" class="close" onclick="Passwordhinfo()" aria-hidden="true">X</button>
          <h4><i class="icon fa <?php echo $login_icon;?>"></i><?php echo $login_headline;?></h4>
          <p><?php echo $login_info;?></p>
      </div>
  </div>


</div>
<!-- /.login-box -->


<!-- jQuery 3 -->
<script src="lib/jquery/jquery.min.js"></script>

<!-- iCheck -->
<script src="lib/iCheck/icheck.min.js"></script>
<script>
  if (window.location.hash) {
      document.getElementById('url_hash').value = window.location.hash;
  }
  $(function () {
    $('input').iCheck({
      checkboxClass: 'icheckbox_square-blue',
      radioClass: 'iradio_square-blue',
      increaseArea: '20%' /* optional */
    });
  });

function Passwordhinfo() {
  var x = document.getElementById("myDIV");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}

</script>
</body>
</html>
