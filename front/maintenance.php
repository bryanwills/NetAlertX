<?php

//------------------------------------------------------------------------------
//  Pi.Alert
//  Open Source Network Guard / WIFI & LAN intrusion detector 
//
//  devices.php - Front module. Server side. Manage Devices
//------------------------------------------------------------------------------
//  Puche      2021        pi.alert.application@gmail.com   GNU GPLv3
//  jokob-sk   2022        jokob.sk@gmail.com               GNU GPLv3
//  leiweibau  2022        https://github.com/leiweibau     GNU GPLv3
//------------------------------------------------------------------------------

// Skin selector config ----------------------------------------------------
//
// For security reasons, new language files must be entered into this array.
// The files in the language directory are compared with this array and only 
// then accepted.
//

if(isset($_POST['saveSettingsUI'])){
	if(!file_exists(dirname(__FILE__).'/../config/settings.json')){
		$fp = fopen(dirname(__FILE__).'/../config/settings.json', 'w');
		fwrite($fp, json_encode([], true));
		fclose($fp);
	}
	$config = json_decode(file_get_contents(dirname(__FILE__).'/../config/settings.json'), true);
	$config['skin'] = $_POST['skinselector'];
	$config['columnsTable'] = [];
	$config['numElementDevicesTable'] = $_POST['numElementDevicesTable'];
	foreach($_POST['columnsTable'] as $column){
		$config['columnsTable'][] = $column;
	}
	$fp = fopen(dirname(__FILE__).'/../config/settings.json', 'w');
	fwrite($fp, json_encode($config, true));
	fclose($fp);
}

//------------------------------------------------------------------------------

require 'php/templates/header.php';

$installed_skins = [
	'skin-black-light' => 'black light',
	'skin-black' => 'black',
	'skin-blue-light' => 'blue light',
	'skin-blue' => 'blue',
	'skin-green-light' => 'green light',
	'skin-green' => 'green',
	'skin-purple-light' => 'purple light',
	'skin-purple' => 'purple',
	'skin-red-light' => 'red light',
	'skin-red' => 'red',
	'skin-yellow-light' => 'yellow light',
	'skin-yellow' => 'yellow',
];

$columsTable = [
	'0' => lang('Device_TableHead_Name'),
	'1' => lang('Device_TableHead_Owner'),
	'2' => lang('Device_TableHead_Type'),
	'3' => lang('Device_TableHead_Icon'),
	'4' => lang('Device_TableHead_Favorite'),
	'5' => lang('Device_TableHead_Group'),
	'6' => lang('Device_TableHead_FirstSession'),
	'7' => lang('Device_TableHead_LastSession'),
	'8' => lang('Device_TableHead_LastIP'),
	'9' => lang('Device_TableHead_MAC'),
	'10' => lang('Device_TableHead_Status'),
	'11' => lang('Device_TableHead_MAC_full'),
	'12' => lang('Device_TableHead_LastIPOrder'),
	'13' => lang('Device_TableHead_Rowid'),
	'14' => lang('Device_TableHead_Parent_MAC'),
	'15' => lang('Device_TableHead_Connected_Devices'),
	'16' => lang('Device_TableHead_Location'),
	'17' => lang('Device_TableHead_Vendor'),
];

$numElementDevicesTable = [10, 25, 50, 100, 500];

?>
<!-- Page ------------------------------------------------------------------ -->
<div class="content-wrapper">

	<!-- Content header--------------------------------------------------------- -->
	<section class="content-header">
		<?php require 'php/templates/notification.php'; ?>
		<h1 id="pageTitle">
			<?= lang('Maintenance_Title'); ?>
		</h1>
	</section>

	<!-- Main content ---------------------------------------------------------- -->
	<section class="content">

		<?php
		// Size and last mod of DB ------------------------------------------------------
		$pia_db = str_replace('front', 'db', getcwd()) . '/pialert.db';
		$pia_db_size = number_format((filesize($pia_db) / 1000000), 2, ",", ".") . ' MB';
		$pia_db_mod = date("F d Y H:i:s", filemtime($pia_db));

		// Count and Calc Backups -------------------------------------------------------
		$Pia_Archive_Path = str_replace('front', 'db', getcwd()) . '/';
		$Pia_Archive_count = 0;
		$Pia_Archive_diskusage = 0;
		$files = glob($Pia_Archive_Path . "pialertdb_*.zip");
		if ($files) {
			$Pia_Archive_count = count($files);
		}
		foreach ($files as $result) {
			$Pia_Archive_diskusage = $Pia_Archive_diskusage + filesize($result);
		}
		$Pia_Archive_diskusage = number_format(($Pia_Archive_diskusage / 1000000), 2, ",", ".") . ' MB';

		// Find latest Backup for restore -----------------------------------------------
		$latestfiles = glob($Pia_Archive_Path . "pialertdb_*.zip");
		natsort($latestfiles);
		$latestfiles = array_reverse($latestfiles, False);

		$latestbackup = 'none';
		$latestbackup_date = 'no backup';

		if (count($latestfiles) > 0) {
			$latestbackup = $latestfiles[0];
			$latestbackup_date = date("Y-m-d H:i:s", filemtime($latestbackup));
		}
		?>

		<div class="row">
			<div class="col-md-12">
				<div class="box" id="Maintain-Status">
					<div class="box-header with-border">
						<h3 class="box-title">Status</h3>
					</div>
					<div class="box-body" style="padding-bottom: 5px;">
						<div class="db_info_table">
							<div class="db_info_table_row">
								<div class="db_info_table_cell" style="min-width: 140px"><?= lang('Maintenance_version'); ?></div>
								<div class="db_info_table_cell">
									<div class="version" id="version" data-build-time="<?php echo file_get_contents("buildtimestamp.txt"); ?>"><?php echo '<span id="new-version-text" class="myhidden">' . lang('Maintenance_new_version') . '</span>' . '<span id="current-version-text" class="myhidden">' . lang('Maintenance_current_version') . '</span>'; ?></div>
								</div>
							</div>
							<div class="db_info_table_row">
							<div class="db_info_table_cell" style="min-width: 140px"><?= lang('Maintenance_database_path'); ?></div>
							<div class="db_info_table_cell">
								<?php echo $pia_db; ?>
							</div>
						</div>
						<div class="db_info_table_row">
							<div class="db_info_table_cell"><?= lang('Maintenance_database_size'); ?></div>
							<div class="db_info_table_cell">
								<?php echo $pia_db_size; ?>
							</div>
						</div>
						<div class="db_info_table_row">
							<div class="db_info_table_cell"><?= lang('Maintenance_database_lastmod'); ?></div>
							<div class="db_info_table_cell">
								<?php echo $pia_db_mod; ?>
							</div>
						</div>
						<div class="db_info_table_row">
							<div class="db_info_table_cell"><?= lang('Maintenance_database_backup'); ?></div>
							<div class="db_info_table_cell">
								<?php echo $Pia_Archive_count . ' ' . lang('Maintenance_database_backup_found') . ' / ' . lang('Maintenance_database_backup_total') . ': ' . $Pia_Archive_diskusage; ?>
							</div>
						</div>
					</div>
				</div>
				<!-- /.box-body -->
			</div>
			</div>
		</div>

		<div class="nav-tabs-custom">
			<ul class="nav nav-tabs">
				<li class="active">
					<a id="tab_Settings_id" href="#tab_Settings" data-toggle="tab"><?= lang('Maintenance_Tools_Tab_UISettings'); ?></a>
				</li>
				<li>
					<a id="tab_DBTools_id" href="#tab_DBTools" data-toggle="tab"><?= lang('Maintenance_Tools_Tab_Tools'); ?></a>
				</li>
				<li>
					<a id="tab_BackupRestore_id" href="#tab_BackupRestore" data-toggle="tab"><?= lang('Maintenance_Tools_Tab_BackupRestore'); ?></a>
				</li>
				<li>
					<a id="tab_Logging_id" href="#tab_Logging" data-toggle="tab"><?= lang('Maintenance_Tools_Tab_Logging'); ?></a>
				</li>
			</ul>
		<div class="tab-content">
			<div class="tab-pane active" id="tab_Settings">
				<form method="post" action="maintenance.php">
					<div class="db_info_table">
						<div class="db_info_table_row">
							<div class="db_tools_table_cell_a" style="text-align: center;">
								<div style="display: inline-block; text-align: center;">
									<select name="skinselector" class="form-control bg-green" style="width:160px; margin-bottom:5px;">
										<?php
										foreach($installed_skins as $skin => $name){
											echo sprintf('<option value="%s" %s>%s</option>', $skin, $skin == _CONFIG_['skin'] ? 'SELECTED' : '', $name);
										}
										?>										
									</select>
								</div>
							</div>
							<div class="db_info_table_cell" style="padding: 10px; height:40px; text-align:left; vertical-align: middle;">
								<?= lang('Maintenance_themeselector_text'); ?>
							</div>
						</div>
						<div class="db_info_table_row">
							<div class="db_tools_table_cell_a">
								<button type="button" class="btn bg-green dbtools-button" id="btnToggleDarkmode" onclick="askToggleDarkmode()"><?= lang('Maintenance_Tool_darkmode'); ?></button>
							</div>
							<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_darkmode_text'); ?></div>
						</div>
						<div class="db_info_table_row">
							<div class="db_tools_table_cell_a">
								<div class="form-group">
									<div class="input-group">
										<select id="columnsTable" name="columnsTable[]" class="form-control select2 select2-hidden-accessible" multiple="" style="width: 100%;" tabindex="-1" aria-hidden="true">
											<?php
											foreach($columsTable as $id => $name){
												echo sprintf('<option value="%s" %s>%s</option>', $id, in_array($id, _CONFIG_['columnsTable']) ? 'SELECTED' : '', $name);
											}
											?>
										</select>
									</div>
								</div>

							</div>

							<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_displayed_columns_text'); ?></div>
						</div>
						<div class="db_info_table_row">
							<div class="db_tools_table_cell_a">
								<div class="form-group">
									<div class="">
										<select id="numElementDevicesTable" name="numElementDevicesTable" class="form-control " style="width: 100%;" tabindex="-1" aria-hidden="true">
											<?php
											foreach($numElementDevicesTable as $num){
												echo sprintf('<option value="%s" %s>%s</option>', $num, in_array($num, _CONFIG_['numElementDevicesTable']) ? 'SELECTED' : '', $num);
											}
											?>
										</select>
									</div>
								</div>

							</div>

							<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_displayed_columns_num'); ?></div>
						</div>
						<div class="db_info_table_row">
							<div class="db_tools_table_cell_a">
								<button type="submit" class="btn bg-green " id="btnToggleDarkmode" name="saveSettingsUI"><?= lang('Gen_Save'); ?></button>
							</div>
							<div class="db_tools_table_cell_b">
								
							</div>
						</div>

					</div>
				</form>
			</div>
			<div class="tab-pane" id="tab_DBTools">
				<div class="db_info_table">
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteMAC" onclick="askDeleteDevicesWithEmptyMACs()"><?= lang('Maintenance_Tool_del_empty_macs'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_empty_macs_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteMAC" onclick="askDeleteAllDevices()"><?= lang('Maintenance_Tool_del_alldev'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_alldev_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteUnknown" onclick="askDeleteUnknown()"><?= lang('Maintenance_Tool_del_unknowndev'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_unknowndev_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteEvents" onclick="askDeleteEvents()"><?= lang('Maintenance_Tool_del_allevents'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_allevents_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteEvents30" onclick="askDeleteEvents30()"><?= lang('Maintenance_Tool_del_allevents30'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_allevents30_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnDeleteActHistory" onclick="askDeleteActHistory()"><?= lang('Maintenance_Tool_del_ActHistory'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_del_ActHistory_text'); ?></div>
					</div>
				</div>
			</div>
			<div class="tab-pane" id="tab_BackupRestore">
				<div class="db_info_table">
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnPiaBackupDBtoArchive" onclick="askPiaBackupDBtoArchive()"><?= lang('Maintenance_Tool_backup'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_backup_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnPiaRestoreDBfromArchive" onclick="askPiaRestoreDBfromArchive()"><?= lang('Maintenance_Tool_restore'); ?><br><?php echo $latestbackup_date; ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_restore_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnPiaPurgeDBBackups" onclick="askPiaPurgeDBBackups()"><?= lang('Maintenance_Tool_purgebackup'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_purgebackup_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn bg-green dbtools-button" id="btnExportCSV" onclick="askExportCSV()"><?= lang('Maintenance_Tool_ExportCSV'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_ExportCSV_text'); ?></div>
					</div>
					<div class="db_info_table_row">
						<div class="db_tools_table_cell_a">
							<button type="button" class="btn btn-default pa-btn pa-btn-delete bg-red dbtools-button" id="btnImportCSV" onclick="askImportCSV()"><?= lang('Maintenance_Tool_ImportCSV'); ?></button>
						</div>
						<div class="db_tools_table_cell_b"><?= lang('Maintenance_Tool_ImportCSV_text'); ?></div>
					</div>
				</div>
			</div>
			<!-- ---------------------------Logging-------------------------------------------- -->
			<div class="tab-pane" id="tab_Logging">
				<div class="db_info_table">
					<div class="log-area">
						<div class="row logs-row">
							<textarea id="pialert_log" class="logs" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/pialert.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">pialert.log <div class="logs-size"><?php echo number_format((filesize("./log/pialert.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/pialert.log" target="_blank"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('pialert.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>
					</div>
					<div class="log-area">
						<div class="row logs-row">
							<textarea id="pialert_front_log" class="logs" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/pialert_front.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">pialert_front.log<div class="logs-size"><?php echo number_format((filesize("./log/pialert_front.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/pialert_front.log"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('pialert_front.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>
					</div>
					<div class="log-area">

						<div class="row logs-row">
							<textarea id="pialert_pholus_log" class="logs" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/pialert_pholus.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">pialert_pholus.log<div class="logs-size"><?php echo number_format((filesize("./log/pialert_pholus.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/pialert_pholus.log"><i class="fa fa-download"></i> </a></span>
								</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('pialert_pholus.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>

					</div>
					<div class="log-area">

						<div class="row logs-row">
							<textarea id="pialert_pholus_lastrun_log" class="logs logs-small" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/pialert_pholus_lastrun.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">pialert_pholus_lastrun.log<div class="logs-size"><?php echo number_format((filesize("./log/pialert_pholus_lastrun.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/pialert_pholus_lastrun.log"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('pialert_pholus_lastrun.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>

					</div>
					<div class="log-area">

						<div class="row logs-row">
							<textarea id="IP_changes_log" class="logs logs-small" cols="70" rows="10" readonly><?php echo file_get_contents("./log/IP_changes.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">IP_changes.log<div class="logs-size"><?php echo number_format((filesize("./log/IP_changes.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/IP_changes.log"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('IP_changes.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>

					</div>
					<div class="log-area">
						<div class="row logs-row">
							<textarea id="stdout_log" class="logs logs-small" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/stdout.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">stdout.log<div class="logs-size"><?php echo number_format((filesize("./log/stdout.log") / 1000000), 2, ",", ".") . ' MB'; ?>
										<span class="span-padding"><a href="./log/stdout.log"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('stdout.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>

					</div>
					<div class="log-area">
						<div class="row logs-row">
							<textarea id="stderr_log" class="logs logs-small" cols="70" rows="10" wrap='off' readonly><?php echo file_get_contents("./log/stderr.log"); ?>
							</textarea>
						</div>
						<div class="row logs-row">
							<div>
								<div class="log-file">stderr.log<div class="logs-size"><?php echo number_format((filesize("./log/stderr.log") / 1000000), 2, ",", ".") . ' MB'; ?>
									<span class="span-padding"><a href="./log/stderr.log"><i class="fa fa-download"></i> </a></span>
									</div>
								</div>
								<div class="log-purge">
									<button class="btn btn-primary" onclick="logManage('stderr.log','cleanLog')"><?= lang('Gen_Purge'); ?></button>
								</div>
							</div>
						</div>

					</div>

				</div>
			</div>
		</div>
		<!-- ------------------------------------------------------------------------------ -->
	</div>

	<div class="box-body" style="text-align: center;">
		<h5 class="text-aqua" style="font-size: 16px;">
			<span id="lastCommit">

			</span>
			<span id="lastDockerUpdate">

			</span>
		</h5>
	</div>


	</div>

	</section>

	<!-- /.content -->
	<?php
	require 'php/templates/footer.php';
	?>
	</div>
	<!-- /.content-wrapper -->

	<!-- ----------------------------------------------------------------------- -->




	<script>
		var emptyArr = ['undefined', "", undefined, null];
		var selectedTab = 'tab_Settings_id';

		initializeTabs();

		// delete devices with emty macs
		function askDeleteDevicesWithEmptyMACs() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_empty_macs_noti'); ?>', '<?= lang('Maintenance_Tool_del_empty_macs_noti_text'); ?>',
			'Cancel', 'Delete', 'deleteDevicesWithEmptyMACs');
		}

		function deleteDevicesWithEmptyMACs() {
			// Delete device
			$.get('php/server/devices.php?action=deleteAllWithEmptyMACs', function(msg) {
				showMessage(msg);
			});
		}

		// delete all devices 
		function askDeleteAllDevices() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_alldev_noti'); ?>', '<?= lang('Maintenance_Tool_del_alldev_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Delete'); ?>', 'deleteAllDevices');
		}

		function deleteAllDevices() {
			// Delete device
			$.get('php/server/devices.php?action=deleteAllDevices', function(msg) {
				showMessage(msg);
			});
		}

		// delete all (unknown) devices 
		function askDeleteUnknown() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_unknowndev_noti'); ?>', '<?= lang('Maintenance_Tool_del_unknowndev_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Delete'); ?>', 'deleteUnknownDevices');
		}

		function deleteUnknownDevices() {
			// Execute
			$.get('php/server/devices.php?action=deleteUnknownDevices', function(msg) {
				showMessage(msg);
			});
		}

		// delete all Events 
		function askDeleteEvents() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_allevents_noti'); ?>', '<?= lang('Maintenance_Tool_del_allevents_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Delete'); ?>', 'deleteEvents');
		}

		function deleteEvents() {
			// Execute
			$.get('php/server/devices.php?action=deleteEvents', function(msg) {
				showMessage(msg);
			});
		}

		// delete all Events older than 30 days
		function askDeleteEvents30() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_allevents30_noti'); ?>', '<?= lang('Maintenance_Tool_del_allevents30_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Delete'); ?>', 'deleteEvents30');
		}

		function deleteEvents30() {
			// Execute
			$.get('php/server/devices.php?action=deleteEvents30', function(msg) {
				showMessage(msg);
			});
		}

		// delete History 
		function askDeleteActHistory() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_del_ActHistory_noti'); ?>', '<?= lang('Maintenance_Tool_del_ActHistory_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Delete'); ?>', 'deleteActHistory');
		}

		function deleteActHistory() {
			// Execute
			$.get('php/server/devices.php?action=deleteActHistory', function(msg) {
				showMessage(msg);
			});
		}

		// Backup DB to Archive 
		function askPiaBackupDBtoArchive() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_backup_noti'); ?>', '<?= lang('Maintenance_Tool_backup_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Backup'); ?>', 'PiaBackupDBtoArchive');
		}

		function PiaBackupDBtoArchive() {
			// Execute
			$.get('php/server/devices.php?action=PiaBackupDBtoArchive', function(msg) {
				showMessage(msg);
			});
		}

		// Restore DB from Archive 
		function askPiaRestoreDBfromArchive() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_restore_noti'); ?>', '<?= lang('Maintenance_Tool_restore_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Restore'); ?>', 'PiaRestoreDBfromArchive');
		}

		function PiaRestoreDBfromArchive() {
			// Execute
			$.get('php/server/devices.php?action=PiaRestoreDBfromArchive', function(msg) {
				showMessage(msg);
			});
		}

		// Purge Backups 
		function askPiaPurgeDBBackups() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_purgebackup_noti'); ?>', '<?= lang('Maintenance_Tool_purgebackup_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Purge'); ?>', 'PiaPurgeDBBackups');
		}

		function PiaPurgeDBBackups() {
			// Execute
			$.get('php/server/devices.php?action=PiaPurgeDBBackups', function(msg) {
				showMessage(msg);
			});
		}

		// Export CSV
		function askExportCSV() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_ExportCSV_noti'); ?>', '<?= lang('Maintenance_Tool_ExportCSV_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Okay'); ?>', 'ExportCSV');
		}

		function ExportCSV() {
			// Execute
			openInNewTab(window.location.origin + "/php/server/devices.php?action=ExportCSV")
		}

		// Import CSV
		function askImportCSV() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_ImportCSV_noti'); ?>', '<?= lang('Maintenance_Tool_ImportCSV_noti_text'); ?>',
		'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Okay'); ?>', 'ImportCSV');
		}

		function ImportCSV() {
			// Execute
			$.get('/php/server/devices.php?action=ImportCSV', function(msg) {
				showMessage(msg);
			});
		}


		// --------------------------------------------------------
		// Switch Darkmode 
		function askToggleDarkmode() {
			// Ask 
			showModalWarning('<?= lang('Maintenance_Tool_darkmode_noti'); ?>', '<?= lang('Maintenance_Tool_darkmode_noti_text'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Switch'); ?>', 'ToggleDarkmode');
		}

		// --------------------------------------------------------
		function ToggleDarkmode() {
			// get parameter Front_Dark_Mode_Enabled value
			$.get('php/server/parameters.php?action=get&defaultValue=false&expireMinutes=525600&parameter=Front_Dark_Mode_Enabled', function(data) {
				var result = JSON.parse(data);
				if (result) {
					darkModeEnabled = result == 'true';

					// invert value
					darkModeEnabled = !darkModeEnabled;

					// save inverted value
					$.get('php/server/parameters.php?action=set&parameter=Front_Dark_Mode_Enabled&expireMinutes=525600&value=' + darkModeEnabled,
						function(data) {
							if (data != "OK") {
								showMessage(data);
								setTimeout(function() {
									location.reload()
								}, 1000);

							} else {
								showMessage(data);
							};
						}
					);

				}
			});
		}

		// --------------------------------------------------------

		// Clean log file 
		var targetLogFile = "";
		var logFileAction = "";


		// --------------------------------------------------------

		function logManage(callback) {
			targetLogFile = arguments[0]; // target
			logFileAction = arguments[1]; // action
			// Ask 
			showModalWarning('<?= lang('Gen_Purge'); ?>' + ' ' + arguments[1], '<?= lang('Gen_AreYouSure'); ?>',
			'<?= lang('Gen_Cancel'); ?>', '<?= lang('Gen_Okay'); ?>', "performLogManage");
		}

		// --------------------------------------------------------
		function performLogManage() {
			// Execute
			console.log("targetLogFile:" + targetLogFile)
			console.log("logFileAction:" + logFileAction)

			$.ajax({
				method: "POST",
				url: "php/server/util.php",
				data: {
					function: logFileAction,
					settings: targetLogFile
				},
				success: function(data, textStatus) {
					showModalOk('Result', data);
				}
			})
		}

		// --------------------------------------------------------
		function scrollDown() {
			var areaIDs = ['pialert_log', 'pialert_front_log', 'IP_changes_log', 'stdout_log', 'stderr_log', 'pialert_pholus_log', 'pialert_pholus_lastrun_log'];

			for (let i = 0; i < areaIDs.length; i++) {

				var tempArea = $('#' + areaIDs[i]);
				$(tempArea[0]).scrollTop(tempArea[0].scrollHeight);

			}
		}

		// --------------------------------------------------------
		// Manage displayed columns
		// --------------------------------------------------------
		colDefaultOrder = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '12', '13', '14', '15', '16', '17'];
		colDefaultOrderTxt = '[0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]';


		// --------------------------------------------------------
		//Initialize Select2 Elements and make them sortable

		$(function() {
			selectEl = $('.select2').select2();

			selectEl.next().children().children().children().sortable({
				containment: 'parent',
				stop: function(event, ui) {
					ui.item.parent().children('[title]').each(function() {
						var title = $(this).attr('title');
						var original = $('option:contains(' + title + ')', selectEl).first();
						original.detach();
						selectEl.append(original)
					});
					selectEl.change();
				}
			});
		});



		// --------------------------------------------------------
		// General initialization
		// --------------------------------------------------------
		function initializeTabs() {

			key = "activeMaintenanceTab"

			// default selection
			selectedTab = "tab_Settings"

			// the #target from the url
			target = window.location.hash.substr(1)

			// update cookie if target specified
			if (target != "") {
				setCache(key, target + '_id') // _id is added so it doesn't conflict with AdminLTE tab behavior
			}

			// get the tab id from the cookie (already overriden by the target)
			if (!emptyArr.includes(getCache(key))) {
				selectedTab = getCache(key);
			}

			// Activate panel
			$('.nav-tabs a[id=' + selectedTab + ']').tab('show');

			// When changed save new current tab
			$('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
				setCache(key, $(e.target).attr('id'))
			});

			// events on tab change
			$('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
				var target = $(e.target).attr("href") // activated tab

				if (target == "#tab_Logging") {
					scrollDown();
				}
			});
		}

		// --------------------------------------------------------

		// save language in a cookie
		$('#langselector').on('change', function(e) {
			var optionSelected = $("option:selected", this);
			var valueSelected = this.value;
			setCookie("language", valueSelected)
			location.reload();
		});
		// --------------------------------------------------------

		// load footer asynchronously not to block the page load/other sections
		window.onload = function asyncFooter() {
			scrollDown();

			initializeTabs();

			$("#lastCommit").append('<a href="https://github.com/jokob-sk/Pi.Alert/commits" target="_blank"><img  alt="GitHub last commit" src="https://img.shields.io/github/last-commit/jokob-sk/pi.alert/main?logo=github"></a>');

			$("#lastDockerUpdate").append(
			'<a href="https://hub.docker.com/r/jokobsk/pi.alert/tags" target="_blank"><img alt="Docker last pushed" src="https://img.shields.io/badge/dynamic/json?color=blue&label=Last%20pushed&query=last_updated&url=https%3A%2F%2Fhub.docker.com%2Fv2%2Frepositories%2Fjokobsk%2Fpi.alert%2F&logo=docker&?link=http://left&link=https://hub.docker.com/repository/docker/jokobsk/pi.alert"></a>');

		}
	</script>

	<link rel="stylesheet" href="lib/AdminLTE/bower_components/select2/dist/css/select2.min.css">
	<script src="lib/AdminLTE/bower_components/select2/dist/js/select2.full.min.js"></script>
	<script src="lib/AdminLTE/bower_components/jquery-ui/jquery-ui.min.js"></script>



	<!-- ----------------------------------------------------------------------- -->
	<script src="js/pialert_common.js"></script>