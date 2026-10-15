import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { getExposureSummary, getHotspots, getPublicExposure, type ExposureSummary, type HotspotResponse } from "../lib/dataApi";
import { SYNTHETIC_COMPANIES } from "../data/syntheticCompanies";

/**
 * Live fire monitoring map.
 *
 * Real layer: NASA EOSDIS GIBS "MODIS Terra Thermal Anomalies (Day)" rendered as
 * per-tile WMS GetMap images (the GIBS vector tiles are not publicly served).
 * Synthetic layers: pipeline hotspot dataset (labeled) and fictional company
 * assets. Concession exposure layer is the anonymized, simplified public export.
 */

const GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi";
const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

function defaultDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 2); // GIBS daily composites lag slightly
  return d.toISOString().slice(0, 10);
}

function tileBounds(z: number, x: number, y: number) {
  const n = 2 ** z;
  const lonLeft = (x / n) * 360 - 180;
  const lonRight = ((x + 1) / n) * 360 - 180;
  const latTop = (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))) * 180) / Math.PI;
  const latBottom = (Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 1)) / n))) * 180) / Math.PI;
  return { lonLeft, lonRight, latTop, latBottom };
}

function gibsTileUrl(templateUrl: string): string {
  // template: gibs://{z}/{x}/{y}/{date}
  const match = templateUrl.replace("gibs://", "").split("/");
  const [z, x, y, date] = match.map((part, index) => (index < 3 ? Number(part) : part)) as [
    number,
    number,
    number,
    string,
  ];
  const b = tileBounds(z, x, y);
  // WMS 1.3.0 with CRS=EPSG:4326 uses lat,lon axis order in BBOX.
  const bbox = `${b.latBottom},${b.lonLeft},${b.latTop},${b.lonRight}`;
  return (
    `${GIBS_WMS}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap` +
    `&LAYERS=MODIS_Terra_Thermal_Anomalies_Day&STYLES=default&FORMAT=image/png` +
    `&CRS=EPSG:4326&WIDTH=256&HEIGHT=256&TIME=${date}&BBOX=${bbox}`
  );
}

let protocolRegistered = false;
function ensureGibsProtocol() {
  if (protocolRegistered) return;
  protocolRegistered = true;
  maplibregl.addProtocol("gibs", async (params, abortController) => {
    const response = await fetch(gibsTileUrl(params.url), { signal: abortController.signal });
    return { data: await response.arrayBuffer() };
  });
}

const assetFeatures = () => ({
  type: "FeatureCollection" as const,
  features: SYNTHETIC_COMPANIES.flatMap((company) =>
    company.assets.map((asset) => ({
      type: "Feature" as const,
      properties: {
        label: asset.name,
        company: company.fictionalName,
        province: asset.province,
        areaHa: asset.areaHa,
      },
      geometry: { type: "Point" as const, coordinates: [asset.longitude, asset.latitude] },
    })),
  ),
});

export default function LiveFireMap() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [date, setDate] = useState(defaultDate());
  const [showGibs, setShowGibs] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [showExposure, setShowExposure] = useState(true);
  const [summary, setSummary] = useState<ExposureSummary | null>(null);
  const [hotspots, setHotspots] = useState<HotspotResponse | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    getExposureSummary().then(setSummary).catch(() => setSummary(null));
    getHotspots(500).then(setHotspots).catch(() => setHotspots(null));
  }, []);

  const hotspotGeojson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: (hotspots?.features ?? []).map((h) => ({
        type: "Feature" as const,
        properties: {
          label: `Detection ${h.hotspot_id}`,
          time: h.observation_time,
          fixture: h.is_fixture,
          frp: h.frp_mw,
        },
        geometry: { type: "Point" as const, coordinates: [h.longitude, h.latitude] },
      })),
    }),
    [hotspots],
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    try {
      ensureGibsProtocol();
      const map = new maplibregl.Map({
        container: containerRef.current,
        style: MAP_STYLE,
        center: [113.5, -1.8],
        zoom: 4.6,
        attributionControl: false,
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
          customAttribution:
            "Fire detections: NASA EOSDIS GIBS / FIRMS (real) · Basemap © OpenStreetMap · Exposure: anonymized pipeline export",
        }),
        "bottom-right",
      );

      map.on("load", () => {
        // Anonymized concession exposure (simplified geometry, no attribution fields).
        map.addSource("exposure", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({
          id: "exposure-fill",
          type: "fill",
          source: "exposure",
          paint: { "fill-color": "#c27821", "fill-opacity": 0.1 },
        });
        map.addLayer({
          id: "exposure-line",
          type: "line",
          source: "exposure",
          paint: { "line-color": "#c27821", "line-width": 1, "line-opacity": 0.5 },
        });

        map.addSource("hotspots", { type: "geojson", data: hotspotGeojson });
        map.addLayer({
          id: "hotspot-circles",
          type: "circle",
          source: "hotspots",
          paint: {
            "circle-radius": 5,
            "circle-color": "#e25555",
            "circle-opacity": 0.85,
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 1,
          },
        });

        map.addSource("assets", { type: "geojson", data: assetFeatures() });
        map.addLayer({
          id: "asset-circles",
          type: "circle",
          source: "assets",
          paint: {
            "circle-radius": 7,
            "circle-color": "#172235",
            "circle-stroke-color": "#d9b86b",
            "circle-stroke-width": 2,
          },
        });

        map.addSource("gibs-fires", {
          type: "raster",
          tiles: [`gibs://{z}/{x}/{y}/${date}`],
          tileSize: 256,
          maxzoom: 9,
          attribution: "NASA EOSDIS GIBS",
        });
        map.addLayer({
          id: "gibs-fires-layer",
          type: "raster",
          source: "gibs-fires",
          paint: { "raster-opacity": 0.85 },
        });

        getPublicExposure()
          .then((geojson) => {
            (map.getSource("exposure") as maplibregl.GeoJSONSource | undefined)?.setData(geojson);
          })
          .catch(() => undefined);

        for (const layer of ["exposure-fill", "exposure-line"]) {
          map.on("click", layer, (event) => {
            const feature = event.features?.[0];
            if (!feature) return;
            const p = feature.properties as Record<string, string | number>;
            new maplibregl.Popup()
              .setLngLat(event.lngLat)
              .setHTML(
                `<strong style="font-family:IBM Plex Mono,monospace;font-size:11px">${p.polygon_id}</strong><br/>` +
                  `<span style="font-size:11px">detections in polygon (30d): ${p.hotspot_count_in_polygon_30d} · within ${p.hotspot_count_near_30d}</span><br/>` +
                  `<span style="font-size:10px;color:#6f7b8e">${p.caveat ?? ""}</span>`,
              )
              .addTo(map);
          });
        }
        map.on("click", "asset-circles", (event) => {
          const feature = event.features?.[0];
          if (!feature) return;
          const p = feature.properties as Record<string, string | number>;
          new maplibregl.Popup()
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong style="font-family:IBM Plex Mono,monospace;font-size:11px">${p.label}</strong><br/>` +
                `<span style="font-size:11px">${p.company} · ${p.province} · ${p.areaHa} ha</span><br/>` +
                `<span style="font-size:10px;color:#c27821">SYNTHETIC ASSET - FICTIONAL</span>`,
            )
            .addTo(map);
        });
      });

      map.on("error", (event) => {
        // Tile-level errors (e.g. offline) should not kill the page.
        if (!mapRef.current) setMapError("Map failed to initialize.");
        void event;
      });
      mapRef.current = map;
    } catch {
      setMapError("Map rendering unavailable in this environment (WebGL required).");
    }
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  // Rebuild the GIBS raster source when the observation date changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const source = map.getSource("gibs-fires") as maplibregl.RasterTileSource | undefined;
    if (source?.setTiles) source.setTiles([`gibs://{z}/{x}/{y}/${date}`]);
  }, [date]);

  // Layer visibility toggles.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      for (const [layer, visible] of [
        ["gibs-fires-layer", showGibs],
        ["hotspot-circles", showHotspots],
        ["exposure-fill", showExposure],
        ["exposure-line", showExposure],
      ] as const) {
        if (map.getLayer(layer)) map.setLayoutProperty(layer, "visibility", visible ? "visible" : "none");
      }
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [showGibs, showHotspots, showExposure]);

  return (
    <div className="space-y-5">
      <div>
        <p className="eyebrow">Monitor / Live fire map</p>
        <h1 className="mt-1 text-xl font-semibold text-ink">Fire &amp; haze monitoring</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Real NASA thermal-anomaly observations over anonymized concession exposure and fictional
          borrower assets. Detections are not confirmed burned area and do not establish causation.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface-elevated px-4 py-3">
        <label className="flex items-center gap-2">
          <span className="eyebrow">Observation date</span>
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            className="rounded border border-border px-2 py-1 font-mono text-xs"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          {[
            { label: "NASA thermal anomalies (real)", on: showGibs, set: setShowGibs, color: "#e25555" },
            { label: "Pipeline detections", on: showHotspots, set: setShowHotspots, color: "#e25555" },
            { label: "Concession exposure (anonymized)", on: showExposure, set: setShowExposure, color: "#c27821" },
          ].map((toggle) => (
            <button
              key={toggle.label}
              onClick={() => toggle.set(!toggle.on)}
              className={`flex items-center gap-2 rounded border px-3 py-1.5 text-xs ${
                toggle.on ? "border-accent-fill bg-accent-fill text-accent-ink" : "border-border bg-surface-elevated text-muted"
              }`}
            >
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: toggle.color }} />
              {toggle.label}
            </button>
          ))}
        </div>
      </div>

      <div className="relative overflow-hidden rounded-md border border-line bg-surface-elevated">
        {mapError ? (
          <div className="flex h-[560px] items-center justify-center bg-paper text-sm text-muted">
            {mapError}
          </div>
        ) : (
          <div ref={containerRef} className="h-[560px] w-full" />
        )}
        <div className="flex flex-wrap gap-4 border-t border-line px-4 py-2 font-mono text-[10px] text-muted">
          <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#e25555]" />THERMAL ANOMALY (NASA, REAL)</span>
          <span><span className="mr-1 inline-block h-2 w-2 rounded-full border-2 border-gold bg-ink" />SYNTHETIC ASSET</span>
          <span><span className="mr-1 inline-block h-2 w-2 rounded-sm bg-[#c27821] opacity-60" />EXPOSURE (ANONYMIZED)</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-md border border-line bg-surface-elevated p-4">
          <p className="eyebrow">Exposure summary</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {[
              { label: "Polygons", value: summary?.polygons ?? "—" },
              { label: "With detections", value: summary?.polygons_with_detections ?? "—" },
              { label: "Detections (30d)", value: summary?.hotspots_considered ?? "—" },
              { label: "Buffer", value: summary ? `${summary.buffer_km} km` : "—" },
            ].map((metric) => (
              <div key={metric.label} className="rounded bg-paper px-3 py-2">
                <span className="block font-mono text-[10px] uppercase text-muted">{metric.label}</span>
                <b className="mt-1 block font-mono text-base text-ink">{metric.value}</b>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-line bg-surface-elevated p-4">
          <p className="eyebrow">Data treatment</p>
          <ul className="mt-3 space-y-2 text-xs text-[#4f5d70]">
            <li>
              <span className="mr-2 rounded-full bg-greenbg px-2 py-[2px] font-mono text-[9px] font-semibold text-green">
                REAL
              </span>
              NASA EOSDIS GIBS thermal anomalies
            </li>
            <li>
              <span className="mr-2 rounded-full bg-amberbg px-2 py-[2px] font-mono text-[9px] font-semibold text-amber">
                {hotspots?.treatment === "real" ? "REAL" : "FIXTURE"}
              </span>
              Pipeline hotspot dataset ({hotspots?.count ?? 0} rows)
            </li>
            <li>
              <span className="mr-2 rounded-full bg-amberbg px-2 py-[2px] font-mono text-[9px] font-semibold text-amber">
                AGGREGATED
              </span>
              Concession exposure (simplified, anonymized)
            </li>
            <li>
              <span className="mr-2 rounded-full bg-rosebg px-2 py-[2px] font-mono text-[9px] font-semibold text-rose">
                SYNTHETIC
              </span>
              Borrower assets &amp; financials (fictional)
            </li>
          </ul>
        </div>

        <div className="rounded border-l-[3px] border-amber bg-amberbg p-4 text-xs leading-relaxed text-[#8b4f12]">
          <strong>Caveats.</strong> {summary?.caveat ?? "Hotspot counts are satellite fire detections within a buffer, not confirmed burned area, damage, or evidence of causation or responsibility."}
          {summary?.warning && (
            <p className="mt-2">
              <strong>Input mix:</strong> {summary.warning}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
