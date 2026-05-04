"use client";

import { useState, useTransition } from "react";
import { api } from "@/lib/api";

export function ApprovalActions({
  postId,
  onDone,
}: {
  postId: string;
  onDone?: () => void;
}) {
  const [pending, start] = useTransition();
  const [reason, setReason] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const act = (decision: "approve" | "reject" | "edit") =>
    start(async () => {
      try {
        setError(null);
        await api.decideApproval(postId, decision, reason || undefined);
        if (decision === "approve" && scheduledFor) {
          await api.schedulePost(postId, new Date(scheduledFor).toISOString());
        }
        setDone(decision);
        onDone?.();
      } catch (e: any) {
        setError(e.message ?? "Error desconocido");
      }
    });

  if (done)
    return (
      <p className="text-sm text-eucalyptus">
        ✓ Decisión registrada: {done}
        {done === "approve" && scheduledFor
          ? ` — agendado para ${new Date(scheduledFor).toLocaleString("es-AR")}`
          : ""}
      </p>
    );

  return (
    <div className="flex flex-col gap-3">
      {error && <p className="text-xs text-red-500">{error}</p>}
      <textarea
        className="w-full border border-carbon/15 rounded-md p-2 text-sm"
        placeholder="Comentario / feedback (opcional para editar)"
        rows={2}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs text-carbon/60">Agendar publicación:</label>
        <input
          type="datetime-local"
          className="border border-carbon/15 rounded-md px-2 py-1 text-sm"
          value={scheduledFor}
          onChange={(e) => setScheduledFor(e.target.value)}
        />
      </div>
      <div className="flex gap-2 flex-wrap">
        <button
          disabled={pending}
          onClick={() => act("approve")}
          className="px-4 py-2 rounded-md bg-eucalyptus text-white text-sm disabled:opacity-50"
        >
          Aprobar{scheduledFor ? " + Agendar" : ""}
        </button>
        <button
          disabled={pending}
          onClick={() => act("edit")}
          className="px-4 py-2 rounded-md bg-fire text-white text-sm disabled:opacity-50"
        >
          Pedir edición
        </button>
        <button
          disabled={pending}
          onClick={() => act("reject")}
          className="px-4 py-2 rounded-md bg-carbon/80 text-white text-sm disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
