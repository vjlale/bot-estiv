import { Card, CardBody, CardHeader } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function AnalyticsPage() {
  const [report, trends] = await Promise.all([
    safe(api.weeklyAnalytics, null as any),
    safe(api.trends, null as any),
  ]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Analytics</h1>
        <p className="text-sm text-carbon/60 mt-1">
          KPIs semanales + tendencias del rubro.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title={report ? `Reporte — ${report.period}` : "Reporte semanal"}
          />
          <CardBody>
            {!report && <p className="text-sm text-carbon/50">Sin datos aún.</p>}
            {report && (
              <>
                <pre className="text-xs bg-bone p-3 rounded overflow-auto max-h-60">
                  {JSON.stringify(report.kpis, null, 2)}
                </pre>
                <h4 className="font-heading text-base mt-4 mb-2">Recomendaciones</h4>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {report.recommendations?.map((r: string, i: number) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={trends ? `Tendencias — ${trends.month}` : "Tendencias"} />
          <CardBody>
            {!trends && <p className="text-sm text-carbon/50">Sin datos aún.</p>}
            {trends && (
              <ul className="space-y-3">
                {trends.ideas?.map((i: any, idx: number) => (
                  <li key={idx} className="border-l-2 border-fire pl-3">
                    <p className="font-medium text-sm">{i.title}</p>
                    <p className="text-xs text-carbon/60">
                      [{i.pillar}] — {i.why_now}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
