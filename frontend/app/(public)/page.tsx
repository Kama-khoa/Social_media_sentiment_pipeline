"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { SearchResultItem, TopProduct } from "@/lib/types";
import { Icon } from "@/components/shared/Icon";
import { ScoreRing } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadge } from "@/components/shared/ControversyBadge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";

const categories = [
  { slug: "all", label: "Tất cả" },
  { slug: "dien_thoai", label: "Điện thoại" },
  { slug: "laptop", label: "Laptop" },
  { slug: "tai_nghe", label: "Tai nghe" },
];

function topProductToSearchResult(product: TopProduct): SearchResultItem {
  return {
    rank: product.rank,
    product_id: product.product_id,
    product_name: product.product_name,
    brand: product.brand,
    category: product.category,
    bayesian_score: product.bayesian_score,
    controversy_label: product.controversy_label,
    total_mentions: product.total_mentions,
    positive_pct: product.positive_pct,
    negative_pct: product.negative_pct,
  };
}

export default function ExplorePage() {
  const [category, setCategory] = useState("all");
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [overviewProducts, setOverviewProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"top" | "search">("top");
  const [query, setQuery] = useState("");
  const [searchCategory, setSearchCategory] = useState("all");
  const [sort, setSort] = useState<"score" | "mentions" | "positive">("score");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    function syncView() { setView(window.location.hash === "#search" ? "search" : "top"); }
    function syncPublicTab(event: Event) {
      setView((event as CustomEvent<string>).detail === "#search" ? "search" : "top");
    }
    syncView();
    window.addEventListener("hashchange", syncView);
    window.addEventListener("popstate", syncView);
    window.addEventListener("techchoice:public-tab", syncPublicTab);
    return () => {
      window.removeEventListener("hashchange", syncView);
      window.removeEventListener("popstate", syncView);
      window.removeEventListener("techchoice:public-tab", syncPublicTab);
    };
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.products.top(category)
      .then((items) => {
        setProducts(items);
        if (category === "all") setOverviewProducts(items);
      })
      .catch(() => setError("Không thể tải dữ liệu. Vui lòng thử lại."))
      .finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    if (category === "all" || overviewProducts.length > 0) return;
    api.products.top("all").then(setOverviewProducts).catch(() => undefined);
  }, [category, overviewProducts.length]);

  useEffect(() => {
    if (view !== "search") return;
    let active = true;
    if (!query.trim()) {
      setSearchError(null);
      setSearchLoading(true);
      api.products.top(searchCategory, 50)
        .then((items) => {
          if (active) setSearchResults(items.map(topProductToSearchResult));
        })
        .catch(() => {
          if (active) setSearchError("Không thể tải danh sách mặc định. Vui lòng thử lại.");
        })
        .finally(() => {
          if (active) setSearchLoading(false);
        });
      return () => {
        active = false;
      };
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearchLoading(true);
      setSearchError(null);
      const categoryLabel = categories.find((item) => item.slug === searchCategory)?.label ?? "";
      api.search(query, searchCategory === "all" ? "" : categoryLabel, 50, { signal: controller.signal })
        .then((response) => {
          if (active) setSearchResults(response.results);
        })
        .catch((err: unknown) => {
          if (active && (err as DOMException)?.name !== "AbortError") {
            setSearchError("Không thể tải kết quả tìm kiếm. Vui lòng thử lại.");
          }
        })
        .finally(() => {
          if (active) setSearchLoading(false);
        });
    }, 250);
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, searchCategory, view]);

  const categoryCards = useMemo(() => categories.map((item) => ({
    ...item,
    mentions: item.slug === "all" ? overviewProducts.reduce((sum, product) => sum + product.total_mentions, 0) : overviewProducts.filter((product) => product.category.toLocaleLowerCase("vi").includes(item.label.toLocaleLowerCase("vi"))).reduce((sum, product) => sum + product.total_mentions, 0),
  })), [overviewProducts]);

  const searchProducts = useMemo(() => [...searchResults].sort((a, b) => sort === "mentions" ? b.total_mentions - a.total_mentions : sort === "positive" ? b.positive_pct - a.positive_pct : b.bayesian_score - a.bayesian_score), [searchResults, sort]);

  if (view === "search") return <SearchView products={searchProducts} query={query} setQuery={setQuery} category={searchCategory} setCategory={setSearchCategory} sort={sort} setSort={setSort} loading={searchLoading} error={searchError} />;

  return (
    <main className="mx-auto max-w-[1240px] px-6 py-10 pb-20">
      <div className="mb-2 flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="m-0 text-[30px] font-extrabold tracking-[-.02em]">Bảng xếp hạng sản phẩm</h1><p className="muted mt-1.5 text-[15px]">Xếp hạng theo điểm Bayesian, cập nhật từ dữ liệu cộng đồng mới nhất.</p></div>
        <div className="flex flex-wrap gap-[7px]">{categories.map((item) => <button key={item.slug} onClick={() => setCategory(item.slug)} className={`focusable rounded-full border px-[15px] py-2 text-[13.5px] font-semibold transition-all ${category === item.slug ? "border-transparent bg-[var(--primary)] text-[var(--on-primary)]" : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}>{item.label}</button>)}</div>
      </div>

      {error && <div className="card my-6 border-[var(--neg)] p-4 text-sm text-[var(--neg)]">{error}</div>}
      <div className="my-6 grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3.5">{categoryCards.map((item) => <div key={item.slug} className="card flex flex-col gap-1.5 p-4"><span className="muted text-[13px] font-semibold">{item.label}</span><span className="num text-2xl font-bold">{item.mentions.toLocaleString("vi-VN")}</span><span className="faint text-xs">lượt đề cập từ BigQuery</span></div>)}</div>

      {loading && products.length === 0 ? <div className="grid min-h-72 place-items-center"><div className="spinner" /></div> : <>
        {loading && <div className="muted mb-3 text-[13px] font-semibold">Đang cập nhật dữ liệu...</div>}
        <div className="mb-[22px] grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-[18px]">
          {products.slice(0, 3).map((product, index) => <Link key={product.product_id} href={`/product/${product.product_id}`} className="card focusable fade-up p-5 text-left transition-all hover:-translate-y-[3px] hover:shadow-[var(--shadow-md)]" style={{ borderTop: `3px solid ${["#f5b50a", "#9aa3b2", "#cd7f32"][index]}` }}><div className="flex items-center justify-between"><span className="num text-[34px] font-extrabold text-[var(--text-3)]">#{product.rank}</span><ScoreRing score={product.bayesian_score} size={72} /></div><h3 className="mb-0.5 mt-2.5 text-lg font-bold">{product.product_name}</h3><p className="faint mb-3 text-[13px]">{product.brand}</p><SentimentBar positivePct={product.positive_pct} negativePct={product.negative_pct} height={8} /></Link>)}
        </div>
        <div className="card overflow-hidden"><div className="overflow-x-auto"><table className="tbl"><thead><tr><th className="w-14">#</th><th>Sản phẩm</th><th>Thương hiệu</th><th>Điểm Bayes</th><th className="min-w-36">Cảm xúc</th><th>Đề cập</th><th>Tranh cãi</th></tr></thead><tbody>{products.map((product) => <tr key={product.product_id}><td className="num font-bold text-[var(--primary)]">{product.rank}</td><td><Link href={`/product/${product.product_id}`} className="font-bold hover:text-[var(--primary)]">{product.product_name} {product.rank <= 3 && <span className="text-xs">🔥</span>}</Link></td><td className="muted">{product.brand}</td><td className="num font-bold text-[var(--primary)]">{(product.bayesian_score * 100).toFixed(1)}</td><td><SentimentBar positivePct={product.positive_pct} negativePct={product.negative_pct} height={8} /></td><td className="num muted">{product.total_mentions.toLocaleString("vi-VN")}</td><td><ControversyBadge label={product.controversy_label} /></td></tr>)}</tbody></table></div></div>
      </>}
    </main>
  );
}

function SearchView({ products, query, setQuery, category, setCategory, sort, setSort, loading, error }: { products: SearchResultItem[]; query: string; setQuery: (value: string) => void; category: string; setCategory: (value: string) => void; sort: "score" | "mentions" | "positive"; setSort: (value: "score" | "mentions" | "positive") => void; loading: boolean; error: string | null }) {
  return <main className="mx-auto max-w-[1240px] px-6 py-10 pb-20">
    <div className="mb-8 text-center"><span className="chip brand mb-3.5"><Icon name="spark" size={13} />Phân tích cảm xúc từ cộng đồng YouTube Việt</span><h1 className="m-0 text-[38px] font-extrabold leading-[1.1] tracking-[-.03em]">Tìm hiểu người dùng thực sự<br />nói gì về thiết bị công nghệ</h1><p className="muted mx-auto mt-2 max-w-xl text-base">Tổng hợp hàng chục nghìn bình luận, xếp hạng Bayesian và phân tích theo 6 khía cạnh.</p></div>
    <div className="mx-auto mb-[18px] flex max-w-[720px] items-center gap-2.5 rounded-full border border-[var(--border-strong)] bg-[var(--surface)] p-2 pl-5 shadow-[var(--shadow-md)]"><Icon name="search" size={20} style={{ color: "var(--text-3)" }} /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm kiếm sản phẩm — vd: iPhone 17 Pro Max, Galaxy S25..." className="h-auto border-0 bg-transparent px-0 focus-visible:ring-0" /><Button className="rounded-full">Tìm kiếm</Button></div>
    <div className="mb-7 flex flex-wrap justify-center gap-3.5"><div className="flex flex-wrap justify-center gap-[7px]">{categories.map((item) => <button key={item.slug} onClick={() => setCategory(item.slug)} className={`focusable rounded-full border px-[15px] py-2 text-[13.5px] font-semibold transition-all ${category === item.slug ? "border-transparent bg-[var(--primary)] text-[var(--on-primary)]" : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}>{item.label}</button>)}</div><div className="flex items-center gap-2 text-[var(--text-3)]"><Icon name="filter" size={15} /><Select value={sort} onChange={(event) => setSort(event.target.value as "score" | "mentions" | "positive")} className="w-auto"><option value="score">Điểm Bayesian cao nhất</option><option value="mentions">Nhiều đề cập nhất</option><option value="positive">Tích cực nhất</option></Select></div></div>
    <div className="muted mb-3.5 text-[13.5px] font-semibold">{products.length} kết quả</div>
    {error ? <div className="card border-[var(--neg)] p-4 text-sm text-[var(--neg)]">{error}</div> : loading ? <div className="grid min-h-72 place-items-center"><div className="spinner" /></div> : products.length ? <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-[18px]">{products.map((product) => <Link href={`/product/${product.product_id}`} key={product.product_id} className="card focusable fade-up flex flex-col gap-3.5 p-[18px] transition-all hover:-translate-y-[3px] hover:shadow-[var(--shadow-md)]"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="mb-1.5 flex gap-2">{product.rank > 0 && product.rank <= 3 && <span className="num text-[13px] font-extrabold text-[var(--primary)]">#{product.rank}</span>}{product.rank > 0 && product.rank <= 3 && <span className="chip neg px-2 py-0.5">🔥 Nổi bật</span>}</div><h3 className="truncate text-[16.5px] font-bold">{product.product_name}</h3><p className="faint mt-1 text-[13px]">{product.brand} • {product.category}</p></div><ScoreRing score={product.bayesian_score} size={64} /></div><SentimentBar positivePct={product.positive_pct} negativePct={product.negative_pct} height={10} /><div className="flex justify-between text-[12.5px]"><span className="font-semibold text-[var(--pos)]">{product.positive_pct.toFixed(0)}% tích cực</span><span className="num faint">{product.total_mentions.toLocaleString("vi-VN")} đề cập</span><span className="font-semibold text-[var(--neg)]">{product.negative_pct.toFixed(0)}% tiêu cực</span></div></Link>)}</div> : <div className="card p-14 text-center text-[var(--text-3)]">Không tìm thấy sản phẩm phù hợp với &ldquo;{query}&rdquo;.</div>}
  </main>;
}
