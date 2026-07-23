import os
import sqlite3
import tempfile
import unittest

from oj_persistence import Manager

from store import Store, ASSETS_TABLE, FINDINGS_TABLE, ASSET_INDEX_FIELDS, FINDING_INDEX_FIELDS, execute_sql


ASSET_1 = {'AssetID': 'a1', 'name': 'Server1', 'is_internet_facing': True}
ASSET_2 = {'AssetID': 'a2', 'name': 'Server2', 'is_internet_facing': False}
FINDING_A1_CRITICAL = {'Asset': {'AssetId': 'a1'}, 'severity': 'Critical', 'title': 'CVE-001'}
FINDING_A1_HIGH = {'Asset': {'AssetId': 'a1'}, 'severity': 'High', 'title': 'CVE-002'}
FINDING_A2 = {'Asset': {'AssetId': 'a2'}, 'severity': 'Low', 'title': 'CVE-003'}


class TestStoreJoin(unittest.TestCase):
    def setUp(self):
        Manager()._reset()
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.store = Store(path=self.db_path)

    def tearDown(self):
        self.store.close()
        Manager()._reset()
        os.unlink(self.db_path)

    def test_asset_with_no_findings_yields_empty_list(self):
        self.store.save_asset(ASSET_1)
        results = list(self.store.iter_joined())
        self.assertEqual(results[0]['findings'], [])

    def test_finding_joined_to_correct_asset(self):
        self.store.save_asset(ASSET_1)
        self.store.save_finding(FINDING_A1_CRITICAL)
        results = list(self.store.iter_joined())
        self.assertEqual(len(results[0]['findings']), 1)
        self.assertEqual(results[0]['findings'][0]['severity'], 'Critical')

    def test_multiple_findings_per_asset(self):
        self.store.save_asset(ASSET_1)
        self.store.save_finding(FINDING_A1_CRITICAL)
        self.store.save_finding(FINDING_A1_HIGH)
        results = list(self.store.iter_joined())
        self.assertEqual(len(results[0]['findings']), 2)

    def test_findings_not_crossed_between_assets(self):
        self.store.save_asset(ASSET_1)
        self.store.save_asset(ASSET_2)
        self.store.save_finding(FINDING_A2)
        by_id = {r['AssetID']: r for r in self.store.iter_joined()}
        self.assertEqual(by_id['a1']['findings'], [])
        self.assertEqual(len(by_id['a2']['findings']), 1)

    def test_internal_asset_id_field_stripped_from_output(self):
        self.store.save_asset(ASSET_1)
        self.store.save_finding(FINDING_A1_CRITICAL)
        results = list(self.store.iter_joined())
        self.assertNotIn('_asset_id', results[0]['findings'][0])

    def test_asset_fields_preserved_in_output(self):
        self.store.save_asset(ASSET_1)
        results = list(self.store.iter_joined())
        self.assertEqual(results[0]['name'], 'Server1')
        self.assertTrue(results[0]['is_internet_facing'])


class TestStoreTruncation(unittest.TestCase):
    def setUp(self):
        Manager()._reset()
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

    def tearDown(self):
        Manager()._reset()
        os.unlink(self.db_path)

    def test_second_store_instance_starts_empty(self):
        store1 = Store(path=self.db_path)
        store1.save_asset(ASSET_1)
        store1.close()

        Manager()._reset()
        store2 = Store(path=self.db_path)
        results = list(store2.iter_joined())
        store2.close()
        self.assertEqual(results, [])


class TestStoreIndexes(unittest.TestCase):
    def setUp(self):
        Manager()._reset()
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.store = Store(path=self.db_path)

    def tearDown(self):
        self.store.close()
        Manager()._reset()
        os.unlink(self.db_path)

    def _index_names(self) -> set[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
            return {row[0] for row in rows}
        finally:
            conn.close()

    def test_default_asset_indexes_created(self):
        indexes = self._index_names()
        for field in ASSET_INDEX_FIELDS:
            expected = f'idx_{ASSETS_TABLE}_{field}'
            self.assertIn(expected, indexes, f'Missing index for asset field: {field}')

    def test_default_finding_indexes_created(self):
        indexes = self._index_names()
        for field in FINDING_INDEX_FIELDS:
            expected = f'idx_{FINDINGS_TABLE}_{field}'
            self.assertIn(expected, indexes, f'Missing index for finding field: {field}')

    def test_join_key_index_created(self):
        self.assertIn('idx__asset_id', self._index_names())

    def test_custom_asset_fields_indexed(self):
        self.store.close()
        Manager()._reset()
        store2 = Store(path=self.db_path, asset_fields=['criticality'])
        indexes = self._index_names()
        store2.close()
        self.assertIn('idx_assets_criticality', indexes)

    def test_custom_finding_fields_indexed(self):
        self.store.close()
        Manager()._reset()
        store2 = Store(path=self.db_path, finding_fields=['category'])
        indexes = self._index_names()
        store2.close()
        self.assertIn('idx_findings_category', indexes)

    def test_nested_field_index_name_uses_underscores(self):
        self.store.close()
        Manager()._reset()
        store2 = Store(path=self.db_path, finding_fields=['Asset.AssetId'])
        indexes = self._index_names()
        store2.close()
        self.assertIn('idx_findings_Asset_AssetId', indexes)

    def test_unsafe_field_name_skipped(self):
        self.store.close()
        Manager()._reset()
        store2 = Store(path=self.db_path, asset_fields=['bad field; DROP TABLE assets--'])
        indexes = self._index_names()
        store2.close()
        self.assertFalse(
            any('bad' in name for name in indexes),
            'Unsafe field name should not produce an index',
        )


class TestExecuteSql(unittest.TestCase):
    def setUp(self):
        Manager()._reset()
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        store = Store(path=self.db_path)
        store.save_asset(ASSET_1)
        store.save_asset(ASSET_2)
        store.save_finding(FINDING_A1_CRITICAL)
        store.save_finding(FINDING_A1_HIGH)
        store.save_finding(FINDING_A2)
        store.close()
        Manager()._reset()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_returns_all_assets(self):
        rows = list(execute_sql(self.db_path, 'SELECT key, value FROM assets'))
        self.assertEqual(len(rows), 2)

    def test_row_is_dict_with_column_names(self):
        rows = list(execute_sql(self.db_path, 'SELECT key FROM assets'))
        self.assertIn('key', rows[0])

    def test_filter_by_json_extract(self):
        sql = "SELECT key FROM assets WHERE json_extract(value, '$.is_internet_facing') = 1"
        rows = list(execute_sql(self.db_path, sql))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['key'], 'a1')

    def test_join_assets_and_findings(self):
        sql = (
            "SELECT a.key AS asset_id, json_extract(f.value, '$.severity') AS severity "
            "FROM assets a "
            "JOIN findings f ON json_extract(f.value, '$._asset_id') = a.key"
        )
        rows = list(execute_sql(self.db_path, sql))
        self.assertEqual(len(rows), 3)

    def test_returns_empty_for_no_matches(self):
        rows = list(execute_sql(self.db_path, "SELECT key FROM assets WHERE key = 'nonexistent'"))
        self.assertEqual(rows, [])

    def test_column_aliases_used_as_keys(self):
        sql = "SELECT key AS asset_id FROM assets WHERE key = 'a1'"
        rows = list(execute_sql(self.db_path, sql))
        self.assertIn('asset_id', rows[0])
        self.assertNotIn('key', rows[0])


if __name__ == '__main__':
    unittest.main()
