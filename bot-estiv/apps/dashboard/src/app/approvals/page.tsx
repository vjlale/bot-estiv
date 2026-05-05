"use client";

import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";
import { ApprovalActions } from "./actions";

export default function Approvals() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const approvals = await api.listApprovals();
      const resolved = await Promise.all(
        approvals.map((a: any) =>
          api.getPost(a.post_id).catch(() => null)
        )
      );
      setPosts(resolved.filter(Boolean));
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-4xl">Cola de aprobación</h1>
          <p className="text-sm text-carbon/60 mt-1">
            Revisá las previews y decidí. Se actualiza cada 30 segundos.
          </p>
        </div>
        {!loading && (
          <span className="text-xs text-carbon/40">
            {posts.length} pendiente{posts.length !== 1 ? "s" : ""}
          </span>
        )}
      </header>

      {!loading && posts.length === 0 && (
        <Card>
          <CardBody>
            <p className="text-sm text-carbon/60">
              No hay piezas esperando aprobación.
            </p>
          </CardBody>
        </Card>
      )}

      {posts.map((p: any) => (
        <Card key={p.id}>
          <CardHeader
            title={p.title}
            subtitle={`${p.format} · ${p.pillar ?? "—"}`}
            action={<Badge tone="warning">pendiente</Badge>}
          />
          <CardBody>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              {p.assets?.map((a: any) => (
                <img
                  key={a.id}
                  src={a.url}
                  alt="preview"
                  className="rounded-md border border-carbon/10"
                />
              ))}
            </div>
            <p className="text-sm whitespace-pre-wrap">{p.caption}</p>
            {p.hashtags && (
              <p className="text-xs text-quebracho mt-3">
                {p.hashtags.join(" ")}
              </p>
            )}
            <div className="mt-6">
              <ApprovalActions postId={p.id} onDone={fetchData} />
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
