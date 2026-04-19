"""WMS thumbnail generator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, List, Optional, cast

from metsis_thumbnail_generator.models import ThumbnailTask

from .base import BaseThumbnailGenerator

ccrs: Any
plt: Any
WebMapService: Any

try:
    import cartopy.crs as _ccrs
    import matplotlib.pyplot as _plt
    from owslib.wms import WebMapService as _WebMapService

    ccrs = _ccrs
    plt = _plt
    plt.switch_backend("agg")
    WebMapService = _WebMapService
except ImportError:  # pragma: no cover - depends on optional extras
    ccrs = cast(Any, None)
    plt = cast(Any, None)
    WebMapService = cast(Any, None)


@dataclass
class WmsThumbnail(BaseThumbnailGenerator):
    """WMS thumbnail generator."""

    wms_projection: str
    wms_layer: Optional[str]
    wms_style: Optional[str]
    wms_zoom: float
    wms_coastlines: bool
    wms_extent: Optional[List[float]]
    wms_timeout: int = 240

    def generate(self, task: ThumbnailTask) -> bytes:
        """Generate a thumbnail PNG for one task and return bytes."""
        if ccrs is None or plt is None or WebMapService is None:
            raise RuntimeError(
                "WMS dependencies are missing. Install extras with: pip install .[wms]"
            )

        if not task.wms_url:
            raise ValueError("Task is missing WMS URL")

        logger = logging.getLogger("metsis_thumbnail_generator.wms")
        logger.debug(
            "Generating WMS thumbnail metadata_identifier=%s wms_url=%s",
            task.metadata_identifier,
            task.wms_url,
        )

        wms_layer = self.wms_layer
        wms_style = self.wms_style
        wms_zoom_level = self.wms_zoom
        wms_timeout = self.wms_timeout
        add_coastlines = self.wms_coastlines
        map_projection = self.wms_projection
        thumbnail_extent = self.wms_extent

        # map projection string to ccrs projection
        if isinstance(map_projection, str):
            if map_projection == 'PolarStereographic':
                map_projection = ccrs.Stereographic(central_longitude=0.0,central_latitude=90., true_scale_latitude=60.)
            else:
                try:
                    map_projection = getattr(ccrs, map_projection)()
                except AttributeError as exc:
                    raise ValueError(f"Unknown cartopy projection: {map_projection}") from exc

        wms = WebMapService(task.wms_url, timeout=wms_timeout)
        available_layers = list(wms.contents.keys())
        if not available_layers:
            raise ValueError("WMS service has no available layers")

        if wms_layer not in available_layers:
            wms_layer = available_layers[0]
            logger.info("Creating WMS thumbnail for layer: %s", wms_layer)

        # Checking styles
        available_styles = list(wms.contents[wms_layer].styles.keys())
        wms_style_value: Optional[List[str]]

        if available_styles:
            if wms_style not in available_styles:
                wms_style_value = [available_styles[0]]
            else:
                wms_style_value = [wms_style] if wms_style else None
        else:
            wms_style_value = None

        if not thumbnail_extent:
            wms_extent = wms.contents[available_layers[0]].boundingBoxWGS84
            cartopy_extent_zoomed = [
                wms_extent[0] - wms_zoom_level,
                wms_extent[2] + wms_zoom_level,
                wms_extent[1] - wms_zoom_level,
                wms_extent[3] + wms_zoom_level,
            ]
        else:
            cartopy_extent_zoomed = [float(v) for v in thumbnail_extent]

        max_extent = [-180.0, 180.0, -90.0, 90.0]

        for i, extent in enumerate(cartopy_extent_zoomed):
            if i % 2 == 0:
                if extent < max_extent[i]:
                    cartopy_extent_zoomed[i] = max_extent[i]
            else:
                if extent > max_extent[i]:
                    cartopy_extent_zoomed[i] = max_extent[i]

        subplot_kw = {"projection": map_projection}
        logger.info("Subplot kwargs: %s", subplot_kw)

        fig, ax = plt.subplots(subplot_kw=subplot_kw)
        ax_cartopy: Any = ax

        try:
            # transparent background
            ax_cartopy.spines["geo"].set_visible(False)
            fig.patch.set_alpha(0)
            fig.set_alpha(0)
            fig.set_figwidth(4.5)
            fig.set_figheight(4.5)
            fig.set_dpi(100)

            ax_cartopy.add_wms(
                wms,
                wms_layer,
                wms_kwargs={"transparent": False, "styles": wms_style_value},
            )

            if add_coastlines:
                ax_cartopy.coastlines(resolution="50m", linewidth=0.5)

            if isinstance(map_projection, ccrs.PlateCarree):
                ax_cartopy.set_extent(cartopy_extent_zoomed)
            else:
                ax_cartopy.set_extent(cartopy_extent_zoomed, ccrs.PlateCarree())

            buffer = BytesIO()
            fig.savefig(buffer, format="png", bbox_inches="tight")
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as exc:
            logger.error("Could not set up WMS plotting: %s", exc)
            raise
        finally:
            plt.close(fig)
