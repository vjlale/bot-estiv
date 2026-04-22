import { Card, CardBody, CardHeader } from "@/components/Card";
import { api } from "@/lib/api";

async function safe<T>(fn: () => Promise<T>, fallback: T) {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default async function AssetsPage() {
  const assets = await safe(() => api.listAssets(), []);
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Biblioteca de assets</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Imágenes y videos generados por Bot Estiv.
        </p>
      </header>
      <Card>
        <CardHeader title={`${assets.length} assets`} />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {assets.map((a: any) => (
              <div key={a.id} className="border border-carbon/10 rounded-md overflow-hidden">
                {a.kind === "image" ? (
                  <img src={a.url} alt="" className="w-full h-40 object-cover" />
                ) : (
                  <video src={a.url} className="w-full h-40 object-cover" controls />
                )}
                <p className="text-[11px] text-carbon/60 px-2 py-1 truncate">
                  {a.kind} · {a.width ?? "?"}×{a.height ?? "?"}
                </p>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
