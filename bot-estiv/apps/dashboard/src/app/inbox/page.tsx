import { Card, CardBody, CardHeader } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function Inbox() {
  const convs = await safe(api.listConversations, []);
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Inbox WhatsApp</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Conversaciones con Bot Estiv.
        </p>
      </header>
      <Card>
        <CardHeader title="Hilos recientes" />
        <CardBody>
          {convs.length === 0 && (
            <p className="text-sm text-carbon/50">
              Aún no hay conversaciones. Mandá un mensaje al WhatsApp conectado para
              iniciar.
            </p>
          )}
          <ul className="divide-y divide-carbon/5">
            {convs.map((c: any) => (
              <li key={c.id} className="py-3">
                <p className="font-medium text-sm">{c.user_wa_id}</p>
                <p className="text-xs text-carbon/50">
                  Último mensaje: {new Date(c.last_message_at).toLocaleString("es-AR")}
                </p>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
