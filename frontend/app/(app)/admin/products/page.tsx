"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type {
  ProductAliasItem,
  ProductConfigItem,
  ProductDetailChangeRequestItem,
  ProductSpecTemplateItem,
  ProductResolutionCandidate,
} from "@/lib/types";

export default function ProductsAdminPage() {
  const [products, setProducts] = useState<ProductConfigItem[]>([]);
  const [aliases, setAliases] = useState<ProductAliasItem[]>([]);
  const [templates, setTemplates] = useState<ProductSpecTemplateItem[]>([]);
  const [requests, setRequests] = useState<ProductDetailChangeRequestItem[]>([]);
  const [candidates, setCandidates] = useState<ProductResolutionCandidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [productName, setProductName] = useState("");
  const [productBrand, setProductBrand] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [aliasProductId, setAliasProductId] = useState("");
  const [aliasText, setAliasText] = useState("");
  const [templateCategory, setTemplateCategory] = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [templateLabel, setTemplateLabel] = useState("");

  async function load() {
    try {
      const [nextProducts, nextAliases, nextTemplates, nextRequests, nextCandidates] = await Promise.all([
        api.admin.products.list(),
        api.admin.products.aliases(),
        api.admin.products.templates(),
        api.admin.products.detailRequests(),
        api.admin.products.candidates(),
      ]);
      setProducts(nextProducts);
      setAliases(nextAliases);
      setTemplates(nextTemplates);
      setRequests(nextRequests);
      setCandidates(nextCandidates);
      setError(null);
    } catch {
      setError("Không thể tải catalog sản phẩm.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function review(id: string, action: "approve" | "reject") {
    await api.admin.products.reviewDetailRequest(id, action);
    await load();
  }

  async function createProduct() {
    await api.admin.products.create({ product_name: productName, brand: productBrand || undefined, category: productCategory || undefined });
    setProductName(""); setProductBrand(""); setProductCategory(""); await load();
  }

  async function createAlias() {
    await api.admin.products.createAlias({ product_id: aliasProductId, alias_text: aliasText });
    setAliasText(""); await load();
  }

  async function createTemplate() {
    await api.admin.products.createTemplate({ category: templateCategory, spec_key: templateKey, display_label: templateLabel, value_type: "string" });
    setTemplateKey(""); setTemplateLabel(""); await load();
  }

  async function resolveCandidate(item: ProductResolutionCandidate) {
    const productId = window.prompt("Product ID chuẩn để gắn candidate này:");
    if (!productId) return;
    const alias = window.prompt("Alias mới cần lưu (để trống nếu không cần):") || undefined;
    const sentiment = item.source_type === "sentence"
      ? window.prompt("Sentiment cho target này: POSITIVE, NEGATIVE hoặc NEUTRAL")?.toUpperCase()
      : undefined;
    if (item.source_type === "sentence" && !["POSITIVE", "NEGATIVE", "NEUTRAL"].includes(sentiment ?? "")) return;
    await api.admin.products.reviewCandidate(
      item.candidate_id,
      productId,
      alias,
      sentiment as "POSITIVE" | "NEGATIVE" | "NEUTRAL" | undefined,
    );
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Catalog sản phẩm</h1>
        <p className="text-sm text-slate-500 mt-1">Theo dõi model chuẩn, alias, template specs và đề xuất từ người dùng.</p>
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
          <h2 className="font-medium text-slate-700">Thêm sản phẩm</h2>
          <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="Tên model" className="w-full border rounded px-2 py-1 text-sm" />
          <input value={productBrand} onChange={(e) => setProductBrand(e.target.value)} placeholder="Hãng" className="w-full border rounded px-2 py-1 text-sm" />
          <input value={productCategory} onChange={(e) => setProductCategory(e.target.value)} placeholder="Danh mục" className="w-full border rounded px-2 py-1 text-sm" />
          <button onClick={createProduct} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm">Thêm</button>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
          <h2 className="font-medium text-slate-700">Thêm alias</h2>
          <input value={aliasProductId} onChange={(e) => setAliasProductId(e.target.value)} placeholder="Product ID" className="w-full border rounded px-2 py-1 text-sm" />
          <input value={aliasText} onChange={(e) => setAliasText(e.target.value)} placeholder="Alias" className="w-full border rounded px-2 py-1 text-sm" />
          <button onClick={createAlias} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm">Thêm</button>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
          <h2 className="font-medium text-slate-700">Thêm template specs</h2>
          <input value={templateCategory} onChange={(e) => setTemplateCategory(e.target.value)} placeholder="Danh mục" className="w-full border rounded px-2 py-1 text-sm" />
          <input value={templateKey} onChange={(e) => setTemplateKey(e.target.value)} placeholder="spec_key" className="w-full border rounded px-2 py-1 text-sm" />
          <input value={templateLabel} onChange={(e) => setTemplateLabel(e.target.value)} placeholder="Nhãn hiển thị" className="w-full border rounded px-2 py-1 text-sm" />
          <button onClick={createTemplate} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm">Thêm</button>
        </div>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <h2 className="px-4 py-3 font-medium text-slate-700 border-b border-slate-200">Sản phẩm ({products.length})</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-slate-500 border-b border-slate-100"><th className="px-4 py-2">Tên</th><th>Hãng</th><th>Danh mục</th><th>ID</th></tr></thead>
          <tbody>{products.map((item) => <tr key={item.product_id} className="border-b border-slate-100"><td className="px-4 py-2 font-medium">{item.product_name}</td><td>{item.brand ?? "-"}</td><td>{item.category ?? "-"}</td><td className="text-xs text-slate-500">{item.product_id}</td></tr>)}</tbody>
        </table>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="bg-white border border-slate-200 rounded-xl p-4">
          <h2 className="font-medium text-slate-700">Alias ({aliases.length})</h2>
          <div className="mt-3 max-h-64 overflow-auto space-y-1 text-sm">
            {aliases.map((item) => <div key={item.alias_id} className="flex justify-between gap-3 border-b border-slate-100 py-1"><span>{item.alias_text}</span><span className="text-slate-400">{item.product_id}</span></div>)}
          </div>
        </section>
        <section className="bg-white border border-slate-200 rounded-xl p-4">
          <h2 className="font-medium text-slate-700">Template specs ({templates.length})</h2>
          <div className="mt-3 max-h-64 overflow-auto space-y-1 text-sm">
            {templates.map((item) => <div key={`${item.category}-${item.spec_key}`} className="flex justify-between gap-3 border-b border-slate-100 py-1"><span>{item.category}: {item.display_label}</span><span className="text-slate-400">{item.value_type}{item.unit ? ` (${item.unit})` : ""}</span></div>)}
          </div>
        </section>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl p-4">
        <h2 className="font-medium text-slate-700">Đề xuất đang chờ duyệt ({requests.length})</h2>
        <div className="mt-3 space-y-3">
          {requests.length === 0 && <p className="text-sm text-slate-400">Không có đề xuất đang chờ.</p>}
          {requests.map((item) => (
            <div key={item.request_id} className="border border-slate-200 rounded-lg p-3 text-sm">
              <div className="font-medium text-slate-700">{item.product_id}</div>
              <pre className="mt-2 text-xs bg-slate-50 rounded p-2 overflow-auto">{JSON.stringify(item.proposed_specs, null, 2)}</pre>
              <div className="flex gap-2 mt-3">
                <button onClick={() => review(item.request_id, "approve")} className="px-3 py-1 rounded bg-emerald-600 text-white">Duyệt</button>
                <button onClick={() => review(item.request_id, "reject")} className="px-3 py-1 rounded bg-rose-600 text-white">Từ chối</button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl p-4">
        <h2 className="font-medium text-slate-700">Candidate cần resolve ({candidates.length})</h2>
        <div className="mt-3 space-y-2">
          {candidates.length === 0 && <p className="text-sm text-slate-400">Không có candidate đang chờ.</p>}
          {candidates.map((item) => (
            <div key={item.candidate_id} className="border border-slate-200 rounded-lg p-3 text-sm flex items-center justify-between gap-3">
              <div><span className="text-xs text-slate-400">{item.source_type}</span><p className="text-slate-700">{item.candidate_text}</p></div>
              <button onClick={() => resolveCandidate(item)} className="px-3 py-1 rounded bg-indigo-600 text-white shrink-0">Resolve</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
