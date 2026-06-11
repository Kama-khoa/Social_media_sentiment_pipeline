"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { FavoriteProductItem } from "@/lib/types";
import { ControversyBadge } from "@/components/shared/ControversyBadge";
import { Icon } from "@/components/shared/Icon";
import { Button } from "@/components/ui/button";

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
        <Link href="/"><Button variant="outline"><Icon name="search" size={16} />Khám phá thêm</Button></Link>
      </div>

      {error ? (
        <div className="card border-[var(--neg)] p-4 text-sm text-[var(--neg)]">{error}</div>
      ) : favorites.length ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-[18px]">
          {favorites.map((product) => (
            <div key={product.product_id} className="card flex flex-col gap-3.5 p-[18px]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="mb-2 flex flex-wrap gap-2">
                    {product.category && <span className="chip brand">{product.category}</span>}
                    <ControversyBadge label={product.controversy_label} />
                  </div>
                  <Link href={`/product/${product.product_id}`} className="block truncate text-[17px] font-bold hover:text-[var(--primary)]">
                    {product.product_name}
                  </Link>
                  <p className="faint mt-1 text-[13px]">{product.brand ?? "Chưa rõ thương hiệu"}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFavorite(product.product_id)}
                  title="Bỏ lưu sản phẩm"
                  className="text-[var(--neg)]"
                >
                  <Icon name="heart" size={17} />
                </Button>
              </div>
              <div className="flex items-center justify-between border-t border-[var(--border)] pt-3 text-[12.5px]">
                <span className="num font-bold text-[var(--primary)]">Bayes {product.bayesian_score.toFixed(2)}</span>
                <span className="num faint">{product.total_mentions.toLocaleString("vi-VN")} đề cập</span>
              </div>
            </div>
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
