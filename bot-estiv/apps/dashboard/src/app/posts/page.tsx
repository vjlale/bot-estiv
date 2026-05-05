"use client";

import { useEffect, useState, useTransition } from "react";
import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api, type Post } from "@/lib/api";

const STATUS_TONE: Record<string, "success" | "warning" | "danger" | "default"> = {
  published: "success",
  approved: "success",
  scheduled: "default",
  pending_approval: "warning",
  draft: "default",
  failed: "danger",
  rejected: "danger",
};

function RetryButton({ post, onDone }: { post: Post; onDone: () => void }) {
  const [pending, start] = useTransition();
  const [scheduledFor, setScheduledFor] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (done) return <p className="text-xs text-eucalyptus">✓ Reintento agendado</p>;

  return (
    <div className="flex flex-wrap items-center gap-2 mt-3">
      <input
        type="datetime-local"
        className="border border-carbon/15 rounded-md px-2 py-1 text-xs"
        value={scheduledFor}
        onChange={(e) => setScheduledFor(e.target.value)}
      />
      <button
        disabled={pending || !scheduledFor}
        onClick={() =>
          start(async () => {
            try {
              setError(null);
              await api.retryPost(post.id, new Date(scheduledFor).toISOString());
              setDone(true);
              onDone();
            } catch (e: any) {
              setError(e.message);
            }
          })
        }
        className="px-3 py-1 rounded-md bg-fire text-white text-xs disabled:opacity-50"
      >
        Reintentar
      </button>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

export default function Posts() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const fetchPosts = async () => {
    try {
      const result = await api.listPosts(statusFilter !== "all" ? statusFilter : undefined);
      setPosts(result);
    } catch {
      setPosts([]);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, [statusFilter]);

  const statuses = ["all", "pending_approval", "approved", "scheduled", "published", "failed", "rejected"];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Posts</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Historial de piezas generadas por Bot Estiv.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs border ${
              statusFilter === s
                ? "bg-carbon text-white border-carbon"
                : "border-carbon/20 text-carbon/60"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {posts.length === 0 && (
        <Card>
          <CardBody>
            <p className="text-sm text-carbon/60">No hay posts en este estado.</p>
          </CardBody>
        </Card>
      )}

      <div className="space-y-4">
        {posts.map((p) => (
          <Card key={p.id}>
            <CardHeader
              title={p.title}
              subtitle={`${p.format} · ${p.pillar ?? "—"} · ${new Date(p.created_at).toLocaleDateString("es-AR")}`}
              action={
                <Badge tone={STATUS_TONE[p.status] ?? "neutral"}>
                  {p.status}
                </Badge>
              }
            />
            <CardBody>
              {p.assets && p.assets.length > 0 && (
                <div className="flex gap-2 mb-3 overflow-x-auto">
                  {p.assets.map((a) => (
                    <img
                      key={a.id}
                      src={a.url}
                      alt="asset"
                      className="h-24 rounded-md border border-carbon/10 flex-shrink-0"
                    />
                  ))}
                </div>
              )}
              <p className="text-sm whitespace-pre-wrap line-clamp-3">{p.caption}</p>
              {p.scheduled_for && (
                <p className="text-xs text-carbon/50 mt-2">
                  Agendado: {new Date(p.scheduled_for).toLocaleString("es-AR")}
                </p>
              )}
              {p.published_at && (
                <p className="text-xs text-eucalyptus mt-2">
                  Publicado: {new Date(p.published_at).toLocaleString("es-AR")}
                </p>
              )}
              {p.status === "failed" && (
                <RetryButton post={p} onDone={fetchPosts} />
              )}
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
