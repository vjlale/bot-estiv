/**
 * Tests para src/app/approvals/actions.tsx
 * Verifica el flujo de UI del componente ApprovalActions:
 * - renderizado de botones
 * - llamada a api.decideApproval con la decisión correcta
 * - muestra confirmación tras la decisión
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApprovalActions } from "@/app/approvals/actions";
import * as apiModule from "@/lib/api";

// Mock del módulo api
vi.mock("@/lib/api", () => ({
  api: {
    decideApproval: vi.fn(),
  },
}));

const mockDecide = vi.mocked(apiModule.api.decideApproval);

beforeEach(() => {
  mockDecide.mockReset();
  mockDecide.mockResolvedValue(undefined);
});

// ---------------------------------------------------------------------------
// Renderizado inicial
// ---------------------------------------------------------------------------

describe("ApprovalActions — renderizado", () => {
  it("muestra los tres botones de decisión", () => {
    render(<ApprovalActions postId="test-post-id" />);
    expect(screen.getByText("Aprobar")).toBeInTheDocument();
    expect(screen.getByText("Pedir edición")).toBeInTheDocument();
    expect(screen.getByText("Cancelar")).toBeInTheDocument();
  });

  it("muestra el campo de comentario", () => {
    render(<ApprovalActions postId="test-post-id" />);
    expect(
      screen.getByPlaceholderText(/comentario/i)
    ).toBeInTheDocument();
  });

  it("los botones están habilitados al inicio", () => {
    render(<ApprovalActions postId="test-post-id" />);
    expect(screen.getByText("Aprobar")).not.toBeDisabled();
    expect(screen.getByText("Pedir edición")).not.toBeDisabled();
    expect(screen.getByText("Cancelar")).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Acciones — Aprobar
// ---------------------------------------------------------------------------

describe("ApprovalActions — Aprobar", () => {
  it("llama a decideApproval con 'approve' al hacer click en Aprobar", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-123" />);
    await user.click(screen.getByText("Aprobar"));
    await waitFor(() => {
      expect(mockDecide).toHaveBeenCalledWith("uuid-123", "approve", undefined);
    });
  });

  it("muestra mensaje de confirmación tras aprobar", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-123" />);
    await user.click(screen.getByText("Aprobar"));
    await waitFor(() => {
      expect(screen.getByText(/decisión registrada: approve/i)).toBeInTheDocument();
    });
  });

  it("oculta los botones tras la decisión", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-123" />);
    await user.click(screen.getByText("Aprobar"));
    await waitFor(() => {
      expect(screen.queryByText("Aprobar")).not.toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Acciones — Rechazar
// ---------------------------------------------------------------------------

describe("ApprovalActions — Cancelar", () => {
  it("llama a decideApproval con 'reject'", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-456" />);
    await user.click(screen.getByText("Cancelar"));
    await waitFor(() => {
      expect(mockDecide).toHaveBeenCalledWith("uuid-456", "reject", undefined);
    });
  });
});

// ---------------------------------------------------------------------------
// Acciones — Pedir edición con comentario
// ---------------------------------------------------------------------------

describe("ApprovalActions — Pedir edición", () => {
  it("llama a decideApproval con 'edit' y el comentario ingresado", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-789" />);

    const textarea = screen.getByPlaceholderText(/comentario/i);
    await user.type(textarea, "Cambiar el tono del texto");
    await user.click(screen.getByText("Pedir edición"));

    await waitFor(() => {
      expect(mockDecide).toHaveBeenCalledWith(
        "uuid-789",
        "edit",
        "Cambiar el tono del texto"
      );
    });
  });

  it("pasa undefined como reason si el comentario está vacío", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-empty" />);
    await user.click(screen.getByText("Pedir edición"));
    await waitFor(() => {
      expect(mockDecide).toHaveBeenCalledWith("uuid-empty", "edit", undefined);
    });
  });
});

// ---------------------------------------------------------------------------
// Manejo del estado `done`
// ---------------------------------------------------------------------------

describe("ApprovalActions — estado done", () => {
  it("muestra la decisión exacta registrada en el mensaje de confirmación", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-done" />);
    await user.click(screen.getByText("Cancelar"));
    await waitFor(() => {
      expect(screen.getByText(/decisión registrada: reject/i)).toBeInTheDocument();
    });
  });

  it("no hay botones ni textarea tras registrar decisión", async () => {
    const user = userEvent.setup();
    render(<ApprovalActions postId="uuid-clean" />);
    await user.click(screen.getByText("Aprobar"));
    await waitFor(() => {
      expect(screen.queryByText(/pedir edición/i)).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });
  });
});
