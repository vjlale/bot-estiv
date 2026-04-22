import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function Home() {
  const [approvals, upcoming, assets] = await Promise.all([
    safe(api.listApprovals, []),
    safe(api.upcoming, []),
    safe(() => api.listAssets(), []),
  ]);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-heading text-4xl">Panel</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Resumen del marketing digital de Gardens Wood.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Stat
          label="Pendientes de aprobación"
          value={approvals.length}
          tone="warning"
        />
        <Stat label="Programados" value={upcoming.length} tone="info" />
        <Stat label="Assets generados" value={assets.length} tone="success" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Próximas publicaciones" subtitle="Orden cronológico" />
          <CardBody>
            {upcoming.length === 0 && (
              <p className="text-sm text-carbon/50">No hay posts programados.</p>
            )}
            <ul className="divide-y divide-carbon/5">
              {upcoming.slice(0, 6).map((p) => (
                <li key={p.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{p.title}</p>
                    <p className="text-xs text-carbon/50">
                      {p.scheduled_for
                        ? new Date(p.scheduled_for).toLocaleString("es-AR")
                        : "—"}
                    </p>
                  </div>
                  <Badge tone="info">{p.format}</Badge>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Esperando aprobación"
            subtitle="Revisá y decidí desde WhatsApp o acá"
          />
          <CardBody>
            {approvals.length === 0 && (
              <p className="text-sm text-carbon/50">Todo al día.</p>
            )}
            <ul className="divide-y divide-carbon/5">
              {approvals.slice(0, 6).map((a: any) => (
                <li key={a.id} className="py-3">
                  <p className="font-medium text-sm">Post {a.post_id.slice(0, 8)}…</p>
                  <p className="text-xs text-carbon/50">
                    Solicitado {new Date(a.requested_at).toLocaleString("es-AR")}
                  </p>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "warning" | "info" | "success";
}) {
  return (
    <Card>
      <CardBody className="flex items-baseline justify-between">
        <div>
          <p className="text-xs text-carbon/60 uppercase tracking-wide">{label}</p>
          <p className="font-heading text-4xl mt-2">{value}</p>
        </div>
        <Badge tone={tone}>live</Badge>
      </CardBody>
    </Card>
  );
}
