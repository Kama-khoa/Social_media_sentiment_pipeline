interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[22px] font-extrabold tracking-[-.01em] text-[var(--text)]">{title}</h1>
        {description && <p className="muted mt-1 text-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}
