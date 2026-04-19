# Metsis Thumbnail Generator

Simple thumbnail generator scaffold for METSIS.

## Features implemented now

- Python project scaffold with `pyproject.toml` and `tox.ini`
- Input mode from MMD XML folder (parsed with lxml)
- Input mode from Solr query (queried with pysolr)
- Threaded input extraction for folder and Solr
- Multiprocess worker pipeline for thumbnail generation
- Path hierarchy for output thumbnails:
  - `{thumbnail_base_path}/{org}/{year}{month}/{metadata_identifier}.png`
- Solr atomic updates for `thumbnail_url` using pysolr
- Generator class hierarchy with placeholder `WmsThumbnail`

## Run without installation

```bash
./thumbnail-generator --help
```

## Install

```bash
pip install -e .
```

Optional WMS dependencies:

```bash
pip install -e .[wms]
```

## Example

```bash
./thumbnail-generator \
  --config etc/config.yml \
  --input-dir /data/mmd \
  --org nbs
```

Solr mode (explicit solr-indexer config path required):

```bash
./thumbnail-generator \
  --config etc/config.yml \
  --solr-query "metadata_identifier:*" \
  --solr-config ../solr-indexer/etc/cfg-template.yml \
  --org nbs
```
