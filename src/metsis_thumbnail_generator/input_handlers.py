"""Input handlers for folder and Solr source modes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

import pysolr
from lxml import etree

from .models import ThumbnailTask

_MMD_NS = {"mmd": "http://www.met.no/schema/mmd"}


class FileInputHandler:
    """Read MMD XML files from folder or single file and extract thumbnail tasks."""

    def __init__(
        self,
        num_threads: int,
        input_dir: Path | None = None,
        input_file: Path | None = None,
        recursive: bool = True,
    ) -> None:
        self.input_dir = input_dir
        self.input_file = input_file
        self.recursive = recursive
        self.num_threads = num_threads

    def _discover_files(self) -> list[Path]:
        if self.input_file is not None:
            return [self.input_file]
        if self.input_dir is None:
            return []
        if self.recursive:
            return sorted(self.input_dir.rglob("*.xml"))
        return sorted(self.input_dir.glob("*.xml"))

    def _extract_task(self, xml_path: Path) -> ThumbnailTask | None:
        try:
            root = etree.parse(str(xml_path)).getroot()
        except (OSError, etree.XMLSyntaxError):
            return None

        metadata_identifier = root.findtext(".//mmd:metadata_identifier", namespaces=_MMD_NS)
        if not metadata_identifier:
            return None

        start_date = root.findtext(
            ".//mmd:temporal_extent/mmd:start_date",
            namespaces=_MMD_NS,
        )

        wms_url = None
        for data_access in root.findall(".//mmd:data_access", namespaces=_MMD_NS):
            access_type = data_access.findtext("mmd:type", namespaces=_MMD_NS)
            if not access_type:
                continue
            if access_type.strip().upper() != "OGC WMS":
                continue
            wms_url = data_access.findtext("mmd:resource", namespaces=_MMD_NS)
            if wms_url:
                break

        if not wms_url:
            return None

        return ThumbnailTask(
            metadata_identifier=metadata_identifier.strip(),
            start_date=start_date.strip() if start_date else None,
            wms_url=wms_url.strip(),
        )

    def iter_tasks(self) -> Iterable[ThumbnailTask]:
        xml_files = self._discover_files()
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            for task in executor.map(self._extract_task, xml_files):
                if task is not None:
                    yield task


class SolrInputHandler:
    """Read documents from Solr and extract thumbnail tasks."""

    def __init__(
        self,
        solr_client: pysolr.Solr,
        query: str,
        num_threads: int,
        page_size: int,
    ) -> None:
        self.solr_client = solr_client
        self.query = query
        self.num_threads = num_threads
        self.page_size = page_size

    @staticmethod
    def _first_value(value: object) -> str | None:
        if isinstance(value, list):
            if not value:
                return None
            first = value[0]
            return str(first) if first is not None else None
        if value is None:
            return None
        return str(value)

    def _doc_to_task(self, doc: dict[str, object]) -> ThumbnailTask | None:
        metadata_identifier = self._first_value(doc.get("metadata_identifier"))
        if not metadata_identifier:
            return None

        wms_url = self._first_value(
            doc.get("data_access_url_ogc_wms")
            or doc.get("data_access_url_opendap")
            or doc.get("wms_url")
        )

        start_date = self._first_value(
            doc.get("temporal_extent_start_date") or doc.get("start_date")
        )

        if not wms_url:
            return None

        return ThumbnailTask(
            metadata_identifier=metadata_identifier.strip(),
            start_date=start_date.strip() if start_date else None,
            wms_url=wms_url.strip(),
        )

    def iter_tasks(self) -> Iterable[ThumbnailTask]:
        start = 0
        while True:
            results = self.solr_client.search(self.query, start=start, rows=self.page_size)
            docs = list(results.docs)
            if not docs:
                break

            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                for task in executor.map(self._doc_to_task, docs):
                    if task is not None:
                        yield task

            start += len(docs)
            if len(docs) < self.page_size:
                break
