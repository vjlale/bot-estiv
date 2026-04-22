import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function CalendarPage() {
  const [week, upcoming] = await Promise.all([
    safe(api.weekPlan, null as any),
    safe(api.upcoming, []),
  ]);
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Calendario editorial</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Plan semanal propuesto por Bot Estiv + publicaciones programadas.
        </p>
      </header>

      <Card>
        <CardHeader
          title={week ? `Plan — semana del ${week.week_of}` : "Plan semanal"}
          subtitle={week?.summary}
        />
        <CardBody>
          {!week && <p className="text-sm text-carbon/50">No hay plan aún.</p>}
          {week && (
            <ul className="divide-y divide-carbon/5">
              {week.entries?.map((e: any, i: number) => (
                <li key={i} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium">
                      {e.day} · {e.slot}
                    </p>
                    <p className="text-xs text-carbon/60">{e.topic}</p>
                  </div>
                  <div className="flex gap-2">
                    <Badge tone="info">{e.format}</Badge>
                    <Badge tone="default">{e.pillar}</Badge>
                    <Badge tone="success">{e.content_type}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Publicaciones programadas" />
        <CardBody>
          {upcoming.length === 0 && (
            <p className="text-sm text-carbon/50">Nada programado todavía.</p>
          )}
          <ul className="divide-y divide-carbon/5">
            {upcoming.map((p) => (
              <li key={p.id} className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium">{p.title}</p>
                  <p className="text-xs text-carbon/60">
                    {p.scheduled_for
                      ? new Date(p.scheduled_for).toLocaleString("es-AR")
                      : "—"}
                  </p>
                </div>
                <Badge tone="info">{p.status}</Badge>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
