"use client";

import { useState, useTransition } from "react";
import { api } from "@/lib/api";

export function ApprovalActions({ postId }: { postId: string }) {
  const [pending, start] = useTransition();
  const [reason, setReason] = useState("");
  const [done, setDone] = useState<string | null>(null);

  const act = (decision: "approve" | "reject" | "edit") =>
    start(async () => {
      await api.decideApproval(postId, decision, reason || undefined);
      setDone(decision);
    });

  if (done) return <p className="text-sm text-eucalyptus">Decisión registrada: {done}</p>;

  return (
    <div className="flex flex-col gap-3">
      <textarea
        className="w-full border border-carbon/15 rounded-md p-2 text-sm"
        placeholder="Comentario / feedback (opcional para editar)"
        rows={2}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          disabled={pending}
          onClick={() => act("approve")}
          className="px-4 py-2 rounded-md bg-eucalyptus text-white text-sm disabled:opacity-50"
        >
          Aprobar
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
