// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import BankingDemo from "./BankingDemo";

afterEach(cleanup);

describe("BankingDemo", () => {
  it("renders the synthetic notice and baseline metrics", () => {
    render(<BankingDemo />);
    expect(screen.getByText(/entirely synthetic and fictional/i)).toBeInTheDocument();
    expect(screen.getByText(/Net debt \/ EBITDA/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculation trace/i)).toBeInTheDocument();
  });

  it("updates metrics when an assumption changes", () => {
    render(<BankingDemo />);
    const slider = screen.getByLabelText("Production disruption");
    const before = screen.getAllByText(/^-?\d+\.\d+x$/i).map((n) => n.textContent);

    fireEvent.change(slider, { target: { value: "100" } });

    const after = screen.getAllByText(/^-?\d+\.\d+x$/i).map((n) => n.textContent);
    expect(after).not.toEqual(before);
  });

  it("switches borrowers via the selector", () => {
    render(<BankingDemo />);
    fireEvent.change(screen.getByLabelText("Borrower (fictional)"), {
      target: { value: "SYN-002" },
    });
    expect(screen.getByText(/resilience of well-capped borrowers/i)).toBeInTheDocument();
  });
});
