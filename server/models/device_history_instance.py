"""
device_history_instance.py — Query, group, and prune DevicesHistory records.

Writes are handled entirely by SQLite triggers (trg_devhist_update /
trg_devhist_insert) created in db/db_history.py. This class is read/prune only.
"""

from database import get_temp_db_connection
from logger import mylog


class DevicesHistoryInstance:

    # -------------------------------------------------------------------------
    # DB helpers (mirrors DeviceInstance pattern)
    # -------------------------------------------------------------------------

    def _fetchall(self, query, params=()):
        conn = get_temp_db_connection()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _execute(self, query, params=()):
        conn = get_temp_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected

    # -------------------------------------------------------------------------
    # Public query API
    # -------------------------------------------------------------------------

    def get_grouped_history(self, devGUID, changedColumn=None, changedBy=None,
                            limit=50, offset=0):
        """
        Return grouped change history for a single device.

        Rows are grouped by (timestamp, changedBy, devGUID). Pagination is
        applied at the group level so that `limit` controls how many distinct
        change events are returned, not how many individual field rows.

        Args:
            devGUID:       Device GUID to filter on (required).
            changedColumn: Optional field-name filter — only groups that contain
                           a change to this column are included.
            changedBy:     Optional source filter (e.g. 'USER', 'ARPSCAN').
            limit:         Max number of grouped events to return.
            offset:        Number of grouped events to skip (for pagination).

        Returns:
            list[dict] each with keys: devGUID, timestamp, changedBy, changes
        """
        return self._query_grouped(
            devGUID=devGUID,
            changedColumn=changedColumn,
            changedBy=changedBy,
            limit=limit,
            offset=offset,
        )

    def get_all_grouped_history(self, changedColumn=None, changedBy=None,
                                limit=100, offset=0):
        """
        Return grouped change history across all devices (global view).

        Same behaviour as get_grouped_history but without a devGUID filter.
        """
        return self._query_grouped(
            devGUID=None,
            changedColumn=changedColumn,
            changedBy=changedBy,
            limit=limit,
            offset=offset,
        )

    def get_available_filter_values(self, devGUID=None):
        """
        Return distinct changedBy and changedColumn values present in the table.

        Used by the frontend to dynamically populate filter dropdowns.

        Args:
            devGUID: If provided, scope to a single device.

        Returns:
            dict with keys 'changedBy' and 'changedColumn', each a sorted list.
        """
        where = "WHERE devGUID = ?" if devGUID else ""
        params = (devGUID,) if devGUID else ()

        by_rows = self._fetchall(
            f"SELECT DISTINCT changedBy FROM DevicesHistory {where} ORDER BY changedBy",
            params,
        )
        col_rows = self._fetchall(
            f"SELECT DISTINCT changedColumn FROM DevicesHistory {where} ORDER BY changedColumn",
            params,
        )
        return {
            "changedBy": [r["changedBy"] for r in by_rows],
            "changedColumn": [r["changedColumn"] for r in col_rows],
        }

    def get_total_group_count(self, devGUID=None, changedColumn=None, changedBy=None):
        """
        Return the total number of distinct change-event groups matching the
        given filters. Used by the frontend to calculate total pages.
        """
        clauses, params = self._build_clauses(devGUID, changedColumn, changedBy)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self._fetchall(
            f"""
            SELECT COUNT(*) AS cnt FROM (
                SELECT DISTINCT timestamp, changedBy, devGUID
                FROM DevicesHistory {where}
            )
            """,
            tuple(params),
        )
        return rows[0]["cnt"] if rows else 0

    # -------------------------------------------------------------------------
    # Retention management
    # -------------------------------------------------------------------------

    def prune_history(self, days):
        """
        Delete DevicesHistory rows older than `days` days.

        Called by the DBCLNP plugin during scheduled cleanup.

        Args:
            days: Retention window. Rows with timestamp older than this are
                  deleted.

        Returns:
            int: Number of rows deleted.
        """
        if days <= 0:
            mylog("verbose", ["[DevicesHistory] prune skipped — DEV_HIST_DAYS is 0"])
            return 0

        affected = self._execute(
            "DELETE FROM DevicesHistory WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",),
        )
        mylog("verbose", [f"[DevicesHistory] pruned {affected} rows older than {days} days"])
        return affected

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_clauses(devGUID, changedColumn, changedBy):
        clauses = []
        params = []
        if devGUID:
            clauses.append("devGUID = ?")
            params.append(devGUID)
        if changedColumn:
            clauses.append("changedColumn = ?")
            params.append(changedColumn)
        if changedBy:
            clauses.append("changedBy = ?")
            params.append(changedBy)
        return clauses, params

    def _query_grouped(self, devGUID, changedColumn, changedBy, limit, offset):
        """
        Core fetch-and-group logic shared by all public query methods.

        1. Fetch matching rows ordered by timestamp DESC.
        2. Group by (timestamp, changedBy, devGUID) in Python.
        3. Apply limit/offset at the group level.
        """
        clauses, params = self._build_clauses(devGUID, changedColumn, changedBy)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self._fetchall(
            f"""
            SELECT devGUID, timestamp, changedBy, changedColumn, oldValue, newValue
            FROM DevicesHistory
            {where}
            ORDER BY timestamp DESC, changedBy, changedColumn
            """,
            tuple(params),
        )

        # Group by (timestamp, changedBy, devGUID) — preserving DESC order
        groups = {}
        order = []

        for row in rows:
            key = (row["timestamp"], row["changedBy"], row["devGUID"])
            if key not in groups:
                groups[key] = {
                    "devGUID": row["devGUID"],
                    "timestamp": row["timestamp"],
                    "changedBy": row["changedBy"],
                    "changes": [],
                }
                order.append(key)
            groups[key]["changes"].append({
                "changedColumn": row["changedColumn"],
                "oldValue": row["oldValue"],
                "newValue": row["newValue"],
            })

        grouped_list = [groups[k] for k in order]
        return grouped_list[offset: offset + limit]
