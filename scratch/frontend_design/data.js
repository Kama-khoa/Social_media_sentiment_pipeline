/* ============================================================
   TechChoice — Mock data (tiếng Việt)
   exposes window.DATA
   ============================================================ */
(function () {
  const ASPECTS = ["Hiệu năng", "Pin", "Camera", "Màn hình", "Thiết kế", "Giá bán"];

  // helper to build aspect breakdown from a 0..100 positivity per aspect
  function aspects(arr, mentions) {
    return ASPECTS.map((label, i) => {
      const pos = arr[i];
      const neg = Math.round((100 - pos) * (0.45 + (i % 3) * 0.08));
      const neu = 100 - pos - neg;
      const total = Math.round(mentions * (0.1 + Math.random() * 0.12));
      return {
        aspect_label: label,
        positive_pct: pos,
        negative_pct: neg < 0 ? 0 : neg,
        neutral_pct: neu < 0 ? 0 : neu,
        total_mentions: total,
      };
    });
  }

  const PRODUCTS = [
    {
      product_id: "iphone-17-pro-max", product_name: "iPhone 17 Pro Max", brand: "Apple",
      category: "Điện thoại", release_year: 2025, score: 0.912, controversy: "low",
      mentions: 18420, pos: 78, neg: 9, hot: true, trend: 6.4,
      aspectArr: [92, 71, 88, 90, 86, 54],
      specs: { "Màn hình": "6.9\" LTPO OLED 120Hz", "Chip": "Apple A19 Pro", "RAM": "12 GB",
               "Bộ nhớ": "256GB – 1TB", "Camera chính": "48MP f/1.6", "Pin": "4685 mAh", "Sạc": "40W có dây" },
      desc: "Phiên bản cao cấp nhất của Apple năm 2025 với khung titan, chip A19 Pro và hệ thống camera tele nâng cấp mạnh."
    },
    {
      product_id: "samsung-galaxy-s25-ultra", product_name: "Samsung Galaxy S25 Ultra", brand: "Samsung",
      category: "Điện thoại", release_year: 2025, score: 0.884, controversy: "medium",
      mentions: 15970, pos: 73, neg: 14, hot: true, trend: 4.1,
      aspectArr: [90, 64, 85, 93, 78, 49],
      specs: { "Màn hình": "6.9\" Dynamic AMOLED 2X", "Chip": "Snapdragon 8 Elite", "RAM": "12 GB",
               "Bộ nhớ": "256GB – 1TB", "Camera chính": "200MP f/1.7", "Pin": "5000 mAh", "Sạc": "45W có dây" },
      desc: "Flagship Android với bút S-Pen, camera 200MP và bộ khung titan, đối thủ trực tiếp của iPhone Pro Max."
    },
    {
      product_id: "xiaomi-15-pro", product_name: "Xiaomi 15 Pro", brand: "Xiaomi",
      category: "Điện thoại", release_year: 2025, score: 0.841, controversy: "medium",
      mentions: 9240, pos: 70, neg: 15, hot: true, trend: 9.2,
      aspectArr: [88, 80, 79, 84, 72, 81],
      specs: { "Màn hình": "6.73\" LTPO AMOLED", "Chip": "Snapdragon 8 Elite", "RAM": "12 GB",
               "Bộ nhớ": "256GB – 512GB", "Camera chính": "50MP Leica", "Pin": "6100 mAh", "Sạc": "90W có dây" },
      desc: "Hiệu năng và pin vượt trội trong tầm giá, hợp tác camera cùng Leica."
    },
    {
      product_id: "iphone-16-pro", product_name: "iPhone 16 Pro", brand: "Apple",
      category: "Điện thoại", release_year: 2024, score: 0.823, controversy: "low",
      mentions: 12110, pos: 71, neg: 12, hot: false, trend: -2.3,
      aspectArr: [86, 62, 84, 87, 83, 51],
      specs: { "Màn hình": "6.3\" LTPO OLED 120Hz", "Chip": "Apple A18 Pro", "RAM": "8 GB",
               "Bộ nhớ": "128GB – 1TB", "Camera chính": "48MP f/1.8", "Pin": "3582 mAh", "Sạc": "27W có dây" },
      desc: "Bản Pro nhỏ gọn với nút Camera Control và chip A18 Pro."
    },
    {
      product_id: "oppo-find-x8-pro", product_name: "OPPO Find X8 Pro", brand: "OPPO",
      category: "Điện thoại", release_year: 2024, score: 0.802, controversy: "high",
      mentions: 6730, pos: 66, neg: 21, hot: false, trend: 1.8,
      aspectArr: [84, 78, 88, 82, 75, 60],
      specs: { "Màn hình": "6.78\" AMOLED", "Chip": "Dimensity 9400", "RAM": "16 GB",
               "Bộ nhớ": "512GB", "Camera chính": "50MP Hasselblad", "Pin": "5910 mAh", "Sạc": "80W có dây" },
      desc: "Camera tele kép cùng Hasselblad, gây tranh luận về giá bán tại Việt Nam."
    },
    {
      product_id: "macbook-air-m4", product_name: "MacBook Air M4", brand: "Apple",
      category: "Laptop", release_year: 2025, score: 0.871, controversy: "low",
      mentions: 8420, pos: 75, neg: 8, hot: true, trend: 5.0,
      aspectArr: [85, 91, 60, 84, 89, 58],
      specs: { "Màn hình": "13.6\" Liquid Retina", "Chip": "Apple M4", "RAM": "16 GB",
               "Bộ nhớ": "256GB – 2TB SSD", "Trọng lượng": "1.24 kg", "Pin": "18 giờ", "Cổng": "2× Thunderbolt 4" },
      desc: "Laptop mỏng nhẹ thời lượng pin dài, chip M4 hiệu năng cao cho công việc văn phòng và sáng tạo."
    },
    {
      product_id: "asus-rog-zephyrus-g16", product_name: "ASUS ROG Zephyrus G16", brand: "ASUS",
      category: "Laptop", release_year: 2024, score: 0.812, controversy: "medium",
      mentions: 5210, pos: 69, neg: 16, hot: false, trend: 2.6,
      aspectArr: [94, 58, 50, 88, 80, 55],
      specs: { "Màn hình": "16\" OLED 240Hz", "CPU": "Core Ultra 9", "GPU": "RTX 4090 Laptop",
               "RAM": "32 GB", "Bộ nhớ": "1TB SSD", "Trọng lượng": "1.95 kg", "Pin": "90Wh" },
      desc: "Laptop gaming mỏng nhẹ, màn OLED 240Hz, hiệu năng cao nhưng pin trung bình."
    },
    {
      product_id: "sony-wh-1000xm6", product_name: "Sony WH-1000XM6", brand: "Sony",
      category: "Tai nghe", release_year: 2025, score: 0.858, controversy: "low",
      mentions: 4980, pos: 74, neg: 10, hot: true, trend: 7.7,
      aspectArr: [88, 86, 50, 50, 82, 64],
      specs: { "Kiểu": "Over-ear chống ồn", "Driver": "30mm", "Chống ồn": "ANC thế hệ 6",
               "Thời lượng": "32 giờ", "Sạc": "USB-C nhanh", "Kết nối": "Bluetooth 5.4 LDAC" },
      desc: "Tai nghe chống ồn đầu bảng với chất âm cân bằng và đàm thoại rõ ràng."
    },
    {
      product_id: "airpods-pro-3", product_name: "AirPods Pro 3", brand: "Apple",
      category: "Tai nghe", release_year: 2025, score: 0.836, controversy: "medium",
      mentions: 7150, pos: 72, neg: 13, hot: false, trend: 3.3,
      aspectArr: [84, 80, 50, 50, 86, 57],
      specs: { "Kiểu": "In-ear chống ồn", "Chip": "Apple H3", "Chống ồn": "ANC thích ứng",
               "Thời lượng": "8 giờ (30 giờ với hộp)", "Sạc": "USB-C / MagSafe", "Kháng nước": "IP54" },
      desc: "Tai nghe true wireless với chống ồn nâng cấp và cảm biến nhịp tim."
    },
    {
      product_id: "samsung-galaxy-s25", product_name: "Samsung Galaxy S25", brand: "Samsung",
      category: "Điện thoại", release_year: 2025, score: 0.798, controversy: "medium",
      mentions: 8830, pos: 67, neg: 17, hot: false, trend: 0.9,
      aspectArr: [86, 60, 80, 90, 74, 58],
      specs: { "Màn hình": "6.2\" Dynamic AMOLED 2X", "Chip": "Snapdragon 8 Elite", "RAM": "12 GB",
               "Bộ nhớ": "128GB – 512GB", "Camera chính": "50MP", "Pin": "4000 mAh", "Sạc": "25W có dây" },
      desc: "Bản tiêu chuẩn nhỏ gọn, cân bằng giữa hiệu năng và thời lượng pin."
    },
  ];

  PRODUCTS.forEach(p => { p.aspects = aspects(p.aspectArr, p.mentions); });

  // attribution / PELT change-points per product (timeline)
  function attribution(p) {
    const base = 0.5 + (p.pos - 60) / 200;
    const pts = [];
    let cur = base - 0.08;
    const months = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"];
    for (let i = 0; i < 12; i++) {
      cur += (Math.sin(i * 1.3 + p.mentions % 7) * 0.03) + (i === 5 ? 0.12 : 0) + (i === 8 ? -0.07 : 0);
      cur = Math.max(0.18, Math.min(0.95, cur));
      pts.push({ label: months[i], value: +cur.toFixed(3) });
    }
    return {
      series: pts,
      events: [
        { date: "2025-06-12", dir: "POSITIVE", title: `Đánh giá chi tiết ${p.product_name} sau 1 tháng`,
          channel: "Tinh tế", views: 1240000,
          text: "Lượng thảo luận tích cực tăng mạnh sau video đánh giá dài hạn, tập trung khen pin và hiệu năng." },
        { date: "2025-09-03", dir: "NEGATIVE", title: `${p.product_name} bị nóng khi chơi game?`,
          channel: "Vật Vờ Studio", views: 880000,
          text: "Một video thử nghiệm nhiệt độ khiến tỉ lệ tiêu cực về 'hiệu năng' tăng tạm thời." },
        { date: "2025-11-20", dir: "POSITIVE", title: `Cập nhật phần mềm khắc phục lỗi camera`,
          channel: "ThinkView", views: 540000,
          text: "Bản cập nhật giúp cải thiện chất lượng ảnh đêm, sentiment camera phục hồi." },
      ],
    };
  }
  PRODUCTS.forEach(p => { p.attribution = attribution(p); });

  // 9 comments split 3 positive / 3 negative / 3 neutral
  const COMMENTS = [
    { sentiment: "Tích cực", conf: 98, author: "Minh Trí", aspect: "Pin", text: "Pin trâu kinh khủng, dùng cả ngày livestream vẫn còn 30%. Quá ưng!" },
    { sentiment: "Tích cực", conf: 95, author: "Hải Yến", aspect: "Màn hình", text: "Màn hình sáng rực, ngoài nắng vẫn nhìn rõ, tần số quét mượt tay." },
    { sentiment: "Tích cực", conf: 93, author: "Quốc Bảo", aspect: "Thiết kế", text: "Cầm rất đầm tay, hoàn thiện cao cấp, màu mới nhìn ngoài đẹp hơn trên ảnh." },
    { sentiment: "Tiêu cực", conf: 96, author: "Thanh Tùng", aspect: "Hiệu năng", text: "Chơi game nặng tầm 20 phút là nóng lưng máy, hơi thất vọng ở mức giá này." },
    { sentiment: "Tiêu cực", conf: 92, author: "Lan Anh", aspect: "Giá bán", text: "Giá quá cao so với nâng cấp thực tế, phụ kiện đi kèm thì sơ sài." },
    { sentiment: "Tiêu cực", conf: 90, author: "Đức Huy", aspect: "Camera", text: "Chụp đêm vẫn bị nhiễu hạt và bệt chi tiết, chưa như quảng cáo." },
    { sentiment: "Trung lập", conf: 86, author: "Phương Thảo", aspect: "Thiết kế", text: "Thiết kế gần như y hệt đời trước, ai cần mới thì mua chứ không đột phá." },
    { sentiment: "Trung lập", conf: 83, author: "Gia Khang", aspect: "Hiệu năng", text: "Dùng văn phòng cơ bản thì ổn, không có gì để chê mà cũng chẳng có gì nổi bật." },
    { sentiment: "Trung lập", conf: 80, author: "Ngọc Mai", aspect: "Pin", text: "Pin đủ dùng trong ngày, sạc thì bình thường, tổng thể ở mức chấp nhận được." },
  ];

  const CATEGORIES = [
    { slug: "all", label: "Tất cả", mentions: 95910, change: 5.2 },
    { slug: "dien_thoai", label: "Điện thoại", mentions: 71300, change: 6.1 },
    { slug: "laptop", label: "Laptop", mentions: 13630, change: 3.4 },
    { slug: "tai_nghe", label: "Tai nghe", mentions: 12280, change: 8.0 },
  ];

  // ---------- ADMIN data ----------
  const CHANNELS = [
    { id: "UC_tinhte", name: "Tinh tế", handle: "@tinhte", subs: 1820000, active: true, scanned: true, videos: 412 },
    { id: "UC_vatvo", name: "Vật Vờ Studio", handle: "@realvatvostudio", subs: 2640000, active: true, scanned: true, videos: 588 },
    { id: "UC_thinkview", name: "ThinkView", handle: "@thinkview", subs: 1370000, active: true, scanned: true, videos: 347 },
    { id: "UC_duyluan", name: "Duy Luân Dễ Thương", handle: "@duyluandethuong", subs: 690000, active: true, scanned: false, videos: 221 },
    { id: "UC_tgdd", name: "Thế Giới Di Động", handle: "@tgddreview", subs: 1150000, active: true, scanned: true, videos: 503 },
    { id: "UC_cellphones", name: "CellphoneS", handle: "@CellphoneSOfficial", subs: 980000, active: false, scanned: true, videos: 466 },
    { id: "UC_gearvn", name: "GEARVN", handle: "@GEARVNOfficial", subs: 540000, active: true, scanned: false, videos: 158 },
    { id: "UC_taixaitech", name: "Tài Xài Tech", handle: "@TaiXaiTech", subs: 312000, active: true, scanned: true, videos: 134 },
  ];

  const KEYWORDS = [
    { id: "kw1", text: "iphone 17 pro max", cluster: "apple_phone", active: true, hits: 18420 },
    { id: "kw2", text: "galaxy s25 ultra", cluster: "samsung_phone", active: true, hits: 15970 },
    { id: "kw3", text: "xiaomi 15 pro", cluster: "xiaomi_phone", active: true, hits: 9240 },
    { id: "kw4", text: "macbook air m4", cluster: "apple_laptop", active: true, hits: 8420 },
    { id: "kw5", text: "rog zephyrus g16", cluster: "gaming_laptop", active: false, hits: 5210 },
    { id: "kw6", text: "sony wh-1000xm6", cluster: "headphone", active: true, hits: 4980 },
    { id: "kw7", text: "airpods pro 3", cluster: "headphone", active: true, hits: 7150 },
    { id: "kw8", text: "find x8 pro", cluster: "oppo_phone", active: true, hits: 6730 },
  ];

  const DAG_RUNS = [
    { dag: "youtube_daily_extraction_dag", run: "scheduled__2026-06-02T01:00", state: "success", start: "02/06 08:00", dur: 1284 },
    { dag: "nlp_inference_batch_dag", run: "scheduled__2026-06-02T03:00", state: "success", start: "02/06 10:02", dur: 2841 },
    { dag: "dbt_transform_dag", run: "scheduled__2026-06-02T04:30", state: "running", start: "02/06 11:30", dur: null },
    { dag: "analytics_ranking_dag", run: "scheduled__2026-06-02T05:00", state: "queued", start: null, dur: null },
    { dag: "youtube_daily_extraction_dag", run: "scheduled__2026-06-01T01:00", state: "success", start: "01/06 08:00", dur: 1190 },
    { dag: "nlp_inference_batch_dag", run: "scheduled__2026-06-01T03:00", state: "failed", start: "01/06 10:01", dur: 410 },
    { dag: "dbt_transform_dag", run: "scheduled__2026-06-01T04:30", state: "success", start: "01/06 11:30", dur: 936 },
  ];

  const DAG_TASKS = [
    { task: "discover_videos", state: "success", dur: 142, tries: 1 },
    { task: "download_metadata", state: "success", dur: 388, tries: 1 },
    { task: "extract_comments", state: "success", dur: 612, tries: 2 },
    { task: "dedup_and_stage", state: "running", dur: null, tries: 1 },
    { task: "load_to_bigquery", state: "queued", dur: null, tries: 0 },
  ];

  const OPS_SERIES = [42, 51, 47, 63, 58, 71, 66, 79, 84, 73, 91, 88, 95, 82, 97];
  const NLP_SERIES = [88, 90, 87, 92, 94, 91, 93, 95, 92, 96, 94, 97, 95, 96, 98];

  window.DATA = {
    ASPECTS, PRODUCTS, COMMENTS, CATEGORIES,
    CHANNELS, KEYWORDS, DAG_RUNS, DAG_TASKS, OPS_SERIES, NLP_SERIES,
    PIPELINE: {
      webserver: "healthy", scheduler: "healthy",
      quotaUsed: 7820, quotaLimit: 10000,
      videosToday: 184, commentsToday: 26410, productsTracked: 168,
      activeChannels: 14, activeKeywords: 31, nlpFallback: 2.3, lastBatch: "nlp_2026_06_02_03",
    },
    findProduct: (id) => PRODUCTS.find(p => p.product_id === id),
  };
})();
