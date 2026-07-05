<?php
require 'php/templates/header.php';
?>
<div class="content-wrapper changeHistoryPage spinnerTarget" id="changeHistoryPage">
  <section class="content-header">
    <h1>
      <?= lang('Navigation_ChangeHistory'); ?>
      <small><?= lang('device_history_col_changes'); ?></small>
    </h1>
  </section>
<?php
  require 'changeLogCore.php';
?>
</div>


<?php require 'php/templates/footer.php'; ?>
