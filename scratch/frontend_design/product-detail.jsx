/* ============================================================
   TechChoice — Product Detail page
   exports: ProductDetail
   ============================================================ */
function ProductDetail({ id, session, onBack, onAuth }) {
  const p = window.DATA.findProduct(id);
  const [loading, setLoading] = React.useState(true);
  const [section, setSection] = React.useState("analytics");
  const [saved, setSaved] = React.useState(false);
  const [proposalSent, setProposalSent] = React.useState(false);
  React.useEffect(() => { setLoading(true); const t = setTimeout(() => setLoading(false), 550); return () => clearTimeout(t); }, [id]);

  if (!p) return null;

  if (loading) {
    return (
      <div style={{ maxWidth: 1120, margin: "0 auto", padding: "32px 24px", display: "grid", placeItems: "center", minHeight: 400 }}>
        <div className="spinner" />
      </div>
    );
  }

  const overallNeu = Math.max(0, 100 - p.pos - p.neg);
  const markers = p.attribution.events.map(ev => {
    const m = +ev.date.slice(5, 7);
    return { index: Math.min(11, m - 1), dir: ev.dir };
  });
  const comments = window.DATA.COMMENTS;
  const groups = [
    { key: "Tích cực", cls: "pos", color: "var(--pos)" },
    { key: "Tiêu cực", cls: "neg", color: "var(--neg)" },
    { key: "Trung lập", cls: "neu", color: "var(--neu)" },
  ];

  const sections = [
    { id: "analytics", label: "Phân tích", icon: "activity" },
    { id: "specs", label: "Thông số kỹ thuật", icon: "spec" },
    { id: "timeline", label: "Dòng thời gian", icon: "clock" },
    { id: "comments", label: "Bình luận (9)", icon: "bell" },
  ];

  return (
    <div style={{ maxWidth: 1120, margin: "0 auto", padding: "28px 24px 80px" }} className="fade-in">
      <button onClick={onBack} style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none", color: "var(--text-2)", fontSize: 14, fontWeight: 600, cursor: "pointer", marginBottom: 18 }}>
        <Icon name="chevron" size={16} style={{ transform: "rotate(90deg)" }} /> Quay lại danh sách
      </button>

      {/* Header */}
      <div className="card" style={{ padding: 26, marginBottom: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 320px" }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
              <span className="chip brand">{p.category}</span>
              <span className="chip">{p.brand}</span>
              {controversyChip(p.controversy)}
              <span className="chip">{p.release_year}</span>
            </div>
            <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, letterSpacing: "-.02em" }}>{p.product_name}</h1>
            <p className="muted" style={{ fontSize: 14.5, marginTop: 8, maxWidth: 560, lineHeight: 1.55 }}>{p.desc}</p>
            <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
              <button className="btn btn-soft" onClick={() => session ? setSaved(s => !s) : onAuth("login")}>
                <Icon name="heart" size={16} />{saved ? "Đã lưu" : "Lưu sản phẩm"}
              </button>
              <button className="btn btn-ghost"><Icon name="external" size={16} />Trang chính thức</button>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, minWidth: 200 }}>
            <ScoreRing score={p.score} size={104} />
            <div style={{ textAlign: "center" }}>
              <div className="num" style={{ fontWeight: 700, fontSize: 15 }}>{p.mentions.toLocaleString("vi-VN")}</div>
              <div className="faint" style={{ fontSize: 12 }}>lượt đề cập đã phân tích</div>
            </div>
          </div>
        </div>
        <div style={{ marginTop: 18 }}>
          <SentimentBar pos={p.pos} neg={p.neg} height={12} />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 13, fontWeight: 600 }}>
            <span style={{ color: "var(--pos)" }}>{p.pos}% tích cực</span>
            <span style={{ color: "var(--neu)" }}>{overallNeu}% trung lập</span>
            <span style={{ color: "var(--neg)" }}>{p.neg}% tiêu cực</span>
          </div>
        </div>
      </div>

      {/* Section tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 18, position: "sticky", top: 72, zIndex: 20, background: "var(--nav-bg)", backdropFilter: "blur(12px)", padding: 6, borderRadius: 14, border: "1px solid var(--border)", flexWrap: "wrap" }}>
        {sections.map(s => (
          <button key={s.id} onClick={() => setSection(s.id)} style={{
            display: "flex", alignItems: "center", gap: 7, padding: "9px 15px", borderRadius: 9, border: "none", cursor: "pointer",
            fontSize: 14, fontWeight: 600, background: section === s.id ? "var(--primary)" : "transparent", color: section === s.id ? "var(--on-primary)" : "var(--text-2)", transition: "all .15s",
          }}><Icon name={s.icon} size={16} />{s.label}</button>
        ))}
      </div>

      {/* ANALYTICS */}
      {section === "analytics" && (
        <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 14 }}>
            <KpiCard icon="gauge" label="Điểm Bayesian" value={(p.score * 100).toFixed(1)} sub="trên thang 100" accent="var(--primary)" />
            <KpiCard icon="heart" label="Tỉ lệ tích cực" value={p.pos + "%"} trend={p.trend} accent="var(--pos)" />
            <KpiCard icon="bell" label="Tổng đề cập" value={(p.mentions / 1000).toFixed(1) + "K"} sub="12 tháng gần nhất" accent="var(--v-400)" />
            <KpiCard icon="activity" label="Mức tranh cãi" value={({ low: "Thấp", medium: "Vừa", high: "Cao" })[p.controversy]} sub="chỉ số controversy" accent="var(--neu)" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: 18 }} className="analytics-grid">
            <div className="card" style={{ padding: 22 }}>
              <h3 style={{ margin: "0 0 4px", fontSize: 16.5, fontWeight: 700 }}>Đánh giá theo 6 khía cạnh</h3>
              <p className="faint" style={{ margin: "0 0 8px", fontSize: 13 }}>Tỉ lệ cảm xúc tích cực ở từng khía cạnh sản phẩm.</p>
              <RadarChart aspects={p.aspects} size={320} />
            </div>
            <div className="card" style={{ padding: 22, display: "flex", flexDirection: "column" }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 16.5, fontWeight: 700 }}>Phân bổ cảm xúc</h3>
              <div style={{ display: "grid", placeItems: "center", marginBottom: 14 }}>
                <Donut pos={p.pos} neg={p.neg} neu={overallNeu} size={150} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[["Tích cực", p.pos, "var(--pos)"], ["Trung lập", overallNeu, "var(--neu)"], ["Tiêu cực", p.neg, "var(--neg)"]].map(([l, v, c]) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: c }} />
                    <span style={{ flex: 1, fontSize: 13.5, fontWeight: 600 }}>{l}</span>
                    <span className="num" style={{ fontWeight: 700 }}>{v}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card" style={{ padding: 22 }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 16.5, fontWeight: 700 }}>Chi tiết theo khía cạnh</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 16 }}>
              {p.aspects.map(a => (
                <div key={a.aspect_label} style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5 }}>
                    <span style={{ fontWeight: 700 }}>{a.aspect_label}</span>
                    <span className="faint num">{a.total_mentions.toLocaleString("vi-VN")} đề cập</span>
                  </div>
                  <SentimentBar pos={a.positive_pct} neg={a.negative_pct} neu={a.neutral_pct} height={8} />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5 }}>
                    <span style={{ color: "var(--pos)", fontWeight: 600 }}>{a.positive_pct}%</span>
                    <span style={{ color: "var(--neg)", fontWeight: 600 }}>{a.negative_pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SPECS */}
      {section === "specs" && (
        <div className="fade-in analytics-grid" style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18 }}>
          <div className="card" style={{ padding: 22 }}>
            <h3 style={{ margin: "0 0 4px", fontSize: 16.5, fontWeight: 700 }}>Thông số thiết bị</h3>
            <p className="faint" style={{ margin: "0 0 16px", fontSize: 13 }}>Thông tin kỹ thuật chính thức của {p.product_name}.</p>
            <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
              {Object.entries(p.specs).map(([k, v], i) => (
                <div key={k} style={{ padding: "13px 4px", borderBottom: "1px solid var(--border)", gridColumn: k === "Màn hình" ? "1 / -1" : "auto" }}>
                  <dt className="faint" style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>{k}</dt>
                  <dd style={{ margin: 0, fontSize: 14.5, fontWeight: 700 }}>{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="card" style={{ padding: 22, background: "var(--primary-soft)", border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: 16.5, fontWeight: 700, color: "var(--primary)" }}>Đề xuất bổ sung thông số</h3>
            {session ? (
              proposalSent ? (
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: 14, background: "var(--surface)", borderRadius: 12, marginTop: 8 }}>
                  <span style={{ color: "var(--pos)" }}><Icon name="check" size={22} /></span>
                  <div><div style={{ fontWeight: 700, fontSize: 14 }}>Đã gửi đề xuất</div><div className="faint" style={{ fontSize: 12.5 }}>Đang chờ quản trị viên duyệt.</div></div>
                </div>
              ) : (
                <>
                  <p style={{ fontSize: 13.5, color: "var(--text-2)", marginTop: 4 }}>Bạn thấy thông số chưa chính xác? Gửi đề xuất chỉnh sửa để quản trị viên duyệt.</p>
                  <textarea placeholder='{"Pin": "5000 mAh"}' style={{ ...inputStyle, minHeight: 110, fontFamily: "var(--font-num)", marginTop: 6 }} />
                  <button className="btn btn-primary" style={{ width: "100%", marginTop: 10 }} onClick={() => setProposalSent(true)}>Gửi đề xuất</button>
                </>
              )
            ) : (
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <p className="muted" style={{ fontSize: 13.5 }}>Đăng nhập để gửi đề xuất bổ sung thông số sản phẩm.</p>
                <button className="btn btn-primary" onClick={() => onAuth("login")}>Đăng nhập</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TIMELINE */}
      {section === "timeline" && (
        <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="card" style={{ padding: 22 }}>
            <h3 style={{ margin: "0 0 4px", fontSize: 16.5, fontWeight: 700 }}>Dòng thời gian quy kết (PELT)</h3>
            <p className="faint" style={{ margin: "0 0 6px", fontSize: 13 }}>Diễn biến điểm cảm xúc theo tháng, đánh dấu các điểm thay đổi đột biến (change-point) gắn với sự kiện.</p>
            <div style={{ display: "flex", gap: 16, fontSize: 12, marginBottom: 6 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 12, height: 3, background: "var(--pos)", borderRadius: 2 }} />Sự kiện tích cực</span>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 12, height: 3, background: "var(--neg)", borderRadius: 2 }} />Sự kiện tiêu cực</span>
            </div>
            <AreaChart series={p.attribution.series} markers={markers} height={280} />
          </div>
          <div className="card" style={{ padding: 22 }}>
            <h3 style={{ margin: "0 0 18px", fontSize: 16.5, fontWeight: 700 }}>Sự kiện ảnh hưởng cảm xúc</h3>
            <div style={{ position: "relative", paddingLeft: 28 }}>
              <div style={{ position: "absolute", left: 9, top: 6, bottom: 6, width: 2, background: "var(--border)" }} />
              {p.attribution.events.map((ev, i) => (
                <div key={i} style={{ position: "relative", paddingBottom: i < p.attribution.events.length - 1 ? 22 : 0 }}>
                  <span style={{ position: "absolute", left: -27, top: 2, width: 20, height: 20, borderRadius: "50%", display: "grid", placeItems: "center",
                    background: ev.dir === "POSITIVE" ? "var(--pos)" : "var(--neg)", color: "#fff" }}>
                    <Icon name={ev.dir === "POSITIVE" ? "arrowUp" : "arrowDown"} size={12} />
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span className="num faint" style={{ fontSize: 12.5 }}>{ev.date}</span>
                    <span className={"chip " + (ev.dir === "POSITIVE" ? "pos" : "neg")} style={{ padding: "2px 9px" }}>{ev.dir === "POSITIVE" ? "Tích cực ↑" : "Tiêu cực ↓"}</span>
                    <span className="faint" style={{ fontSize: 12 }}>· {ev.channel} · {(ev.views / 1e6).toFixed(2)}M lượt xem</span>
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14.5, marginTop: 4 }}>{ev.title}</div>
                  <p className="muted" style={{ margin: "3px 0 0", fontSize: 13.5, lineHeight: 1.5 }}>{ev.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* COMMENTS */}
      {section === "comments" && (
        <div className="fade-in">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }} className="comments-grid">
            {groups.map(g => {
              const items = comments.filter(c => c.sentiment === g.key);
              return (
                <div key={g.key} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 9, height: 9, borderRadius: "50%", background: g.color }} />
                    <h3 style={{ margin: 0, fontSize: 15.5, fontWeight: 700 }}>{g.key}</h3>
                    <span className="faint" style={{ fontSize: 13 }}>({items.length})</span>
                  </div>
                  {items.map((c, i) => (
                    <div key={i} className="card" style={{ padding: 16, borderLeft: "3px solid " + g.color }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 9 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--surface-3)", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 12, color: "var(--text-2)" }}>{c.author.charAt(0)}</span>
                          <span style={{ fontSize: 13, fontWeight: 700 }}>{c.author}</span>
                        </div>
                        <span className={"chip " + g.cls} style={{ padding: "2px 8px", fontSize: 11 }}>{c.aspect}</span>
                      </div>
                      <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "var(--text)" }}>"{c.text}"</p>
                      <div className="faint" style={{ fontSize: 11.5, marginTop: 10, display: "flex", alignItems: "center", gap: 5 }}>
                        <Icon name="spark" size={12} />Độ tin cậy mô hình: <b className="num" style={{ color: g.color }}>{c.conf}%</b>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style>{`
        @media (max-width: 820px){
          .analytics-grid{ grid-template-columns: 1fr !important; }
          .comments-grid{ grid-template-columns: 1fr !important; }
        }
        .fade-in > * { }
      `}</style>
    </div>
  );
}

Object.assign(window, { ProductDetail });
