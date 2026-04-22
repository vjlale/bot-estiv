import { cn } from "@/lib/cn";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-carbon/10 shadow-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between px-6 py-4 border-b border-carbon/5">
      <div>
        <h3 className="font-heading text-lg">{title}</h3>
        {subtitle && <p className="text-xs text-carbon/60 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("px-6 py-4", className)}>{children}</div>;
}

export function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "success" | "warning" | "danger" | "info" }) {
  const tones = {
    default: "bg-carbon/10 text-carbon",
    success: "bg-eucalyptus/20 text-eucalyptus",
    warning: "bg-fire/20 text-fire",
    danger: "bg-red-100 text-red-700",
    info: "bg-quebracho/10 text-quebracho",
  } as const;
  return (
    <span className={cn("inline-block px-2 py-0.5 rounded-full text-[11px] font-medium", tones[tone])}>
      {children}
    </span>
  );
}
