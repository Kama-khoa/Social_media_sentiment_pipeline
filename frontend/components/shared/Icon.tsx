import type { CSSProperties } from "react";

export type IconName = "activity" | "arrowDown" | "arrowUp" | "bell" | "box" | "broadcast" | "check" | "chevron" | "clock" | "close" | "edit" | "external" | "filter" | "flow" | "gauge" | "grid" | "heart" | "heartSolid" | "inbox" | "link" | "logout" | "menu" | "moon" | "play" | "plus" | "refresh" | "search" | "server" | "shield" | "spark" | "spec" | "sun" | "tag" | "trash" | "trophy" | "user" | "users";

interface IconProps {
  name: IconName;
  size?: number;
  style?: CSSProperties;
  className?: string;
}

export function Icon({ name, size = 18, style, className }: IconProps) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths: Record<IconName, React.ReactNode> = {
    search: <><circle cx="11" cy="11" r="7" {...p} /><path d="M21 21l-4.3-4.3" {...p} /></>,
    trophy: <><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z" {...p} /><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3M9 18h6M10 18l.5-3h3l.5 3M8 21h8" {...p} /></>,
    sun: <><circle cx="12" cy="12" r="4" {...p} /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" {...p} /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" {...p} />,
    user: <><circle cx="12" cy="8" r="4" {...p} /><path d="M5 21a7 7 0 0 1 14 0" {...p} /></>,
    users: <><circle cx="9" cy="8" r="3" {...p} /><path d="M3.5 21a5.5 5.5 0 0 1 11 0" {...p} /><path d="M16 11a3 3 0 1 0-.8-5.9M17 21a5.5 5.5 0 0 0-3-4.9" {...p} /></>,
    chevron: <path d="m6 9 6 6 6-6" {...p} />, logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H3" {...p} /></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16" {...p} />, close: <path d="M6 6l12 12M18 6 6 18" {...p} />,
    gauge: <><path d="M12 13l4-3" {...p} /><path d="M4.5 18a9 9 0 1 1 15 0" {...p} /></>, grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" {...p} /><rect x="14" y="3" width="7" height="7" rx="1.5" {...p} /><rect x="3" y="14" width="7" height="7" rx="1.5" {...p} /><rect x="14" y="14" width="7" height="7" rx="1.5" {...p} /></>,
    broadcast: <><circle cx="12" cy="12" r="2" {...p} /><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M6 6a9 9 0 0 0 0 12M18 6a9 9 0 0 1 0 12" {...p} /></>, tag: <><path d="M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9-9-9Z" {...p} /><circle cx="7.5" cy="7.5" r="1.2" fill="currentColor" /></>,
    box: <><path d="M21 8 12 3 3 8l9 5 9-5Z" {...p} /><path d="M3 8v8l9 5 9-5V8M12 13v8" {...p} /></>, heart: <path d="M19 14c1.5-1.5 3-3.3 3-5.6A3.9 3.9 0 0 0 12 5 3.9 3.9 0 0 0 2 8.4c0 2.3 1.5 4.1 3 5.6l7 7 7-7Z" {...p} />,
    heartSolid: <path d="M19 14c1.5-1.5 3-3.3 3-5.6A3.9 3.9 0 0 0 12 5 3.9 3.9 0 0 0 2 8.4c0 2.3 1.5 4.1 3 5.6l7 7 7-7Z" fill="currentColor" stroke="none" />,
    flow: <><circle cx="5" cy="6" r="2.4" {...p} /><circle cx="5" cy="18" r="2.4" {...p} /><circle cx="19" cy="12" r="2.4" {...p} /><path d="M7.4 6H13a3.5 3.5 0 0 1 3.5 3.5M7.4 18H13a3.5 3.5 0 0 0 3.5-3.5" {...p} /></>, activity: <path d="M3 12h4l2 7 4-16 2 9h6" {...p} />, shield: <path d="M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6l-8-3Z" {...p} />,
    link: <><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1" {...p} /><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1" {...p} /></>,
    inbox: <><path d="M4 4h16l2 10v4a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-4L4 4Z" {...p} /><path d="M2 14h6l2 3h4l2-3h6" {...p} /></>,
    bell: <><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" {...p} /><path d="M10.3 21a2 2 0 0 0 3.4 0" {...p} /></>, arrowUp: <path d="M12 19V5M5 12l7-7 7 7" {...p} />, arrowDown: <path d="M12 5v14M5 12l7 7 7-7" {...p} />, check: <path d="M20 6 9 17l-5-5" {...p} />, play: <path d="M7 4v16l13-8-13-8Z" fill="currentColor" />, plus: <path d="M12 5v14M5 12h14" {...p} />, edit: <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" {...p} />, trash: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" {...p} />,
    filter: <path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z" {...p} />, spec: <><rect x="4" y="3" width="16" height="18" rx="2" {...p} /><path d="M8 8h8M8 12h8M8 16h5" {...p} /></>, clock: <><circle cx="12" cy="12" r="9" {...p} /><path d="M12 7v5l3 2" {...p} /></>, refresh: <path d="M4 12a8 8 0 0 1 13.7-5.6L20 8M20 4v4h-4M20 12a8 8 0 0 1-13.7 5.6L4 16m0 4v-4h4" {...p} />, server: <><rect x="3" y="4" width="18" height="7" rx="2" {...p} /><rect x="3" y="13" width="18" height="7" rx="2" {...p} /><path d="M7 7.5h.01M7 16.5h.01" {...p} /></>, spark: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2" {...p} />, external: <path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" {...p} />,
  };
  return <svg viewBox="0 0 24 24" className={className} style={{ width: size, height: size, display: "block", flexShrink: 0, ...style }} aria-hidden="true">{paths[name]}</svg>;
}
