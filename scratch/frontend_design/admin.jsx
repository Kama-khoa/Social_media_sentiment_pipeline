/* ============================================================
   TechChoice — Admin dashboard layout (sidebar)
   exports: AdminApp
   ============================================================ */
const { useState: useStateA } = React;

const ADMIN_MENU = [
  { id: "overview", label: "Tổng quan phân tích", icon: "grid" },
  { id: "channels", label: "Quản lý kênh", icon: "broadcast" },
  { id: "keywords", label: "Quản lý từ khóa", icon: "tag" },
  { id: "products", label: "Quản lý sản phẩm", icon: "box" },
  { id: "pipeline", label: "Tình trạng Pipeline", icon: "heart" },
  { id: "dags", label: "Lịch sử DAG Runs", icon: "flow" },
  { id: "ops", label: "Chỉ số vận hành", icon: "activity" },
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
          <div className="faint" style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".06em", padding: "12px 12px 8px" }}>ĐIỀU HƯỚNG</div>
          {ADMIN_MENU.map(m => (
            <button key={m.id} onClick={() => { setPage(m.id); setOpen(false); }} style={{
              width: "100%", display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 10, border: "none", cursor: "pointer",
              fontSize: 14, fontWeight: 600, marginBottom: 2, textAlign: "left", transition: "all .14s", position: "relative",
              background: page === m.id ? "var(--primary-soft)" : "transparent", color: page === m.id ? "var(--primary)" : "var(--text-2)",
            }}
              onMouseEnter={e => { if (page !== m.id) e.currentTarget.style.background = "var(--surface-3)"; }}
              onMouseLeave={e => { if (page !== m.id) e.currentTarget.style.background = "transparent"; }}>
              {page === m.id && <span style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 3, borderRadius: 3, background: "var(--primary)" }} />}
              <Icon name={m.icon} size={18} />{m.label}
            </button>
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
        <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 700 }}>Top sản phẩm theo điểm Bayesian</h3>
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
  return (
    <div>
      <PageHead title="Quản lý kênh" sub={rows.length + " kênh YouTube đang được giám sát thu thập dữ liệu."}
        action={<button className="btn btn-primary"><Icon name="plus" size={16} />Thêm kênh</button>} />
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>Kênh</th><th>Handle</th><th>Người đăng ký</th><th>Video</th><th>Quét lịch sử</th><th>Hoạt động</th><th></th></tr></thead>
            <tbody>
              {rows.map((c, i) => (
                <tr key={c.id}>
                  <td><div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 32, height: 32, borderRadius: 9, background: "var(--surface-3)", display: "grid", placeItems: "center", color: "var(--primary)" }}><Icon name="broadcast" size={16} /></span>
                    <span style={{ fontWeight: 700 }}>{c.name}</span></div></td>
                  <td className="muted mono" style={{ fontSize: 13 }}>{c.handle}</td>
                  <td className="num">{(c.subs / 1e6).toFixed(2)}M</td>
                  <td className="num muted">{c.videos}</td>
                  <td>{c.scanned ? <span className="chip pos"><Icon name="check" size={12} />Đã quét</span> : <span className="chip neu">Chưa quét</span>}</td>
                  <td><Toggle on={c.active} onClick={() => setRows(r => r.map((x, j) => j === i ? { ...x, active: !x.active } : x))} /></td>
                  <td><div style={{ display: "flex", gap: 4 }}>
                    <button style={miniBtn}><Icon name="edit" size={15} /></button>
                    <button style={{ ...miniBtn, color: "var(--neg)" }}><Icon name="trash" size={15} /></button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Keywords ---------------- */
function KeywordsPage() {
  const [rows, setRows] = useStateA(window.DATA.KEYWORDS.map(k => ({ ...k })));
  const [text, setText] = useStateA("");
  const add = () => { if (!text.trim()) return; setRows(r => [{ id: "k" + Date.now(), text: text.trim(), cluster: "mới", active: true, hits: 0 }, ...r]); setText(""); };
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
              {rows.map((k, i) => (
                <tr key={k.id}>
                  <td><span style={{ fontWeight: 700, fontFamily: "var(--font-num)" }}>{k.text}</span></td>
                  <td><span className="chip">{k.cluster}</span></td>
                  <td className="num muted">{k.hits.toLocaleString("vi-VN")}</td>
                  <td><Toggle on={k.active} onClick={() => setRows(r => r.map((x, j) => j === i ? { ...x, active: !x.active } : x))} /></td>
                  <td><button style={{ ...miniBtn, color: "var(--neg)" }} onClick={() => setRows(r => r.filter((_, j) => j !== i))}><Icon name="trash" size={15} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Products + moderation ---------------- */
function ProductsPage() {
  const [tab, setTab] = useStateA("catalog");
  const products = window.DATA.PRODUCTS;
  const [requests, setRequests] = useStateA([
    { id: "r1", product: "iPhone 17 Pro Max", by: "user@example.com", field: '{"Sạc": "45W có dây"}', status: "pending" },
    { id: "r2", product: "Galaxy S25 Ultra", by: "minhtri@gmail.com", field: '{"Trọng lượng": "218 g"}', status: "pending" },
    { id: "r3", product: "MacBook Air M4", by: "haiyen@gmail.com", field: '{"Màu sắc": "Xanh skyblue"}', status: "pending" },
  ]);
  const review = (id, st) => setRequests(r => r.map(x => x.id === id ? { ...x, status: st } : x));
  return (
    <div>
      <PageHead title="Quản lý sản phẩm" sub="Catalog sản phẩm, alias và phiếu đề xuất chỉnh sửa thông số chờ duyệt."
        action={<button className="btn btn-primary"><Icon name="plus" size={16} />Thêm sản phẩm</button>} />
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {[["catalog", "Danh mục sản phẩm"], ["requests", `Phiếu chờ duyệt (${requests.filter(r => r.status === "pending").length})`]].map(([id, l]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "8px 16px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13.5, fontWeight: 600,
            background: tab === id ? "var(--primary)" : "var(--surface)", color: tab === id ? "var(--on-primary)" : "var(--text-2)", boxShadow: tab === id ? "none" : "var(--shadow-sm)",
          }}>{l}</button>
        ))}
      </div>
      {tab === "catalog" ? (
        <div className="card" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead><tr><th>Sản phẩm</th><th>Thương hiệu</th><th>Danh mục</th><th>Năm</th><th>Đề cập</th><th>Trạng thái</th><th></th></tr></thead>
              <tbody>
                {products.map(p => (
                  <tr key={p.product_id}>
                    <td style={{ fontWeight: 700 }}>{p.product_name}</td>
                    <td className="muted">{p.brand}</td>
                    <td><span className="chip">{p.category}</span></td>
                    <td className="num muted">{p.release_year}</td>
                    <td className="num muted">{p.mentions.toLocaleString("vi-VN")}</td>
                    <td><span className="chip pos">Đang hiển thị</span></td>
                    <td><div style={{ display: "flex", gap: 4 }}>
                      <button style={miniBtn}><Icon name="edit" size={15} /></button>
                      <button style={{ ...miniBtn, color: "var(--neg)" }}><Icon name="trash" size={15} /></button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {requests.map(r => (
            <div key={r.id} className="card" style={{ padding: 18, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 260px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontWeight: 700, fontSize: 15 }}>{r.product}</span>
                  {r.status === "pending" ? <span className="chip neu">Chờ duyệt</span> : r.status === "approved" ? <span className="chip pos">Đã duyệt</span> : <span className="chip neg">Đã từ chối</span>}
                </div>
                <div className="faint" style={{ fontSize: 12.5, marginBottom: 6 }}>Đề xuất bởi {r.by}</div>
                <code style={{ fontSize: 12.5, background: "var(--code-bg)", padding: "5px 9px", borderRadius: 7, color: "var(--primary)", fontFamily: "var(--font-num)" }}>{r.field}</code>
              </div>
              {r.status === "pending" && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn" style={{ background: "var(--pos)", color: "#fff" }} onClick={() => review(r.id, "approved")}><Icon name="check" size={16} />Duyệt</button>
                  <button className="btn btn-ghost" onClick={() => review(r.id, "rejected")}><Icon name="close" size={16} />Từ chối</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- Pipeline Health ---------------- */
function PipelinePage() {
  const P = window.DATA.PIPELINE;
  const tasks = window.DATA.DAG_TASKS;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PageHead title="Tình trạng Pipeline" sub="Giám sát sức khỏe Airflow, hạn ngạch API và batch NLP gần nhất." />
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
      <div className="card" style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <div><h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>DAG đang chạy · youtube_daily_extraction_dag</h3>
            <p className="faint" style={{ margin: "4px 0 0", fontSize: 12.5 }}>Tiến trình các task trong lần chạy hiện tại.</p></div>
          <button className="btn btn-soft"><Icon name="refresh" size={16} />Trigger lại</button>
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

const miniBtn = { width: 32, height: 32, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-2)", cursor: "pointer", display: "grid", placeItems: "center" };

/* ---------------- Admin App shell ---------------- */
function AdminApp({ session, onLogout, onExit, theme, toggleTheme }) {
  const [page, setPage] = useStateA("overview");
  const [open, setOpen] = useStateA(false);
  const title = ADMIN_MENU.find(m => m.id === page)?.label || "";
  const pages = { overview: OverviewPage, channels: ChannelsPage, keywords: KeywordsPage, products: ProductsPage, pipeline: PipelinePage, dags: DagsPage, ops: OpsPage };
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

Object.assign(window, { AdminApp });
