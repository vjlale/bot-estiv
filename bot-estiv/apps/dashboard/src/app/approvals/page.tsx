import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";
import { ApprovalActions } from "./actions";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function Approvals() {
  const approvals = await safe(api.listApprovals, []);
  const posts = await Promise.all(
    approvals.map((a: any) => safe(() => api.getPost(a.post_id), null)),
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Cola de aprobación</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Revisá las previews y decidí. Las decisiones se replican en WhatsApp.
        </p>
      </header>

      {approvals.length === 0 && (
        <Card>
          <CardBody>
            <p className="text-sm text-carbon/60">
              No hay piezas esperando aprobación.
            </p>
          </CardBody>
        </Card>
      )}

      {posts.map((p: any) =>
        p ? (
          <Card key={p.id}>
            <CardHeader
              title={p.title}
              subtitle={`${p.format} · ${p.pillar ?? "—"}`}
              action={<Badge tone="warning">pending</Badge>}
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
                <ApprovalActions postId={p.id} />
              </div>
            </CardBody>
          </Card>
        ) : null,
      )}
    </div>
  );
}
