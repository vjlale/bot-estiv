"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardBody, CardHeader, Badge } from "@/components/Card";
import { api } from "@/lib/api";

type Project = { project_tag: string; count: number; last_upload: string };
type SourceAsset = {
  id: string;
  project_tag: string | null;
  source_channel: string;
  url: string;
  kind: string;
  width: number | null;
  height: number | null;
  caption: string | null;
  uploaded_by_wa_id: string | null;
  created_at: string;
};

export default function LibraryPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [assets, setAssets] = useState<SourceAsset[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [newTag, setNewTag] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([
        api.listProjects().catch(() => []),
        api.listSourceAssets(selected || undefined).catch(() => []),
      ]);
      setProjects(p as Project[]);
      setAssets(a as SourceAsset[]);
    } finally {
      setLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    try {
      for (const file of files) {
        await api.uploadSourceAsset(file, selected || newTag || undefined);
      }
      await refresh();
    } catch (err) {
      alert(`Error subiendo: ${err}`);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="font-heading text-4xl">Biblioteca de obras</h1>
          <p className="text-sm text-carbon/60 mt-1">
            Fotos reales de trabajos, agrupadas por proyecto. Usá el hashtag{" "}
            <code className="bg-bone/40 px-1 rounded">#proyecto-nombre</code> al
            enviarlas por WhatsApp para taguearlas automáticamente.
          </p>
        </div>
      </header>

      {/* Uploader */}
      <Card>
        <CardHeader title="Subir nuevas fotos" />
        <CardBody>
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="project-tag (ej: cerco-mendiolaza)"
              value={selected ?? newTag}
              onChange={(e) => {
                setSelected(null);
                setNewTag(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"));
              }}
              className="px-3 py-2 border border-carbon/20 rounded text-sm min-w-[260px]"
            />
            <label className="cursor-pointer px-4 py-2 bg-carbon text-bone text-sm rounded hover:bg-carbon/80 transition">
              {uploading ? "Subiendo…" : "Elegí archivos"}
              <input
                type="file"
                multiple
                accept="image/*,video/mp4"
                onChange={handleUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
          </div>
        </CardBody>
      </Card>

      {/* Proyectos */}
      <Card>
        <CardHeader
          title={`Proyectos (${projects.length})`}
          action={
            selected ? (
              <button
                onClick={() => setSelected(null)}
                className="text-xs text-fire hover:underline"
              >
                Ver todos
              </button>
            ) : null
          }
        />
        <CardBody>
          {projects.length === 0 ? (
            <p className="text-sm text-carbon/50">
              Todavía no hay proyectos tagueados. Subí fotos o mandalas por WhatsApp con un hashtag.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {projects.map((p) => (
                <button
                  key={p.project_tag}
                  onClick={() => setSelected(p.project_tag)}
                  className={`px-3 py-2 rounded text-sm border transition ${
                    selected === p.project_tag
                      ? "bg-carbon text-bone border-carbon"
                      : "bg-bone/30 text-carbon border-carbon/20 hover:border-fire"
                  }`}
                >
                  <span className="font-medium">#{p.project_tag}</span>
                  <span className="ml-2 opacity-70">{p.count}</span>
                </button>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Grilla de fotos */}
      <Card>
        <CardHeader
          title={
            selected
              ? `#${selected} — ${assets.length} foto(s)`
              : `Últimas fotos (${assets.length})`
          }
          action={
            selected ? (
              <Badge tone="warning">listo para generar carrusel</Badge>
            ) : null
          }
        />
        <CardBody>
          {loading ? (
            <p className="text-sm text-carbon/50">Cargando…</p>
          ) : assets.length === 0 ? (
            <p className="text-sm text-carbon/50">No hay fotos todavía.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {assets.map((a) => (
                <div
                  key={a.id}
                  className="border border-carbon/10 rounded-md overflow-hidden bg-bone/30"
                >
                  {a.kind === "image" ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={a.url}
                      alt=""
                      className="w-full h-40 object-cover"
                    />
                  ) : (
                    <video src={a.url} className="w-full h-40 object-cover" controls />
                  )}
                  <div className="px-2 py-1 text-[11px] text-carbon/60 flex justify-between">
                    <span className="truncate">
                      {a.project_tag ? `#${a.project_tag}` : "sin tag"}
                    </span>
                    <span>{a.source_channel === "whatsapp" ? "WA" : "UI"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {selected && (
        <div className="rounded-md border border-carbon/10 bg-bone/20 p-4 text-sm text-carbon/80">
          <p className="font-medium mb-1">Siguiente paso</p>
          <p>
            Mandale por WhatsApp al bot:{" "}
            <code className="bg-bone/60 px-1 rounded">
              generá carrusel {selected}
            </code>
          </p>
        </div>
      )}
    </div>
  );
}
