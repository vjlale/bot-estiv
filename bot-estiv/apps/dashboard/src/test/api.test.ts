/**
 * Tests para src/lib/api.ts
 * Verifica que las funciones armen las URLs y payloads correctos,
 * mockeando fetch globalmente.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, API_BASE } from "@/lib/api";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

function okResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

function errorResponse(status: number, text = "Error") {
  return Promise.resolve({
    ok: false,
    status,
    text: () => Promise.resolve(text),
    json: () => Promise.resolve({ detail: text }),
  } as unknown as Response);
}

// ---------------------------------------------------------------------------
// listPosts
// ---------------------------------------------------------------------------

describe("api.listPosts", () => {
  it("llama a GET /posts sin filtro", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listPosts();
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/posts`,
      expect.objectContaining({ cache: "no-store" })
    );
  });

  it("llama a GET /posts?status=pending_approval con filtro", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listPosts("pending_approval");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/posts?status=pending_approval`,
      expect.anything()
    );
  });

  it("retorna el listado de posts", async () => {
    const posts = [{ id: "123", title: "Pérgola" }];
    mockFetch.mockReturnValue(okResponse(posts));
    const result = await api.listPosts();
    expect(result).toEqual(posts);
  });

  it("lanza error cuando la respuesta no es ok", async () => {
    mockFetch.mockReturnValue(errorResponse(500, "Internal server error"));
    await expect(api.listPosts()).rejects.toThrow("500");
  });
});

// ---------------------------------------------------------------------------
// getPost
// ---------------------------------------------------------------------------

describe("api.getPost", () => {
  it("llama a GET /posts/:id", async () => {
    const post = { id: "abc-123", title: "Test" };
    mockFetch.mockReturnValue(okResponse(post));
    const result = await api.getPost("abc-123");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/posts/abc-123`,
      expect.anything()
    );
    expect(result).toEqual(post);
  });
});

// ---------------------------------------------------------------------------
// listApprovals
// ---------------------------------------------------------------------------

describe("api.listApprovals", () => {
  it("llama a GET /approvals", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listApprovals();
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/approvals`,
      expect.anything()
    );
  });
});

// ---------------------------------------------------------------------------
// decideApproval
// ---------------------------------------------------------------------------

describe("api.decideApproval", () => {
  it("llama a POST /approvals/:id/decision con approve", async () => {
    mockFetch.mockReturnValue(okResponse({ status: "approved" }));
    await api.decideApproval("post-uuid-123", "approve");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/approvals/post-uuid-123/decision`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ decision: "approve", reason: undefined }),
      })
    );
  });

  it("incluye reason en el payload cuando se proporciona", async () => {
    mockFetch.mockReturnValue(okResponse({ status: "edit_requested" }));
    await api.decideApproval("post-uuid-456", "edit", "Cambiar el tono");
    const call = mockFetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.reason).toBe("Cambiar el tono");
    expect(body.decision).toBe("edit");
  });

  it("lanza error cuando el servidor responde 404", async () => {
    mockFetch.mockReturnValue(errorResponse(404, "Aprobación no encontrada"));
    await expect(api.decideApproval("no-existe", "approve")).rejects.toThrow("404");
  });
});

// ---------------------------------------------------------------------------
// listCampaigns
// ---------------------------------------------------------------------------

describe("api.listCampaigns", () => {
  it("llama a GET /campaigns", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listCampaigns();
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/campaigns`,
      expect.anything()
    );
  });
});

// ---------------------------------------------------------------------------
// weeklyAnalytics
// ---------------------------------------------------------------------------

describe("api.weeklyAnalytics", () => {
  it("llama a GET /analytics/weekly", async () => {
    mockFetch.mockReturnValue(okResponse({ period: "W01" }));
    await api.weeklyAnalytics();
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/analytics/weekly`,
      expect.anything()
    );
  });
});

// ---------------------------------------------------------------------------
// schedule
// ---------------------------------------------------------------------------

describe("api.schedule", () => {
  it("llama a POST /calendar/:id/schedule con fecha", async () => {
    mockFetch.mockReturnValue(okResponse({ id: "p1", status: "scheduled" }));
    await api.schedule("p1", "2024-12-25T19:00:00");
    const call = mockFetch.mock.calls[0];
    expect(call[0]).toBe(`${API_BASE}/calendar/p1/schedule`);
    expect(call[1].method).toBe("POST");
    const body = JSON.parse(call[1].body);
    expect(body.scheduled_for).toBe("2024-12-25T19:00:00");
  });
});

// ---------------------------------------------------------------------------
// listSourceAssets
// ---------------------------------------------------------------------------

describe("api.listSourceAssets", () => {
  it("llama sin filtro", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listSourceAssets();
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/source-assets`,
      expect.anything()
    );
  });

  it("agrega el project_tag codificado cuando se proporciona", async () => {
    mockFetch.mockReturnValue(okResponse([]));
    await api.listSourceAssets("cerco-mendiolaza");
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/source-assets?project_tag=cerco-mendiolaza`,
      expect.anything()
    );
  });
});
