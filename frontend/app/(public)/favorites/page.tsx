"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { FavoriteProductItem } from "@/lib/types";
import { ControversyBadge } from "@/components/shared/ControversyBadge";
import { Icon } from "@/components/shared/Icon";
import { ScoreRing, hasEnoughBayesData } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { Button } from "@/components/ui/button";
import { calculateControversyLabel } from "@/lib/utils";

export default function FavoritesPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [favorites, setFavorites] = useState<FavoriteProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login?next=/favorites");
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    api.products.favorites
      .list()
      .then((items) => {
        if (active) setFavorites(items);
      })
      .catch(() => {
        if (active) setError("Không thể tải danh sách sản phẩm đã lưu.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isLoading, router, user]);

  async function removeFavorite(productId: string) {
    await api.products.favorites.remove(productId);
    setFavorites((items) => items.filter((item) => item.product_id !== productId));
  }

  if (isLoading || loading) {
    return <div className="grid min-h-[400px] place-items-center"><div className="spinner" /></div>;
  }

  if (!user) return null;

  return (
    <main className="mx-auto max-w-[1120px] px-6 py-10 pb-20">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="chip brand mb-3"><Icon name="heart" size={13} />Sản phẩm đã lưu</span>
          <h1 className="m-0 text-[30px] font-extrabold tracking-[-.02em]">Danh sách yêu thích của bạn</h1>
          <p className="muted mt-1.5 text-[15px]">{favorites.length} sản phẩm đang được theo dõi.</p>
        </div>
        {favorites.length > 0 && <Link href="/"><Button variant="outline"><Icon name="search" size={16} />Khám phá thêm</Button></Link>}
      </div>

      {error ? (
        <div className="card border-[var(--neg)] p-4 text-sm text-[var(--neg)]">{error}</div>
      ) : favorites.length ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-[18px]">
          {favorites.map((product) => (
            <Link href={`/product/${product.product_id}`} key={product.product_id} className="card focusable fade-up relative flex flex-col gap-3.5 p-[18px] transition-all hover:-translate-y-[3px] hover:shadow-[var(--shadow-md)]">
              <button
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  removeFavorite(product.product_id);
                }}
                className={`focusable absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full border transition-colors border-transparent bg-transparent text-[var(--neg)]`}
                title="Bỏ lưu sản phẩm"
              >
                <Icon name="heartSolid" size={16} />
              </button>
              <div className="flex items-start justify-between gap-3 pr-10">
                <div className="min-w-0">
                  <div className="mb-1.5 flex gap-2">
                    <ControversyBadge label={calculateControversyLabel(product.positive_pct, product.negative_pct)} />
                  </div>
                  <h3 className="truncate text-[16.5px] font-bold">{product.product_name}</h3>
                  <p className="faint mt-1 text-[13px]">{product.brand ?? "Chưa rõ"} • {product.category ?? "Khác"}</p>
                </div>
                <ScoreRing score={product.bayesian_score} statementCount={product.statement_count} size={64} />
              </div>
              <SentimentBar positivePct={product.positive_pct} negativePct={product.negative_pct} height={10} />
              {!hasEnoughBayesData(product.statement_count) && <div className="faint text-[12.5px] font-semibold">Chưa đủ dữ liệu Bayes</div>}
              <div className="flex justify-between text-[12.5px]">
                <span className="font-semibold text-[var(--pos)]">{product.positive_pct.toFixed(0)}% hài lòng</span>
                <span className="num faint">{product.total_mentions.toLocaleString("vi-VN")} đề cập</span>
                <span className="font-semibold text-[var(--neg)]">{product.negative_pct.toFixed(0)}% bất mãn</span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
            <Icon name="heart" size={22} />
          </div>
          <h2 className="text-lg font-bold">Chưa có sản phẩm đã lưu</h2>
          <p className="muted mx-auto mt-2 max-w-md text-sm">Khi bạn lưu sản phẩm, chúng sẽ xuất hiện tại đây để quay lại nhanh hơn.</p>
          <Link href="/" className="mt-5 inline-flex"><Button>Khám phá sản phẩm</Button></Link>
        </div>
      )}
    </main>
  );
}
