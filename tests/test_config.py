from pathlib import Path

from metsis_thumbnail_generator.config import load_app_config, load_solr_config


def test_load_app_config_defaults(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("thumbnail_base_path: /tmp/out\n", encoding="utf-8")

    cfg = load_app_config(cfg_file)

    assert cfg.thumbnail_base_path == Path("/tmp/out")
    assert cfg.default_org == "unknown"


def test_load_solr_config_builds_full_solr_url(tmp_path: Path) -> None:
    cfg_file = tmp_path / "solr.yml"
    cfg_file.write_text(
        "solrserver: http://localhost:8983/solr/\nsolrcore: mmd-data\n",
        encoding="utf-8",
    )

    cfg = load_solr_config(cfg_file)

    assert cfg.solr_url == "http://localhost:8983/solr/mmd-data"
