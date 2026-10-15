// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChatPanel from "./ChatPanel";

afterEach(cleanup);

function mockFetch(reply: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          reply,
          sources: [
            {
              dataset_id: "exposure::2026-02-01",
              source: "pipeline",
              treatment: "synthetic-fixture",
              license: "derived",
            },
          ],
          model: "none (deterministic)",
          provider: "deterministic-fallback",
          fallback: true,
          guardrail_flags: [],
          disclaimer: "Research prototype. Companies and financial data are synthetic.",
        }),
    }),
  );
}

describe("ChatPanel", () => {
  it("renders the empty state and disclaimer policy line", () => {
    render(<ChatPanel />);
    expect(screen.getByText(/Ask the data/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask about exposure/i)).toBeInTheDocument();
  });

  it("sends a question and renders the grounded reply with sources", async () => {
    mockFetch("5 polygons have detections in the exposure summary.");
    render(<ChatPanel />);

    fireEvent.change(screen.getByLabelText("Chat question"), {
      target: { value: "How many concessions have detections?" },
    });
    fireEvent.submit(screen.getByLabelText("Chat question").closest("form")!);

    await waitFor(() =>
      expect(screen.getByText(/5 polygons have detections/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/deterministic fallback/i)).toBeInTheDocument();
    expect(screen.getByText(/exposure::2026-02-01 \(synthetic-fixture\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Companies and financial data are synthetic/i)).toBeInTheDocument();
  });

  it("shows an error state when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down")),
    );
    render(<ChatPanel />);
    fireEvent.change(screen.getByLabelText("Chat question"), {
      target: { value: "hello" },
    });
    fireEvent.submit(screen.getByLabelText("Chat question").closest("form")!);

    await waitFor(() => expect(screen.getByText(/Chat request failed/i)).toBeInTheDocument());
  });
});
