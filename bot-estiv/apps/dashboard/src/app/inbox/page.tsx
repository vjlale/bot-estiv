"use client";

import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { api } from "@/lib/api";

function ConversationThread({ conv }: { conv: any }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingMsgs, setLoadingMsgs] = useState(false);

  const loadMessages = async () => {
    setLoadingMsgs(true);
    try {
      const msgs = await api.listMessages(conv.id);
      setMessages(msgs);
    } finally {
      setLoadingMsgs(false);
    }
  };

  const toggleOpen = () => {
    if (!open) loadMessages();
    setOpen((v) => !v);
  };

  const sendReply = async () => {
    if (!reply.trim()) return;
    setSending(true);
    try {
      await api.replyInbox(conv.id, reply.trim());
      setReply("");
      await loadMessages();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <li className="py-3">
      <button
        className="w-full text-left"
        onClick={toggleOpen}
      >
        <p className="font-medium text-sm">{conv.user_wa_id}</p>
        <p className="text-xs text-carbon/50">
          Último mensaje: {new Date(conv.last_message_at).toLocaleString("es-AR")}
        </p>
      </button>

      {open && (
        <div className="mt-3 border-t border-carbon/10 pt-3 space-y-2">
          {loadingMsgs && <p className="text-xs text-carbon/40">Cargando…</p>}
          <ul className="space-y-1 max-h-64 overflow-y-auto">
            {messages.map((m: any) => (
              <li
                key={m.id}
                className={`text-xs px-3 py-2 rounded-md max-w-lg ${
                  m.role === "user"
                    ? "bg-carbon/5 self-start"
                    : "bg-eucalyptus/10 ml-auto text-right"
                }`}
              >
                <span className="text-carbon/40 mr-1">
                  [{m.role}{m.agent ? `·${m.agent}` : ""}]
                </span>
                {m.content}
              </li>
            ))}
          </ul>
          <div className="flex gap-2 mt-2">
            <input
              type="text"
              className="flex-1 border border-carbon/15 rounded-md px-3 py-1.5 text-sm"
              placeholder="Escribí una respuesta manual…"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendReply()}
            />
            <button
              disabled={sending || !reply.trim()}
              onClick={sendReply}
              className="px-4 py-1.5 rounded-md bg-eucalyptus text-white text-sm disabled:opacity-50"
            >
              Enviar
            </button>
          </div>
        </div>
      )}
    </li>
  );
}

export default function Inbox() {
  const [convs, setConvs] = useState<any[]>([]);

  useEffect(() => {
    api.listConversations().then(setConvs).catch(() => setConvs([]));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-4xl">Inbox</h1>
        <p className="text-sm text-carbon/60 mt-1">
          Conversaciones WhatsApp y Telegram. Hacé clic para ver el hilo y responder.
        </p>
      </header>
      <Card>
        <CardHeader title="Hilos recientes" />
        <CardBody>
          {convs.length === 0 && (
            <p className="text-sm text-carbon/50">
              Aún no hay conversaciones. Mandá un mensaje al canal conectado para iniciar.
            </p>
          )}
          <ul className="divide-y divide-carbon/5">
            {convs.map((c: any) => (
              <ConversationThread key={c.id} conv={c} />
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
