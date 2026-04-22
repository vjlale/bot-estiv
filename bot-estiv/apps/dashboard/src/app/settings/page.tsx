import { Card, CardBody, CardHeader } from "@/components/Card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Configuración</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Variables y prompts del sistema Bot Estiv.
        </p>
      </header>
      <Card>
        <CardHeader title="Variables de entorno" subtitle="Se configuran en .env" />
        <CardBody>
          <ul className="text-sm space-y-2 text-carbon/80">
            <li>
              <code className="bg-bone px-2 py-0.5 rounded">TWILIO_*</code> credenciales WhatsApp
            </li>
            <li>
              <code className="bg-bone px-2 py-0.5 rounded">META_*</code> access token + Page + IG + Ad Account
            </li>
            <li>
              <code className="bg-bone px-2 py-0.5 rounded">OPENAI_API_KEY</code> + <code className="bg-bone px-2 py-0.5 rounded">GOOGLE_API_KEY</code>
            </li>
            <li>
              <code className="bg-bone px-2 py-0.5 rounded">S3_*</code> Cloudflare R2 / S3 para media pública
            </li>
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
