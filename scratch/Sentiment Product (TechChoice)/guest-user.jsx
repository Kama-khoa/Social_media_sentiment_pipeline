/* ============================================================
   TechChoice — Guest/User layout (top navbar app)
   exports: PublicApp
   ============================================================ */
const { useState: useStateP, useEffect: useEffectP, useRef: useRefP } = React;

/* ---------------- Top Navbar ---------------- */
function TopNav({ tab, setTab, session, onAuth, onLogout, onGoAdmin, theme, toggleTheme, savedCount = 0 }) {
  const [menuOpen, setMenuOpen] = useStateP(false);
  const [acctOpen, setAcctOpen] = useStateP(false);
  const [mobileOpen, setMobileOpen] = useStateP(false);
  const acctRef = useRefP(null);
  useEffectP(() => {
    function h(e) { if (acctRef.current && !acctRef.current.contains(e.target)) setAcctOpen(false); }
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);
  const tabs = [
    { id: "search", label: "Tìm kiếm", icon: "search" },
    { id: "top", label: "Top sản phẩm", icon: "trophy" },
    ...(session ? [{ id: "saved", label: savedCount > 0 ? "Đã lưu (" + savedCount + ")" : "Đã lưu", icon: "heart" }] : []),
  ];
  return (
    <header style={{
      position: "sticky", top: 0, zIndex: 50,
      background: "var(--nav-bg)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
      borderBottom: "1px solid var(--border)",
    }}>
      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 24px", height: 64, display: "flex", alignItems: "center", gap: 18 }}>
        {/* Logo */}
        <button onClick={() => setTab("top")} className="focusable" style={{ display: "flex", alignItems: "center", gap: 11, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
          <span style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center",
            background: "linear-gradient(135deg, var(--v-500), var(--v-700))", color: "#fff", boxShadow: "0 6px 14px -4px var(--ring)" }}>
            <Icon name="spark" size={19} />
          </span>
          <span style={{ fontWeight: 800, fontSize: 19, letterSpacing: "-.02em", color: "var(--text)" }}>
            Tech<span style={{ color: "var(--primary)" }}>Choice</span>
          </span>
        </button>

        {/* Center tabs (desktop) */}
        <nav className="nav-center" style={{ flex: 1, display: "flex", justifyContent: "center", gap: 6 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} className="focusable"
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "9px 18px", borderRadius: 11,
                fontSize: 14.5, fontWeight: 600, cursor: "pointer", border: "none", position: "relative",
                background: tab === t.id ? "var(--primary-soft)" : "transparent",
                color: tab === t.id ? "var(--primary)" : "var(--text-2)", transition: "all .15s",
              }}>
              <Icon name={t.icon} size={17} />{t.label}
            </button>
          ))}
        </nav>

        {/* Right: theme + account */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={toggleTheme} title="Đổi giao diện sáng/tối" className="focusable" style={iconBtnStyle}>
            <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
          </button>

          {!session ? (
            <div className="auth-buttons" style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-ghost" style={{ padding: "8px 16px" }} onClick={() => onAuth("login")}>Đăng nhập</button>
              <button className="btn btn-primary" style={{ padding: "8px 16px" }} onClick={() => onAuth("register")}>Đăng ký</button>
            </div>
          ) : (
            <div ref={acctRef} style={{ position: "relative" }} className="acct-wrap">
              <button onClick={() => setAcctOpen(o => !o)} className="focusable" style={{
                display: "flex", alignItems: "center", gap: 9, padding: "5px 11px 5px 5px", borderRadius: 99,
                border: "1px solid var(--border-strong)", background: "var(--surface)", cursor: "pointer", color: "var(--text)",
              }}>
                <span style={{ width: 30, height: 30, borderRadius: "50%", background: "linear-gradient(135deg,var(--v-400),var(--v-600))", color: "#fff", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 13 }}>
                  {session.name.charAt(0)}
                </span>
                <span className="acct-name" style={{ fontSize: 14, fontWeight: 600 }}>{session.name}</span>
                <Icon name="chevron" size={15} style={{ color: "var(--text-3)" }} />
              </button>
              {acctOpen && (
                <div className="card" style={{ position: "absolute", right: 0, top: "calc(100% + 10px)", width: 240, padding: 8, boxShadow: "var(--shadow-lg)", animation: "pop .15s ease both" }}>
                  <div style={{ padding: "10px 12px" }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{session.name}</div>
                    <div className="faint" style={{ fontSize: 12.5 }}>{session.email}</div>
                    <span className="chip brand" style={{ marginTop: 8 }}>{session.role === "admin" ? "Quản trị viên" : "Người dùng"}</span>
                  </div>
                  <hr className="divider" />
                  <DropItem icon="user" label="Tài khoản của tôi" onClick={() => { setAcctOpen(false); setTab("account"); }} />
                  <DropItem icon="heart" label={"Sản phẩm đã lưu" + (savedCount > 0 ? " (" + savedCount + ")" : "")} onClick={() => { setAcctOpen(false); setTab("saved"); }} />
                  {session.role === "admin" && (
                    <DropItem icon="grid" label="Trang quản trị" highlight onClick={() => { setAcctOpen(false); onGoAdmin(); }} />
                  )}
                  <hr className="divider" />
                  <DropItem icon="logout" label="Đăng xuất" danger onClick={() => { setAcctOpen(false); onLogout(); }} />
                </div>
              )}
            </div>
          )}

          {/* Mobile hamburger */}
          <button className="hamburger focusable" style={{ ...iconBtnStyle, display: "none" }} onClick={() => setMobileOpen(o => !o)}>
            <Icon name={mobileOpen ? "close" : "menu"} size={20} />
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="mobile-menu" style={{ borderTop: "1px solid var(--border)", padding: 12, display: "none", flexDirection: "column", gap: 4, background: "var(--surface)" }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => { setTab(t.id); setMobileOpen(false); }} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", borderRadius: 10, border: "none", textAlign: "left",
              background: tab === t.id ? "var(--primary-soft)" : "transparent", color: tab === t.id ? "var(--primary)" : "var(--text)", fontWeight: 600, fontSize: 15, cursor: "pointer",
            }}><Icon name={t.icon} size={18} />{t.label}</button>
          ))}
          {!session && (
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => { onAuth("login"); setMobileOpen(false); }}>Đăng nhập</button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => { onAuth("register"); setMobileOpen(false); }}>Đăng ký</button>
            </div>
          )}
        </div>
      )}
      <style>{`
        @media (max-width: 860px){
          .nav-center{ display:none !important; }
          .auth-buttons{ display:none !important; }
          .acct-name{ display:none !important; }
          .hamburger{ display:grid !important; }
          .mobile-menu{ display:flex !important; }
        }
      `}</style>
    </header>
  );
}

const iconBtnStyle = {
  width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center",
  background: "var(--surface)", border: "1px solid var(--border-strong)", color: "var(--text-2)", cursor: "pointer", transition: "all .15s",
};

function DropItem({ icon, label, danger, highlight, onClick }) {
  return (
    <button onClick={onClick} className="focusable" style={{
      width: "100%", display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 9,
      border: "none", background: "transparent", cursor: "pointer", textAlign: "left", fontSize: 14, fontWeight: 600,
      color: danger ? "var(--neg)" : highlight ? "var(--primary)" : "var(--text)",
    }}
      onMouseEnter={e => e.currentTarget.style.background = "var(--surface-3)"}
      onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
      <Icon name={icon} size={17} />{label}
    </button>
  );
}

/* ---------------- Product card ---------------- */
function ProductCard({ p, onOpen, idx }) {
  return (
    <button onClick={() => onOpen(p.product_id)} className="card focusable fade-up"
      style={{ padding: 18, textAlign: "left", cursor: "pointer", display: "flex", flexDirection: "column", gap: 14, border: "1px solid var(--border)" }}
      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "var(--shadow-md)"; e.currentTarget.style.borderColor = "var(--border-strong)"; }}
      onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "var(--shadow-sm)"; e.currentTarget.style.borderColor = "var(--border)"; }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            {p.rank <= 3 && <span className="num" style={{ fontWeight: 800, color: "var(--primary)", fontSize: 13 }}>#{p.rank}</span>}
            {p.hot && <span className="chip neg" style={{ padding: "2px 8px" }}>🔥 Nổi bật</span>}
          </div>
          <h3 style={{ margin: 0, fontSize: 16.5, fontWeight: 700, color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.product_name}</h3>
          <p className="faint" style={{ margin: "3px 0 0", fontSize: 13 }}>{p.brand} • {p.category}</p>
        </div>
        <ScoreRing score={p.score} size={64} />
      </div>
      <SentimentBar pos={p.pos} neg={p.neg} />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
        <span style={{ color: "var(--pos)", fontWeight: 600 }}>{p.pos}% tích cực</span>
        <span className="faint num">{p.mentions.toLocaleString("vi-VN")} đề cập</span>
        <span style={{ color: "var(--neg)", fontWeight: 600 }}>{p.neg}% tiêu cực</span>
      </div>
    </button>
  );
}

/* ---------------- Search page ---------------- */
function SearchPage({ onOpen }) {
  const [q, setQ] = useStateP("");
  const [cat, setCat] = useStateP("all");
  const [sort, setSort] = useStateP("score");
  const products = window.DATA.PRODUCTS.map((p, i) => ({ ...p, rank: i + 1 }));
  let list = products.filter(p =>
    (cat === "all" || p.category === ({ dien_thoai: "Điện thoại", laptop: "Laptop", tai_nghe: "Tai nghe" }[cat])) &&
    (q.trim() === "" || (p.product_name + " " + p.brand).toLowerCase().includes(q.toLowerCase())));
  list = [...list].sort((a, b) => sort === "score" ? b.score - a.score : sort === "mentions" ? b.mentions - a.mentions : b.pos - a.pos);
  const cats = window.DATA.CATEGORIES;
  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "40px 24px 80px" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <span className="chip brand" style={{ marginBottom: 14 }}><Icon name="spark" size={13} /> Phân tích cảm xúc từ cộng đồng YouTube Việt</span>
        <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-.03em", margin: "10px 0 6px", lineHeight: 1.1 }}>
          Tìm hiểu người dùng thực sự nghĩ gì?
        </h1>
        <p className="muted" style={{ fontSize: 16, maxWidth: 580, margin: "0 auto" }}>
          Đưa ra phân tích dựa trên bình luận và xếp hạng theo điểm tín nhiệm.
        </p>
      </div>

      {/* Search bar */}
      <div style={{ maxWidth: 720, margin: "0 auto 18px", display: "flex", alignItems: "center", gap: 10, background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 99, padding: "8px 8px 8px 20px", boxShadow: "var(--shadow-md)" }}>
        <Icon name="search" size={20} style={{ color: "var(--text-3)" }} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Tìm kiếm sản phẩm — vd: iPhone 17 Pro Max, Galaxy S25..."
          style={{ flex: 1, border: "none", background: "transparent", fontSize: 15.5, color: "var(--text)", outline: "none" }} />
        <button className="btn btn-primary" style={{ borderRadius: 99 }}>Tìm kiếm</button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap", marginBottom: 28 }}>
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap", justifyContent: "center" }}>
          {cats.map(c => (
            <button key={c.slug} onClick={() => setCat(c.slug)} style={{
              padding: "8px 15px", borderRadius: 99, fontSize: 13.5, fontWeight: 600, cursor: "pointer",
              border: "1px solid " + (cat === c.slug ? "transparent" : "var(--border-strong)"),
              background: cat === c.slug ? "var(--primary)" : "var(--surface)", color: cat === c.slug ? "var(--on-primary)" : "var(--text-2)", transition: "all .15s",
            }}>{c.label}</button>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-3)" }}>
          <Icon name="filter" size={15} />
          <select value={sort} onChange={e => setSort(e.target.value)} className="focusable" style={{
            border: "1px solid var(--border-strong)", background: "var(--surface)", color: "var(--text)", borderRadius: 99, padding: "8px 14px", fontSize: 13.5, fontWeight: 600, cursor: "pointer",
          }}>
            <option value="score">Điểm tín nhiệm cao nhất</option>
            <option value="mentions">Nhiều đề cập nhất</option>
            <option value="pos">Tích cực nhất</option>
          </select>
        </div>
      </div>

      <div className="muted" style={{ fontSize: 13.5, marginBottom: 14, fontWeight: 600 }}>{list.length} kết quả</div>
      {list.length ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 18 }}>
          {list.map((p, i) => <ProductCard key={p.product_id} p={p} onOpen={onOpen} idx={i} />)}
        </div>
      ) : (
        <div className="card" style={{ padding: 60, textAlign: "center", color: "var(--text-3)" }}>
          Không tìm thấy sản phẩm phù hợp với "{q}".
        </div>
      )}
    </div>
  );
}

/* ---------------- Top Products page ---------------- */
function TopProductsPage({ onOpen }) {
  const [cat, setCat] = useStateP("all");
  const cats = window.DATA.CATEGORIES;
  const products = window.DATA.PRODUCTS
    .filter(p => cat === "all" || p.category === ({ dien_thoai: "Điện thoại", laptop: "Laptop", tai_nghe: "Tai nghe" }[cat]))
    .map((p, i) => ({ ...p, rank: i + 1 }));
  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "40px 24px 80px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16, marginBottom: 8 }}>
        <div>
          <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.02em", margin: 0 }}>Bảng xếp hạng sản phẩm</h1>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 15 }}>Xếp hạng theo điểm tín nhiệm, cập nhật ngày 02/06/2026.</p>
        </div>
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
          {cats.map(c => (
            <button key={c.slug} onClick={() => setCat(c.slug)} style={{
              padding: "8px 15px", borderRadius: 99, fontSize: 13.5, fontWeight: 600, cursor: "pointer",
              border: "1px solid " + (cat === c.slug ? "transparent" : "var(--border-strong)"),
              background: cat === c.slug ? "var(--primary)" : "var(--surface)", color: cat === c.slug ? "var(--on-primary)" : "var(--text-2)",
            }}>{c.label}</button>
          ))}
        </div>
      </div>

      {/* category KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 14, margin: "24px 0 28px" }}>
        {cats.map(c => (
          <div key={c.slug} className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="muted" style={{ fontSize: 13, fontWeight: 600 }}>{c.label}</span>
            <span className="num" style={{ fontSize: 24, fontWeight: 700 }}>{c.mentions.toLocaleString("vi-VN")}</span>
            <span className="chip pos" style={{ alignSelf: "flex-start" }}><Icon name="arrowUp" size={11} />{c.change}% tuần</span>
          </div>
        ))}
      </div>

      {/* podium top 3 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 18, marginBottom: 22 }}>
        {products.slice(0, 3).map((p, i) => (
          <button key={p.product_id} onClick={() => onOpen(p.product_id)} className="card focusable fade-up"
            style={{ padding: 20, cursor: "pointer", textAlign: "left", borderTop: "3px solid " + ["#f5b50a", "#9aa3b2", "#cd7f32"][i] }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="num" style={{ fontSize: 34, fontWeight: 800, color: "var(--text-3)" }}>#{p.rank}</span>
              <ScoreRing score={p.score} size={72} />
            </div>
            <h3 style={{ margin: "10px 0 2px", fontSize: 18, fontWeight: 700 }}>{p.product_name}</h3>
            <p className="faint" style={{ margin: "0 0 12px", fontSize: 13 }}>{p.brand}</p>
            <SentimentBar pos={p.pos} neg={p.neg} />
          </button>
        ))}
      </div>

      {/* full table */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr>
              <th style={{ width: 56 }}>#</th><th>Sản phẩm</th><th>Thương hiệu</th>
              <th>Điểm tín nhiệm</th><th style={{ minWidth: 140 }}>Cảm xúc</th><th>Đề cập</th><th>Tranh cãi</th>
            </tr></thead>
            <tbody>
              {products.map(p => (
                <tr key={p.product_id} onClick={() => onOpen(p.product_id)} style={{ cursor: "pointer" }}>
                  <td className="num" style={{ fontWeight: 700, color: p.rank <= 3 ? "var(--primary)" : "var(--text-3)" }}>{p.rank}</td>
                  <td style={{ fontWeight: 700 }}>{p.product_name} {p.hot && <span style={{ fontSize: 12 }}>🔥</span>}</td>
                  <td className="muted">{p.brand}</td>
                  <td className="num" style={{ fontWeight: 700, color: "var(--primary)" }}>{(p.score * 100).toFixed(1)}</td>
                  <td><div style={{ minWidth: 120 }}><SentimentBar pos={p.pos} neg={p.neg} height={8} /></div></td>
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

/* ---------------- Saved Products page ---------------- */
function SavedProductsPage({ savedIds, onOpen, onToggleSave, onGoSearch, session, onAuth }) {
  const allProducts = window.DATA.PRODUCTS;
  const saved = allProducts
    .filter(p => savedIds.includes(p.product_id))
    .map(p => ({ ...p, rank: allProducts.findIndex(x => x.product_id === p.product_id) + 1 }));

  if (!session) {
    return (
      <div style={{ maxWidth: 520, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
        <div style={{ width: 72, height: 72, borderRadius: 20, background: "var(--surface-3)", display: "grid", placeItems: "center", margin: "0 auto 22px", color: "var(--text-3)" }}>
          <Icon name="heart" size={30} />
        </div>
        <h2 style={{ margin: "0 0 10px", fontSize: 24, fontWeight: 800, letterSpacing: "-.02em" }}>Lưu sản phẩm yêu thích</h2>
        <p className="muted" style={{ fontSize: 15, lineHeight: 1.6, marginBottom: 24 }}>
          Theo dõi điểm tín nhiệm và cảm xúc cộng đồng của các thiết bị bạn quan tâm.
        </p>
        <button className="btn btn-primary" onClick={() => onAuth("login")}>Đăng nhập để lưu</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "40px 24px 80px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 28 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, letterSpacing: "-.02em" }}>Sản phẩm đã lưu</h1>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 15 }}>
            {saved.length > 0 ? saved.length + " sản phẩm trong danh sách của bạn." : "Danh sách lưu trữ trống."}
          </p>
        </div>
      </div>
      {saved.length === 0 ? (
        <div className="card" style={{ padding: "60px 24px", textAlign: "center" }}>
          <div style={{ width: 60, height: 60, borderRadius: 18, background: "var(--surface-3)", display: "grid", placeItems: "center", margin: "0 auto 18px", color: "var(--text-3)" }}>
            <Icon name="heart" size={26} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 8 }}>Chưa có sản phẩm nào được lưu</div>
          <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>Nhấn "Lưu sản phẩm" ở trang chi tiết để thêm vào đây.</p>
          <button className="btn btn-primary" onClick={onGoSearch}>Khám phá sản phẩm</button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 18 }}>
          {saved.map((p, i) => (
            <div key={p.product_id} style={{ position: "relative", display: "flex", flexDirection: "column" }}>
              <ProductCard p={p} onOpen={onOpen} idx={i} />
              <button
                onClick={() => onToggleSave(p.product_id)}
                title="Bỏ lưu"
                style={{
                  position: "absolute", top: 10, right: 10, zIndex: 5,
                  width: 28, height: 28, borderRadius: 8, border: "none",
                  background: "var(--surface)", boxShadow: "var(--shadow-sm)",
                  cursor: "pointer", display: "grid", placeItems: "center",
                  color: "var(--neg)", transition: "all .15s",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--neg-soft)"}
                onMouseLeave={e => e.currentTarget.style.background = "var(--surface)"}
              >
                <Icon name="close" size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* Status helpers for edit requests */
const REQ_STATUS = {
  pending:    { label: "Đang chờ",     chip: "neu",   dot: "#d97706" },
  processing: { label: "Đang xử lý",  chip: "brand", dot: "var(--primary)" },
  accepted:   { label: "Đã tiếp nhận",chip: "pos",   dot: "var(--pos)" },
  rejected:   { label: "Đã từ chối",  chip: "neg",   dot: "var(--neg)" },
};

/* ---------------- My Account page ---------------- */
function AccountProfilePage({ session, onUpdateSession, onGoSaved, savedCount, onAuth, editRequests, onCancelEditRequest }) {
  const [displayName,      setDisplayName]      = useStateP(session?.name || "");
  const [nameSaved,        setNameSaved]        = useStateP(false);
  const [pwForm,           setPwForm]           = useStateP({ current: "", next: "", confirm: "" });
  const [pwMsg,            setPwMsg]            = useStateP(null);
  const [expandedReasonId, setExpandedReasonId] = useStateP(null);

  if (!session) {
    return (
      <div style={{ maxWidth: 520, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>
        <div style={{ width: 72, height: 72, borderRadius: 20, background: "var(--surface-3)", display: "grid", placeItems: "center", margin: "0 auto 22px", color: "var(--text-3)" }}>
          <Icon name="user" size={30} />
        </div>
        <h2 style={{ margin: "0 0 10px", fontSize: 24, fontWeight: 800 }}>Đăng nhập để xem tài khoản</h2>
        <button className="btn btn-primary" onClick={() => onAuth("login")}>Đăng nhập</button>
      </div>
    );
  }

  const myRequests     = (editRequests || []).filter(r => r.by_email === session.email);
  const pendingReqCnt  = myRequests.filter(r => r.status === "pending").length;

  const saveName = () => {
    if (!displayName.trim()) return;
    onUpdateSession({ ...session, name: displayName.trim() });
    setNameSaved(true);
    setTimeout(() => setNameSaved(false), 2200);
  };

  const changePw = (e) => {
    e.preventDefault();
    if (!pwForm.current) { setPwMsg({ ok: false, text: "Nhập mật khẩu hiện tại." }); return; }
    if (pwForm.next.length < 8) { setPwMsg({ ok: false, text: "Mật khẩu mới tối thiểu 8 ký tự." }); return; }
    if (pwForm.next !== pwForm.confirm) { setPwMsg({ ok: false, text: "Xác nhận mật khẩu không khớp." }); return; }
    setPwMsg({ ok: true, text: "Đổi mật khẩu thành công!" });
    setPwForm({ current: "", next: "", confirm: "" });
    setTimeout(() => setPwMsg(null), 3000);
  };

  const fieldStyle  = { width: "100%", padding: "10px 13px", borderRadius: 9, border: "1px solid var(--border-strong)", background: "var(--surface)", color: "var(--text)", fontSize: 14, outline: "none", boxSizing: "border-box", fontFamily: "var(--font-ui)" };
  const sectionHead = { margin: "0 0 16px", fontSize: 11.5, fontWeight: 700, letterSpacing: ".07em", color: "var(--text-3)", textTransform: "uppercase" };

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "40px 24px 80px" }}>

      {/* Profile hero */}
      <div className="card" style={{ padding: 26, marginBottom: 16, display: "flex", gap: 22, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ width: 72, height: 72, borderRadius: "50%", flexShrink: 0,
          background: "linear-gradient(135deg,var(--v-400),var(--v-700))", color: "#fff",
          display: "grid", placeItems: "center", fontWeight: 800, fontSize: 30 }}>
          {session.name.charAt(0)}
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: "0 0 4px", fontSize: 24, fontWeight: 800, letterSpacing: "-.02em" }}>{session.name}</h1>
          <div className="faint" style={{ fontSize: 14, marginBottom: 10 }}>{session.email}</div>
          <span className={"chip " + (session.role === "admin" ? "brand" : "")}>
            {session.role === "admin" ? "Quản trị viên" : "Người dùng"}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
        <button className="card" onClick={onGoSaved}
          style={{ padding: "18px 22px", textAlign: "left", cursor: "pointer", background: "var(--surface)", border: "1px solid var(--border)", transition: "all .15s" }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.background = "var(--primary-soft)"; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--surface)"; }}>
          <div className="num" style={{ fontSize: 32, fontWeight: 700, color: "var(--primary)" }}>{savedCount}</div>
          <div className="muted" style={{ fontSize: 13.5, fontWeight: 600, marginTop: 4 }}>Sản phẩm đã lưu</div>
          <div className="faint" style={{ fontSize: 12, marginTop: 3 }}>Nhấn để xem danh sách →</div>
        </button>
        <div className="card" style={{ padding: "18px 22px" }}>
          <div className="num" style={{ fontSize: 32, fontWeight: 700, color: "var(--v-400)" }}>{myRequests.length}</div>
          <div className="muted" style={{ fontSize: 13.5, fontWeight: 600, marginTop: 4 }}>Đề xuất đã gửi</div>
          <div className="faint" style={{ fontSize: 12, marginTop: 3 }}>
            {pendingReqCnt > 0 ? pendingReqCnt + " đang chờ duyệt" : "Không có phiếu chờ"}
          </div>
        </div>
      </div>

      {/* Profile edit */}
      <div className="card" style={{ padding: 24, marginBottom: 14 }}>
        <h3 style={sectionHead}>Thông tin cá nhân</h3>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-3)", marginBottom: 7 }}>Email</div>
          <div style={{ ...fieldStyle, background: "var(--surface-2)", color: "var(--text-3)", cursor: "default" }}>{session.email}</div>
        </div>
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-3)", marginBottom: 7 }}>Tên hiển thị</div>
          <div style={{ display: "flex", gap: 10 }}>
            <input value={displayName} onChange={e => setDisplayName(e.target.value)}
              style={{ ...fieldStyle, flex: 1 }} />
            <button className="btn btn-primary" onClick={saveName} style={{ flexShrink: 0 }}>
              {nameSaved ? <><Icon name="check" size={16} />Đã lưu</> : "Lưu"}
            </button>
          </div>
        </div>
      </div>

      {/* Change password */}
      <div className="card" style={{ padding: 24, marginBottom: 14 }}>
        <h3 style={sectionHead}>Đổi mật khẩu</h3>
        <form onSubmit={changePw} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-3)", marginBottom: 7 }}>Mật khẩu hiện tại</div>
            <input type="password" value={pwForm.current}
              onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
              placeholder="••••••••" style={fieldStyle} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-3)", marginBottom: 7 }}>Mật khẩu mới</div>
              <input type="password" value={pwForm.next}
                onChange={e => setPwForm(f => ({ ...f, next: e.target.value }))}
                placeholder="Tối thiểu 8 ký tự" style={fieldStyle} />
            </div>
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-3)", marginBottom: 7 }}>Xác nhận mật khẩu</div>
              <input type="password" value={pwForm.confirm}
                onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                placeholder="Nhập lại mật khẩu mới" style={fieldStyle} />
            </div>
          </div>
          {pwMsg && (
            <div style={{ padding: "10px 14px", borderRadius: 9, fontWeight: 600, fontSize: 13.5, display: "flex", gap: 8, alignItems: "center",
              background: pwMsg.ok ? "var(--pos-soft)" : "var(--neg-soft)",
              color: pwMsg.ok ? "var(--pos)" : "var(--neg)" }}>
              <Icon name={pwMsg.ok ? "check" : "close"} size={16} />{pwMsg.text}
            </div>
          )}
          <button type="submit" className="btn btn-primary" style={{ alignSelf: "flex-start" }}>Đổi mật khẩu</button>
        </form>
      </div>

      {/* Edit requests list */}
      <div className="card" style={{ padding: 24 }}>
        <h3 style={{ ...sectionHead, marginBottom: myRequests.length ? 14 : 0 }}>Yêu cầu chỉnh sửa đã gửi</h3>
        {myRequests.length === 0 ? (
          <div style={{ padding: "20px 0", textAlign: "center", color: "var(--text-3)", fontSize: 13.5 }}>
            Chưa có yêu cầu nào.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {myRequests.map(r => {
              const st        = REQ_STATUS[r.status] || { label: r.status, chip: "" };
              const isExpanded = expandedReasonId === r.id;
              return (
                <div key={r.id}>
                  <div style={{ borderRadius: 11, border: "1px solid var(--border)", background: "var(--surface-2)", padding: "14px 16px" }}>

                    {/* Top row: product + status + date */}
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7, flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 700, fontSize: 13.5, flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {r.product}
                      </span>
                      <span className={"chip " + st.chip} style={{ flexShrink: 0 }}>{st.label}</span>
                      {r.status === "rejected" && r.reason && (
                        <button
                          onClick={() => setExpandedReasonId(isExpanded ? null : r.id)}
                          style={{ fontSize: 11.5, fontWeight: 700, padding: "3px 9px", borderRadius: 6,
                            border: "1px solid var(--neg)", color: "var(--neg)", background: "transparent",
                            cursor: "pointer", flexShrink: 0 }}>
                          Lý do {isExpanded ? "▲" : "▼"}
                        </button>
                      )}
                      <span className="faint" style={{ fontSize: 11.5, flexShrink: 0 }}>{r.created_at}</span>
                    </div>

                    {/* Title */}
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 7 }}>{r.title}</div>

                    {/* Content */}
                    <code style={{ fontSize: 12.5, background: "var(--code-bg)", padding: "5px 10px", borderRadius: 7,
                      color: "var(--primary)", fontFamily: "var(--font-num)", display: "block" }}>
                      {r.content}
                    </code>

                    {/* Cancel button — only when pending */}
                    {r.status === "pending" && (
                      <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => onCancelEditRequest(r.id)}
                          style={{ fontSize: 13, fontWeight: 600, padding: "7px 14px", borderRadius: 9,
                            border: "1px solid var(--neg)", color: "var(--neg)", background: "transparent",
                            cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                          <Icon name="close" size={14} />Hủy yêu cầu
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Reason expansion panel */}
                  {isExpanded && r.reason && (
                    <div style={{ padding: "11px 16px", borderRadius: "0 0 11px 11px", marginTop: -1,
                      background: "var(--neg-soft)", border: "1px solid var(--border)", borderTop: "none" }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--neg)", marginBottom: 4, textTransform: "uppercase", letterSpacing: ".04em" }}>
                        Lý do từ chối:
                      </div>
                      <div style={{ fontSize: 13.5, color: "var(--text)", lineHeight: 1.6 }}>{r.reason}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------------- Auth modal ---------------- */
function AuthModal({ mode, onClose, onSuccess }) {
  const [m, setM] = useStateP(mode);
  const [email, setEmail] = useStateP("user@example.com");
  const [pw, setPw] = useStateP("user1234");
  const [name, setName] = useStateP("");
  const submit = (e) => {
    e.preventDefault();
    const role = email.startsWith("admin") ? "admin" : "user";
    const display = m === "register" ? (name || email.split("@")[0]) : (role === "admin" ? "Quản trị viên" : "Người dùng");
    onSuccess({ email, name: display, role });
  };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(20,12,40,.5)", backdropFilter: "blur(4px)", display: "grid", placeItems: "center", padding: 20, animation: "fadeIn .2s ease" }}>
      <div onClick={e => e.stopPropagation()} className="card" style={{ width: "100%", maxWidth: 410, padding: 30, boxShadow: "var(--shadow-lg)", animation: "pop .2s ease both" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>{m === "login" ? "Đăng nhập" : "Đăng ký"}</h2>
          <button onClick={onClose} style={iconBtnStyle}><Icon name="close" size={18} /></button>
        </div>
        <p className="muted" style={{ fontSize: 13.5, marginTop: 0 }}>
          {m === "login" ? "Đăng nhập để lưu sản phẩm và gửi đề xuất thông số." : "Tạo tài khoản TechChoice miễn phí."}
        </p>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
          {m === "register" && <Field label="Tên hiển thị"><input className="focusable" value={name} onChange={e => setName(e.target.value)} placeholder="Nguyễn Văn A" style={inputStyle} /></Field>}
          <Field label="Email"><input className="focusable" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} /></Field>
          <Field label="Mật khẩu"><input className="focusable" type="password" value={pw} onChange={e => setPw(e.target.value)} style={inputStyle} /></Field>
          <button className="btn btn-primary" style={{ width: "100%", marginTop: 4 }}>{m === "login" ? "Đăng nhập" : "Tạo tài khoản"}</button>
        </form>
        <div style={{ marginTop: 12, padding: 10, borderRadius: 10, background: "var(--surface-3)", fontSize: 12, color: "var(--text-2)" }}>
          💡 Mẹo demo: email bắt đầu bằng <b>admin</b> sẽ đăng nhập với quyền quản trị.
        </div>
        <p className="muted" style={{ fontSize: 13.5, textAlign: "center", marginTop: 14 }}>
          {m === "login" ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
          <button onClick={() => setM(m === "login" ? "register" : "login")} style={{ background: "none", border: "none", color: "var(--primary)", fontWeight: 700, cursor: "pointer", fontSize: 13.5 }}>
            {m === "login" ? "Đăng ký ngay" : "Đăng nhập"}
          </button>
        </p>
      </div>
    </div>
  );
}
const inputStyle = { width: "100%", padding: "11px 13px", borderRadius: 10, border: "1px solid var(--border-strong)", background: "var(--surface-2)", color: "var(--text)", fontSize: 14.5, outline: "none" };
function Field({ label, children }) {
  return <label style={{ display: "block" }}><span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-2)", display: "block", marginBottom: 6 }}>{label}</span>{children}</label>;
}

/* ---------------- Public App shell ---------------- */
function PublicApp({ session, setSession, theme, toggleTheme, onGoAdmin }) {
  const [tab,          setTab]          = useStateP(() => localStorage.getItem("tc_pub_tab") || "top");
  const [productId,    setProductId]    = useStateP(null);
  const [auth,         setAuth]         = useStateP(null);
  const [savedIds,     setSavedIds]     = useStateP(() => {
    try { return JSON.parse(localStorage.getItem("tc_saved") || "[]"); } catch { return []; }
  });
  const [editRequests, setEditRequests] = useStateP(() =>
    (window.DATA.EDIT_REQUESTS || []).map(r => ({ ...r }))
  );

  useEffectP(() => { localStorage.setItem("tc_saved", JSON.stringify(savedIds)); }, [savedIds]);

  const toggleSave = (pid) => setSavedIds(ids =>
    ids.includes(pid) ? ids.filter(id => id !== pid) : [pid, ...ids]);

  const cancelEditRequest = (id) => {
    setEditRequests(reqs => {
      const next = reqs.filter(r => r.id !== id);
      window.DATA.EDIT_REQUESTS = next;
      return next;
    });
  };

  const updateSession = (s) => setSession(s);

  const openProduct = (id) => { setProductId(id); window.scrollTo({ top: 0 }); };
  const goTab = (t) => {
    setProductId(null); setTab(t);
    localStorage.setItem("tc_pub_tab", t);
    window.scrollTo({ top: 0 });
  };

  return (
    <div style={{ minHeight: "100vh" }}>
      <TopNav tab={productId ? "" : tab} setTab={goTab} session={session}
        onAuth={setAuth} onLogout={() => setSession(null)} onGoAdmin={onGoAdmin}
        theme={theme} toggleTheme={toggleTheme} savedCount={savedIds.length} />
      {productId ? (
        <ProductDetail id={productId} session={session} onBack={() => goTab(tab)} onAuth={setAuth}
          savedIds={savedIds} onToggleSave={toggleSave} />
      ) : tab === "search" ? (
        <SearchPage onOpen={openProduct} />
      ) : tab === "saved" ? (
        <SavedProductsPage savedIds={savedIds} onOpen={openProduct} onToggleSave={toggleSave}
          onGoSearch={() => goTab("top")} session={session} onAuth={setAuth} />
      ) : tab === "account" ? (
        <AccountProfilePage session={session} savedCount={savedIds.length}
          onUpdateSession={updateSession} onGoSaved={() => goTab("saved")} onAuth={setAuth}
          editRequests={editRequests} onCancelEditRequest={cancelEditRequest} />
      ) : (
        <TopProductsPage onOpen={openProduct} />
      )}
      {auth && <AuthModal mode={auth} onClose={() => setAuth(null)} onSuccess={(s) => { setSession(s); setAuth(null); }} />}
    </div>
  );
}

Object.assign(window, { PublicApp });
