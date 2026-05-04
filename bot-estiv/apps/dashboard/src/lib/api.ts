export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export type Post = {
  id: string;
  title: string;
  caption: string;
  hashtags: string[] | null;
  format: string;
  status: string;
  pillar: string | null;
  scheduled_for: string | null;
  published_at: string | null;
  assets: { id: string; kind: string; url: string; slide_index: number | null }[];
  created_at: string;
};

export type DeploymentSettings = {
  environment: string;
  tenant_id: string;
  dashboard_domain: string;
  api_domain: string;
  api_base_url: string;
  twilio_webhook_url: string;
  brand_logo_path: string;
  brand_manual_path: string;
  checks: Record<string, boolean>;
};

export const api = {
  listPosts: (status?: string) =>
    http<Post[]>(`/posts${status ? `?status=${status}` : ""}`),
  getPost: (id: string) => http<Post>(`/posts/${id}`),
  listApprovals: () => http<any[]>(`/approvals`),
  decideApproval: (postId: string, decision: "approve" | "reject" | "edit", reason?: string) =>
    http(`/approvals/${postId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, reason }),
    }),
  listCampaigns: () => http<any[]>(`/campaigns`),
  planCampaigns: (instruction: string) =>
    http(`/campaigns/plan?instruction=${encodeURIComponent(instruction)}`, { method: "POST" }),
  weeklyAnalytics: () => http<any>(`/analytics/weekly`),
  trends: () => http<any>(`/analytics/trends`),
  weekPlan: () => http<any>(`/calendar/week`),
  upcoming: () => http<Post[]>(`/calendar/upcoming`),
  schedule: (postId: string, scheduled_for: string) =>
    http(`/calendar/${postId}/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_for }),
    }),
  listAssets: (kind?: string) =>
    http<any[]>(`/assets${kind ? `?kind=${kind}` : ""}`),
  deploymentSettings: () => http<DeploymentSettings>(`/settings/deployment`),
  schedulePost: (postId: string, scheduledFor: string) =>
    http(`/posts/${postId}/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_for: scheduledFor }),
    }),
  retryPost: (postId: string, scheduledFor: string) =>
    http(`/posts/${postId}/retry`, {
      method: "POST",
      body: JSON.stringify({ scheduled_for: scheduledFor }),
    }),
  listConversations: () => http<any[]>(`/inbox/conversations`),
  listMessages: (convId: string) => http<any[]>(`/inbox/conversations/${convId}/messages`),
  replyInbox: (convId: string, text: string) =>
    http(`/inbox/conversations/${convId}/reply`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  ingestBrand: () => http<any>(`/admin/ingest-brand`, { method: "POST" }),
  ragStatus: () => http<any>(`/admin/rag-status`),
  // ===== Fotos reales (biblioteca de obras) =====
  listSourceAssets: (projectTag?: string) =>
    http<any[]>(
      `/source-assets${projectTag ? `?project_tag=${encodeURIComponent(projectTag)}` : ""}`
    ),
  listProjects: () => http<any[]>(`/source-assets/projects`),
  updateSourceAssetTag: (id: string, projectTag: string | null) =>
    http(`/source-assets/${id}/tag`, {
      method: "POST",
      body: JSON.stringify({ project_tag: projectTag }),
    }),
  uploadSourceAsset: async (file: File, projectTag?: string, caption?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (projectTag) fd.append("project_tag", projectTag);
    if (caption) fd.append("caption", caption);
    const res = await fetch(`${API_BASE}/source-assets/upload`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(`upload: ${res.status} ${await res.text()}`);
    return res.json();
  },
};
