import { Card, CardBody, CardHeader } from "@/components/Card";
import { api } from "@/lib/api";

const labels: Record<string, string> = {
  database_url: "DATABASE_URL",
  database_url_sync: "DATABASE_URL_SYNC",
  redis_url: "REDIS_URL",
  google_api_key: "GOOGLE_API_KEY",
  twilio_account_sid: "TWILIO_ACCOUNT_SID",
  twilio_auth_token: "TWILIO_AUTH_TOKEN",
  twilio_whatsapp_from: "TWILIO_WHATSAPP_FROM",
  twilio_whatsapp_to: "TWILIO_WHATSAPP_TO",
  meta_access_token: "META_ACCESS_TOKEN",
  meta_ad_account_id: "META_AD_ACCOUNT_ID",
  meta_ig_business_id: "META_IG_BUSINESS_ID",
  meta_fb_page_id: "META_FB_PAGE_ID",
  s3_bucket: "S3_BUCKET",
  s3_public_base_url: "S3_PUBLIC_BASE_URL",
  sentry_dsn: "SENTRY_DSN",
};

export default async function SettingsPage() {
  const deployment = await api.deploymentSettings();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Configuración</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Variables, despliegue y prompts del sistema Bot Estiv.
        </p>
      </header>
      <Card>
        <CardHeader title="Despliegue VPS" subtitle="Estado visible desde la API, sin exponer secretos" />
        <CardBody>
          <dl className="grid gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-carbon/50">Entorno</dt>
              <dd className="font-medium">{deployment.environment}</dd>
            </div>
            <div>
              <dt className="text-carbon/50">Tenant</dt>
              <dd className="font-medium">{deployment.tenant_id}</dd>
            </div>
            <div>
              <dt className="text-carbon/50">Dashboard</dt>
              <dd className="font-medium">{deployment.dashboard_domain || "Sin configurar"}</dd>
            </div>
            <div>
              <dt className="text-carbon/50">API</dt>
              <dd className="font-medium">{deployment.api_domain || "Sin configurar"}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-carbon/50">Webhook Twilio</dt>
              <dd className="break-all font-medium">{deployment.twilio_webhook_url}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-carbon/50">Branding</dt>
              <dd className="break-all">
                {deployment.brand_logo_path} · {deployment.brand_manual_path}
              </dd>
            </div>
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Variables de entorno" subtitle="Presencia en .env de producción" />
        <CardBody>
          <ul className="grid gap-2 text-sm md:grid-cols-2">
            {Object.entries(deployment.checks).map(([key, ok]) => (
              <li key={key} className="flex items-center justify-between rounded-lg bg-bone px-3 py-2">
                <code>{labels[key] || key}</code>
                <span className={ok ? "text-green-700" : "text-red-700"}>
                  {ok ? "Configurada" : "Pendiente"}
                </span>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Agentes habilitados" />
        <CardBody>
          <ul className="grid grid-cols-2 gap-2 text-sm">
            <li>Director (Bot Estiv)</li>
            <li>Copywriter</li>
            <li>ContentDesigner</li>
            <li>VideoEditor</li>
            <li>BrandGuardian</li>
            <li>CampaignPlanner</li>
            <li>MetaAdsManager</li>
            <li>AnalyticsAgent</li>
            <li>TrendScout</li>
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
