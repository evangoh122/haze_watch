// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import FireForecast from "./FireForecast";

afterEach(cleanup);

const ROWS = [
  {
    polygon_id: "poly_abc",
    as_of: "2026-02-01",
    horizon_hours: 24,
    hazard_score: 0.62,
    detections_30d: 9,
    area_ha: 20552,
  },
  {
    polygon_id: "poly_def",
    as_of: "2026-02-01",
    horizon_hours: 24,
    hazard_score: 0.11,
    detections_30d: 0,
    area_ha: 940,
  },
];

function mockForecast(horizon = 24) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      expect(url).toContain(`horizon_hours=${horizon}`);
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            model_name: "persistence_recency_baseline",
            model_version: "0.1.0",
            data_type: "baseline",
            disclaimer: "not a calibrated probability",
            rows: ROWS,
          }),
      });
    }),
  );
}

describe("FireForecast", () => {
  it("renders baseline rows with bands and the disclaimer", async () => {
    mockForecast();
    render(<FireForecast />);
    await waitFor(() => expect(screen.getAllByText(/poly_abc/).length).toBeGreaterThan(0));
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("LOW")).toBeInTheDocument();
    expect(screen.getAllByText(/not a calibrated probability/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("BASELINE").length).toBeGreaterThan(0);
  });

  it("refetches when the horizon changes", async () => {
    mockForecast(24);
    render(<FireForecast />);
    await waitFor(() => expect(screen.getAllByText(/poly_abc/).length).toBeGreaterThan(0));

    mockForecast(72);
    fireEvent.click(screen.getByRole("button", { name: "72 H" }));
    await waitFor(() => expect(screen.getByText(/persistence_recency_baseline/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "72 H" })).toBeInTheDocument();
  });

  it("shows an empty-state message when the dataset is missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("missing")));
    render(<FireForecast />);
    await waitFor(() =>
      expect(screen.getByText(/Run the ingestion pipeline first/i)).toBeInTheDocument(),
    );
  });
});
