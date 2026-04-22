import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function Campaigns() {
  const campaigns = await safe(api.listCampaigns, []);
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Meta Ads</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Campañas activas, sugerencias y métricas.
        </p>
      </header>
      <Card>
        <CardHeader
          title="Campañas"
          subtitle="Estado en vivo desde la Marketing API"
        />
        <CardBody>
          {campaigns.length === 0 && (
            <p className="text-sm text-carbon/50">
              Sin campañas o sin credenciales configuradas aún.
            </p>
          )}
          <ul className="divide-y divide-carbon/5">
            {campaigns.map((c: any) => (
              <li key={c.id} className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-carbon/60">
                    {c.objective} · daily: $
                    {((c.daily_budget || 0) / 100).toLocaleString("es-AR")}
                  </p>
                </div>
                <Badge
                  tone={c.effective_status === "ACTIVE" ? "success" : "default"}
                >
                  {c.effective_status || c.status}
                </Badge>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
