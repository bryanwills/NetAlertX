<!-- Change Log Tab Skeleton =============================================== -->
<div id="skel-tab-history" class="skel-tab-pane spinnerTarget">
  <!-- Filter row -->
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding:0 2px;">
    <span class="skel-shimmer" style="width:120px; height:28px; border-radius:4px; flex-shrink:0;"></span>
    <span class="skel-shimmer" style="width:120px; height:28px; border-radius:4px; flex-shrink:0;"></span>
  </div>
  <!-- Table -->
  <div class="skel-table-box">
    <div class="skel-table-header-row">
      <span class="skel-th skel-shimmer" style="flex:1.5"></span>
      <span class="skel-th skel-shimmer" style="flex:1.5"></span>
      <span class="skel-th skel-shimmer" style="flex:4"></span>
    </div>
    <?php for ($i = 0; $i < 6; $i++): ?>
    <div class="skel-tr">
      <span class="skel-td skel-shimmer" style="flex:1.5; max-width:16%"></span>
      <span class="skel-td skel-shimmer" style="flex:1.5; max-width:14%"></span>
      <div style="flex:4; display:flex; flex-direction:column; gap:4px; padding:4px 0;">
        <span class="skel-td skel-shimmer" style="width:<?= 40 + ($i * 7) % 30 ?>%"></span>
        <span class="skel-td skel-shimmer" style="width:<?= 30 + ($i * 11) % 25 ?>%"></span>
      </div>
    </div>
    <?php endfor; ?>
  </div>
</div>
