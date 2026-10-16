// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import LiveFireMap from "./LiveFireMap";

afterEach(cleanup);

function mockDataApis() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.includes("/exposure/summary"))
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              as_of: "2026-02-01",
              polygons: 300,
              hotspots_considered: 40,
              polygons_with_detections: 5,
              buffer_km: 25,
              polygon_treatment: ["real-restricted"],
              hotspot_treatment: "synthetic-fixture",
              caveat: "not confirmed burned area",
              warning: "INPUT MIX: fixture detections",
            }),
        });
      if (url.includes("/exposure/public"))
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ type: "FeatureCollection", features: [] }) });
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            treatment: "synthetic-fixture",
            caveat: "not confirmed burned area",
            count: 2,
            features: [],
          }),
      });
    }),
  );
}

describe("LiveFireMap", () => {
  it("renders the map chrome, legend and treatment labels", async () => {
    mockDataApis();
    render(<LiveFireMap />);
    expect(screen.getByText(/Fire & haze monitoring/i)).toBeInTheDocument();
    expect(screen.getByText(/Observation date/i)).toBeInTheDocument();
    expect(screen.getByText(/NASA thermal anomalies \(real\)/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/300/).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/INPUT MIX/i).length).toBeGreaterThan(0);
  });

  it("falls back gracefully when WebGL map rendering is unavailable", async () => {
    mockDataApis();
    render(<LiveFireMap />);
    // jsdom has no WebGL: either the map initializes as an empty container or the
    // fallback notice shows - both are acceptable, the page must not crash.
    await waitFor(() =>
      expect(
        screen.getByText(/Fire & haze monitoring/i),
      ).toBeInTheDocument(),
    );
  });
});
