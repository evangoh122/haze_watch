import { apiGet } from "./api";

/** Shapes served by backend/app/api/v1/data.py (precomputed pipeline outputs). */

export interface HotspotFeature {
  hotspot_id: string;
  latitude: number;
  longitude: number;
  observation_time: string;
  confidence_pct: number | null;
  frp_mw: number | null;
  source: string;
  is_fixture: boolean;
}

export interface HotspotResponse {
  treatment: "real" | "synthetic-fixture";
  caveat: string;
  count: number;
  features: HotspotFeature[];
}

export interface ExposureSummary {
  as_of: string;
  polygons: number;
  hotspots_considered: number;
  polygons_with_detections: number;
  buffer_km: number;
  polygon_treatment: string[];
  hotspot_treatment: string;
  caveat: string;
  warning?: string;
}

export interface ForecastRow {
  polygon_id: string;
  as_of: string;
  horizon_hours: number;
  hazard_score: number;
  detections_30d: number;
  area_ha: number | null;
}

export interface ForecastResponse {
  model_name: string | null;
  model_version: string | null;
  data_type: string | null;
  disclaimer: string;
  rows: ForecastRow[];
}

export function getHotspots(limit = 500): Promise<HotspotResponse> {
  return apiGet<HotspotResponse>(`/fires/hotspots?limit=${limit}`);
}

export function getExposureSummary(): Promise<ExposureSummary> {
  return apiGet<ExposureSummary>("/exposure/summary");
}

export function getPublicExposure(): Promise<GeoJSON.FeatureCollection> {
  return apiGet<GeoJSON.FeatureCollection>("/exposure/public");
}

export function getForecasts(horizonHours = 24, limit = 50): Promise<ForecastResponse> {
  return apiGet<ForecastResponse>(`/forecasts?horizon_hours=${horizonHours}&limit=${limit}`);
}
