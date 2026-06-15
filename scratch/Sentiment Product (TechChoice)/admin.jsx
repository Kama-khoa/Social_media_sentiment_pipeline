/* ============================================================
   TechChoice — Admin dashboard layout (sidebar)
   exports: AdminApp
   ============================================================ */
const { useState: useStateA } = React;

const iconBtnStyle = {
  width: 36, height: 36, borderRadius: 10, border: "none",
  background: "transparent", cursor: "pointer", display: "grid",
  placeItems: "center", color: "var(--text-2)",
};
const inputStyle = {
  padding: "9px 13px", borderRadius: 9, border: "1px solid var(--border)",
  background: "var(--surface)", fontSize: 13.5, fontFamily: "var(--font-ui)",
  outline: "none", color: "var(--text)", width: "100%", boxSizing: "border-box",
};

const ADMIN_MENU = [
  { id: "overview",       label: "Tổng quan phân tích", icon: "grid",      group: "PHÂN TÍCH" },
  { id: "channels",       label: "Quản lý kênh",        icon: "broadcast", group: "THU THẬP"  },
  { id: "keywords",       label: "Quản lý từ khóa",     icon: "tag",       group: "THU THẬP"  },
  { id: "products",       label: "Quản lý sản phẩm",    icon: "box",       group: "SẢN PHẨM" },
  { id: "aliases",        label: "Tên gọi khác",        icon: "link",      group: "SẢN PHẨM" },
  { id: "candidates",     label: "Duyệt ánh xạ SP",     icon: "inbox",     group: "SẢN PHẨM" },
  { id: "spec_templates", label: "Mẫu thông số",        icon: "spec",      group: "SẢN PHẨM" },
  { id: "pipeline",       label: "Tình trạng Pipeline", icon: "heart",     group: "HỆ THỐNG" },
  { id: "dags",           label: "Lịch sử DAG Runs",    icon: "flow",      group: "HỆ THỐNG" },
  { id: "ops",            label: "Chỉ số vận hành",     icon: "activity",  group: "HỆ THỐNG" },
  { id: "accounts",       label: "Quản lý tài khoản",   icon: "users",     group: "HỆ THỐNG" },
];

function stateChip(state) {
  const map = {
    success: ["Thành công", "pos"], running: ["Đang chạy", "brand"],
    queued: ["Đang chờ", "neu"], failed: ["Thất bại", "neg"],
  };
  const [t, cls] = map[state] || [state, ""];
  return <span className={"chip " + cls}>{state === "running" && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor", animation: "pulseDot 1s infinite" }} />}{t}</span>;
}

/* ---------------- Sidebar ---------------- */
function Sidebar({ page, setPage, open, setOpen }) {
  return (
    <>
      {open && <div onClick={() => setOpen(false)} className="sidebar-scrim" style={{ position: "fixed", inset: 0, background: "rgba(20,12,40,.5)", zIndex: 60, display: "none" }} />}
      <aside className={"admin-sidebar" + (open ? " open" : "")} style={{
        width: 256, flexShrink: 0, background: "var(--surface)", borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column", position: "sticky", top: 0, height: "100vh",
      }}>
        <div style={{ padding: "20px 20px 14px", display: "flex", alignItems: "center", gap: 11 }}>
          <span style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: "linear-gradient(135deg, var(--v-500), var(--v-700))", color: "#fff" }}>
            <Icon name="spark" size={19} />
          </span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>TechChoice</div>
            <div className="faint" style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".04em" }}>BẢNG QUẢN TRỊ</div>
          </div>
        </div>
        <div style={{ padding: "6px 12px", flex: 1, overflowY: "auto" }}>
          {[...new Set(ADMIN_MENU.map(m => m.group))].map(group => (
            <div key={group}>
              <div className="faint" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".07em", padding: "14px 12px 5px", textTransform: "uppercase" }}>{group}</div>
              {ADMIN_MENU.filter(m => m.group === group).map(m => (
                <button key={m.id} onClick={() => { setPage(m.id); setOpen(false); }} style={{
                  width: "100%", display: "flex", alignItems: "center", gap: 11, padding: "9px 12px", borderRadius: 10, border: "none", cursor: "pointer",
                  fontSize: 13.5, fontWeight: 600, marginBottom: 2, textAlign: "left", transition: "all .14s", position: "relative",
                  background: page === m.id ? "var(--primary-soft)" : "transparent", color: page === m.id ? "var(--primary)" : "var(--text-2)",
                }}
                  onMouseEnter={e => { if (page !== m.id) e.currentTarget.style.background = "var(--surface-3)"; }}
                  onMouseLeave={e => { if (page !== m.id) e.currentTarget.style.background = "transparent"; }}>
                  {page === m.id && <span style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 3, borderRadius: 3, background: "var(--primary)" }} />}
                  <Icon name={m.icon} size={16} />{m.label}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div style={{ padding: 14, borderTop: "1px solid var(--border)" }}>
          <div className="card" style={{ padding: 12, background: "var(--surface-2)", display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--pos)", animation: "pulseDot 1.4s infinite" }} />
            <div style={{ fontSize: 12 }}><div style={{ fontWeight: 700 }}>Hệ thống ổn định</div><div className="faint">Airflow · BigQuery · Redis</div></div>
          </div>
        </div>
      </aside>
    </>
  );
}

/* ---------------- Header ---------------- */
function AdminHeader({ session, onLogout, onExit, theme, toggleTheme, onMenu, title }) {
  return (
    <header style={{
      position: "sticky", top: 0, zIndex: 40, height: 64, background: "var(--nav-bg)", backdropFilter: "blur(14px)",
      borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 14, padding: "0 24px",
    }}>
      <button className="admin-menu-btn" style={{ ...iconBtnStyle, display: "none" }} onClick={onMenu}><Icon name="menu" size={20} /></button>
      <div style={{ flex: 1 }}>
        <h1 style={{ margin: 0, fontSize: 19, fontWeight: 800, letterSpacing: "-.01em" }}>{title}</h1>
      </div>
      <div className="sys-status" style={{ display: "flex", alignItems: "center", gap: 14, marginRight: 4 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, fontWeight: 600, color: "var(--text-2)" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--pos)", animation: "pulseDot 1.4s infinite" }} />Hệ thống hoạt động
        </span>
        <span className="chip" style={{ fontFamily: "var(--font-num)" }}>Quota 78%</span>
      </div>
      <button onClick={toggleTheme} className="focusable" style={iconBtnStyle} title="Sáng/tối"><Icon name={theme === "dark" ? "sun" : "moon"} size={18} /></button>
      <button onClick={onExit} className="btn btn-ghost" style={{ padding: "8px 14px" }} title="Về giao diện công khai"><Icon name="external" size={16} />Trang công khai</button>
      <div style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 8, borderLeft: "1px solid var(--border)" }}>
        <span style={{ width: 34, height: 34, borderRadius: "50%", background: "linear-gradient(135deg,var(--v-400),var(--v-600))", color: "#fff", display: "grid", placeItems: "center", fontWeight: 700 }}>{session.name.charAt(0)}</span>
        <div className="user-meta" style={{ lineHeight: 1.2 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>{session.name}</div>
          <div className="chip brand" style={{ padding: "0 7px", fontSize: 10.5, marginTop: 2 }}>Quản trị viên</div>
        </div>
        <button onClick={onLogout} className="focusable" style={{ ...iconBtnStyle, color: "var(--neg)" }} title="Đăng xuất"><Icon name="logout" size={18} /></button>
      </div>
    </header>
  );
}

/* ---------------- Page section helpers ---------------- */
function PageHead({ title, sub, action }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
      <div><h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, letterSpacing: "-.01em" }}>{title}</h2>
        {sub && <p className="muted" style={{ margin: "5px 0 0", fontSize: 14 }}>{sub}</p>}</div>
      {action}
    </div>
  );
}
function Toggle({ on, onClick }) {
  return (
    <button onClick={onClick} className="focusable" style={{
      width: 40, height: 23, borderRadius: 99, border: "none", cursor: "pointer", padding: 2,
      background: on ? "var(--primary)" : "var(--border-strong)", transition: "background .2s", display: "flex", justifyContent: on ? "flex-end" : "flex-start",
    }}>
      <span style={{ width: 19, height: 19, borderRadius: "50%", background: "#fff", transition: "all .2s", boxShadow: "0 1px 3px rgba(0,0,0,.3)" }} />
    </button>
  );
}

/* ---------------- Overview ---------------- */
function OverviewPage() {
  const P = window.DATA.PIPELINE;
  const cats = window.DATA.CATEGORIES.filter(c => c.slug !== "all");
  const top = window.DATA.PRODUCTS.slice(0, 5).map((p, i) => ({ ...p, rank: i + 1 }));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PageHead title="Tổng quan phân tích" sub="Bức tranh toàn cảnh dữ liệu cảm xúc & vận hành hệ thống, cập nhật 02/06/2026." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 14 }}>
        <KpiCard icon="play" label="Video thu thập hôm nay" value={P.videosToday} trend={4.2} accent="var(--primary)" spark={window.DATA.OPS_SERIES} />
        <KpiCard icon="bell" label="Bình luận phân tích" value={(P.commentsToday / 1000).toFixed(1) + "K"} trend={6.8} accent="var(--v-400)" spark={window.DATA.NLP_SERIES} />
        <KpiCard icon="box" label="Sản phẩm theo dõi" value={P.productsTracked} sub="trên 4 danh mục" accent="var(--pos)" />
        <KpiCard icon="broadcast" label="Kênh đang hoạt động" value={P.activeChannels} sub={P.activeKeywords + " từ khóa"} accent="var(--neu)" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18 }} className="analytics-grid">
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Lượng đề cập 15 ngày qua</h3>
          <p className="faint" style={{ margin: "0 0 10px", fontSize: 12.5 }}>Tổng số bình luận được pipeline xử lý mỗi ngày (nghìn).</p>
          <BarChart data={window.DATA.OPS_SERIES.map((v, i) => ({ label: i % 3 === 0 ? (i + 1) + "" : "", value: v }))} height={210} />
        </div>
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 700 }}>Đề cập theo danh mục</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {cats.map(c => {
              const max = Math.max(...cats.map(x => x.mentions));
              return (
                <div key={c.slug}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5, marginBottom: 6, gap: 10 }}>
                    <span style={{ fontWeight: 700, whiteSpace: "nowrap" }}>{c.label}</span>
                    <span className="num faint" style={{ flexShrink: 0 }}>{c.mentions.toLocaleString("vi-VN")}</span>
                  </div>
                  <div style={{ height: 9, borderRadius: 99, background: "var(--surface-3)", overflow: "hidden" }}>
                    <div style={{ width: (c.mentions / max * 100) + "%", height: "100%", background: "linear-gradient(90deg,var(--v-500),var(--v-400))", borderRadius: 99, transition: "width .8s ease" }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="card" style={{ padding: 22 }}>
        <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 700 }}>Top sản phẩm theo điểm tín nhiệm</h3>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>#</th><th>Sản phẩm</th><th>Điểm</th><th style={{ minWidth: 130 }}>Cảm xúc</th><th>Đề cập</th><th>Tranh cãi</th></tr></thead>
            <tbody>
              {top.map(p => (
                <tr key={p.product_id}>
                  <td className="num" style={{ fontWeight: 700, color: "var(--primary)" }}>{p.rank}</td>
                  <td style={{ fontWeight: 700 }}>{p.product_name}</td>
                  <td className="num" style={{ fontWeight: 700 }}>{(p.score * 100).toFixed(1)}</td>
                  <td><SentimentBar pos={p.pos} neg={p.neg} height={8} /></td>
                  <td className="num muted">{p.mentions.toLocaleString("vi-VN")}</td>
                  <td>{controversyChip(p.controversy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Channels ---------------- */
function ChannelsPage() {
  const [rows, setRows] = useStateA(window.DATA.CHANNELS.map(c => ({ ...c })));
  const [dagModal, setDagModal] = useStateA(null);
  const [dagConf, setDagConf] = useStateA({ lookback_days: 30, crawl_mode: "api_or_ytdlp" });
  const [dagStatus, setDagStatus] = useStateA(null); // null | loading | success | error
  const pg = usePagination(rows, 8);

  const openDag = (ch) => { setDagModal(ch); setDagStatus(null); setDagConf({ lookback_days: 30, crawl_mode: "api_or_ytdlp" }); };
  const closeDag = () => { setDagModal(null); setDagStatus(null); };
  const triggerDag = () => {
    setDagStatus("loading");
    // Simulate Airflow API call — POST /api/v1/dags/youtube_daily_extraction_dag/dagRuns
    setTimeout(() => setDagStatus("success"), 1600);
  };

  return (
    <div>
      <PageHead title="Quản lý kênh" sub={rows.length + " kênh YouTube đang được giám sát thu thập dữ liệu."}
        action={<button className="btn btn-primary"><Icon name="plus" size={16} />Thêm kênh</button>} />
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>Kênh</th><th>Handle</th><th>Người đăng ký</th><th>Video</th><th>Quét lịch sử</th><th>Hoạt động</th><th></th></tr></thead>
            <tbody>
              {pg.paged.map((c, i) => (
                <tr key={c.id}>
                  <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 32, height: 32, borderRadius: 9, background: "var(--surface-3)", display: "grid", placeItems: "center", color: "var(--primary)" }}><Icon name="broadcast" size={16} /></span>
                    <span style={{ fontWeight: 700 }}>{c.name}</span></div></td>
                  <td className="muted mono" style={{ fontSize: 13 }}>{c.handle}</td>
                  <td className="num">{(c.subs / 1e6).toFixed(2)}M</td>
                  <td className="num muted">{c.videos}</td>
                  <td>{c.scanned ? <span className="chip pos"><Icon name="check" size={12} />Đã quét</span> : <span className="chip neu">Chưa quét</span>}</td>
                  <td><Toggle on={c.active} onClick={() => setRows(r => r.map(x => x.id === c.id ? { ...x, active: !x.active } : x))} /></td>
                  <td><div style={{ display: "flex", gap: 4 }}>
                    <button style={{ ...miniBtn, color: "var(--primary)" }} title="Trigger DAG thu thập video" onClick={() => openDag(c)}><Icon name="play-circle" size={16} /></button>
                    <button style={miniBtn}><Icon name="edit" size={15} /></button>
                    <button style={{ ...miniBtn, color: "var(--neg)" }}><Icon name="trash" size={15} /></button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination {...pg} />
      </div>

      {/* DAG Trigger Modal */}
      {dagModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(20,12,40,.58)", zIndex: 200, display: "grid", placeItems: "center", padding: 20 }}
          onClick={e => e.target === e.currentTarget && closeDag()}>
          <div className="card" style={{ width: 460, maxWidth: "100%", padding: 26 }}>
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Trigger DAG thu thập video</h3>
                <p className="faint" style={{ margin: "4px 0 0", fontSize: 12.5 }}>youtube_daily_extraction_dag</p>
              </div>
              <button onClick={closeDag} style={iconBtnStyle}><Icon name="close" size={18} /></button>
            </div>
            {/* Channel info */}
            <div style={{ padding: "12px 14px", borderRadius: 10, background: "var(--surface-2)", display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
              <span style={{ width: 38, height: 38, borderRadius: 10, background: "var(--primary-soft)", color: "var(--primary)", display: "grid", placeItems: "center", flexShrink: 0 }}>
                <Icon name="broadcast" size={19} />
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14.5 }}>{dagModal.name}</div>
                <div className="faint" style={{ fontSize: 12 }}>{dagModal.handle} · {dagModal.videos.toLocaleString("vi-VN")} videos</div>
              </div>
              <code style={{ fontSize: 11, background: "var(--code-bg)", padding: "3px 8px", borderRadius: 6, color: "var(--text-3)", fontFamily: "var(--font-num)", flexShrink: 0 }}>{dagModal.id}</code>
            </div>
            {/* Config */}
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 7, color: "var(--text-2)" }}>Lookback days</div>
                  <input type="number" value={dagConf.lookback_days}
                    onChange={e => setDagConf(c => ({ ...c, lookback_days: Math.max(1, +e.target.value) }))}
                    style={{ ...inputStyle }} min={1} max={365} />
                </div>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 7, color: "var(--text-2)" }}>Crawl mode</div>
                  <select value={dagConf.crawl_mode}
                    onChange={e => setDagConf(c => ({ ...c, crawl_mode: e.target.value }))}
                    style={{ ...inputStyle }}>
                    <option value="api_or_ytdlp">api_or_ytdlp</option>
                    <option value="ytdlp_only">ytdlp_only</option>
                    <option value="api_only">api_only</option>
                  </select>
                </div>
              </div>
              <div style={{ padding: "10px 13px", borderRadius: 9, background: "var(--surface-3)", fontSize: 12, fontFamily: "var(--font-num)", color: "var(--text-3)", lineHeight: 1.7 }}>
                conf: <span style={{ color: "var(--primary)" }}>{JSON.stringify({ channel_id: dagModal.id, lookback_days: dagConf.lookback_days, crawl_mode: dagConf.crawl_mode })}</span>
              </div>
            </div>
            {/* Status */}
            {dagStatus === "success" && (
              <div style={{ marginTop: 14, padding: "11px 14px", borderRadius: 10, background: "var(--pos-soft)", color: "var(--pos)", fontWeight: 600, display: "flex", gap: 9, alignItems: "center", fontSize: 13.5 }}>
                <Icon name="check" size={17} />DAG triggered! Run đã được tạo trong Airflow.
              </div>
            )}
            {dagStatus === "error" && (
              <div style={{ marginTop: 14, padding: "11px 14px", borderRadius: 10, background: "var(--neg-soft)", color: "var(--neg)", fontWeight: 600, display: "flex", gap: 9, alignItems: "center", fontSize: 13.5 }}>
                <Icon name="close" size={17} />Không kết nối được Airflow. Kiểm tra cấu hình.
              </div>
            )}
            {/* Footer */}
            <div style={{ display: "flex", gap: 10, marginTop: 20, justifyContent: "flex-end" }}>
              <button className="btn btn-ghost" onClick={closeDag}>Đóng</button>
              <button className="btn btn-primary" disabled={dagStatus === "loading" || dagStatus === "success"} onClick={triggerDag}>
                {dagStatus === "loading"
                  ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Đang trigger...</>
                  : <><Icon name="play-circle" size={16} />Trigger DAG</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------------- Keywords ---------------- */
function KeywordsPage() {
  const [rows, setRows] = useStateA(window.DATA.KEYWORDS.map(k => ({ ...k })));
  const [text, setText] = useStateA("");
  const pg = usePagination(rows, 10);
  const add = () => { if (!text.trim()) return; setRows(r => [{ id: "k" + Date.now(), text: text.trim(), cluster: "mới", active: true, hits: 0 }, ...r]); pg.setPage(1); setText(""); };
  return (
    <div>
      <PageHead title="Quản lý từ khóa" sub="Các từ khóa tìm kiếm dùng để khám phá video liên quan trên YouTube." />
      <div className="card" style={{ padding: 16, marginBottom: 18, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === "Enter" && add()} placeholder="Nhập từ khóa mới — vd: vivo x200 pro" style={{ ...inputStyle, flex: 1, minWidth: 200 }} />
        <button className="btn btn-primary" onClick={add}><Icon name="plus" size={16} />Thêm từ khóa</button>
      </div>
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>Từ khóa</th><th>Cụm tìm kiếm</th><th>Lượt khớp</th><th>Hoạt động</th><th></th></tr></thead>
            <tbody>
              {pg.paged.map((k, i) => (
                <tr key={k.id}>
                  <td><span style={{ fontWeight: 700, fontFamily: "var(--font-num)" }}>{k.text}</span></td>
                  <td><span className="chip">{k.cluster}</span></td>
                  <td className="num muted">{k.hits.toLocaleString("vi-VN")}</td>
                  <td><Toggle on={k.active} onClick={() => setRows(r => r.map(x => x.id === k.id ? { ...x, active: !x.active } : x))} /></td>
                  <td><button style={{ ...miniBtn, color: "var(--neg)" }} onClick={() => setRows(r => r.filter(x => x.id !== k.id))}><Icon name="trash" size={15} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination {...pg} />
      </div>
    </div>
  );
}

/* ---------------- Edit Request Modal (Admin) ---------------- */
const STATUS_OPTS = [
  { v: "pending",    l: "Đang chờ",     dot: "#d97706" },
  { v: "processing", l: "Đang xử lý",   dot: "var(--primary)" },
  { v: "accepted",   l: "Đã tiếp nhận", dot: "var(--pos)" },
  { v: "rejected",   l: "Đã từ chối",   dot: "var(--neg)" },
];

function EditRequestModal({ request, onClose, onSave }) {
  const [status,  setStatus]  = useStateA(request.status);
  const [handler, setHandler] = useStateA(request.handler || "");
  const [reason,  setReason]  = useStateA(request.reason  || "");
  const dot = (STATUS_OPTS.find(o => o.v === status) || {}).dot || "var(--text-3)";

  const rowLbl = { fontSize: 11.5, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 6 };

  const save = () => onSave(request.id, {
    status,
    handler: handler.trim() || null,
    reason:  status === "rejected" ? (reason.trim() || null) : null,
  });

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(20,12,40,.58)", zIndex: 200, display: "grid", placeItems: "center", padding: 20 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card" style={{ width: 520, maxWidth: "100%", padding: 26, maxHeight: "90vh", overflowY: "auto" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Chi tiết phiếu chỉnh sửa</h3>
            <p className="faint" style={{ margin: "4px 0 0", fontSize: 12 }}>#{request.id} · Gửi ngày {request.created_at}</p>
          </div>
          <button onClick={onClose} style={iconBtnStyle}><Icon name="close" size={18} /></button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Sender + product */}
          <div style={{ padding: "13px 15px", borderRadius: 11, background: "var(--surface-2)", display: "flex", alignItems: "center", gap: 13, flexWrap: "wrap" }}>
            <span style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg,var(--v-400),var(--v-600))", color: "#fff", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 17, flexShrink: 0 }}>
              {request.by_name.charAt(0)}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{request.by_name}</div>
              <div className="faint" style={{ fontSize: 12.5 }}>{request.by_email}</div>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-3)", marginBottom: 2 }}>SẢN PHẨM</div>
              <div style={{ fontWeight: 700, fontSize: 13.5, color: "var(--primary)" }}>{request.product}</div>
            </div>
          </div>

          {/* Title */}
          <div>
            <div style={rowLbl}>Tiêu đề chỉnh sửa</div>
            <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.4 }}>{request.title}</div>
          </div>

          {/* Content */}
          <div>
            <div style={rowLbl}>Nội dung chỉnh sửa</div>
            <code style={{ fontSize: 13, background: "var(--code-bg)", padding: "10px 13px", borderRadius: 9, color: "var(--primary)", fontFamily: "var(--font-num)", display: "block", lineHeight: 1.7 }}>
              {request.content}
            </code>
          </div>

          {/* Status + handler */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 13 }}>
            <div>
              <div style={rowLbl}>Trạng thái</div>
              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", width: 9, height: 9, borderRadius: "50%", background: dot, pointerEvents: "none", zIndex: 1 }} />
                <select value={status} onChange={e => setStatus(e.target.value)}
                  style={{ ...inputStyle, paddingLeft: 28, fontWeight: 700 }}>
                  {STATUS_OPTS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                </select>
              </div>
            </div>
            <div>
              <div style={rowLbl}>Người xử lý</div>
              <input value={handler} onChange={e => setHandler(e.target.value)}
                placeholder="Chưa phân công" style={inputStyle} />
            </div>
          </div>

          {/* Rejection reason */}
          {status === "rejected" && (
            <div>
              <div style={rowLbl}>Lý do từ chối</div>
              <textarea value={reason} onChange={e => setReason(e.target.value)}
                placeholder="Nhập lý do từ chối để thông báo cho người dùng..."
                rows={3}
                style={{ ...inputStyle, resize: "vertical", lineHeight: 1.6, fontFamily: "var(--font-ui)" }} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
          <button className="btn btn-ghost" onClick={onClose}>Đóng</button>
          <button className="btn btn-primary" onClick={save}><Icon name="check" size={16} />Lưu thay đổi</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Products + moderation ---------------- */
const KANBAN_COLS = [
  { id: "pending",    label: "Đang chờ",     dot: "#d97706", bg: "#fef9ec", bgOver: "#fef3c7", border: "#fde68a" },
  { id: "processing", label: "Đang xử lý",   dot: "var(--primary)", bg: "var(--surface-2)", bgOver: "var(--primary-soft)", border: "var(--primary)" },
  { id: "accepted",   label: "Đã tiếp nhận", dot: "var(--pos)",     bg: "var(--surface-2)", bgOver: "var(--pos-soft)",     border: "var(--pos)"  },
  { id: "rejected",   label: "Đã từ chối",   dot: "var(--neg)",     bg: "var(--surface-2)", bgOver: "var(--neg-soft)",     border: "var(--neg)"  },
];

function ProductsPage() {
  const [tab,      setTab]      = useStateA("catalog");
  const [requests, setRequests] = useStateA(() => (window.DATA.EDIT_REQUESTS || []).map(r => ({ ...r })));
  const [dragId,   setDragId]   = useStateA(null);
  const [dragOver, setDragOver] = useStateA(null);
  const [modalId,  setModalId]  = useStateA(null);
  const products = window.DATA.PRODUCTS;
  const pgProd = usePagination(products, 10);

  const updateRequest = (id, changes) => {
    setRequests(prev => {
      const next = prev.map(r => r.id === id ? { ...r, ...changes } : r);
      window.DATA.EDIT_REQUESTS = next;
      return next;
    });
  };

  const modalRequest = modalId ? requests.find(r => r.id === modalId) : null;

  return (
    <div>
      <PageHead title="Quản lý sản phẩm" sub="Catalog sản phẩm, alias và phiếu đề xuất chỉnh sửa thông số."
        action={<button className="btn btn-primary"><Icon name="plus" size={16} />Thêm sản phẩm</button>} />

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
        {[["catalog", "Danh mục sản phẩm"], ["requests", `Phiếu chỉnh sửa (${requests.length})`]].map(([id, l]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "8px 16px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13.5, fontWeight: 600,
            background: tab === id ? "var(--primary)" : "var(--surface)",
            color: tab === id ? "var(--on-primary)" : "var(--text-2)",
            boxShadow: tab === id ? "none" : "var(--shadow-sm)",
          }}>{l}</button>
        ))}
      </div>

      {tab === "catalog" ? (
        <div className="card" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead><tr><th>Sản phẩm</th><th>Thương hiệu</th><th>Danh mục</th><th>Năm</th><th>Đề cập</th><th>Trạng thái</th><th></th></tr></thead>
              <tbody>
                {pgProd.paged.map(p => (
                  <tr key={p.product_id}>
                    <td style={{ fontWeight: 700 }}>{p.product_name}</td>
                    <td className="muted">{p.brand}</td>
                    <td><span className="chip">{p.category}</span></td>
                    <td className="num muted">{p.release_year}</td>
                    <td className="num muted">{p.mentions.toLocaleString("vi-VN")}</td>
                    <td><span className="chip pos">Đang hiển thị</span></td>
                    <td><div style={{ display: "flex", gap: 4 }}>
                      <button style={miniBtn}><Icon name="edit" size={15} /></button>
                      <button style={{ ...miniBtn, color: "var(--neg)" }}><Icon name="trash" size={15} /></button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination {...pgProd} />
        </div>
      ) : (
        /* ---- Kanban board ---- */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(210px, 1fr))", gap: 14, overflowX: "auto" }}>
          {KANBAN_COLS.map(col => {
            const cards   = requests.filter(r => r.status === col.id);
            const isOver  = dragOver === col.id;
            return (
              <div key={col.id}
                onDragEnter={() => setDragOver(col.id)}
                onDragOver={e  => e.preventDefault()}
                onDragLeave={e => { if (e.relatedTarget && !e.currentTarget.contains(e.relatedTarget)) setDragOver(null); }}
                onDrop={e => {
                  e.preventDefault();
                  if (dragId) updateRequest(dragId, { status: col.id });
                  setDragId(null); setDragOver(null);
                }}
                style={{
                  borderRadius: 14, padding: 14, minHeight: 200, transition: "all .15s",
                  background: isOver ? col.bgOver : col.bg,
                  border: "2px dashed " + (isOver ? col.border : "transparent"),
                }}
              >
                {/* Column header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 9, height: 9, borderRadius: "50%", background: col.dot, flexShrink: 0 }} />
                    <span style={{ fontWeight: 700, fontSize: 13.5 }}>{col.label}</span>
                  </div>
                  <span style={{ fontSize: 11.5, fontWeight: 800, minWidth: 22, height: 22, borderRadius: 99, display: "grid", placeItems: "center", color: col.dot, background: isOver ? "rgba(255,255,255,.7)" : "var(--surface)" }}>
                    {cards.length}
                  </span>
                </div>

                {/* Cards */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {cards.map(r => (
                    <div key={r.id}
                      draggable
                      onDragStart={e => { e.dataTransfer.effectAllowed = "move"; setDragId(r.id); }}
                      onDragEnd={() => { setDragId(null); setDragOver(null); }}
                      onClick={() => setModalId(r.id)}
                      style={{
                        background: "var(--surface)", borderRadius: 11, padding: "13px 14px",
                        border: "1px solid var(--border)", cursor: "grab",
                        boxShadow: "var(--shadow-sm)", opacity: dragId === r.id ? .3 : 1,
                        transition: "opacity .1s, box-shadow .14s, transform .14s",
                        userSelect: "none",
                      }}
                      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "var(--shadow-md)"; }}
                      onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "var(--shadow-sm)"; }}
                    >
                      <div style={{ fontSize: 11.5, fontWeight: 700, color: col.dot, marginBottom: 5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {r.product}
                      </div>
                      <div style={{ fontSize: 13.5, fontWeight: 700, lineHeight: 1.35, color: "var(--text)", marginBottom: 8 }}>
                        {r.title}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 11.5, color: "var(--text-3)", fontWeight: 600 }}>{r.by_name}</span>
                        <span style={{ fontSize: 11, color: "var(--text-3)" }}>{r.created_at}</span>
                      </div>
                    </div>
                  ))}
                  {cards.length === 0 && (
                    <div style={{ padding: "28px 0", textAlign: "center", color: "var(--text-3)", fontSize: 12.5, fontWeight: 500 }}>
                      Chưa có phiếu
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {modalRequest && (
        <EditRequestModal
          request={modalRequest}
          onClose={() => setModalId(null)}
          onSave={(id, changes) => { updateRequest(id, changes); setModalId(null); }}
        />
      )}
    </div>
  );
}

/* ---------------- Pipeline Health ---------------- */
const PIPELINE_DAGS = [
  { id: "youtube_daily_extraction_dag", label: "Thu thập video YouTube",  desc: "ELT extract + dbt staging" },
  { id: "sentiment_analysis_dag",       label: "Phân tích cảm xúc NLP",   desc: "PhoBERT + vELECTRA batch" },
  { id: "analytics_dag",                label: "Tính toán Analytics",      desc: "Bayesian ranking + controversy" },
  { id: "dbt_transform_dag",            label: "Biến đổi dữ liệu (dbt)",   desc: "Toàn bộ dbt models" },
];

function PipelinePage() {
  const P = window.DATA.PIPELINE;
  const tasks = window.DATA.DAG_TASKS;
  const [selectedDag, setSelectedDag] = useStateA("youtube_daily_extraction_dag");
  const [triggerStatus, setTriggerStatus] = useStateA(null);

  const doTrigger = () => {
    setTriggerStatus("loading");
    setTimeout(() => {
      setTriggerStatus("success");
      setTimeout(() => setTriggerStatus(null), 4500);
    }, 1600);
  };

  const selectedInfo = PIPELINE_DAGS.find(d => d.id === selectedDag);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PageHead title="Tình trạng Pipeline" sub="Giám sát sức khỏe Airflow, hạn ngạch API và batch NLP gần nhất." />

      {/* KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 14 }}>
        <div className="card" style={{ padding: 20 }}>
          <div className="faint" style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Airflow Webserver</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}><span style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--pos)", animation: "pulseDot 1.4s infinite" }} /><span style={{ fontWeight: 700, fontSize: 18 }}>Hoạt động tốt</span></div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="faint" style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Airflow Scheduler</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}><span style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--pos)", animation: "pulseDot 1.4s infinite" }} /><span style={{ fontWeight: 700, fontSize: 18 }}>Hoạt động tốt</span></div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="faint" style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Hạn ngạch YouTube API</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}><span className="num" style={{ fontWeight: 700, fontSize: 22 }}>{P.quotaUsed.toLocaleString("vi-VN")}</span><span className="faint">/ {P.quotaLimit.toLocaleString("vi-VN")}</span></div>
          <div style={{ height: 8, borderRadius: 99, background: "var(--surface-3)", marginTop: 10, overflow: "hidden" }}><div style={{ width: (P.quotaUsed / P.quotaLimit * 100) + "%", height: "100%", background: "var(--neu)", borderRadius: 99 }} /></div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="faint" style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>NLP Fallback Rate</div>
          <div className="num" style={{ fontWeight: 700, fontSize: 22, color: "var(--pos)" }}>{P.nlpFallback}%</div>
          <div className="faint" style={{ fontSize: 12, marginTop: 6 }}>batch {P.lastBatch}</div>
        </div>
      </div>

      {/* DAG Trigger */}
      <div className="card" style={{ padding: 22 }}>
        <div style={{ marginBottom: 18 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Kích hoạt DAG thủ công</h3>
          <p className="faint" style={{ margin: 0, fontSize: 12.5 }}>Trigger một DAG run ngay lập tức qua Airflow REST API.</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 18, alignItems: "start" }} className="analytics-grid">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {PIPELINE_DAGS.map(d => (
              <label key={d.id} onClick={() => setSelectedDag(d.id)} style={{
                display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: 11,
                cursor: "pointer", transition: "all .14s",
                background: selectedDag === d.id ? "var(--primary-soft)" : "var(--surface-2)",
                border: "1px solid " + (selectedDag === d.id ? "var(--primary)" : "transparent"),
              }}>
                <input type="radio" name="pipeline_dag" value={d.id} checked={selectedDag === d.id}
                  onChange={() => setSelectedDag(d.id)}
                  style={{ accentColor: "var(--primary)", width: 16, height: 16, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: selectedDag === d.id ? "var(--primary)" : "var(--text)" }}>{d.label}</div>
                  <div style={{ fontSize: 12, fontFamily: "var(--font-num)", color: "var(--text-3)", marginTop: 2 }}>{d.id}</div>
                </div>
                <span className="faint" style={{ fontSize: 12, flexShrink: 0 }}>{d.desc}</span>
              </label>
            ))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 190 }}>
            <button className="btn btn-primary" disabled={triggerStatus === "loading"} onClick={doTrigger}
              style={{ width: "100%", padding: "12px 18px" }}>
              {triggerStatus === "loading"
                ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Đang trigger...</>
                : <><Icon name="play-circle" size={16} />Trigger DAG</>}
            </button>
            <div style={{ padding: "12px 14px", borderRadius: 10, background: "var(--surface-2)", fontSize: 12.5 }}>
              <div className="faint" style={{ fontWeight: 600, marginBottom: 5 }}>DAG đã chọn</div>
              <div style={{ fontWeight: 700, color: "var(--primary)", marginBottom: 3 }}>{selectedInfo?.label}</div>
              <div className="faint" style={{ fontSize: 11.5, fontFamily: "var(--font-num)", wordBreak: "break-all" }}>{selectedDag}</div>
            </div>
            {triggerStatus === "success" && (
              <div style={{ padding: "11px 14px", borderRadius: 10, background: "var(--pos-soft)", color: "var(--pos)", fontWeight: 600, fontSize: 13, display: "flex", gap: 8, alignItems: "center" }}>
                <Icon name="check" size={16} />Run đã được tạo!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Task progress */}
      <div className="card" style={{ padding: 22 }}>
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Tiến trình DAG hiện tại</h3>
          <p className="faint" style={{ margin: 0, fontSize: 12.5 }}>youtube_daily_extraction_dag · lần chạy gần nhất.</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {tasks.map((t, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 14px", borderRadius: 10, background: "var(--surface-2)" }}>
              <span style={{ width: 26, height: 26, borderRadius: 8, display: "grid", placeItems: "center", color: "#fff",
                background: t.state === "success" ? "var(--pos)" : t.state === "running" ? "var(--primary)" : "var(--text-3)" }}>
                {t.state === "success" ? <Icon name="check" size={14} /> : t.state === "running" ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : <Icon name="clock" size={14} />}
              </span>
              <span style={{ flex: 1, fontWeight: 600, fontSize: 14, fontFamily: "var(--font-num)" }}>{t.task}</span>
              <span className="faint num" style={{ fontSize: 12.5 }}>{t.dur ? t.dur + "s" : "—"}</span>
              {stateChip(t.state)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- DAG Runs ---------------- */
function DagsPage() {
  const runs = window.DATA.DAG_RUNS;
  return (
    <div>
      <PageHead title="Lịch sử DAG Runs" sub="Lịch sử các lần chạy pipeline điều phối bởi Airflow."
        action={<button className="btn btn-soft"><Icon name="refresh" size={16} />Làm mới</button>} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 14, marginBottom: 18 }}>
        {[["Thành công", runs.filter(r => r.state === "success").length, "var(--pos)"], ["Đang chạy", runs.filter(r => r.state === "running").length, "var(--primary)"], ["Đang chờ", runs.filter(r => r.state === "queued").length, "var(--neu)"], ["Thất bại", runs.filter(r => r.state === "failed").length, "var(--neg)"]].map(([l, v, c]) => (
          <div key={l} className="card" style={{ padding: 16 }}>
            <div className="num" style={{ fontSize: 26, fontWeight: 700, color: c }}>{v}</div>
            <div className="muted" style={{ fontSize: 13, fontWeight: 600 }}>{l}</div>
          </div>
        ))}
      </div>
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>DAG</th><th>Run ID</th><th>Bắt đầu</th><th>Thời lượng</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>
              {runs.map((r, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 700, fontFamily: "var(--font-num)", fontSize: 13 }}>{r.dag}</td>
                  <td className="muted mono" style={{ fontSize: 12 }}>{r.run}</td>
                  <td className="num muted" style={{ fontSize: 13 }}>{r.start || "—"}</td>
                  <td className="num muted">{r.dur ? Math.floor(r.dur / 60) + "m " + (r.dur % 60) + "s" : "—"}</td>
                  <td>{stateChip(r.state)}</td>
                  <td><button style={miniBtn}><Icon name="external" size={15} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Operational Metrics ---------------- */
function OpsPage() {
  const P = window.DATA.PIPELINE;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PageHead title="Chỉ số vận hành" sub="Thông lượng thu thập, độ trễ và độ chính xác mô hình NLP theo thời gian." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 14 }}>
        <KpiCard icon="play" label="Video / ngày" value={P.videosToday} trend={4.2} accent="var(--primary)" />
        <KpiCard icon="bell" label="Bình luận / ngày" value={(P.commentsToday / 1000).toFixed(1) + "K"} trend={6.8} accent="var(--v-400)" />
        <KpiCard icon="gauge" label="Độ trễ pipeline" value="2.1s" trend={-3.4} accent="var(--pos)" />
        <KpiCard icon="spark" label="Độ chính xác NLP" value="97.7%" trend={1.2} accent="var(--neu)" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }} className="analytics-grid">
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Thông lượng thu thập</h3>
          <p className="faint" style={{ margin: "0 0 8px", fontSize: 12.5 }}>Số bình luận xử lý mỗi ngày (nghìn) · 15 ngày.</p>
          <AreaChart series={window.DATA.OPS_SERIES.map((v, i) => ({ label: (i + 1) % 3 === 1 ? (i + 1) + "" : "", value: v / 100 }))} height={240} color="var(--primary)" />
        </div>
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Độ chính xác mô hình NLP</h3>
          <p className="faint" style={{ margin: "0 0 8px", fontSize: 12.5 }}>Tỉ lệ dự đoán đúng của PhoBERT / vELECTRA (%).</p>
          <AreaChart series={window.DATA.NLP_SERIES.map((v, i) => ({ label: (i + 1) % 3 === 1 ? (i + 1) + "" : "", value: v / 100 }))} height={240} color="var(--pos)" />
        </div>
      </div>
    </div>
  );
}

/* ---------- Pagination ---------- */
const pgBtnStyle = (disabled, active) => ({
  width: 32, height: 32, borderRadius: 8,
  border: "1px solid " + (active ? "var(--primary)" : "var(--border)"),
  background: active ? "var(--primary)" : "var(--surface)",
  color: active ? "var(--on-primary)" : disabled ? "var(--text-3)" : "var(--text-2)",
  cursor: disabled ? "default" : "pointer",
  fontSize: 13, fontWeight: 700, display: "grid", placeItems: "center",
  opacity: disabled ? 0.45 : 1, fontFamily: "var(--font-ui)", transition: "all .12s",
});

function pgRange(cur, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (cur <= 4)         return [1, 2, 3, 4, 5, "…", total];
  if (cur >= total - 3) return [1, "…", total-4, total-3, total-2, total-1, total];
  return [1, "…", cur-1, cur, cur+1, "…", total];
}

function usePagination(items, size) {
  size = size || 10;
  const [page, setPage] = React.useState(1);
  const totalPages = Math.max(1, Math.ceil(items.length / size));
  const p = Math.min(page, totalPages);
  const from = items.length ? (p - 1) * size + 1 : 0;
  const to   = Math.min(p * size, items.length);
  return { page: p, setPage, totalPages, paged: items.slice((p-1)*size, p*size), total: items.length, from, to };
}

function Pagination({ page, totalPages, total, from, to, setPage }) {
  if (total === 0) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 18px", borderTop: "1px solid var(--border)", gap: 12, flexWrap: "wrap" }}>
      <span style={{ fontSize: 12.5, color: "var(--text-3)", fontWeight: 500 }}>
        Hiển thị {from}–{to} / <b style={{ color: "var(--text-2)", fontWeight: 700 }}>{total}</b> mục
      </span>
      {totalPages > 1 && (
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <button onClick={() => setPage(1)} disabled={page === 1} style={pgBtnStyle(page===1, false)} title="Trang đầu">«</button>
          <button onClick={() => setPage(function(p){ return Math.max(1, p-1); })} disabled={page === 1} style={pgBtnStyle(page===1, false)}>‹</button>
          {pgRange(page, totalPages).map(function(n, i) {
            return n === "…"
              ? <span key={"e"+i} style={{ width: 32, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>…</span>
              : <button key={n} onClick={() => setPage(n)} style={pgBtnStyle(false, n===page)}>{n}</button>;
          })}
          <button onClick={() => setPage(function(p){ return Math.min(totalPages, p+1); })} disabled={page===totalPages} style={pgBtnStyle(page===totalPages, false)}>›</button>
          <button onClick={() => setPage(totalPages)} disabled={page===totalPages} style={pgBtnStyle(page===totalPages, false)} title="Trang cuối">»</button>
        </div>
      )}
    </div>
  );
}

const miniBtn = { width: 32, height: 32, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-2)", cursor: "pointer", display: "grid", placeItems: "center" };

/* ---------------- Admin App shell ---------------- */
function AdminApp({ session, onLogout, onExit, theme, toggleTheme }) {
  const [page, setPage] = useStateA("overview");
  const [open, setOpen] = useStateA(false);
  const title = ADMIN_MENU.find(m => m.id === page)?.label || "";
  const pages = {
    overview: OverviewPage, channels: ChannelsPage, keywords: KeywordsPage,
    products: ProductsPage, pipeline: PipelinePage, dags: DagsPage, ops: OpsPage,
    aliases: window.AliasesPage, candidates: window.CandidatesPage,
    spec_templates: window.SpecTemplatesPage, accounts: window.AccountsPage,
  };
  const Page = pages[page];
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar page={page} setPage={setPage} open={open} setOpen={setOpen} />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <AdminHeader session={session} onLogout={onLogout} onExit={onExit} theme={theme} toggleTheme={toggleTheme} onMenu={() => setOpen(true)} title={title} />
        <main style={{ padding: 28, flex: 1 }}>
          <div key={page} className="fade-up"><Page /></div>
        </main>
      </div>
      <style>{`
        @media (max-width: 940px){
          .admin-sidebar{ position: fixed !important; left: 0; top: 0; z-index: 70; transform: translateX(-100%); transition: transform .25s ease; }
          .admin-sidebar.open{ transform: translateX(0); box-shadow: var(--shadow-lg); }
          .sidebar-scrim{ display: block !important; }
          .admin-menu-btn{ display: grid !important; }
          .analytics-grid{ grid-template-columns: 1fr !important; }
        }
        @media (max-width: 720px){
          .sys-status{ display:none !important; }
          .user-meta{ display:none !important; }
        }
      `}</style>
    </div>
  );
}

Object.assign(window, { AdminApp, PageHead, Toggle, miniBtn, iconBtnStyle, inputStyle, Pagination, usePagination });
