/* ============================================================
   TechChoice — Admin extra pages
   Depends on: admin.jsx (PageHead, Toggle, miniBtn, iconBtnStyle, inputStyle)
   exports: AccountsPage, AliasesPage, CandidatesPage, SpecTemplatesPage
   ============================================================ */
const { useState: useStateE } = React;

/* Borrow shared helpers exported by admin.jsx */
const _ph  = () => window.PageHead;
const _tog = () => window.Toggle;
const _mb  = () => window.miniBtn;
const _ibs = () => window.iconBtnStyle;
const _is  = () => window.inputStyle;
const _pg  = () => window.Pagination;
const _upg = () => window.usePagination;

/* ---------- Inline Modal shell ---------- */
function AdminModal({ title, onClose, children, width = 460 }) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(20,12,40,.58)", zIndex: 200, display: "grid", placeItems: "center", padding: 20 }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="card" style={{ width, maxWidth: "100%", padding: 26, maxHeight: "90vh", overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>{title}</h3>
          <button onClick={onClose} style={_ibs()}><Icon name="close" size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ---------- Field wrapper ---------- */
function Field({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-2)", marginBottom: 7 }}>{label}</div>
      {children}
    </div>
  );
}

/* ============================================================
   AccountsPage — Quản lý tài khoản
   ============================================================ */
function AccountsPage() {
  const PageHead = _ph();
  const Toggle   = _tog();
  const miniBtn  = _mb();
  const inputStyle = _is();

  const [users, setUsers] = useStateE(window.DATA.ACCOUNTS.map(u => ({ ...u })));
  const [showAdd, setShowAdd] = useStateE(false);
  const [editUser, setEditUser] = useStateE(null);
  const [form, setForm] = useStateE({ email: "", display_name: "", role: "user", password: "" });
  const Pagination = _pg();
  const pg = _upg()(users, 10);

  const openAdd = () => { setForm({ email: "", display_name: "", role: "user", password: "" }); setShowAdd(true); };

  const saveAdd = () => {
    if (!form.email.trim() || !form.display_name.trim()) return;
    setUsers(u => [{
      id: "usr_" + Date.now(), email: form.email.trim(), display_name: form.display_name.trim(),
      role: form.role, is_active: true,
      created_at: new Date().toISOString().slice(0, 10), last_login_at: null,
    }, ...u]);
    setShowAdd(false);
  };

  const saveEdit = () => {
    setUsers(u => u.map(x => x.id === editUser.id ? { ...x, display_name: editUser.display_name, role: editUser.role } : x));
    setEditUser(null);
  };

  const roleLabel = r => r === "admin" ? "Quản trị viên" : "Người dùng";

  return (
    <div>
      <PageHead title="Quản lý tài khoản" sub={users.length + " tài khoản · " + users.filter(u => u.is_active).length + " đang hoạt động."}
        action={<button className="btn btn-primary" onClick={openAdd}><Icon name="plus" size={16} />Thêm tài khoản</button>} />
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr><th>Tài khoản</th><th>Email</th><th>Vai trò</th><th>Trạng thái</th><th>Ngày tạo</th><th>Đăng nhập cuối</th><th></th></tr>
            </thead>
            <tbody>
              {pg.paged.map((u, i) => (
                <tr key={u.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{
                        width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
                        background: u.role === "admin" ? "linear-gradient(135deg,var(--v-500),var(--v-700))" : "var(--surface-3)",
                        color: u.role === "admin" ? "#fff" : "var(--primary)",
                        display: "grid", placeItems: "center", fontWeight: 700, fontSize: 14,
                      }}>
                        {u.display_name.charAt(0)}
                      </span>
                      <span style={{ fontWeight: 700 }}>{u.display_name}</span>
                    </div>
                  </td>
                  <td className="muted" style={{ fontSize: 13 }}>{u.email}</td>
                  <td>
                    <span className={"chip " + (u.role === "admin" ? "brand" : "")}>
                      {roleLabel(u.role)}
                    </span>
                  </td>
                  <td>
                    <Toggle on={u.is_active}
                      onClick={() => setUsers(r => r.map(x => x.id === u.id ? { ...x, is_active: !x.is_active } : x))} />
                  </td>
                  <td className="num muted" style={{ fontSize: 13 }}>{u.created_at}</td>
                  <td className="num muted" style={{ fontSize: 13 }}>{u.last_login_at || "—"}</td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button style={miniBtn} onClick={() => setEditUser({ ...u })}><Icon name="edit" size={15} /></button>
                      <button style={{ ...miniBtn, color: "var(--neg)" }}
                        onClick={() => setUsers(r => r.filter(x => x.id !== u.id))}>
                        <Icon name="trash" size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination {...pg} />
      </div>

      {/* Add modal */}
      {showAdd && (
        <AdminModal title="Thêm tài khoản mới" onClose={() => setShowAdd(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Email *">
              <input value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                placeholder="email@example.com" style={inputStyle} />
            </Field>
            <Field label="Tên hiển thị *">
              <input value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
                placeholder="Nguyễn Văn A" style={inputStyle} />
            </Field>
            <Field label="Vai trò">
              <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} style={inputStyle}>
                <option value="user">Người dùng</option>
                <option value="admin">Quản trị viên</option>
              </select>
            </Field>
            <Field label="Mật khẩu *">
              <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                placeholder="••••••••" style={inputStyle} />
            </Field>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Hủy</button>
            <button className="btn btn-primary" onClick={saveAdd}><Icon name="plus" size={16} />Tạo tài khoản</button>
          </div>
        </AdminModal>
      )}

      {/* Edit modal */}
      {editUser && (
        <AdminModal title="Chỉnh sửa tài khoản" onClose={() => setEditUser(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Email">
              <div style={{ ...inputStyle, background: "var(--surface-2)", color: "var(--text-3)", cursor: "default" }}>{editUser.email}</div>
            </Field>
            <Field label="Tên hiển thị">
              <input value={editUser.display_name} onChange={e => setEditUser(u => ({ ...u, display_name: e.target.value }))}
                style={inputStyle} />
            </Field>
            <Field label="Vai trò">
              <select value={editUser.role} onChange={e => setEditUser(u => ({ ...u, role: e.target.value }))} style={inputStyle}>
                <option value="user">Người dùng</option>
                <option value="admin">Quản trị viên</option>
              </select>
            </Field>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setEditUser(null)}>Hủy</button>
            <button className="btn btn-primary" onClick={saveEdit}><Icon name="check" size={16} />Lưu thay đổi</button>
          </div>
        </AdminModal>
      )}
    </div>
  );
}

/* ============================================================
   AliasesPage — Quản lý alias sản phẩm
   ============================================================ */
function AliasesPage() {
  const PageHead   = _ph();
  const miniBtn    = _mb();
  const inputStyle = _is();

  const [aliases, setAliases] = useStateE(window.DATA.ALIASES.map(a => ({ ...a })));
  const [showAdd, setShowAdd] = useStateE(false);
  const [filterProd, setFilterProd] = useStateE("all");
  const [form, setForm] = useStateE({ product_id: "", alias_text: "", alias_type: "variant" });
  const products = window.DATA.PRODUCTS;

  const addAlias = () => {
    if (!form.product_id || !form.alias_text.trim()) return;
    setAliases(a => [{
      alias_id: "al" + Date.now(), product_id: form.product_id,
      alias_text: form.alias_text.trim(), alias_type: form.alias_type,
      is_active: true, created_at: new Date().toISOString().slice(0, 10),
    }, ...a]);
    setForm({ product_id: "", alias_text: "", alias_type: "variant" });
    setShowAdd(false);
  };

  const typeLabel = { variant: "Biến thể", abbreviation: "Viết tắt", typo: "Lỗi chính tả", exact: "Chính xác" };
  const typeChip  = { variant: "", abbreviation: "brand", typo: "neg", exact: "pos" };

  const filtered = filterProd === "all" ? aliases : aliases.filter(a => a.product_id === filterProd);
  const Pagination = _pg();
  const pg = _upg()(filtered, 10);
  React.useEffect(() => { pg.setPage(1); }, [filterProd]);

  return (
    <div>
      <PageHead title="Tên gọi khác (Alias)"
        sub={aliases.length + " tên gọi khác đang quản lý · dùng để khớp tên sản phẩm từ bình luận YouTube."}
        action={<button className="btn btn-primary" onClick={() => setShowAdd(true)}><Icon name="plus" size={16} />Thêm alias</button>} />

      {/* Product filter chips */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={() => setFilterProd("all")} style={{
          padding: "6px 14px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
          background: filterProd === "all" ? "var(--primary)" : "var(--surface)",
          color: filterProd === "all" ? "var(--on-primary)" : "var(--text-2)",
          boxShadow: filterProd === "all" ? "none" : "var(--shadow-sm)",
        }}>Tất cả ({aliases.length})</button>
        {products.map(p => {
          const cnt = aliases.filter(a => a.product_id === p.product_id).length;
          if (!cnt) return null;
          return (
            <button key={p.product_id} onClick={() => setFilterProd(p.product_id)} style={{
              padding: "6px 14px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
              background: filterProd === p.product_id ? "var(--primary)" : "var(--surface)",
              color: filterProd === p.product_id ? "var(--on-primary)" : "var(--text-2)",
              boxShadow: filterProd === p.product_id ? "none" : "var(--shadow-sm)",
            }}>{p.product_name} ({cnt})</button>
          );
        })}
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr><th>Alias text</th><th>Sản phẩm</th><th>Loại</th><th>Trạng thái</th><th>Ngày tạo</th><th></th></tr>
            </thead>
            <tbody>
              {pg.paged.map((a, i) => {
                const prod = products.find(p => p.product_id === a.product_id);
                return (
                  <tr key={a.alias_id}>
                    <td>
                      <code style={{ fontSize: 13, background: "var(--code-bg)", padding: "3px 9px", borderRadius: 7, color: "var(--primary)", fontFamily: "var(--font-num)", fontWeight: 700 }}>
                        {a.alias_text}
                      </code>
                    </td>
                    <td style={{ fontWeight: 600 }}>{prod?.product_name || a.product_id}</td>
                    <td><span className={"chip " + (typeChip[a.alias_type] || "")}>{typeLabel[a.alias_type] || a.alias_type}</span></td>
                    <td>{a.is_active ? <span className="chip pos">Hoạt động</span> : <span className="chip">Đã tắt</span>}</td>
                    <td className="num muted" style={{ fontSize: 13 }}>{a.created_at}</td>
                    <td>
                      <button style={{ ...miniBtn, color: "var(--neg)" }}
                        onClick={() => setAliases(r => r.map((x, j) => {
                          const idx = filtered.indexOf(a);
                          return x.alias_id === a.alias_id ? { ...x, is_active: false } : x;
                        }))}>
                        <Icon name="trash" size={15} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <Pagination {...pg} />
      </div>

      {showAdd && (
        <AdminModal title="Thêm alias mới" onClose={() => setShowAdd(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Alias text *">
              <input value={form.alias_text} onChange={e => setForm(f => ({ ...f, alias_text: e.target.value }))}
                placeholder="vd: ip17pm, s25 ultra 5g, mi 15..." style={inputStyle} />
            </Field>
            <Field label="Sản phẩm *">
              <select value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))} style={inputStyle}>
                <option value="">— Chọn sản phẩm —</option>
                {products.map(p => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}
              </select>
            </Field>
            <Field label="Loại alias">
              <select value={form.alias_type} onChange={e => setForm(f => ({ ...f, alias_type: e.target.value }))} style={inputStyle}>
                <option value="variant">Biến thể</option>
                <option value="abbreviation">Viết tắt</option>
                <option value="typo">Lỗi chính tả</option>
                <option value="exact">Chính xác</option>
              </select>
            </Field>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Hủy</button>
            <button className="btn btn-primary" onClick={addAlias}><Icon name="link" size={16} />Thêm alias</button>
          </div>
        </AdminModal>
      )}
    </div>
  );
}

/* ============================================================
   CandidatesPage — Duyệt resolution candidates
   ============================================================ */
function CandidatesPage() {
  const PageHead   = _ph();
  const inputStyle = _is();

  const [candidates, setCandidates] = useStateE(window.DATA.CANDIDATES.map(c => ({ ...c })));
  const [filterStatus, setFilterStatus] = useStateE("pending");
  const [reviewModal, setReviewModal] = useStateE(null);
  const [selectedProduct, setSelectedProduct] = useStateE("");
  const products = window.DATA.PRODUCTS;

  const counts = {
    pending:  candidates.filter(c => c.status === "pending").length,
    approved: candidates.filter(c => c.status === "approved").length,
    rejected: candidates.filter(c => c.status === "rejected").length,
  };
  const filtered = candidates.filter(c => c.status === filterStatus);

  const openReview = (cand) => { setReviewModal(cand); setSelectedProduct(""); };

  const doApprove = () => {
    if (!selectedProduct) return;
    setCandidates(r => r.map(c => c.candidate_id === reviewModal.candidate_id
      ? { ...c, status: "approved", resolved_product_id: selectedProduct } : c));
    setReviewModal(null);
  };

  const doReject = (cand) => {
    setCandidates(r => r.map(c => c.candidate_id === cand.candidate_id ? { ...c, status: "rejected" } : c));
  };

  const statusStyle = {
    pending:  { chip: "neu",  label: "Chờ duyệt" },
    approved: { chip: "pos",  label: "Đã duyệt"  },
    rejected: { chip: "neg",  label: "Từ chối"   },
  };

  return (
    <div>
      <PageHead title="Duyệt ánh xạ sản phẩm"
        sub="Văn bản / video chưa khớp được sản phẩm, cần xét duyệt thủ công." />

      {/* Status tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
        {["pending", "approved", "rejected"].map(st => (
          <button key={st} onClick={() => setFilterStatus(st)} style={{
            padding: "8px 18px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13.5, fontWeight: 600,
            background: filterStatus === st ? "var(--primary)" : "var(--surface)",
            color: filterStatus === st ? "var(--on-primary)" : "var(--text-2)",
            boxShadow: filterStatus === st ? "none" : "var(--shadow-sm)",
          }}>
            {statusStyle[st].label}
            <span style={{ marginLeft: 8, opacity: .6, fontWeight: 700 }}>{counts[st]}</span>
          </button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="card" style={{ padding: "48px 24px", textAlign: "center" }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: "var(--surface-3)", display: "grid", placeItems: "center", margin: "0 auto 14px", color: "var(--text-3)" }}>
            <Icon name="inbox" size={24} />
          </div>
          <div style={{ fontWeight: 700, color: "var(--text-2)" }}>Không có candidate nào ở trạng thái này.</div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map(c => {
          const resolvedProd = products.find(p => p.product_id === c.resolved_product_id);
          return (
            <div key={c.candidate_id} className="card" style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 260px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                  <code style={{ fontSize: 14, background: "var(--code-bg)", padding: "4px 11px", borderRadius: 8, color: "var(--primary)", fontFamily: "var(--font-num)", fontWeight: 700 }}>
                    {c.candidate_text}
                  </code>
                  <span className={"chip " + (c.source_type === "video" ? "brand" : "")}>
                    {c.source_type === "video" ? "Video" : "Sentence"}
                  </span>
                </div>
                <div className="faint" style={{ fontSize: 12.5, fontFamily: "var(--font-num)" }}>
                  source_id: {c.source_id} &nbsp;·&nbsp; {c.created_at}
                </div>
                {resolvedProd && (
                  <div style={{ marginTop: 8, fontSize: 13, fontWeight: 700, color: "var(--pos)", display: "flex", gap: 6, alignItems: "center" }}>
                    <Icon name="check" size={14} />{resolvedProd.product_name}
                  </div>
                )}
              </div>
              {c.status === "pending" && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn" style={{ background: "var(--pos)", color: "#fff", padding: "8px 16px" }}
                    onClick={() => openReview(c)}>
                    <Icon name="check" size={16} />Duyệt
                  </button>
                  <button className="btn btn-ghost" onClick={() => doReject(c)}>
                    <Icon name="close" size={16} />Từ chối
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {reviewModal && (
        <AdminModal title="Xác nhận duyệt candidate" onClose={() => setReviewModal(null)}>
          <div style={{ padding: "12px 14px", borderRadius: 10, background: "var(--surface-2)", marginBottom: 18 }}>
            <div className="faint" style={{ fontSize: 12, marginBottom: 5 }}>Candidate text</div>
            <code style={{ fontWeight: 700, color: "var(--primary)", fontFamily: "var(--font-num)", fontSize: 14 }}>
              {reviewModal.candidate_text}
            </code>
            <div className="faint" style={{ fontSize: 12, marginTop: 8 }}>source_type: {reviewModal.source_type} · {reviewModal.source_id}</div>
          </div>
          <Field label="Ánh xạ đến sản phẩm *">
            <select value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)} style={inputStyle}>
              <option value="">— Chọn sản phẩm —</option>
              {products.map(p => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}
            </select>
          </Field>
          <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setReviewModal(null)}>Hủy</button>
            <button className="btn" style={{ background: "var(--pos)", color: "#fff" }}
              disabled={!selectedProduct} onClick={doApprove}>
              <Icon name="check" size={16} />Xác nhận duyệt
            </button>
          </div>
        </AdminModal>
      )}
    </div>
  );
}

/* ============================================================
   SpecTemplatesPage — Quản lý product_spec_templates
   ============================================================ */
function SpecTemplatesPage() {
  const PageHead   = _ph();
  const miniBtn    = _mb();
  const inputStyle = _is();

  const [templates, setTemplates] = useStateE(window.DATA.SPEC_TEMPLATES.map(t => ({ ...t })));
  const [showAdd, setShowAdd] = useStateE(false);
  const [filterCat, setFilterCat] = useStateE("all");
  const [form, setForm] = useStateE({ category: "Điện thoại", spec_key: "", display_label: "", value_type: "string", unit: "" });

  const categories = [...new Set(templates.map(t => t.category))];
  const filtered = filterCat === "all" ? templates : templates.filter(t => t.category === filterCat);
  const Pagination = _pg();
  const pg = _upg()(filtered, 10);
  React.useEffect(() => { pg.setPage(1); }, [filterCat]);

  const addTemplate = () => {
    if (!form.spec_key.trim() || !form.display_label.trim()) return;
    setTemplates(t => [...t, { ...form, spec_key: form.spec_key.trim(), display_label: form.display_label.trim(), is_active: true }]);
    setForm({ category: "Điện thoại", spec_key: "", display_label: "", value_type: "string", unit: "" });
    setShowAdd(false);
  };

  const deactivate = (tgt) => setTemplates(r => r.map(t =>
    t.category === tgt.category && t.spec_key === tgt.spec_key ? { ...t, is_active: false } : t));

  const catAccent = { "Điện thoại": "brand", "Laptop": "pos", "Tai nghe": "neu" };
  const typeAccent = { string: "", number: "brand", boolean: "neu" };

  return (
    <div>
      <PageHead title="Mẫu thông số kỹ thuật"
        sub="Định nghĩa các trường thông số kỹ thuật chuẩn cho từng danh mục sản phẩm."
        action={<button className="btn btn-primary" onClick={() => setShowAdd(true)}><Icon name="plus" size={16} />Thêm template</button>} />

      {/* Category filter */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {["all", ...categories].map(cat => (
          <button key={cat} onClick={() => setFilterCat(cat)} style={{
            padding: "7px 15px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
            background: filterCat === cat ? "var(--primary)" : "var(--surface)",
            color: filterCat === cat ? "var(--on-primary)" : "var(--text-2)",
            boxShadow: filterCat === cat ? "none" : "var(--shadow-sm)",
          }}>
            {cat === "all" ? "Tất cả" : cat}
            <span style={{ marginLeft: 6, opacity: .6 }}>
              ({cat === "all" ? templates.length : templates.filter(t => t.category === cat).length})
            </span>
          </button>
        ))}
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr><th>Danh mục</th><th>spec_key</th><th>Nhãn hiển thị</th><th>Kiểu dữ liệu</th><th>Đơn vị</th><th>Trạng thái</th><th></th></tr>
            </thead>
            <tbody>
              {pg.paged.map(t => (
                <tr key={t.category + "_" + t.spec_key}>
                  <td><span className={"chip " + (catAccent[t.category] || "")}>{t.category}</span></td>
                  <td>
                    <code style={{ fontSize: 12.5, background: "var(--code-bg)", padding: "3px 8px", borderRadius: 6, fontFamily: "var(--font-num)", color: "var(--text-2)" }}>
                      {t.spec_key}
                    </code>
                  </td>
                  <td style={{ fontWeight: 600 }}>{t.display_label}</td>
                  <td><span className={"chip " + (typeAccent[t.value_type] || "")}>{t.value_type}</span></td>
                  <td className="muted">{t.unit || "—"}</td>
                  <td>{t.is_active ? <span className="chip pos">Hoạt động</span> : <span className="chip">Đã tắt</span>}</td>
                  <td>
                    {t.is_active && (
                      <button style={{ ...miniBtn, color: "var(--neg)" }} onClick={() => deactivate(t)}>
                        <Icon name="trash" size={15} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination {...pg} />
      </div>

      {showAdd && (
        <AdminModal title="Thêm Spec Template" onClose={() => setShowAdd(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="Danh mục">
              <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} style={inputStyle}>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
                <option value="__new">+ Danh mục mới...</option>
              </select>
            </Field>
            <Field label="spec_key *">
              <input value={form.spec_key} onChange={e => setForm(f => ({ ...f, spec_key: e.target.value }))}
                placeholder="vd: screen_size, battery_capacity, weight..." style={inputStyle} />
            </Field>
            <Field label="Nhãn hiển thị *">
              <input value={form.display_label} onChange={e => setForm(f => ({ ...f, display_label: e.target.value }))}
                placeholder="vd: Màn hình, Dung lượng pin, Trọng lượng..." style={inputStyle} />
            </Field>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Field label="Kiểu dữ liệu">
                <select value={form.value_type} onChange={e => setForm(f => ({ ...f, value_type: e.target.value }))} style={inputStyle}>
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                </select>
              </Field>
              <Field label="Đơn vị">
                <input value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
                  placeholder="GB, mAh, kg..." style={inputStyle} />
              </Field>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 22, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setShowAdd(false)}>Hủy</button>
            <button className="btn btn-primary" onClick={addTemplate}><Icon name="spec" size={16} />Thêm template</button>
          </div>
        </AdminModal>
      )}
    </div>
  );
}

Object.assign(window, { AccountsPage, AliasesPage, CandidatesPage, SpecTemplatesPage });
