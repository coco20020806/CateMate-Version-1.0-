from api.catemate_api import _build_datasource_catalog_response


def test_datasource_catalog_lists_fixed_sources():
    catalog = _build_datasource_catalog_response()

    entries = catalog["entries"]
    assert len(entries) >= 9
    assert catalog["summary"]["total"] == len(entries)

    keys = {entry["id"] for entry in entries}
    assert "category/rm_raw_data" in keys
    assert "category/dashboard_history" in keys
    assert "item/item_l3_category_csv" in keys


def test_datasource_entries_include_health_metadata():
    catalog = _build_datasource_catalog_response()
    by_id = {entry["id"]: entry for entry in catalog["entries"]}

    rm_raw_data = by_id["category/rm_raw_data"]
    assert rm_raw_data["grain"] == "category"
    assert rm_raw_data["tableId"] == "rm_raw_data"
    assert rm_raw_data["category"] == "category"
    assert rm_raw_data["type"] == "rm_raw_data"
    assert rm_raw_data["status"] == "available"
    assert rm_raw_data["processedPath"].endswith("source_tables/rm_raw_data.csv")
    assert rm_raw_data["rowCount"] == 10
    assert rm_raw_data["columnCount"] == 7
    assert rm_raw_data["usedByModules"]
    assert rm_raw_data["rawdataPath"] == "CateMate_rawdata/category"
    assert rm_raw_data["rawdataExists"] is True
    assert rm_raw_data["rawdataHasCsv"] is False
    assert rm_raw_data["v2SourceRule"]


def test_datasource_statuses_surface_partial_and_folder_sources():
    catalog = _build_datasource_catalog_response()
    by_id = {entry["id"]: entry for entry in catalog["entries"]}

    assert by_id["shop/dashboard_top_shop"]["status"] == "partial"
    assert by_id["item/item_l3_category_csv"]["status"] == "derived_or_folder"
    assert by_id["shop/shop_monthly_sales"]["status"] == "missing"


def test_datasource_catalog_includes_v2_rawdata_tree():
    catalog = _build_datasource_catalog_response()

    assert catalog["rawdataRoot"] == "CateMate_rawdata"
    groups = {group["grain"]: group for group in catalog["rawdataTree"]["groups"]}
    assert {"category", "shop", "item"}.issubset(groups)

    category = groups["category"]
    assert category["exists"] is True
    assert category["fileCount"] >= 1
    assert category["csvFileCount"] == 0
    assert category["items"] == []

    shop = groups["shop"]
    assert shop["exists"] is True
    assert shop["fileCount"] == 0
    assert shop["csvFileCount"] == 0
    assert shop["items"] == []

    item = groups["item"]
    assert item["exists"] is True
    assert item["fileCount"] >= 1
    assert item["csvFileCount"] >= 1
    assert _count_data_bearing_dirs(item["items"]) >= 1


def _count_data_bearing_dirs(items: list[dict]) -> int:
    count = 0
    for item in items:
        children = item.get("children") or []
        if item.get("kind") == "directory" and item.get("csvFileCount", 0) > 0 and not [
            child for child in children if child.get("kind") == "directory"
        ]:
            count += 1
        count += _count_data_bearing_dirs(children)
    return count
